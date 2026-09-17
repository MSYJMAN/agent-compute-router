# Changelog

All notable changes to Agent Compute Router are documented in this file.

The project follows Semantic Versioning: `MAJOR.MINOR.PATCH`.

- **MAJOR**: incompatible or architectural breaking changes.
- **MINOR**: backward-compatible features or meaningful capability additions.
- **PATCH**: backward-compatible bug fixes, docs corrections, or small reliability improvements.

## [Unreleased]

### Added

- Nothing yet.

### Changed

- Nothing yet.

### Fixed

- Nothing yet.

## [0.2.0] - 2026-09-16

### Added

- Structured scheduling problem IR with validation for tasks, durations, dependencies, eligible agents, and file ownership.
- Stable SHA-256 problem fingerprints over normalized structured inputs.
- Optional OR-Tools CP-SAT execution backend.
- Multi-agent makespan minimization with precedence, agent-capacity, eligibility, and shared-file conflict constraints.
- Independent schedule verification that does not trust solver status alone.
- Machine-readable **Compute Receipts** containing route, backend, solver status, runtime, objective, verification evidence, solution, and backend metrics.
- `compute-router solve` command for structured scheduling JSON.
- CI workflow that installs the CP-SAT extra and runs the full test suite on Python 3.11 and 3.12.

### Changed

- Package version advanced to `0.2.0`.
- Release verification now installs the CP-SAT extra before running tests.
- The roadmap now treats quantum as a later benchmark backend, after verified classical execution and comparison.

### Evidence

- Existing v0.1 routing tests remain in place.
- New tests cover invalid scheduling IR, dependency cycles, independent verification, shared-file conflicts, and CP-SAT execution.
- CP-SAT runs with one worker and a fixed seed in v0.2 to prioritize reproducibility over maximum throughput.

### Known limitations

- v0.2 executes only the constrained scheduling problem family.
- Natural-language `assess` remains a transparent heuristic classifier and is not used to invent solver constraints.
- OR-Tools is optional and must be installed with the `cp-sat` extra to execute schedules.
- No benchmark portfolio, MCP server, GPU backend, hybrid quantum service, or QPU execution exists yet.

## [0.1.0] - 2026-08-14

### Added

- Deterministic workload classification.
- Explainable compute recommendations.
- Local CLI and JSON output.
- Explicit quantum-escalation gate.
- Local-first operation with no cloud or quantum account required.

### Known limitations

- v0.1.0 assesses and routes only.
- External solvers, GPUs, hybrid services, and QPUs are not executed.
