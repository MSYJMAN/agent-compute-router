from __future__ import annotations

from ..ir import SchedulingProblem
from ..models import BackendResult, TaskAssignment


class BackendUnavailable(RuntimeError):
    pass


def solve(
    problem: SchedulingProblem,
    *,
    max_seconds: float = 10.0,
    fixed_allocation: dict[str, str] | None = None,
) -> BackendResult:
    if max_seconds <= 0:
        raise ValueError("max_seconds must be greater than zero")

    try:
        from ortools.sat.python import cp_model
    except ImportError as exc:
        raise BackendUnavailable(
            "OR-Tools is not installed. Install the CP-SAT extra with "
            "`python -m pip install 'agent-compute-router[cp-sat]'`."
        ) from exc

    model = cp_model.CpModel()
    horizon = sum(task.duration for task in problem.tasks)
    starts = {}
    ends = {}
    task_intervals = {}
    assignment_literals = {}
    agent_intervals = {agent: [] for agent in problem.agents}

    for task in problem.tasks:
        start = model.new_int_var(0, horizon, f"start_{task.id}")
        end = model.new_int_var(0, horizon, f"end_{task.id}")
        model.add(end == start + task.duration)
        starts[task.id] = start
        ends[task.id] = end
        task_interval = model.new_interval_var(start, task.duration, end, f"task_{task.id}")
        task_intervals[task.id] = task_interval

        if fixed_allocation is not None:
            agent = fixed_allocation.get(task.id)
            if agent not in task.eligible_agents:
                raise ValueError(f"fixed allocation for task {task.id!r} is missing or ineligible")
            agent_intervals[agent].append(task_interval)
        else:
            literals = []
            for agent in task.eligible_agents:
                assigned = model.new_bool_var(f"assign_{task.id}_{agent}")
                interval = model.new_optional_interval_var(
                    start, task.duration, end, assigned, f"agent_{agent}_{task.id}"
                )
                assignment_literals[(task.id, agent)] = assigned
                agent_intervals[agent].append(interval)
                literals.append(assigned)
            model.add_exactly_one(literals)

    for task in problem.tasks:
        for dependency in task.depends_on:
            model.add(starts[task.id] >= ends[dependency])

    for intervals in agent_intervals.values():
        if len(intervals) > 1:
            model.add_no_overlap(intervals)

    file_intervals: dict[str, list] = {}
    for task in problem.tasks:
        for path in task.files:
            file_intervals.setdefault(path, []).append(task_intervals[task.id])
    for intervals in file_intervals.values():
        if len(intervals) > 1:
            model.add_no_overlap(intervals)

    makespan = model.new_int_var(0, horizon, "makespan")
    model.add_max_equality(makespan, list(ends.values()))
    model.minimize(makespan)

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = float(max_seconds)
    solver.parameters.num_search_workers = 1
    solver.parameters.random_seed = 0

    status = solver.solve(model)
    status_name = solver.status_name(status)
    metrics: dict[str, int | float | str | bool] = {
        "wall_time_seconds": solver.wall_time,
        "branches": solver.num_branches,
        "conflicts": solver.num_conflicts,
        "search_workers": 1,
        "random_seed": 0,
        "fixed_allocation": fixed_allocation is not None,
    }

    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return BackendResult(status=status_name, assignments={}, objective_value=None, metrics=metrics)

    assignments: dict[str, TaskAssignment] = {}
    for task in problem.tasks:
        if fixed_allocation is not None:
            selected_agent = fixed_allocation[task.id]
        else:
            selected_agent = next(
                agent for agent in task.eligible_agents
                if solver.value(assignment_literals[(task.id, agent)]) == 1
            )
        assignments[task.id] = TaskAssignment(
            agent=selected_agent,
            start=int(solver.value(starts[task.id])),
            end=int(solver.value(ends[task.id])),
        )

    return BackendResult(
        status=status_name,
        assignments=assignments,
        objective_value=int(solver.value(makespan)),
        metrics=metrics,
    )
