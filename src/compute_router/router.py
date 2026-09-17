from __future__ import annotations

from .backends.cp_sat import BackendUnavailable, solve as solve_cp_sat
from .classifier import classify
from .ir import SchedulingProblem
from .models import ComputeReceipt, RoutingDecision
from .verification import verify_schedule


def assess(problem: str) -> RoutingDecision:
    """Return an inspectable routing recommendation for a problem description."""
    return classify(problem)


def solve_schedule(
    problem: SchedulingProblem,
    *,
    max_seconds: float = 10.0,
) -> ComputeReceipt:
    """Solve and independently verify a structured scheduling problem."""
    route = RoutingDecision(
        classification="constrained_scheduling",
        recommended_backend="cp-sat",
        quantum_escalation="NO",
        reason=(
            "The structured problem contains discrete task assignment, precedence, "
            "resource, and file-conflict constraints that map directly to CP-SAT."
        ),
        alternatives=("milp", "heuristic-planner"),
    )

    try:
        backend_result = solve_cp_sat(problem, max_seconds=max_seconds)
    except BackendUnavailable as exc:
        return ComputeReceipt(
            schema_version="1",
            problem_type="constrained_scheduling",
            problem_sha256=problem.fingerprint(),
            route=route,
            backend="ortools-cp-sat",
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

    verified = None
    violations: tuple[str, ...] = ()
    if backend_result.assignments:
        verified, violations = verify_schedule(problem, backend_result.assignments)

    wall_time = backend_result.metrics.get("wall_time_seconds")
    runtime_ms = float(wall_time) * 1000.0 if isinstance(wall_time, (int, float)) else None

    return ComputeReceipt(
        schema_version="1",
        problem_type="constrained_scheduling",
        problem_sha256=problem.fingerprint(),
        route=route,
        backend="ortools-cp-sat",
        solver_status=backend_result.status,
        runtime_ms=runtime_ms,
        objective_name=problem.objective,
        objective_value=backend_result.objective_value,
        verified=verified,
        violations=violations,
        solution=backend_result.assignments,
        metrics=backend_result.metrics,
        notes=(),
    )
