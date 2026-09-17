import importlib.util
import unittest

from compute_router.ir import SchedulingProblem
from compute_router.router import solve_schedule


@unittest.skipUnless(importlib.util.find_spec("ortools"), "OR-Tools extra not installed")
class CpSatSolveTests(unittest.TestCase):
    def test_dependency_schedule_is_solved_and_verified(self):
        problem = SchedulingProblem.from_dict(
            {
                "agents": ["dev-a", "dev-b"],
                "tasks": [
                    {"id": "schema", "duration": 3},
                    {"id": "api", "duration": 2, "depends_on": ["schema"]},
                    {"id": "ui", "duration": 4},
                    {"id": "tests", "duration": 2, "depends_on": ["api", "ui"]},
                ],
            }
        )
        receipt = solve_schedule(
            problem,
            max_seconds=5,
            allocator="hybrid",
            allow_remote=False,
        )
        self.assertIn(receipt.solver_status, {"OPTIMAL", "FEASIBLE"})
        self.assertTrue(receipt.verified)
        self.assertEqual(receipt.violations, ())
        self.assertEqual(receipt.objective_value, 7)
        self.assertEqual(receipt.route.quantum_escalation, "REVIEW")
        self.assertEqual(receipt.metrics["quantum_boundary"], "task-to-agent-allocation-only")
        self.assertTrue(any(stage.status == "REMOTE_NOT_AUTHORIZED" for stage in receipt.stages))

    def test_file_conflict_is_serialized_even_across_agents(self):
        problem = SchedulingProblem.from_dict(
            {
                "agents": ["a", "b"],
                "tasks": [
                    {"id": "one", "duration": 3, "files": ["shared.py"]},
                    {"id": "two", "duration": 3, "files": ["shared.py"]},
                ],
            }
        )
        receipt = solve_schedule(problem, max_seconds=5, allocator="classical")
        self.assertTrue(receipt.verified)
        self.assertEqual(receipt.objective_value, 6)


if __name__ == "__main__":
    unittest.main()
