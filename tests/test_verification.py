import unittest

from compute_router.ir import SchedulingProblem
from compute_router.models import TaskAssignment
from compute_router.verification import verify_schedule


class VerificationTests(unittest.TestCase):
    def test_valid_schedule_passes(self):
        problem = SchedulingProblem.from_dict(
            {
                "agents": ["a", "b"],
                "tasks": [
                    {"id": "one", "duration": 2},
                    {"id": "two", "duration": 2, "depends_on": ["one"]},
                ],
            }
        )
        verified, violations = verify_schedule(
            problem,
            {
                "one": TaskAssignment(agent="a", start=0, end=2),
                "two": TaskAssignment(agent="b", start=2, end=4),
            },
        )
        self.assertTrue(verified)
        self.assertEqual(violations, ())

    def test_shared_file_overlap_fails(self):
        problem = SchedulingProblem.from_dict(
            {
                "agents": ["a", "b"],
                "tasks": [
                    {"id": "one", "duration": 3, "files": ["shared.py"]},
                    {"id": "two", "duration": 3, "files": ["shared.py"]},
                ],
            }
        )
        verified, violations = verify_schedule(
            problem,
            {
                "one": TaskAssignment(agent="a", start=0, end=3),
                "two": TaskAssignment(agent="b", start=0, end=3),
            },
        )
        self.assertFalse(verified)
        self.assertTrue(any("file conflict" in violation for violation in violations))


if __name__ == "__main__":
    unittest.main()
