import unittest

from compute_router.ir import SchedulingProblem


class SchedulingIRTests(unittest.TestCase):
    def test_defaults_eligible_agents_and_stable_fingerprint(self):
        payload = {
            "agents": ["a", "b"],
            "tasks": [{"id": "one", "duration": 2}],
        }
        left = SchedulingProblem.from_dict(payload)
        right = SchedulingProblem.from_dict(payload)
        self.assertEqual(left.tasks[0].eligible_agents, ("a", "b"))
        self.assertEqual(left.fingerprint(), right.fingerprint())

    def test_unknown_dependency_rejected(self):
        with self.assertRaisesRegex(ValueError, "unknown dependencies"):
            SchedulingProblem.from_dict(
                {
                    "agents": ["a"],
                    "tasks": [
                        {"id": "one", "duration": 1, "depends_on": ["missing"]}
                    ],
                }
            )

    def test_dependency_cycle_rejected(self):
        with self.assertRaisesRegex(ValueError, "cycle"):
            SchedulingProblem.from_dict(
                {
                    "agents": ["a"],
                    "tasks": [
                        {"id": "one", "duration": 1, "depends_on": ["two"]},
                        {"id": "two", "duration": 1, "depends_on": ["one"]},
                    ],
                }
            )


if __name__ == "__main__":
    unittest.main()
