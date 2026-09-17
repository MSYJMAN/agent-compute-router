from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .ir import SchedulingProblem
from .router import assess, solve_schedule


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="compute-router",
        description="Route AI-agent subproblems to appropriate computation.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    assess_parser = subparsers.add_parser(
        "assess",
        help="Assess a natural-language problem and recommend a compute backend",
    )
    assess_parser.add_argument("problem", help="Natural-language problem description")
    assess_parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON")

    solve_parser = subparsers.add_parser(
        "solve",
        help="Solve a structured sprint and emit a verified Compute Receipt",
    )
    solve_parser.add_argument("problem_file", type=Path, help="Path to scheduling problem JSON")
    solve_parser.add_argument(
        "--max-seconds",
        type=float,
        default=10.0,
        help="Maximum time for each classical CP-SAT stage (default: 10)",
    )
    solve_parser.add_argument(
        "--allocator",
        choices=("hybrid", "classical"),
        default="hybrid",
        help="Allocation strategy. Hybrid remains allocation-only (default: hybrid).",
    )
    solve_parser.add_argument(
        "--allow-remote",
        action="store_true",
        help="Explicitly authorize remote quantum-hybrid execution.",
    )
    solve_parser.add_argument(
        "--hybrid-seconds",
        type=float,
        default=None,
        help="Requested D-Wave hybrid time limit; provider minimum still applies.",
    )
    solve_parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON")
    return parser


def _print_receipt(receipt) -> None:
    print("COMPUTE RECEIPT")
    print(f"Problem SHA-256: {receipt.problem_sha256}")
    print(f"Classification: {receipt.route.classification}")
    print(f"Backend pipeline: {receipt.backend}")
    print(f"Status: {receipt.solver_status}")
    print(f"Verified: {receipt.verified}")
    print(f"Quantum escalation: {receipt.route.quantum_escalation}")
    if receipt.objective_value is not None:
        print(f"Objective ({receipt.objective_name}): {receipt.objective_value}")
    if receipt.runtime_ms is not None:
        print(f"Runtime: {receipt.runtime_ms:.3f} ms")
    if receipt.stages:
        print("Stages:")
        for stage in receipt.stages:
            print(
                f"- {stage.name}: backend={stage.backend} status={stage.status} "
                f"verified={stage.verified}"
            )
    for task_id, assignment in sorted(receipt.solution.items()):
        print(
            f"{task_id}: agent={assignment.agent} "
            f"start={assignment.start} end={assignment.end}"
        )
    if receipt.violations:
        print("Violations:")
        for violation in receipt.violations:
            print(f"- {violation}")
    if receipt.notes:
        print("Notes:")
        for note in receipt.notes:
            print(f"- {note}")


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command == "assess":
        try:
            decision = assess(args.problem)
        except ValueError as exc:
            parser.error(str(exc))
            return 2

        if args.json:
            print(json.dumps(decision.to_dict(), indent=2, sort_keys=True))
        else:
            print("COMPUTE ROUTE")
            print(f"Classification: {decision.classification}")
            print(f"Backend: {decision.recommended_backend}")
            print(f"Quantum escalation: {decision.quantum_escalation}")
            print(f"Reason: {decision.reason}")
            if decision.alternatives:
                print(f"Alternatives: {', '.join(decision.alternatives)}")
        return 0

    try:
        problem = SchedulingProblem.from_json(args.problem_file.read_text(encoding="utf-8"))
        receipt = solve_schedule(
            problem,
            max_seconds=args.max_seconds,
            allocator=args.allocator,
            allow_remote=args.allow_remote,
            hybrid_time_limit=args.hybrid_seconds,
        )
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
        return 2

    if args.json:
        print(json.dumps(receipt.to_dict(), indent=2, sort_keys=True))
    else:
        _print_receipt(receipt)

    if receipt.solver_status == "BACKEND_UNAVAILABLE":
        return 3
    if receipt.verified is True and receipt.solver_status in {"OPTIMAL", "FEASIBLE"}:
        return 0
    return 4


if __name__ == "__main__":
    sys.exit(main())
