"""CLI behaviour: classical defaults, exit codes, and the remote gate."""

from __future__ import annotations

import importlib.util
import io
import json
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock

from compute_router import router as router_module
from compute_router.cli import main

HAS_ORTOOLS = importlib.util.find_spec("ortools") is not None

EXAMPLE = Path(__file__).resolve().parents[1] / "examples" / "scheduling.json"


def run_cli(args: list[str]) -> tuple[int, str]:
    buffer = io.StringIO()
    with redirect_stdout(buffer):
        code = main(args)
    return code, buffer.getvalue()


class AssessTests(unittest.TestCase):
    def test_assess_emits_json(self):
        code, output = run_cli(["assess", "Schedule 20 tasks across 4 agents", "--json"])
        self.assertEqual(code, 0)
        payload = json.loads(output)
        self.assertEqual(payload["classification"], "constrained_scheduling")
        self.assertEqual(payload["quantum_escalation"], "NO")

    def test_qubo_phrasing_escalates_to_review_only(self):
        code, output = run_cli(["assess", "Solve this as a QUBO", "--json"])
        self.assertEqual(code, 0)
        payload = json.loads(output)
        self.assertEqual(payload["quantum_escalation"], "REVIEW")
        self.assertEqual(payload["recommended_backend"], "classical-baseline-first")


@unittest.skipUnless(HAS_ORTOOLS, "OR-Tools extra not installed")
class SolveTests(unittest.TestCase):
    def test_default_solve_is_classical_and_contacts_no_provider(self):
        with mock.patch.object(
            router_module,
            "solve_dwave_allocation",
            side_effect=AssertionError("provider contacted"),
        ) as spy:
            code, output = run_cli(["solve", str(EXAMPLE)])
        spy.assert_not_called()
        self.assertEqual(code, 0)
        self.assertIn("Verified: True", output)
        self.assertNotIn("quantum_hybrid_allocation", output)

    def test_hybrid_without_allow_remote_contacts_no_provider(self):
        with mock.patch.object(
            router_module,
            "solve_dwave_allocation",
            side_effect=AssertionError("provider contacted"),
        ) as spy:
            code, output = run_cli(["solve", str(EXAMPLE), "--allocator", "hybrid"])
        spy.assert_not_called()
        self.assertEqual(code, 0)
        self.assertIn("REMOTE_NOT_AUTHORIZED", output)
        self.assertIn("Verified: True", output)

    def test_json_receipt_carries_both_winners(self):
        code, output = run_cli(["solve", str(EXAMPLE), "--json"])
        self.assertEqual(code, 0)
        payload = json.loads(output)
        self.assertIn("winners", payload)
        self.assertIn("research", payload["winners"])
        self.assertIn("production", payload["winners"])
        self.assertIs(payload["metrics"]["quantum_advantage_claimed"], False)

    def test_human_output_reports_both_winners(self):
        _, output = run_cli(["solve", str(EXAMPLE)])
        self.assertIn("Research winner", output)
        self.assertIn("Production winner", output)

    def test_receipt_json_contains_no_absolute_paths(self):
        _, output = run_cli(["solve", str(EXAMPLE), "--allocator", "hybrid", "--json"])
        self.assertNotIn("C:\\", output)
        self.assertNotIn("/home/", output)

    def test_malformed_problem_file_exits_with_usage_error(self):
        with TemporaryDirectory() as tmp:
            bad = Path(tmp) / "bad.json"
            bad.write_text("{not json", encoding="utf-8")
            with self.assertRaises(SystemExit) as caught:
                run_cli(["solve", str(bad)])
            self.assertEqual(caught.exception.code, 2)

    def test_missing_problem_file_exits_with_usage_error(self):
        with TemporaryDirectory() as tmp:
            with self.assertRaises(SystemExit) as caught:
                run_cli(["solve", str(Path(tmp) / "nope.json")])
            self.assertEqual(caught.exception.code, 2)

    def test_allocator_choice_is_validated(self):
        with self.assertRaises(SystemExit):
            run_cli(["solve", str(EXAMPLE), "--allocator", "quantum"])


if __name__ == "__main__":
    unittest.main()
