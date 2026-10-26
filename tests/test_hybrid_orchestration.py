"""Deterministic coverage of hybrid orchestration and provider failure paths.

Every test here runs locally. No test contacts a provider or can spend provider
credits: the real sampler is either never reached or replaced by a local fake.
"""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path
from unittest import mock

from compute_router.backends.dwave_hybrid import (
    BackendExecutionError,
    RemoteNotAuthorized,
)
from compute_router.backends.dwave_hybrid import solve as solve_hybrid
from compute_router.ir import SchedulingProblem
from compute_router.models import AllocationBackendResult, BackendResult
from compute_router.provider import (
    AUTHENTICATION_FAILED,
    CREDENTIALS_MISSING,
    FEASIBLE,
    INVALID_SAMPLE,
    NETWORK_FAILURE,
    NO_FEASIBLE_SAMPLE,
    PROVIDER_ACCESS_REQUIRED,
    PROVIDER_UNAVAILABLE,
    REMOTE_NOT_AUTHORIZED,
)
from compute_router import router as router_module
from compute_router.router import (
    CLASSICAL_DECOMPOSED,
    CLASSICAL_JOINT,
    HYBRID,
    TIE,
    UNAVAILABLE,
    solve_schedule,
)

HAS_ORTOOLS = importlib.util.find_spec("ortools") is not None
HAS_DIMOD = importlib.util.find_spec("dimod") is not None

EXAMPLE_PATH = Path(__file__).resolve().parents[1] / "examples" / "scheduling.json"

# Decomposed allocation is suboptimal here (makespan 12) while the joint model
# reaches 9. That gap lets a fake hybrid allocator genuinely win the fair
# allocator comparison while still losing to the strongest classical baseline.
GAP_PROBLEM = {
    "agents": ["a0", "a1"],
    "tasks": [
        {"id": "t0", "duration": 4},
        {"id": "t1", "duration": 1, "depends_on": ["t0"]},
        {"id": "t2", "duration": 4},
        {"id": "t3", "duration": 2, "depends_on": ["t0"], "eligible_agents": ["a0"]},
        {"id": "t4", "duration": 5, "depends_on": ["t2"]},
    ],
}

# The allocation the joint solver finds for GAP_PROBLEM.
GOOD_ALLOCATION = {"t0": "a1", "t1": "a0", "t2": "a0", "t3": "a0", "t4": "a1"}

SIMPLE_PROBLEM = {
    "agents": ["a", "b"],
    "tasks": [
        {"id": "one", "duration": 2},
        {"id": "two", "duration": 2, "depends_on": ["one"]},
    ],
}


def problem_of(data: dict) -> SchedulingProblem:
    return SchedulingProblem.from_dict(data)


def hybrid_result(
    allocation: dict[str, str],
    *,
    status: str = FEASIBLE,
    objective_value: int | None = 0,
) -> AllocationBackendResult:
    return AllocationBackendResult(
        backend="dwave-leap-hybrid-cqm",
        status=status,
        allocation=allocation,
        runtime_ms=12.0,
        objective_value=objective_value,
        metrics={"allocation_only": True},
    )


def stage_named(receipt, name):
    for stage in receipt.stages:
        if stage.name == name:
            return stage
    return None


class FakeSampler:
    """Local stand-in for LeapHybridCQMSampler."""

    properties = {"category": "hybrid"}

    def __init__(self, sample=None, *, raises=None, feasible=True):
        self._sample = sample
        self._raises = raises
        self._feasible = feasible

    def __enter__(self):
        if self._raises is not None:
            raise self._raises
        return self

    def __exit__(self, *exc_info):
        return False

    def min_time_limit(self, cqm):
        return 5.0

    def sample_cqm(self, cqm, time_limit=None, label=None):
        import dimod

        return dimod.SampleSet.from_samples_cqm(self._sample, cqm)


class _StubRow:
    def __init__(self, sample):
        self.sample = sample


class _StubSampleSet:
    """A sampleset that claims every sample is feasible."""

    def __init__(self, sample):
        self._sample = sample
        self.info: dict[str, object] = {}

    def resolve(self):
        return None

    def filter(self, predicate):
        return self

    def __len__(self):
        return 1

    @property
    def first(self):
        return _StubRow(self._sample)


