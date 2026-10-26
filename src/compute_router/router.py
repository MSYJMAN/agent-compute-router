from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter

from .allocation import score_allocation
from .backends.cp_sat import BackendUnavailable, solve as solve_cp_sat
from .backends.cp_sat_allocation import solve as solve_classical_allocation
from .backends.dwave_hybrid import BackendExecutionError, solve as solve_dwave_allocation
from .classifier import classify
from .ir import SchedulingProblem
from .models import BackendResult, ComputeReceipt, ComputeStage, RoutingDecision
from .provider import (
    AUTHENTICATION_FAILED,
    BACKEND_UNAVAILABLE,
    CREDENTIALS_MISSING,
    EXECUTION_ERROR,
    FEASIBLE,
    NETWORK_FAILURE,
    OPTIMAL,
    PROVIDER_ACCESS_REQUIRED,
    PROVIDER_UNAVAILABLE,
    REMOTE_NOT_AUTHORIZED,
    sanitize_provider_message,
)
from .verification import verify_allocation, verify_schedule

CLASSICAL_DECOMPOSED = "classical_decomposed"
CLASSICAL_JOINT = "classical_joint"
HYBRID = "hybrid"
TIE = "tie"
UNAVAILABLE = "unavailable"

# The production decision is ordered: lowest verified makespan, then lowest
# allocation score (better balance and fewer handoffs at equal speed), then this
# fixed path order. The last level exists so a full tie resolves to the more
# conservative path instead of depending on solver iteration order.
_PRODUCTION_PRIORITY = (CLASSICAL_JOINT, CLASSICAL_DECOMPOSED, HYBRID)

# Provider states meaning the hybrid allocator never actually returned a
# candidate. These must not be reported as the hybrid losing a comparison.
_NO_HYBRID_RESPONSE = frozenset(
    {
        REMOTE_NOT_AUTHORIZED,
        BACKEND_UNAVAILABLE,
        CREDENTIALS_MISSING,
        AUTHENTICATION_FAILED,
        PROVIDER_ACCESS_REQUIRED,
        PROVIDER_UNAVAILABLE,
        NETWORK_FAILURE,
        EXECUTION_ERROR,
    }
)

_SOLVED = frozenset({OPTIMAL, FEASIBLE})


@dataclass(frozen=True)
class _Path:
    """One end-to-end candidate: an allocation plus its verified schedule."""

    name: str
    backend: str
    schedule: BackendResult | None
    verified: bool
    allocation_score: int | float | None
    violations: tuple[str, ...] = ()

    @property
    def makespan(self) -> int | None:
        if self.schedule is None or not self.verified:
            return None
        return self.schedule.objective_value

    @property
    def eligible(self) -> bool:
        return self.makespan is not None

    def sort_key(self) -> tuple[float, float, int]:
        makespan = self.makespan
        return (
            float(makespan) if makespan is not None else float("inf"),
            float(self.allocation_score) if self.allocation_score is not None else float("inf"),
            _PRODUCTION_PRIORITY.index(self.name),
        )


def assess(problem: str) -> RoutingDecision:
    return classify(problem)


def _local_allocation_score(
    problem: SchedulingProblem, allocation: dict[str, str]
) -> int | None:
    """Score an allocation with ACR's own objective function.

    Selection never uses a backend's self-reported objective value. The score is
    a deterministic function of the allocation, so recomputing it locally costs
    nothing and stops a backend from winning the comparison by reporting a
    number that its own allocation does not support.
    """
    if not allocation:
        return None
    return score_allocation(problem, allocation)["weighted_score"]


def _implied_allocation_score(
    problem: SchedulingProblem, schedule: BackendResult
) -> int | None:
    """Score the allocation implied by a joint schedule on the shared objective."""
    allocation = {
        task_id: assignment.agent for task_id, assignment in schedule.assignments.items()
    }
    return _local_allocation_score(problem, allocation)


def _runtime_ms(result: BackendResult) -> float | None:
    seconds = result.metrics.get("wall_time_seconds")
    if isinstance(seconds, (int, float)):
        return float(seconds) * 1000.0
    return None


def _schedule_fixed(
    problem: SchedulingProblem,
    allocation: dict[str, str],
    *,
    max_seconds: float,
) -> tuple[BackendResult, bool, tuple[str, ...]]:
    result = solve_cp_sat(problem, max_seconds=max_seconds, fixed_allocation=allocation)
    if not result.assignments:
        return result, False, ()
    verified, violations = verify_schedule(problem, result.assignments)
    return result, verified, violations


