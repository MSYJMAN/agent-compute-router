from __future__ import annotations

import argparse
import json
import sys

from .router import assess


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="compute-router",
        description="Assess which compute class best fits an AI-agent subproblem.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    assess_parser = subparsers.add_parser("assess", help="Assess a problem and recommend a compute backend")
    assess_parser.add_argument("problem", help="Natural-language problem description")
    assess_parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

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


if __name__ == "__main__":
    sys.exit(main())