class LyingSampler(FakeSampler):
    """Returns a malformed sample while asserting it is feasible.

    A real provider is not trusted to be correct. This proves ACR validates the
    decoded allocation itself rather than believing a feasibility claim.
    """

    def sample_cqm(self, cqm, time_limit=None, label=None):
        return _StubSampleSet(self._sample)


@unittest.skipUnless(HAS_ORTOOLS, "OR-Tools extra not installed")
class RemoteAuthorizationBoundaryTests(unittest.TestCase):
    """Selecting hybrid mode must never be sufficient to contact a provider."""

    def test_hybrid_mode_without_authorization_never_calls_the_backend(self):
        with mock.patch.object(
            router_module, "solve_dwave_allocation", side_effect=AssertionError("provider contacted")
        ) as spy:
            receipt = solve_schedule(
                problem_of(SIMPLE_PROBLEM), max_seconds=5, allocator="hybrid", allow_remote=False
            )
        spy.assert_not_called()
        stage = stage_named(receipt, "quantum_hybrid_allocation")
        self.assertIsNotNone(stage)
        self.assertEqual(stage.status, REMOTE_NOT_AUTHORIZED)
        self.assertTrue(receipt.verified)

    def test_classical_mode_records_no_hybrid_stage_at_all(self):
        with mock.patch.object(
            router_module, "solve_dwave_allocation", side_effect=AssertionError("provider contacted")
        ) as spy:
            receipt = solve_schedule(
                problem_of(SIMPLE_PROBLEM), max_seconds=5, allocator="classical", allow_remote=True
            )
        spy.assert_not_called()
        self.assertIsNone(stage_named(receipt, "quantum_hybrid_allocation"))
        self.assertEqual(receipt.research_winner, UNAVAILABLE)
        self.assertEqual(receipt.route.quantum_escalation, "NO")

    def test_backend_refuses_real_provider_without_explicit_authorization(self):
        with self.assertRaises(RemoteNotAuthorized) as caught:
            solve_hybrid(problem_of(SIMPLE_PROBLEM), allow_remote=False)
        self.assertEqual(caught.exception.state, REMOTE_NOT_AUTHORIZED)

    def test_injected_local_sampler_needs_no_remote_authorization(self):
        if not HAS_DIMOD:
            self.skipTest("D-Wave Ocean extra not installed")
        sample = {
            "x::one::a": 1,
            "x::one::b": 0,
            "x::two::a": 0,
            "x::two::b": 1,
            "allocation::max_load": 2,
        }
        result = solve_hybrid(
            problem_of(SIMPLE_PROBLEM),
            sampler_factory=lambda: FakeSampler(sample),
            allow_remote=False,
        )
        self.assertEqual(result.status, FEASIBLE)
        self.assertEqual(result.allocation, {"one": "a", "two": "b"})


@unittest.skipUnless(HAS_ORTOOLS and HAS_DIMOD, "full extras not installed")
class SamplerResultDecodingTests(unittest.TestCase):
    """Malformed provider output must never reach production."""

    def test_no_feasible_sample_is_reported(self):
        # max_load=1 cannot satisfy a 2-unit task, so the sample is infeasible.
        sample = {
            "x::one::a": 1,
            "x::one::b": 0,
            "x::two::a": 1,
            "x::two::b": 0,
            "allocation::max_load": 1,
        }
        result = solve_hybrid(
            problem_of(SIMPLE_PROBLEM),
            sampler_factory=lambda: FakeSampler(sample),
        )
        self.assertEqual(result.status, NO_FEASIBLE_SAMPLE)
        self.assertEqual(result.allocation, {})

    def test_multiple_selected_agents_is_rejected(self):
        sample = {
            "x::one::a": 1,
            "x::one::b": 1,
            "x::two::a": 0,
            "x::two::b": 1,
            "allocation::max_load": 4,
        }
        result = solve_hybrid(
            problem_of(SIMPLE_PROBLEM),
            sampler_factory=lambda: LyingSampler(sample),
        )
        self.assertEqual(result.status, INVALID_SAMPLE)
        self.assertEqual(result.allocation, {})

    def test_missing_selected_agent_is_rejected(self):
        sample = {
            "x::one::a": 0,
            "x::one::b": 0,
            "x::two::a": 0,
            "x::two::b": 1,
            "allocation::max_load": 2,
        }
        result = solve_hybrid(
            problem_of(SIMPLE_PROBLEM),
            sampler_factory=lambda: LyingSampler(sample),
        )
        self.assertEqual(result.status, INVALID_SAMPLE)

    def test_sample_missing_variables_entirely_is_rejected(self):
        result = solve_hybrid(
            problem_of(SIMPLE_PROBLEM),
            sampler_factory=lambda: LyingSampler({}),
        )
        self.assertEqual(result.status, INVALID_SAMPLE)
        self.assertEqual(result.allocation, {})

    def test_provider_exception_is_classified_and_sanitized(self):
        secret = "DEV-0123456789abcdef0123456789abcdef01234567"
        with self.assertRaises(BackendExecutionError) as caught:
            solve_hybrid(
                problem_of(SIMPLE_PROBLEM),
                sampler_factory=lambda: FakeSampler(
                    raises=RuntimeError(f"rejected token {secret}")
                ),
            )
        self.assertNotIn(secret, str(caught.exception))
        self.assertIn("[redacted]", str(caught.exception))


