import unittest

from compute_router.allocation import score_allocation
from compute_router.ir import SchedulingProblem
from compute_router.verification import verify_allocation


class AllocationTests(unittest.TestCase):
    def setUp(self):
        self.problem = SchedulingProblem.from_dict(
            {
                "agents": ["a", "b"],
                "tasks": [
                    {"id": "schema", "duration": 3, "eligible_agents": ["a"]},
                    {"id": "api", "duration": 2, "depends_on": ["schema"]},
                    {"id": "ui", "duration": 4},
                ],
            }
        )

    def test_verifier_rejects_ineligible_agent(self):
        ok, violations = verify_allocation(
            self.problem,
            {"schema": "b", "api": "a", "ui": "b"},
        )
        self.assertFalse(ok)
        self.assertTrue(any("ineligible" in item for item in violations))

    def test_score_records_load_and_handoffs(self):
        score = score_allocation(
            self.problem,
            {"schema": "a", "api": "a", "ui": "b"},
        )
        self.assertEqual(score["max_agent_load"], 5)
        self.assertEqual(score["dependency_handoffs"], 0)


if __name__ == "__main__":
    unittest.main()