def _sequencing_stage(
    name: str,
    result: BackendResult,
    verified: bool,
    violations: tuple[str, ...],
    objective_name: str,
) -> ComputeStage:
    return ComputeStage(
        name=name,
        backend="ortools-cp-sat",
        status=result.status,
        runtime_ms=_runtime_ms(result),
        objective_name=objective_name,
        objective_value=result.objective_value,
        verified=verified,
        violations=violations,
        metrics=result.metrics,
    )


def _unavailable_receipt(
    problem: SchedulingProblem,
    route: RoutingDecision,
    message: str,
) -> ComputeReceipt:
    return ComputeReceipt(
        schema_version="2",
        problem_type="constrained_scheduling",
        problem_sha256=problem.fingerprint(),
        route=route,
        backend="unavailable",
        solver_status=BACKEND_UNAVAILABLE,
        runtime_ms=None,
        objective_name=problem.objective,
        objective_value=None,
        verified=None,
        violations=(),
        solution={},
        metrics={},
        notes=(message,),
        research_winner=UNAVAILABLE,
        production_winner=UNAVAILABLE,
    )


def _resolve_research_winner(
    decomposed: _Path,
    hybrid: _Path | None,
    hybrid_status: str | None,
) -> str:
    """Decide the fair allocator-vs-allocator comparison.

    Only the two decomposed allocators compete here: both hand a fixed
    ownership map to the identical classical sequencer, so the comparison
    isolates allocation quality. The joint solver is deliberately excluded
    because it is a different method class, not a different allocator.
    """
    if hybrid is None or hybrid_status is None or hybrid_status in _NO_HYBRID_RESPONSE:
        return UNAVAILABLE
    if not hybrid.eligible:
        return CLASSICAL_DECOMPOSED
    if not decomposed.eligible:
        return HYBRID
    if hybrid.sort_key()[:2] < decomposed.sort_key()[:2]:
        return HYBRID
    if decomposed.sort_key()[:2] < hybrid.sort_key()[:2]:
        return CLASSICAL_DECOMPOSED
    return TIE


