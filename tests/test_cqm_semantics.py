"""ACR Quantum Challenge 001A - local CQM semantic validation.

These tests run entirely on the local machine using dimod's exact CQM solver.
They are NOT a quantum computation and make no quantum claim. Their purpose is
to prove that the CQM handed to a hybrid provider encodes exactly the allocation
problem ACR intends, and nothing more.
"""

from __future__ import annotations

import importlib.util
import unittest

from compute_router.allocation import score_allocation
from compute_router.ir import SchedulingProblem
from compute_router.verification import verify_allocation

HAS_DIMOD = importlib.util.find_spec("dimod") is not None
HAS_ORTOOLS = importlib.util.find_spec("ortools") is not None


def _problem(data: dict) -> SchedulingProblem:
    return SchedulingProblem.from_dict(data)


SPLIT = {
    "agents": ["a", "b"],
    "tasks": [
        {"id": "schema", "duration": 3, "files": ["db.py"]},
        {"id": "api", "duration": 2, "depends_on": ["schema"]},
        {"id": "ui", "duration": 4, "files": ["db.py"]},
    ],
}

PINNED = {
    "agents": ["a", "b"],
    "tasks": [
        {"id": "only-a", "duration": 2, "eligible_agents": ["a"]},
        {"id": "either", "duration": 2},
    ],
}


@unittest.skipUnless(HAS_DIMOD, "D-Wave Ocean extra not installed")
class CqmSemanticsTests(unittest.TestCase):
    def _solve_exact(self, problem: SchedulingProblem):
        import dimod

        from compute_router.backends.dwave_hybrid import build_cqm

        cqm = build_cqm(problem)
        sampleset = dimod.ExactCQMSolver().sample_cqm(cqm)
        feasible = sampleset.filter(lambda row: row.is_feasible)
        self.assertGreater(len(feasible), 0, "CQM has no feasible assignment")
        return cqm, feasible.first

    def _decode(self, problem: SchedulingProblem, sample) -> dict[str, str]:
        allocation: dict[str, str] = {}
        for task in problem.tasks:
            chosen = [
                agent
                for agent in task.eligible_agents
                if sample.get(f"x::{task.id}::{agent}", 0) > 0.5
            ]
            self.assertEqual(
                len(chosen), 1, f"task {task.id!r} did not select exactly one agent"
            )
            allocation[task.id] = chosen[0]
        return allocation

    def test_cqm_constructs_with_expected_variable_shape(self):
        problem = _problem(SPLIT)
        cqm, _ = self._solve_exact(problem)
        labels = {str(label) for label in cqm.variables}

        expected_allocation = {
            f"x::{task.id}::{agent}"
            for task in problem.tasks
            for agent in task.eligible_agents
        }
        self.assertEqual({l for l in labels if l.startswith("x::")}, expected_allocation)
        self.assertIn("allocation::max_load", labels)
        self.assertEqual(len(labels), len(expected_allocation) + 1)

    def test_timing_and_sequencing_variables_are_absent(self):
        problem = _problem(SPLIT)
        cqm, _ = self._solve_exact(problem)
        labels = [str(label).lower() for label in cqm.variables]
        for token in ("start", "end", "interval", "precedence", "time", "lock", "order"):
            self.assertFalse(
                any(token in label for label in labels),
                f"hybrid boundary leaked a {token!r} variable",
            )

    def test_constraint_set_is_exactly_assignment_and_load(self):
        """An exact set, so a timing constraint cannot be added unnoticed."""
        problem = _problem(SPLIT)
        cqm, _ = self._solve_exact(problem)
        expected = {f"assign::{task.id}" for task in problem.tasks} | {
            f"load::{agent}" for agent in problem.agents
        }
        self.assertEqual({str(label) for label in cqm.constraints}, expected)

    def test_ineligible_allocation_is_excluded_from_the_model(self):
        problem = _problem(PINNED)
        cqm, _ = self._solve_exact(problem)
        labels = {str(label) for label in cqm.variables}
        self.assertIn("x::only-a::a", labels)
        self.assertNotIn(
            "x::only-a::b",
            labels,
            "an ineligible task/agent pair must not be representable at all",
        )

    def test_every_feasible_sample_decodes_to_a_valid_allocation(self):
        import dimod

        from compute_router.backends.dwave_hybrid import build_cqm

        problem = _problem(SPLIT)
        cqm = build_cqm(problem)
        feasible = dimod.ExactCQMSolver().sample_cqm(cqm).filter(lambda row: row.is_feasible)
        self.assertGreater(len(feasible), 0)

        for record in feasible.data(["sample"]):
            allocation = self._decode(problem, record.sample)
            ok, violations = verify_allocation(problem, allocation)
            self.assertTrue(ok, f"feasible CQM sample failed verification: {violations}")

    def test_cqm_energy_equals_the_shared_allocation_score(self):
        """The CQM objective must mean the same thing as ACR's scoring function."""
        problem = _problem(SPLIT)
        _, best = self._solve_exact(problem)
        allocation = self._decode(problem, best.sample)
        score = score_allocation(problem, allocation)
        self.assertEqual(
            round(float(best.energy)),
            score["weighted_score"],
            "CQM energy and score_allocation disagree on the same allocation",
        )

    @unittest.skipUnless(HAS_ORTOOLS, "OR-Tools extra not installed")
    def test_cqm_optimum_matches_the_classical_cp_sat_allocator(self):
        """Cross-validate two independent formulations of the same objective."""
        from compute_router.backends.cp_sat_allocation import solve as solve_classical

        for data in (SPLIT, PINNED):
            with self.subTest(problem=sorted(t["id"] for t in data["tasks"])):
                problem = _problem(data)
                _, best = self._solve_exact(problem)
                classical = solve_classical(problem, max_seconds=5)
                self.assertIn(classical.status, {"OPTIMAL", "FEASIBLE"})
                self.assertEqual(
                    round(float(best.energy)),
                    classical.objective_value,
                    "exact CQM optimum disagrees with the CP-SAT allocator optimum",
                )

    def test_single_eligible_agent_problem_has_one_forced_solution(self):
        problem = _problem(
            {
                "agents": ["a", "b"],
                "tasks": [{"id": "pinned", "duration": 3, "eligible_agents": ["a"]}],
            }
        )
        _, best = self._solve_exact(problem)
        self.assertEqual(self._decode(problem, best.sample), {"pinned": "a"})


if __name__ == "__main__":
    unittest.main()
