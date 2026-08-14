import unittest

from compute_router import assess


class RouterTests(unittest.TestCase):
    def test_general_coding_stays_general(self):
        result = assess("Write a login form and connect it to the existing API")
        self.assertEqual(result.recommended_backend, "llm-or-direct-code")
        self.assertEqual(result.quantum_escalation, "NO")

    def test_scheduling_routes_to_cp_sat(self):
        result = assess("Schedule 50 tasks across 4 agents with precedence constraints")
        self.assertEqual(result.classification, "constrained_scheduling")
        self.assertEqual(result.recommended_backend, "cp-sat")
        self.assertEqual(result.quantum_escalation, "NO")

    def test_graph_problem_routes_to_graph_algorithm(self):
        result = assess("Find the critical path through this dependency graph")
        self.assertEqual(result.recommended_backend, "graph-algorithm")

    def test_qubo_only_triggers_review(self):
        result = assess("Formulate this Max-Cut problem as a QUBO")
        self.assertEqual(result.quantum_escalation, "REVIEW")
        self.assertEqual(result.recommended_backend, "classical-baseline-first")

    def test_empty_input_rejected(self):
        with self.assertRaises(ValueError):
            assess("   ")


if __name__ == "__main__":
    unittest.main()