def solve_schedule(
    problem: SchedulingProblem,
    *,
    max_seconds: float = 10.0,
    allocator: str = "classical",
    allow_remote: bool = False,
    hybrid_time_limit: float | None = None,
) -> ComputeReceipt:
    """Solve a sprint across three paths and emit a Compute Receipt.

    Three paths are evaluated so neither baseline can be a strawman:

    * ``classical_decomposed`` — CP-SAT allocation, then CP-SAT sequencing.
    * ``classical_joint`` — one CP-SAT model solving allocation and timing
      together. This is the strongest credible classical method.
    * ``hybrid`` — a D-Wave CQM allocation candidate, sequenced by the same
      classical sequencer as the decomposed path. Only ever runs when both
      ``allocator='hybrid'`` and ``allow_remote=True``.

    Quantum-hybrid compute may choose task-to-agent ownership only. Timing,
    precedence, file-lock sequencing, and final verification stay classical.
    """
    if allocator not in {"classical", "hybrid"}:
        raise ValueError("allocator must be 'classical' or 'hybrid'")

    hybrid_requested = allocator == "hybrid"
    route = RoutingDecision(
        classification="constrained_scheduling",
        recommended_backend=(
            "hybrid-allocation+cp-sat-sequencing"
            if hybrid_requested
            else "cp-sat-allocation+cp-sat-sequencing"
        ),
        quantum_escalation="REVIEW" if hybrid_requested else "NO",
        reason=(
            "Task-to-agent allocation is isolated as the only quantum-hybrid candidate; "
            "sequencing and verification remain classical."
            if hybrid_requested
            else "Allocation and sequencing are both kept classical with CP-SAT."
        ),
        alternatives=("all-classical-cp-sat",),
    )

    stages: list[ComputeStage] = []
    notes: list[str] = []
    started = perf_counter()

    try:
        decomposed_allocation = solve_classical_allocation(problem, max_seconds=max_seconds)
    except BackendUnavailable as exc:
        return _unavailable_receipt(problem, route, str(exc))

    allocation_ok, allocation_violations = verify_allocation(
        problem, decomposed_allocation.allocation
    )
    stages.append(
        ComputeStage(
            name="classical_decomposed_allocation",
            backend=decomposed_allocation.backend,
            status=decomposed_allocation.status,
            runtime_ms=decomposed_allocation.runtime_ms,
            objective_name="allocation_weighted_score",
            objective_value=decomposed_allocation.objective_value,
            verified=allocation_ok,
            violations=allocation_violations,
            metrics=decomposed_allocation.metrics,
            notes=decomposed_allocation.notes,
        )
    )
    if not allocation_ok:
        return ComputeReceipt(
            schema_version="2",
            problem_type="constrained_scheduling",
            problem_sha256=problem.fingerprint(),
            route=route,
            backend=decomposed_allocation.backend,
            solver_status="INVALID_CLASSICAL_ALLOCATION",
            runtime_ms=(perf_counter() - started) * 1000.0,
            objective_name=problem.objective,
            objective_value=None,
            verified=False,
            violations=allocation_violations,
            solution={},
            metrics={},
            stages=tuple(stages),
            research_winner=UNAVAILABLE,
            production_winner=UNAVAILABLE,
        )

    decomposed_schedule, decomposed_ok, decomposed_violations = _schedule_fixed(
        problem, decomposed_allocation.allocation, max_seconds=max_seconds
    )
    stages.append(
        _sequencing_stage(
            "classical_decomposed_sequencing",
            decomposed_schedule,
            decomposed_ok,
            decomposed_violations,
            problem.objective,
        )
    )
    decomposed_path = _Path(
        name=CLASSICAL_DECOMPOSED,
        backend=f"{decomposed_allocation.backend}->ortools-cp-sat",
        schedule=decomposed_schedule,
        verified=decomposed_ok,
        allocation_score=_local_allocation_score(problem, decomposed_allocation.allocation),
        violations=decomposed_violations,
    )

    # The strongest classical baseline: allocation and timing in one model.
    joint_schedule = solve_cp_sat(problem, max_seconds=max_seconds)
    joint_ok = False
    joint_violations: tuple[str, ...] = ()
    joint_score: int | float | None = None
    if joint_schedule.assignments:
        joint_ok, joint_violations = verify_schedule(problem, joint_schedule.assignments)
        joint_score = _implied_allocation_score(problem, joint_schedule)
    stages.append(
        ComputeStage(
            name="classical_joint_gold",
            backend="ortools-cp-sat-joint",
            status=joint_schedule.status,
            runtime_ms=_runtime_ms(joint_schedule),
            objective_name=problem.objective,
            objective_value=joint_schedule.objective_value,
            verified=joint_ok,
            violations=joint_violations,
            metrics=joint_schedule.metrics,
            notes=(
                "Joint allocation+sequencing CP-SAT model. Strongest credible classical "
                "baseline; excluded from the fair allocator-vs-allocator comparison.",
            ),
        )
    )
    joint_path = _Path(
        name=CLASSICAL_JOINT,
        backend="ortools-cp-sat-joint",
        schedule=joint_schedule,
        verified=joint_ok,
        allocation_score=joint_score,
        violations=joint_violations,
    )

    hybrid_path: _Path | None = None
    hybrid_status: str | None = None

    if hybrid_requested:
        if not allow_remote:
            hybrid_status = REMOTE_NOT_AUTHORIZED
            stages.append(
                ComputeStage(
                    name="quantum_hybrid_allocation",
                    backend="dwave-leap-hybrid-cqm",
                    status=REMOTE_NOT_AUTHORIZED,
                    runtime_ms=None,
                    objective_name="allocation_weighted_score",
                    objective_value=None,
                    verified=None,
                    notes=(
                        "Remote compute was not attempted. Re-run with explicit remote "
                        "authorization to benchmark the hybrid allocator.",
                    ),
                )
            )
        else:
            try:
                hybrid = solve_dwave_allocation(
                    problem,
                    time_limit=hybrid_time_limit,
                    allow_remote=True,
                )
                hybrid_status = hybrid.status
                hybrid_allocation_ok, hybrid_allocation_violations = verify_allocation(
                    problem, hybrid.allocation
                )
                hybrid_score = (
                    _local_allocation_score(problem, hybrid.allocation)
                    if hybrid_allocation_ok
                    else None
                )
                hybrid_notes = list(hybrid.notes)
                if (
                    hybrid_score is not None
                    and hybrid.objective_value is not None
                    and hybrid.objective_value != hybrid_score
                ):
                    hybrid_notes.append(
                        "Backend-reported allocation score "
                        f"{hybrid.objective_value} disagreed with the locally recomputed "
                        f"score {hybrid_score}; the local score was used for selection."
                    )
                stages.append(
                    ComputeStage(
                        name="quantum_hybrid_allocation",
                        backend=hybrid.backend,
                        status=hybrid.status,
                        runtime_ms=hybrid.runtime_ms,
                        objective_name="allocation_weighted_score",
                        objective_value=hybrid_score,
                        verified=hybrid_allocation_ok,
                        violations=hybrid_allocation_violations,
                        metrics=hybrid.metrics,
                        notes=tuple(hybrid_notes),
                    )
                )
                if hybrid.status in _SOLVED and hybrid_allocation_ok:
                    (
                        hybrid_schedule,
                        hybrid_ok,
                        hybrid_violations,
                    ) = _schedule_fixed(
                        problem, hybrid.allocation, max_seconds=max_seconds
                    )
                    stages.append(
                        _sequencing_stage(
                            "hybrid_candidate_classical_sequencing",
                            hybrid_schedule,
                            hybrid_ok,
                            hybrid_violations,
                            problem.objective,
                        )
                    )
                    hybrid_path = _Path(
                        name=HYBRID,
                        backend=f"{hybrid.backend}->ortools-cp-sat",
                        schedule=hybrid_schedule,
                        verified=hybrid_ok,
                        allocation_score=hybrid_score,
                        violations=hybrid_violations,
                    )
                else:
                    hybrid_path = _Path(
                        name=HYBRID,
                        backend=hybrid.backend,
                        schedule=None,
                        verified=False,
                        allocation_score=hybrid_score,
                    )
            except (BackendUnavailable, BackendExecutionError) as exc:
                hybrid_status = getattr(exc, "state", BACKEND_UNAVAILABLE)
                stages.append(
                    ComputeStage(
                        name="quantum_hybrid_allocation",
                        backend="dwave-leap-hybrid-cqm",
                        status=hybrid_status,
                        runtime_ms=None,
                        objective_name="allocation_weighted_score",
                        objective_value=None,
                        verified=None,
                        notes=(sanitize_provider_message(str(exc)),),
                    )
                )
                notes.append(
                    "Quantum-hybrid allocation did not return a candidate; the verified "
                    "classical result was retained."
                )

    candidates = [path for path in (joint_path, decomposed_path, hybrid_path) if path is not None]
    eligible = sorted(
        (path for path in candidates if path.eligible),
        key=lambda path: path.sort_key(),
    )

    research_winner = _resolve_research_winner(decomposed_path, hybrid_path, hybrid_status)

    if eligible:
        production = eligible[0]
        production_winner = production.name
    else:
        # Nothing verified. Report the decomposed path's failure as the outcome
        # rather than inventing a winner.
        production = decomposed_path
        production_winner = UNAVAILABLE

    if research_winner == HYBRID and production_winner != HYBRID:
        notes.append(
            "The hybrid allocator beat the decomposed classical allocator but did not "
            "beat the strongest classical baseline. This is not a quantum advantage."
        )
    elif research_winner == CLASSICAL_DECOMPOSED:
        notes.append(
            "The decomposed classical allocator matched or beat the hybrid allocator."
        )

    metrics: dict[str, int | float | str | bool] = {
        "research_winner": research_winner,
        "production_winner": production_winner,
        "production_backend": production.backend,
        "quantum_boundary": "task-to-agent-allocation-only",
        "sequencing_backend": "ortools-cp-sat",
        "final_verifier": "classical-independent",
        "quantum_advantage_claimed": False,
    }
    for path in candidates:
        makespan = path.makespan
        metrics[f"{path.name}_makespan"] = makespan if makespan is not None else -1
        metrics[f"{path.name}_allocation_score"] = (
            path.allocation_score if path.allocation_score is not None else -1
        )
    if hybrid_status is not None:
        metrics["hybrid_status"] = hybrid_status

    schedule = production.schedule
    return ComputeReceipt(
        schema_version="2",
        problem_type="constrained_scheduling",
        problem_sha256=problem.fingerprint(),
        route=route,
        backend=production.backend,
        solver_status=schedule.status if schedule is not None else "NO_VERIFIED_SCHEDULE",
        runtime_ms=(perf_counter() - started) * 1000.0,
        objective_name=problem.objective,
        objective_value=schedule.objective_value if schedule is not None else None,
        verified=production.verified,
        violations=production.violations,
        solution=schedule.assignments if schedule is not None else {},
        metrics=metrics,
        notes=tuple(notes),
        stages=tuple(stages),
        research_winner=research_winner,
        production_winner=production_winner,
    )
