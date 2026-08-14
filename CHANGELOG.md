# Changelog

All notable changes to Agent Compute Router will be documented in this file.

The project follows Semantic Versioning: `MAJOR.MINOR.PATCH`.

- **MAJOR**: incompatible or architectural breaking changes.
- **MINOR**: backward-compatible features or meaningful capability additions.
- **PATCH**: backward-compatible bug fixes, docs corrections, or small reliability improvements.

## [Unreleased]

### Added

- Release governance, templates, and tag-driven GitHub release workflow.

### Changed

- Nothing yet.

### Fixed

- Nothing yet.

### Evidence

- Release workflow validates the tag against `pyproject.toml` and runs the test suite before publishing a GitHub Release.

## [0.1.0] - 2026-08-14

### Added

- Deterministic workload classification.
- Explainable compute recommendations.
- Local CLI and JSON output.
- Explicit quantum-escalation gate.
- Local-first operation with no cloud or quantum account required.

### Known limitations

- v0.1.0 assesses and routes only.
- External solvers, GPUs, hybrid services, and QPUs are not executed yet.
