"""Three-path baseline behaviour and winner semantics.

ACR evaluates a decomposed classical path, a joint classical path, and an
optional hybrid path. These tests pin the properties that keep the comparison
honest: the joint baseline is genuinely strong, and the two winner fields mean
different things.
"""

from __future__ import annotations

import importlib.util
import unittest

from compute_router.ir import SchedulingProblem
from compute_router.router import (
    CLASSICAL_DECOMPOSED,
    CLASSICAL_JOINT,
    UNAVAILABLE,
    solve_schedule,
)
from compute_router.verification import verify_schedule

HAS_ORTOOLS = importlib.util.find_spec("ortools") is not None

# Decomposed allocation minimizes maximum agent load without knowing the
# precedence timing, so it is forced into a 12-unit schedule here. The joint
# model sees allocation and timing together and reaches 9.
DECOMPOSITION_GAP = {
    "agents": ["a0", "a1"],
    "tasks": [
        {"id": "t0", "duration": 4},
        {"id": "t1", "duration": 1, "depends_on": ["t0"]},
        {"id": "t2", "duration": 4},
        {"id": "t3", "duration": 2, "depends_on": ["t0"], "eligible_agents": ["a0"]},
        {"id": "t4", "duration": 5, "depends_on": ["t2"]},
    ],
}

SHARED_FILE = {
    "agents": ["a", "b"],
    "tasks": [
        {"id": "one", "duration": 3, "files": ["shared.py"]},
        {"id": "two", "duration": 3, "files": ["shared.py"]},
    ],
}


@unittest.skipUnless(HAS_ORTOOLS, "OR-Tools extra not installed")
class ThreePathTests(unittest.TestCase):
    def test_classical_run_records_both_classical_paths(self):
        receipt = solve_schedule(
            SchedulingProblem.from_dict(DECOMPOSITION_GAP), max_seconds=5
        )
        names = [stage.name for stage in receipt.stages]
        self.assertEqual(
            names,
            [
                "classical_decomposed_allocation",
                "classical_decomposed_sequencing",
                "classical_joint_gold",
            ],
        )

    def test_joint_baseline_beats_the_decomposed_baseline_on_this_problem(self):
        """Guards against the joint path silently degrading into a strawman."""
        receipt = solve_schedule(
            SchedulingProblem.from_dict(DECOMPOSITION_GAP), max_seconds=5
        )
        self.assertEqual(receipt.metrics["classical_decomposed_makespan"], 12)
        self.assertEqual(receipt.metrics["classical_joint_makespan"], 9)
        self.assertEqual(receipt.production_winner, CLASSICAL_JOINT)
        self.assertEqual(receipt.objective_value, 9)
        self.assertTrue(receipt.verified)

    def test_production_schedule_passes_independent_verification(self):
        problem = SchedulingProblem.from_dict(DECOMPOSITION_GAP)
        receipt = solve_schedule(problem, max_seconds=5)
        ok, violations = verify_schedule(problem, receipt.solution)
        self.assertTrue(ok, violations)
        self.assertEqual(receipt.violations, ())

    def test_research_winner_is_unavailable_without_a_hybrid_attempt(self):
        receipt = solve_schedule(
            SchedulingProblem.from_dict(DECOMPOSITION_GAP), max_seconds=5
        )
        self.assertEqual(receipt.research_winner, UNAVAILABLE)
        self.assertIn(
            receipt.production_winner, {CLASSICAL_JOINT, CLASSICAL_DECOMPOSED}
        )

    def test_no_quantum_advantage_is_ever_claimed(self):
        receipt = solve_schedule(
            SchedulingProblem.from_dict(DECOMPOSITION_GAP), max_seconds=5
        )
        self.assertIs(receipt.metrics["quantum_advantage_claimed"], False)

    def test_results_are_deterministic_across_repeated_runs(self):
        problem = SchedulingProblem.from_dict(DECOMPOSITION_GAP)
        outcomes = {
            (
                solve_schedule(problem, max_seconds=5).production_winner,
                solve_schedule(problem, max_seconds=5).objective_value,
            )
            for _ in range(3)
        }
        self.assertEqual(len(outcomes), 1, outcomes)

    def test_shared_file_tasks_are_serialized_on_the_production_schedule(self):
        problem = SchedulingProblem.from_dict(SHARED_FILE)
        receipt = solve_schedule(problem, max_seconds=5)
        self.assertTrue(receipt.verified)
        self.assertEqual(receipt.objective_value, 6)

    def test_invalid_allocator_is_rejected(self):
        with self.assertRaises(ValueError):
            solve_schedule(
                SchedulingProblem.from_dict(SHARED_FILE), allocator="quantum"
            )

    def test_receipt_serializes_both_winners(self):
        receipt = solve_schedule(
            SchedulingProblem.from_dict(SHARED_FILE), max_seconds=5
        )
        payload = receipt.to_dict()
        self.assertEqual(payload["winners"]["research"], receipt.research_winner)
        self.assertEqual(payload["winners"]["production"], receipt.production_winner)


@unittest.skipUnless(HAS_ORTOOLS, "OR-Tools extra not installed")
class DefaultsTests(unittest.TestCase):
    def test_default_allocator_is_classical(self):
        receipt = solve_schedule(SchedulingProblem.from_dict(SHARED_FILE), max_seconds=5)
        self.assertEqual(receipt.route.quantum_escalation, "NO")
        self.assertEqual(
            receipt.route.recommended_backend, "cp-sat-allocation+cp-sat-sequencing"
        )
        self.assertFalse(
            any(stage.name == "quantum_hybrid_allocation" for stage in receipt.stages)
        )


if __name__ == "__main__":
    unittest.main()
