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

    def test_self_dependency_rejected(self):
        with self.assertRaisesRegex(ValueError, "depend on itself"):
            SchedulingProblem.from_dict(
                {
                    "agents": ["a"],
                    "tasks": [{"id": "one", "duration": 1, "depends_on": ["one"]}],
                }
            )

    def test_deep_chain_declared_dependents_first_is_accepted(self):
        """Cycle detection must not exhaust the interpreter stack.

        A problem file is untrusted input. Recursive detection raised
        RecursionError here, which is not a ValueError and so escaped the CLI's
        input validation as an unhandled traceback.
        """
        size = 5000
        tasks = [
            {"id": f"t{i}", "duration": 1, "depends_on": [f"t{i - 1}"]}
            for i in range(size - 1, 0, -1)
        ]
        tasks.append({"id": "t0", "duration": 1})
        problem = SchedulingProblem.from_dict({"agents": ["a"], "tasks": tasks})
        self.assertEqual(len(problem.tasks), size)

    def test_deep_cycle_is_still_rejected(self):
        size = 5000
        tasks = [
            {"id": f"t{i}", "duration": 1, "depends_on": [f"t{i - 1}"]}
            for i in range(size - 1, 0, -1)
        ]
        tasks.append({"id": "t0", "duration": 1, "depends_on": [f"t{size - 1}"]})
        with self.assertRaisesRegex(ValueError, "cycle"):
            SchedulingProblem.from_dict({"agents": ["a"], "tasks": tasks})

    def test_shared_dependency_diamond_is_not_a_cycle(self):
        problem = SchedulingProblem.from_dict(
            {
                "agents": ["a"],
                "tasks": [
                    {"id": "d", "duration": 1, "depends_on": ["b", "c"]},
                    {"id": "b", "duration": 1, "depends_on": ["a"]},
                    {"id": "c", "duration": 1, "depends_on": ["a"]},
                    {"id": "a", "duration": 1},
                ],
            }
        )
        self.assertEqual(len(problem.tasks), 4)

    def test_boolean_duration_rejected(self):
        with self.assertRaisesRegex(ValueError, "positive integer"):
            SchedulingProblem.from_dict(
                {"agents": ["a"], "tasks": [{"id": "one", "duration": True}]}
            )

    def test_unknown_eligible_agent_rejected(self):
        with self.assertRaisesRegex(ValueError, "unknown eligible agents"):
            SchedulingProblem.from_dict(
                {
                    "agents": ["a"],
                    "tasks": [
                        {"id": "one", "duration": 1, "eligible_agents": ["ghost"]}
                    ],
                }
            )

    def test_unsupported_objective_rejected(self):
        with self.assertRaisesRegex(ValueError, "minimize_makespan"):
            SchedulingProblem.from_dict(
                {
                    "agents": ["a"],
                    "tasks": [{"id": "one", "duration": 1}],
                    "objective": "maximize_throughput",
                }
            )


if __name__ == "__main__":
    unittest.main()
