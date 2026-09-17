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

    Mixed binary/integer expressions are built explicitly as QuadraticModel
    instances. This avoids relying on symbolic arithmetic between Binary
    variables (represented by BQMs) and Integer variables (represented by QMs),
    which current dimod versions do not support for comparisons.
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
    variable_labels: dict[tuple[str, str], str] = {}

    # Allocation variables only: x::<task>::<agent>.
    # Each task must be assigned to exactly one eligible agent.
    for task in problem.tasks:
        labels: list[str] = []
        for agent in task.eligible_agents:
            label = f"x::{task.id}::{agent}"
            cqm.add_variable("BINARY", label)
            variable_labels[(task.id, agent)] = label
            labels.append(label)
        cqm.add_discrete(labels, label=f"assign::{task.id}")

    total_duration = sum(task.duration for task in problem.tasks)
    max_load_label = "allocation::max_load"
    cqm.add_variable(
        "INTEGER",
        max_load_label,
        lower_bound=0,
        upper_bound=total_duration,
    )

    # For every agent: sum(duration_i * x_i,a) <= max_load.
    # Build each mixed binary/integer constraint as a QuadraticModel explicitly.
    for agent in problem.agents:
        lhs = dimod.QuadraticModel()
        lhs.add_variable(
            "INTEGER",
            max_load_label,
            lower_bound=0,
            upper_bound=total_duration,
        )
        lhs.add_linear(max_load_label, -1)

        for task in problem.tasks:
            label = variable_labels.get((task.id, agent))
            if label is None:
                continue
            lhs.add_variable("BINARY", label)
            lhs.add_linear(label, task.duration)

        cqm.add_constraint_from_model(
            lhs,
            sense="<=",
            rhs=0,
            label=f"load::{agent}",
            copy=False,
        )

    # Build the objective explicitly as one mixed-type QuadraticModel:
    #   primary_weight * max_load
    #   + handoff penalties
    #   + shared-file ownership-split penalties
    objective = dimod.QuadraticModel()
    objective.add_variable(
        "INTEGER",
        max_load_label,
        lower_bound=0,
        upper_bound=total_duration,
    )
    objective.add_linear(max_load_label, primary_weight(problem))

    for label in variable_labels.values():
        objective.add_variable("BINARY", label)

    for left, right in dependency_pairs(problem):
        objective.add_offset(HANDOFF_WEIGHT)
        common = (
            set(task_by_id[left].eligible_agents)
            & set(task_by_id[right].eligible_agents)
        )
        for agent in common:
            objective.add_quadratic(
                variable_labels[(left, agent)],
                variable_labels[(right, agent)],
                -HANDOFF_WEIGHT,
            )

    for left, right in file_conflict_pairs(problem):
        objective.add_offset(FILE_SPLIT_WEIGHT)
        common = (
            set(task_by_id[left].eligible_agents)
            & set(task_by_id[right].eligible_agents)
        )
        for agent in common:
            objective.add_quadratic(
                variable_labels[(left, agent)],
                variable_labels[(right, agent)],
                -FILE_SPLIT_WEIGHT,
            )

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
