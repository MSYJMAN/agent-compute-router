"""Smoke test an installed agent-compute-router CLI.

Run against the console script of a *fresh install*, not an editable checkout:

    python scripts/smoke_installed_wheel.py /path/to/venv/bin/compute-router

A build that succeeds is not evidence that the package installs and runs, so
this exercises the installed entry point end to end and asserts the properties
a release depends on. Used by CI and by local release verification so both
produce the same evidence.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

EXAMPLE = Path(__file__).resolve().parents[1] / "examples" / "scheduling.json"


class SmokeFailure(RuntimeError):
    pass


def run(executable: str, args: list[str], *, expect_code: int = 0) -> str:
    completed = subprocess.run(
        [executable, *args],
        capture_output=True,
        text=True,
        timeout=300,
    )
    if completed.returncode != expect_code:
        raise SmokeFailure(
            f"`{' '.join(args)}` exited {completed.returncode}, expected {expect_code}\n"
            f"stdout:\n{completed.stdout}\nstderr:\n{completed.stderr}"
        )
    return completed.stdout


def check(condition: bool, message: str) -> None:
    if not condition:
        raise SmokeFailure(message)


def stage(receipt: dict, name: str) -> dict | None:
    for candidate in receipt["stages"]:
        if candidate["name"] == name:
            return candidate
    return None


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(__doc__)
        return 2
    executable = argv[1]
    checks: list[str] = []

    assessed = run(executable, ["assess", "Schedule 20 tasks across 4 agents"])
    check("constrained_scheduling" in assessed, f"assess misclassified:\n{assessed}")
    checks.append("assess classifies a scheduling prompt")

    classical = json.loads(run(executable, ["solve", str(EXAMPLE), "--json"]))
    check(classical["verified"] is True, "classical solve was not verified")
    check(
        classical["solver_status"] in {"OPTIMAL", "FEASIBLE"},
        f"unexpected classical status {classical['solver_status']!r}",
    )
    check(
        stage(classical, "quantum_hybrid_allocation") is None,
        "default solve must not create a hybrid stage",
    )
    check(
        stage(classical, "classical_joint_gold") is not None,
        "joint classical baseline stage is missing",
    )
    checks.append("default solve is classical and verified")

    hybrid = json.loads(
        run(executable, ["solve", str(EXAMPLE), "--allocator", "hybrid", "--json"])
    )
    hybrid_stage = stage(hybrid, "quantum_hybrid_allocation")
    check(hybrid_stage is not None, "hybrid-aware solve recorded no hybrid stage")
    check(
        hybrid_stage["status"] == "REMOTE_NOT_AUTHORIZED",
        f"provider was not gated: {hybrid_stage['status']!r}",
    )
    check(hybrid["verified"] is True, "classical result must stay valid in hybrid mode")
    check(
        hybrid["metrics"]["quantum_advantage_claimed"] is False,
        "receipt must not claim quantum advantage",
    )
    checks.append("hybrid mode without authorization contacts no provider")

    serialized = json.dumps(hybrid)
    for leak in ("C:\\", "/home/", "token=", "DWAVE_API_TOKEN"):
        check(leak not in serialized, f"receipt leaked {leak!r}")
    checks.append("receipt contains no paths or credential-shaped values")

    for name in checks:
        print(f"PASS  {name}")
    print(f"\ninstalled-wheel smoke: {len(checks)} checks passed")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv))
    except SmokeFailure as exc:
        print(f"FAIL  {exc}", file=sys.stderr)
        sys.exit(1)