@unittest.skipUnless(HAS_ORTOOLS, "OR-Tools extra not installed")
class HybridComparisonTests(unittest.TestCase):
    def _run_with_hybrid(self, data, result_or_error, **kwargs):
        side = (
            {"side_effect": result_or_error}
            if isinstance(result_or_error, BaseException)
            else {"return_value": result_or_error}
        )
        with mock.patch.object(router_module, "solve_dwave_allocation", **side):
            return solve_schedule(
                problem_of(data),
                max_seconds=5,
                allocator="hybrid",
                allow_remote=True,
                **kwargs,
            )

    def test_hybrid_beating_decomposed_still_loses_to_joint_gold(self):
        """The central integrity case: a research win is not a production win."""
        receipt = self._run_with_hybrid(GAP_PROBLEM, hybrid_result(GOOD_ALLOCATION))
        self.assertEqual(receipt.metrics["classical_decomposed_makespan"], 12)
        self.assertEqual(receipt.metrics["classical_joint_makespan"], 9)
        self.assertEqual(receipt.metrics["hybrid_makespan"], 9)
        self.assertEqual(receipt.research_winner, HYBRID)
        self.assertEqual(receipt.production_winner, CLASSICAL_JOINT)
        self.assertFalse(receipt.metrics["quantum_advantage_claimed"])
        self.assertTrue(
            any("not a quantum advantage" in note for note in receipt.notes),
            receipt.notes,
        )

    def test_backend_reported_score_cannot_win_the_comparison(self):
        """A backend must not win selection by reporting a score it did not earn."""
        everything_on_one = {"t0": "a0", "t1": "a0", "t2": "a0", "t3": "a0", "t4": "a0"}
        receipt = self._run_with_hybrid(
            GAP_PROBLEM,
            hybrid_result(everything_on_one, objective_value=-10_000),
        )
        self.assertEqual(receipt.research_winner, CLASSICAL_DECOMPOSED)
        self.assertNotEqual(receipt.production_winner, HYBRID)
        stage = stage_named(receipt, "quantum_hybrid_allocation")
        self.assertNotEqual(stage.objective_value, -10_000)
        self.assertTrue(
            any("disagreed with the locally recomputed" in note for note in stage.notes),
            stage.notes,
        )

    def test_worse_hybrid_allocation_loses_the_research_comparison(self):
        everything_on_one = {"t0": "a0", "t1": "a0", "t2": "a0", "t3": "a0", "t4": "a0"}
        receipt = self._run_with_hybrid(GAP_PROBLEM, hybrid_result(everything_on_one))
        self.assertEqual(receipt.research_winner, CLASSICAL_DECOMPOSED)
        self.assertNotEqual(receipt.production_winner, HYBRID)
        self.assertGreater(
            receipt.metrics["hybrid_makespan"],
            receipt.metrics["classical_decomposed_makespan"],
        )

    def test_identical_allocation_is_reported_as_a_tie(self):
        """Replay the decomposed allocator's own choice through the hybrid path."""
        from compute_router.backends.cp_sat_allocation import solve as solve_alloc

        mirror = solve_alloc(problem_of(GAP_PROBLEM), max_seconds=5)
        receipt = self._run_with_hybrid(
            GAP_PROBLEM,
            hybrid_result(mirror.allocation, objective_value=mirror.objective_value),
        )
        self.assertEqual(receipt.research_winner, TIE)
        self.assertEqual(
            receipt.metrics["hybrid_makespan"],
            receipt.metrics["classical_decomposed_makespan"],
        )

    def test_ineligible_hybrid_allocation_is_rejected_and_classical_survives(self):
        receipt = self._run_with_hybrid(
            GAP_PROBLEM,
            hybrid_result({**GOOD_ALLOCATION, "t3": "a1"}),
        )
        stage = stage_named(receipt, "quantum_hybrid_allocation")
        self.assertFalse(stage.verified)
        self.assertTrue(any("ineligible" in v for v in stage.violations))
        self.assertIsNone(stage_named(receipt, "hybrid_candidate_classical_sequencing"))
        self.assertEqual(receipt.research_winner, CLASSICAL_DECOMPOSED)
        self.assertNotEqual(receipt.production_winner, HYBRID)
        self.assertTrue(receipt.verified)

    def test_incomplete_hybrid_allocation_is_rejected(self):
        partial = {k: v for k, v in GOOD_ALLOCATION.items() if k != "t4"}
        receipt = self._run_with_hybrid(GAP_PROBLEM, hybrid_result(partial))
        stage = stage_named(receipt, "quantum_hybrid_allocation")
        self.assertFalse(stage.verified)
        self.assertTrue(any("missing allocation" in v for v in stage.violations))
        self.assertTrue(receipt.verified)

    def test_unsolved_hybrid_status_is_not_sequenced(self):
        receipt = self._run_with_hybrid(
            GAP_PROBLEM, hybrid_result({}, status=NO_FEASIBLE_SAMPLE, objective_value=None)
        )
        self.assertIsNone(stage_named(receipt, "hybrid_candidate_classical_sequencing"))
        self.assertEqual(receipt.research_winner, CLASSICAL_DECOMPOSED)
        self.assertTrue(receipt.verified)

    def test_sequencing_failure_on_a_valid_hybrid_allocation_keeps_classical(self):
        real_solve = router_module.solve_cp_sat

        def flaky(problem, *, max_seconds=10.0, fixed_allocation=None):
            if fixed_allocation == GOOD_ALLOCATION:
                return BackendResult(
                    status="UNKNOWN", assignments={}, objective_value=None, metrics={}
                )
            return real_solve(problem, max_seconds=max_seconds, fixed_allocation=fixed_allocation)

        with mock.patch.object(router_module, "solve_cp_sat", side_effect=flaky):
            receipt = self._run_with_hybrid(GAP_PROBLEM, hybrid_result(GOOD_ALLOCATION))

        stage = stage_named(receipt, "hybrid_candidate_classical_sequencing")
        self.assertEqual(stage.status, "UNKNOWN")
        self.assertFalse(stage.verified)
        self.assertEqual(receipt.research_winner, CLASSICAL_DECOMPOSED)
        self.assertNotEqual(receipt.production_winner, HYBRID)
        self.assertTrue(receipt.verified)

    def test_verifier_rejection_of_a_hybrid_schedule_keeps_classical(self):
        real_verify = router_module.verify_schedule
        calls = {"n": 0}

        def selective(problem, assignments):
            calls["n"] += 1
            agents = {a.agent for a in assignments.values()}
            if agents == set(GOOD_ALLOCATION.values()) and all(
                assignments[t].agent == GOOD_ALLOCATION[t] for t in GOOD_ALLOCATION
            ):
                return False, ("injected verifier rejection",)
            return real_verify(problem, assignments)

        with mock.patch.object(router_module, "verify_schedule", side_effect=selective):
            receipt = self._run_with_hybrid(GAP_PROBLEM, hybrid_result(GOOD_ALLOCATION))

        self.assertGreater(calls["n"], 0)
        self.assertNotEqual(receipt.production_winner, HYBRID)
        self.assertEqual(receipt.research_winner, CLASSICAL_DECOMPOSED)


