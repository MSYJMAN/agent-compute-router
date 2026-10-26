# Changelog

All notable changes to Agent Compute Router are documented in this file.

The project follows Semantic Versioning: `MAJOR.MINOR.PATCH`.

## [Unreleased]

- Nothing yet.

## [0.2.0] - 2026-10-26

### Added

- Structured scheduling problem IR with validation for tasks, durations, dependencies, eligible agents, and file ownership.
- Stable SHA-256 problem fingerprints over normalized structured inputs.
- Decomposed classical OR-Tools CP-SAT task-allocation baseline.
- Joint classical CP-SAT baseline (`classical_joint_gold`) solving allocation and timing in one model, as the strongest credible classical method.
- Optional D-Wave Leap Hybrid CQM task-to-agent allocator.
- Strict quantum/hybrid boundary: remote compute may choose task ownership only; all timing, precedence, interval sequencing, shared-file locking, and final verification stay classical.
- Allocation objective that prioritizes maximum agent load, then dependency handoffs and shared-file ownership splits.
- Classical CP-SAT sequencing with fixed task ownership.
- Independent allocation verification and final schedule verification.
- Separate `research_winner` and `production_winner` receipt fields, so a hybrid win in the fair allocator comparison cannot be reported as a production win.
- Narrow provider state taxonomy distinguishing missing credentials, rejected authentication, denied entitlement, provider unavailability, network failure, and unclassified execution errors.
- Sanitization of provider diagnostics so receipts carry no tokens, signed URLs, or local filesystem paths.
- Explicit `--allow-remote` gate before any D-Wave Leap submission, enforced in both the router and the backend boundary.
- Compute Receipt schema v2 with per-stage evidence and per-path makespans.
- ACR Quantum Challenge 001A: local CQM semantic validation using `dimod.ExactCQMSolver`, cross-validated against the independent CP-SAT allocator formulation.
- Deterministic hybrid orchestration coverage for provider failure, malformed samples, sequencing failure, and verifier rejection, using local fakes only.
- `scripts/smoke_installed_wheel.py`, exercising a freshly installed wheel so CI and local release verification produce the same evidence.
- Dependabot configuration for Python dependencies and GitHub Actions on a monthly cadence.

### Changed

- **The default allocator is now `classical`.** Previously both the API and CLI defaulted to `hybrid`.
- `solve` supports `--allocator classical|hybrid` and optional `--hybrid-seconds`.
- Allocation scores used for selection are recomputed locally from the allocation rather than taken from a backend's self-reported objective value; disagreements are recorded as stage evidence.
- Stage names are explicit about method class: `classical_decomposed_allocation`, `classical_decomposed_sequencing`, `classical_joint_gold`.
- `full` installs both OR-Tools and D-Wave Ocean SDK 9.x for local/CI model tests; live D-Wave credentials are not required for CI.
- Release workflow now rejects a tag whose commit is not an ancestor of `main`, verifies the built artifacts exist, and smoke tests the installed wheel.
- CI no longer runs on `push` to `release/**`, which duplicated every pull-request run; added a concurrency group and Python 3.13.
- `actions/checkout` and `actions/setup-python` updated to `v7`.
- Packaging metadata declares Python 3.13 support and uses the SPDX `Apache-2.0` license expression with a modern setuptools minimum.

### Fixed

- `LICENSE` contained only a 17-line boilerplate notice with no numbered sections or appendix, while the project declared Apache-2.0. Replaced with the canonical 202-line text.
- `docs/RELEASING.md` and `docs/ROADMAP.md` described contradictory release ladders.

### Evidence policy

- Both classical paths are always computed; the hybrid path never runs alone.
- Hybrid allocation must pass classical validation before it can be sequenced.
- Hybrid allocation is sequenced by the same classical CP-SAT scheduler as the decomposed baseline, so the comparison isolates allocation quality.
- Final schedules are independently verified.
- Every receipt carries `quantum_advantage_claimed: false`.
- This release makes no claim of quantum advantage.

### Known limitations

- A live D-Wave benchmark requires operator-supplied Leap credentials and may incur provider usage/cost. Challenge 001C has never been executed.
- GitHub Actions has not executed these workflows; the updated action major versions are verified to exist and the YAML parses, but are unverified by execution.
- Minimum-dependency-version combinations are untested; local verification used ortools 9.15.6755 and dwave-ocean-sdk 9.5.0 on Python 3.13.15.
- v0.2 supports one optimization family: multi-agent development sprint allocation + scheduling, objective `minimize_makespan` only.
- No persistent receipt database, MCP server, IBM/QAOA execution, or direct QPU execution exists yet.

## [0.1.0] - 2026-08-14

### Added

- Deterministic workload classification.
- Explainable compute recommendations.
- Local CLI and JSON output.
- Explicit quantum-escalation gate.
- Local-first operation with no cloud or quantum account required.
