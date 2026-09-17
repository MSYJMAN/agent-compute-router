import importlib.util
import unittest

from compute_router.ir import SchedulingProblem


@unittest.skipUnless(importlib.util.find_spec("dimod"), "D-Wave Ocean extra not installed")
class QuantumBoundaryTests(unittest.TestCase):
    def test_cqm_contains_allocation_variables_only(self):
        from compute_router.backends.dwave_hybrid import build_cqm

        problem = SchedulingProblem.from_dict(
            {
                "agents": ["a", "b"],
                "tasks": [
                    {"id": "one", "duration": 3, "files": ["shared.py"]},
                    {"id": "two", "duration": 2, "depends_on": ["one"]},
                ],
            }
        )
        cqm = build_cqm(problem)
        labels = {str(label) for label in cqm.variables}

        allocation_labels = {label for label in labels if label.startswith("x::")}
        self.assertEqual(len(allocation_labels), 4)
        self.assertIn("allocation::max_load", labels)

        forbidden = ("start", "end", "interval", "precedence", "time::")
        self.assertFalse(
            any(token in label.lower() for label in labels for token in forbidden)
        )


if __name__ == "__main__":
    unittest.main()
