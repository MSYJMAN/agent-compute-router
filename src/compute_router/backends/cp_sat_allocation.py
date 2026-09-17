from __future__ import annotations

from time import perf_counter

from ..allocation import (
    FILE_SPLIT_WEIGHT,
    HANDOFF_WEIGHT,
    dependency_pairs,
    file_conflict_pairs,
    primary_weight,
    score_allocation,
)
from ..ir import SchedulingProblem
from ..models import AllocationBackendResult
from .cp_sat import BackendUnavailable


def solve(
    problem: SchedulingProblem,
    *,
    max_seconds: float = 10.0,
) -> AllocationBackendResult:
    if max_seconds <= 0:
        raise ValueError("max_seconds must be greater than zero")

    try:
        from ortools.sat.python import cp_model
    except ImportError as exc:
        raise BackendUnavailable(
            "OR-Tools is not installed. Install the CP-SAT extra with "
            "`python -m pip install 'agent-compute-router[cp-sat]'`."
        ) from exc

    started = perf_counter()
    model = cp_model.CpModel()
    task_by_id = {task.id: task for task in problem.tasks}
    x = {}

    for task in problem.tasks:
        literals = []
        for agent in task.eligible_agents:
            literal = model.new_bool_var(f"alloc_{task.id}_{agent}")
            x[(task.id, agent)] = literal
            literals.append(literal)
        model.add_exactly_one(literals)

    total_duration = sum(task.duration for task in problem.tasks)
    max_load = model.new_int_var(0, total_duration, "max_load")

    for agent in problem.agents:
        load_terms = [
            task.duration * x[(task.id, agent)]
            for task in problem.tasks
            if (task.id, agent) in x
        ]
        model.add(sum(load_terms) <= max_load)

    secondary_terms = []
    constant_penalty = 0

    def add_split_penalty(left_id: str, right_id: str, weight: int, prefix: str) -> None:
        nonlocal constant_penalty
        common_agents = sorted(
            set(task_by_id[left_id].eligible_agents)
            & set(task_by_id[right_id].eligible_agents)
        )
        if not common_agents:
            constant_penalty += weight
            return

        same_literals = []
        for agent in common_agents:
            both = model.new_bool_var(f"{prefix}_same_{left_id}_{right_id}_{agent}")
            model.add(both <= x[(left_id, agent)])
            model.add(both <= x[(right_id, agent)])
            model.add(both >= x[(left_id, agent)] + x[(right_id, agent)] - 1)
            same_literals.append(both)

        split = model.new_bool_var(f"{prefix}_split_{left_id}_{right_id}")
        model.add(split + sum(same_literals) == 1)
        secondary_terms.append(weight * split)

    for left, right in dependency_pairs(problem):
        add_split_penalty(left, right, HANDOFF_WEIGHT, "dep")

    for left, right in file_conflict_pairs(problem):
        add_split_penalty(left, right, FILE_SPLIT_WEIGHT, "file")

    model.minimize(
        primary_weight(problem) * max_load
        + sum(secondary_terms)
        + constant_penalty
    )

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = float(max_seconds)
    solver.parameters.num_search_workers = 1
    solver.parameters.random_seed = 0
    status = solver.solve(model)
    status_name = solver.status_name(status)
    runtime_ms = (perf_counter() - started) * 1000.0

    metrics: dict[str, int | float | str | bool] = {
        "wall_time_seconds": solver.wall_time,
        "branches": solver.num_branches,
        "conflicts": solver.num_conflicts,
        "search_workers": 1,
        "random_seed": 0,
        "allocation_only": True,
    }

    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return AllocationBackendResult(
            backend="ortools-cp-sat-allocation",
            status=status_name,
            allocation={},
            runtime_ms=runtime_ms,
            objective_value=None,
            metrics=metrics,
        )

    allocation = {}
    for task in problem.tasks:
        selected = next(
            agent
            for agent in task.eligible_agents
            if solver.value(x[(task.id, agent)]) == 1
        )
        allocation[task.id] = selected

    score = score_allocation(problem, allocation)
    metrics.update(score)
    return AllocationBackendResult(
        backend="ortools-cp-sat-allocation",
        status=status_name,
        allocation=allocation,
        runtime_ms=runtime_ms,
        objective_value=score["weighted_score"],
        metrics=metrics,
    )