@unittest.skipUnless(HAS_ORTOOLS, "OR-Tools extra not installed")
class NoVerifiedScheduleTests(unittest.TestCase):
    """An unverified schedule must never be emitted as a usable solution."""

    def test_receipt_ships_no_solution_when_nothing_verifies(self):
        with mock.patch.object(
            router_module,
            "verify_schedule",
            return_value=(False, ("injected rejection",)),
        ):
            receipt = solve_schedule(problem_of(GAP_PROBLEM), max_seconds=5)

        self.assertEqual(receipt.production_winner, UNAVAILABLE)
        self.assertEqual(receipt.solver_status, "NO_VERIFIED_SCHEDULE")
        self.assertEqual(receipt.solution, {})
        self.assertIsNone(receipt.objective_value)
        self.assertFalse(receipt.verified)
        # The attempts are still preserved as evidence.
        self.assertTrue(any(s.name == "classical_joint_gold" for s in receipt.stages))

    def test_cli_reports_failure_when_nothing_verifies(self):
        from compute_router.cli import main

        with mock.patch.object(
            router_module,
            "verify_schedule",
            return_value=(False, ("injected rejection",)),
        ):
            import io
            from contextlib import redirect_stdout

            buffer = io.StringIO()
            with redirect_stdout(buffer):
                code = main(["solve", str(EXAMPLE_PATH)])
        self.assertEqual(code, 4)


