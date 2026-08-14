# Releasing Agent Compute Router

Agent Compute Router uses Semantic Versioning and evidence-based releases.

## Version policy

Use `MAJOR.MINOR.PATCH`:

- `PATCH` for backward-compatible fixes and small reliability improvements.
- `MINOR` for backward-compatible capability additions.
- `MAJOR` for incompatible or architectural breaking changes.

During pre-1.0 development, minor releases may still contain meaningful interface changes. Document them explicitly.

## Release principle

A release is justified by verified capability, not by elapsed time or feature count.

For new routing or compute capabilities, record evidence such as tests, benchmarks, constraint verification, or solver comparisons.

Quantum or hybrid support must never be described as an advantage unless measured against a relevant classical baseline.

## Release process

1. Decide the release version.
2. Update `pyproject.toml` to that version.
3. Move relevant entries from `CHANGELOG.md` under `[Unreleased]` into a dated version section.
4. Run the relevant test suite and benchmarks.
5. Review `.github/RELEASE_TEMPLATE.md` and document limitations honestly.
6. Merge the release changes to `main`.
7. Create and push an annotated or lightweight tag named `vMAJOR.MINOR.PATCH` on the intended release commit.
8. GitHub Actions verifies:
   - the tag matches `pyproject.toml`
   - the changelog contains the version
   - tests pass
   - the Python package builds
9. If all gates pass, the workflow creates the GitHub Release and attaches the built package artifacts.

## Example

For version `0.2.0`:

```bash
git tag v0.2.0
git push origin v0.2.0
```

Do not move or reuse published version tags.

## Planned release ladder

The roadmap is evidence-dependent, but the current working sequence is:

- `0.1.x` — routing foundation and reliability fixes
- `0.2.0` — real classical solver execution
- `0.3.0` — MCP/agent integration
- `0.4.0` — simulator/hybrid quantum experimentation with classical baselines
- `0.5.0` — coding-agent orchestration workloads
- `0.6.0` — benchmark-informed routing intelligence
- `1.0.0` — stable interfaces and production-grade release guarantees

Milestones may move if experiments show a different order is more useful.
