from __future__ import annotations

from time import perf_counter
from typing import Any, Callable

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


class BackendExecutionError(RuntimeError):
    pass


def build_cqm(problem: SchedulingProblem):
    """Build an allocation-only CQM.

    The model deliberately contains no start-time, end-time, interval, or
    sequencing variables. Quantum-hybrid compute is permitted to choose only
    task-to-agent ownership.
    """
    try:
        import dimod
    except ImportError as exc:
        raise BackendUnavailable(
            "D-Wave Ocean is not installed. Install the quantum-hybrid extra with "
            "`python -m pip install 'agent-compute-router[quantum-hybrid]'`."
        ) from exc

    cqm = dimod.ConstrainedQuadraticModel()
    task_by_id = {task.id: task for task in problem.tasks}
    x: dict[tuple[str, str], Any] = {}

    for task in problem.tasks:
        task_vars = []
        for agent in task.eligible_agents:
            variable = dimod.Binary(f"x::{task.id}::{agent}")
            x[(task.id, agent)] = variable
            task_vars.append(variable)
        cqm.add_discrete(sum(task_vars), label=f"assign::{task.id}")

    total_duration = sum(task.duration for task in problem.tasks)
    max_load = dimod.Integer(
        "allocation::max_load",
        lower_bound=0,
        upper_bound=total_duration,
    )

    for agent in problem.agents:
        load = sum(
            task.duration * x[(task.id, agent)]
            for task in problem.tasks
            if (task.id, agent) in x
        )
        cqm.add_constraint(load <= max_load, label=f"load::{agent}")

    objective = primary_weight(problem) * max_load

    for left, right in dependency_pairs(problem):
        common = (
            set(task_by_id[left].eligible_agents)
            & set(task_by_id[right].eligible_agents)
        )
        same_agent = sum(x[(left, agent)] * x[(right, agent)] for agent in common)
        objective += HANDOFF_WEIGHT * (1 - same_agent)

    for left, right in file_conflict_pairs(problem):
        common = (
            set(task_by_id[left].eligible_agents)
            & set(task_by_id[right].eligible_agents)
        )
        same_agent = sum(x[(left, agent)] * x[(right, agent)] for agent in common)
        objective += FILE_SPLIT_WEIGHT * (1 - same_agent)

    cqm.set_objective(objective)
    return cqm


def solve(
    problem: SchedulingProblem,
    *,
    time_limit: float | None = None,
    sampler_factory: Callable[[], Any] | None = None,
) -> AllocationBackendResult:
    cqm = build_cqm(problem)

    if sampler_factory is None:
        try:
            from dwave.system import LeapHybridCQMSampler
        except ImportError as exc:
            raise BackendUnavailable(
                "D-Wave Ocean is not installed. Install the quantum-hybrid extra with "
                "`python -m pip install 'agent-compute-router[quantum-hybrid]'`."
            ) from exc
        sampler_factory = LeapHybridCQMSampler

    started = perf_counter()
    try:
        with sampler_factory() as sampler:
            minimum = float(sampler.min_time_limit(cqm))
            effective_limit = max(minimum, float(time_limit)) if time_limit else minimum
            sampleset = sampler.sample_cqm(
                cqm,
                time_limit=effective_limit,
                label="Agent Compute Router allocation",
            )
            sampleset.resolve()
            feasible = sampleset.filter(lambda row: row.is_feasible)
            if len(feasible) == 0:
                return AllocationBackendResult(
                    backend="dwave-leap-hybrid-cqm",
                    status="NO_FEASIBLE_SAMPLE",
                    allocation={},
                    runtime_ms=(perf_counter() - started) * 1000.0,
                    objective_value=None,
                    metrics={
                        "allocation_only": True,
                        "time_limit_seconds": effective_limit,
                        "cqm_variables": len(cqm.variables),
                        "cqm_constraints": len(cqm.constraints),
                    },
                )
            first = feasible.first
            sample = first.sample
            sampler_properties = getattr(sampler, "properties", {}) or {}
    except Exception as exc:
        raise BackendExecutionError(str(exc)) from exc

    allocation: dict[str, str] = {}
    for task in problem.tasks:
        selected = [
            agent
            for agent in task.eligible_agents
            if sample.get(f"x::{task.id}::{agent}", 0) > 0.5
        ]
        if len(selected) != 1:
            return AllocationBackendResult(
                backend="dwave-leap-hybrid-cqm",
                status="INVALID_SAMPLE",
                allocation={},
                runtime_ms=(perf_counter() - started) * 1000.0,
                objective_value=None,
                metrics={"allocation_only": True},
                notes=(f"task {task.id!r} did not have exactly one selected agent",),
            )
        allocation[task.id] = selected[0]

    score = score_allocation(problem, allocation)
    metrics: dict[str, int | float | str | bool] = {
        "allocation_only": True,
        "time_limit_seconds": effective_limit,
        "cqm_variables": len(cqm.variables),
        "cqm_constraints": len(cqm.constraints),
        **score,
    }
    solver_name = sampler_properties.get("category")
    if isinstance(solver_name, (str, int, float, bool)):
        metrics["solver_category"] = solver_name

    info = getattr(sampleset, "info", {}) or {}
    for key in ("run_time", "qpu_access_time", "charge_time"):
        value = info.get(key)
        if isinstance(value, (str, int, float, bool)):
            metrics[f"provider_{key}"] = value

    return AllocationBackendResult(
        backend="dwave-leap-hybrid-cqm",
        status="FEASIBLE",
        allocation=allocation,
        runtime_ms=(perf_counter() - started) * 1000.0,
        objective_value=score["weighted_score"],
        metrics=metrics,
    )