@unittest.skipUnless(HAS_ORTOOLS, "OR-Tools extra not installed")
class ProviderFailureFallbackTests(unittest.TestCase):
    """Each provider failure state must be preserved, not flattened."""

    STATES = (
        CREDENTIALS_MISSING,
        AUTHENTICATION_FAILED,
        PROVIDER_ACCESS_REQUIRED,
        PROVIDER_UNAVAILABLE,
        NETWORK_FAILURE,
    )

    def test_each_provider_state_falls_back_to_verified_classical(self):
        for state in self.STATES:
            with self.subTest(state=state):
                error = BackendExecutionError("provider said no", state=state)
                with mock.patch.object(
                    router_module, "solve_dwave_allocation", side_effect=error
                ):
                    receipt = solve_schedule(
                        problem_of(GAP_PROBLEM),
                        max_seconds=5,
                        allocator="hybrid",
                        allow_remote=True,
                    )
                stage = stage_named(receipt, "quantum_hybrid_allocation")
                self.assertEqual(stage.status, state)
                self.assertEqual(receipt.metrics["hybrid_status"], state)
                # A provider that never answered did not lose a comparison.
                self.assertEqual(receipt.research_winner, UNAVAILABLE)
                self.assertTrue(receipt.verified, "classical fallback must stay verified")
                self.assertIn(receipt.production_winner, {CLASSICAL_JOINT, CLASSICAL_DECOMPOSED})

    def test_sdk_missing_is_reported_as_backend_unavailable(self):
        from compute_router.backends.cp_sat import BackendUnavailable
        from compute_router.provider import BACKEND_UNAVAILABLE

        with mock.patch.object(
            router_module,
            "solve_dwave_allocation",
            side_effect=BackendUnavailable("D-Wave Ocean is not installed."),
        ):
            receipt = solve_schedule(
                problem_of(GAP_PROBLEM), max_seconds=5, allocator="hybrid", allow_remote=True
            )
        stage = stage_named(receipt, "quantum_hybrid_allocation")
        self.assertEqual(stage.status, BACKEND_UNAVAILABLE)
        self.assertTrue(receipt.verified)

    def test_failed_attempt_is_preserved_in_the_receipt(self):
        error = BackendExecutionError("entitlement denied", state=PROVIDER_ACCESS_REQUIRED)
        with mock.patch.object(router_module, "solve_dwave_allocation", side_effect=error):
            receipt = solve_schedule(
                problem_of(GAP_PROBLEM), max_seconds=5, allocator="hybrid", allow_remote=True
            )
        payload = receipt.to_dict()
        hybrid_stages = [s for s in payload["stages"] if s["name"] == "quantum_hybrid_allocation"]
        self.assertEqual(len(hybrid_stages), 1)
        self.assertEqual(hybrid_stages[0]["status"], PROVIDER_ACCESS_REQUIRED)
        self.assertTrue(hybrid_stages[0]["notes"])

    def test_no_provider_state_is_ever_reported_as_success(self):
        for state in self.STATES:
            with self.subTest(state=state):
                error = BackendExecutionError("nope", state=state)
                with mock.patch.object(
                    router_module, "solve_dwave_allocation", side_effect=error
                ):
                    receipt = solve_schedule(
                        problem_of(GAP_PROBLEM),
                        max_seconds=5,
                        allocator="hybrid",
                        allow_remote=True,
                    )
                self.assertNotEqual(receipt.production_winner, HYBRID)
                self.assertNotEqual(receipt.research_winner, HYBRID)


if __name__ == "__main__":
    unittest.main()
