from __future__ import annotations

from time import perf_counter

from .backends.cp_sat import BackendUnavailable, solve as solve_cp_sat
from .backends.cp_sat_allocation import solve as solve_classical_allocation
from .backends.dwave_hybrid import BackendExecutionError, solve as solve_dwave_allocation
from .classifier import classify
from .ir import SchedulingProblem
from .models import ComputeReceipt, ComputeStage, RoutingDecision
from .verification import verify_allocation, verify_schedule


def assess(problem: str) -> RoutingDecision:
    return classify(problem)


def _schedule_fixed(problem: SchedulingProblem, allocation: dict[str, str], *, max_seconds: float):
    result = solve_cp_sat(problem, max_seconds=max_seconds, fixed_allocation=allocation)
    verified = None
    violations: tuple[str, ...] = ()
    if result.assignments:
        verified, violations = verify_schedule(problem, result.assignments)
    return result, verified, violations


def solve_schedule(
    problem: SchedulingProblem,
    *,
    max_seconds: float = 10.0,
    allocator: str = "hybrid",
    allow_remote: bool = False,
    hybrid_time_limit: float | None = None,
) -> ComputeReceipt:
    """Solve a sprint with an allocation-only hybrid boundary.

    A classical allocation baseline is always established. If remote hybrid
    execution is explicitly authorized, D-Wave may propose task-to-agent
    ownership only. Timing, precedence, file-lock sequencing, and final
    verification always remain classical.
    """
    if allocator not in {"classical", "hybrid"}:
        raise ValueError("allocator must be 'classical' or 'hybrid'")

    route = RoutingDecision(
        classification="constrained_scheduling",
        recommended_backend=(
            "hybrid-allocation+cp-sat-sequencing"
            if allocator == "hybrid"
            else "cp-sat-allocation+cp-sat-sequencing"
        ),
        quantum_escalation="REVIEW" if allocator == "hybrid" else "NO",
        reason=(
            "Task-to-agent allocation is isolated as the only quantum-hybrid candidate; "
            "sequencing and verification remain classical."
            if allocator == "hybrid"
            else "Allocation and sequencing are both kept classical with CP-SAT."
        ),
        alternatives=("all-classical-cp-sat",),
    )

    stages: list[ComputeStage] = []
    notes: list[str] = []
    started = perf_counter()

    try:
        baseline = solve_classical_allocation(problem, max_seconds=max_seconds)
    except BackendUnavailable as exc:
        return ComputeReceipt(
            schema_version="2",
            problem_type="constrained_scheduling",
            problem_sha256=problem.fingerprint(),
            route=route,
            backend="unavailable",
            solver_status="BACKEND_UNAVAILABLE",
            runtime_ms=None,
            objective_name=problem.objective,
            objective_value=None,
            verified=None,
            violations=(),
            solution={},
            metrics={},
            notes=(str(exc),),
        )

    baseline_ok, baseline_violations = verify_allocation(problem, baseline.allocation)
    stages.append(
        ComputeStage(
            name="classical_allocation_baseline",
            backend=baseline.backend,
            status=baseline.status,
            runtime_ms=baseline.runtime_ms,
            objective_name="allocation_weighted_score",
            objective_value=baseline.objective_value,
            verified=baseline_ok,
            violations=baseline_violations,
            metrics=baseline.metrics,
            notes=baseline.notes,
        )
    )
    if not baseline_ok:
        return ComputeReceipt(
            schema_version="2",
            problem_type="constrained_scheduling",
            problem_sha256=problem.fingerprint(),
            route=route,
            backend=baseline.backend,
            solver_status="INVALID_CLASSICAL_ALLOCATION",
            runtime_ms=(perf_counter() - started) * 1000.0,
            objective_name=problem.objective,
            objective_value=None,
            verified=False,
            violations=baseline_violations,
            solution={},
            metrics={},
            stages=tuple(stages),
        )

    baseline_schedule, baseline_schedule_ok, baseline_schedule_violations = _schedule_fixed(
        problem, baseline.allocation, max_seconds=max_seconds
    )
    stages.append(
        ComputeStage(
            name="classical_baseline_sequencing",
            backend="ortools-cp-sat",
            status=baseline_schedule.status,
            runtime_ms=(
                float(baseline_schedule.metrics["wall_time_seconds"]) * 1000.0
                if isinstance(baseline_schedule.metrics.get("wall_time_seconds"), (int, float))
                else None
            ),
            objective_name=problem.objective,
            objective_value=baseline_schedule.objective_value,
            verified=baseline_schedule_ok,
            violations=baseline_schedule_violations,
            metrics=baseline_schedule.metrics,
        )
    )

    selected_backend = baseline.backend
    selected_schedule = baseline_schedule
    selected_ok = baseline_schedule_ok
    selected_violations = baseline_schedule_violations
    selected_allocation_score = baseline.objective_value

    if allocator == "hybrid":
        if not allow_remote:
            stages.append(
                ComputeStage(
                    name="quantum_hybrid_allocation",
                    backend="dwave-leap-hybrid-cqm",
                    status="REMOTE_NOT_AUTHORIZED",
                    runtime_ms=None,
                    objective_name="allocation_weighted_score",
                    objective_value=None,
                    verified=None,
                    notes=(
                        "Remote compute was not attempted. Re-run with explicit remote authorization to benchmark the hybrid allocator.",
                    ),
                )
            )
        else:
            try:
                hybrid = solve_dwave_allocation(problem, time_limit=hybrid_time_limit)
                hybrid_ok, hybrid_violations = verify_allocation(problem, hybrid.allocation)
                stages.append(
                    ComputeStage(
                        name="quantum_hybrid_allocation",
                        backend=hybrid.backend,
                        status=hybrid.status,
                        runtime_ms=hybrid.runtime_ms,
                        objective_name="allocation_weighted_score",
                        objective_value=hybrid.objective_value,
                        verified=hybrid_ok,
                        violations=hybrid_violations,
                        metrics=hybrid.metrics,
                        notes=hybrid.notes,
                    )
                )
                if hybrid_ok:
                    hybrid_schedule, hybrid_schedule_ok, hybrid_schedule_violations = _schedule_fixed(
                        problem, hybrid.allocation, max_seconds=max_seconds
                    )
                    stages.append(
                        ComputeStage(
                            name="hybrid_candidate_classical_sequencing",
                            backend="ortools-cp-sat",
                            status=hybrid_schedule.status,
                            runtime_ms=(
                                float(hybrid_schedule.metrics["wall_time_seconds"]) * 1000.0
                                if isinstance(hybrid_schedule.metrics.get("wall_time_seconds"), (int, float))
                                else None
                            ),
                            objective_name=problem.objective,
                            objective_value=hybrid_schedule.objective_value,
                            verified=hybrid_schedule_ok,
                            violations=hybrid_schedule_violations,
                            metrics=hybrid_schedule.metrics,
                        )
                    )
                    baseline_key = (
                        baseline_schedule.objective_value
                        if baseline_schedule_ok and baseline_schedule.objective_value is not None
                        else float("inf"),
                        baseline.objective_value if baseline.objective_value is not None else float("inf"),
                    )
                    hybrid_key = (
                        hybrid_schedule.objective_value
                        if hybrid_schedule_ok and hybrid_schedule.objective_value is not None
                        else float("inf"),
                        hybrid.objective_value if hybrid.objective_value is not None else float("inf"),
                    )
                    if hybrid_key < baseline_key:
                        selected_backend = hybrid.backend
                        selected_schedule = hybrid_schedule
                        selected_ok = hybrid_schedule_ok
                        selected_violations = hybrid_schedule_violations
                        selected_allocation_score = hybrid.objective_value
                        notes.append(
                            "Quantum-hybrid allocation was selected because its verified classical schedule beat the classical baseline."
                        )
                    else:
                        notes.append(
                            "Quantum-hybrid allocation did not beat the verified classical baseline, so ACR retained the classical allocation."
                        )
            except (BackendUnavailable, BackendExecutionError) as exc:
                stages.append(
                    ComputeStage(
                        name="quantum_hybrid_allocation",
                        backend="dwave-leap-hybrid-cqm",
                        status="BACKEND_UNAVAILABLE",
                        runtime_ms=None,
                        objective_name="allocation_weighted_score",
                        objective_value=None,
                        verified=None,
                        notes=(str(exc),),
                    )
                )
                notes.append(
                    "Quantum-hybrid allocation was unavailable; the verified classical baseline was retained."
                )

    metrics: dict[str, int | float | str | bool] = {
        "selected_allocation_backend": selected_backend,
        "selected_allocation_score": selected_allocation_score if selected_allocation_score is not None else -1,
        "classical_baseline_makespan": baseline_schedule.objective_value if baseline_schedule.objective_value is not None else -1,
        "quantum_boundary": "task-to-agent-allocation-only",
        "sequencing_backend": "ortools-cp-sat",
        "final_verifier": "classical-independent",
    }

    return ComputeReceipt(
        schema_version="2",
        problem_type="constrained_scheduling",
        problem_sha256=problem.fingerprint(),
        route=route,
        backend=f"{selected_backend}->ortools-cp-sat",
        solver_status=selected_schedule.status,
        runtime_ms=(perf_counter() - started) * 1000.0,
        objective_name=problem.objective,
        objective_value=selected_schedule.objective_value,
        verified=selected_ok,
        violations=selected_violations,
        solution=selected_schedule.assignments,
        metrics=metrics,
        notes=tuple(notes),
        stages=tuple(stages),
    )
