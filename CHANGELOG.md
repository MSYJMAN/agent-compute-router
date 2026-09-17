# Changelog

All notable changes to Agent Compute Router are documented in this file.

The project follows Semantic Versioning: `MAJOR.MINOR.PATCH`.

## [Unreleased]

- Nothing yet.

## [0.2.0] - 2026-09-16

### Added

- Structured scheduling problem IR with validation for tasks, durations, dependencies, eligible agents, and file ownership.
- Stable SHA-256 problem fingerprints over normalized structured inputs.
- Classical OR-Tools CP-SAT task-allocation baseline.
- Optional D-Wave Leap Hybrid CQM task-to-agent allocator.
- Strict quantum/hybrid boundary: remote compute may choose task ownership only; all timing, precedence, interval sequencing, shared-file locking, and final verification stay classical.
- Allocation objective that prioritizes maximum agent load, then dependency handoffs and shared-file ownership splits.
- Classical CP-SAT sequencing with fixed task ownership.
- Independent allocation verification and final schedule verification.
- Evidence-based comparison that retains a hybrid allocation only when its verified classical schedule beats the classical baseline.
- Explicit `--allow-remote` gate before any D-Wave Leap submission.
- Compute Receipt schema v2 with per-stage evidence.
- CI guardrail that inspects the CQM and rejects timing/sequencing variables from the hybrid boundary.

### Changed

- `solve` now supports `--allocator hybrid|classical` and optional `--hybrid-seconds`.
- `full` installs both OR-Tools and D-Wave Ocean SDK 9.x for local/CI model tests; live D-Wave credentials are not required for CI.
- Release verification installs all optional execution dependencies before publishing.

### Evidence policy

- A classical allocation baseline is always computed first.
- Hybrid allocation must pass classical validation.
- Hybrid allocation is sequenced by the same classical CP-SAT scheduler as the baseline.
- Final schedules are independently verified.
- This release makes no claim of quantum advantage.

### Known limitations

- A live D-Wave benchmark requires operator-supplied Leap credentials and may incur provider usage/cost.
- v0.2 supports one optimization family: multi-agent development sprint allocation + scheduling.
- No persistent receipt database, MCP server, IBM/QAOA execution, or direct QPU execution exists yet.

## [0.1.0] - 2026-08-14

### Added

- Deterministic workload classification.
- Explainable compute recommendations.
- Local CLI and JSON output.
- Explicit quantum-escalation gate.
- Local-first operation with no cloud or quantum account required.
