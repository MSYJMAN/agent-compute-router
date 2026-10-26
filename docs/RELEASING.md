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
5. Build the package and smoke test the **installed wheel** in a clean
   environment — a successful build is not evidence that the package installs
   and runs:
   ```bash
   python -m build
   python -m venv /tmp/smoke
   /tmp/smoke/bin/python -m pip install "$(ls dist/*.whl)[full]"
   python scripts/smoke_installed_wheel.py /tmp/smoke/bin/compute-router
   ```
6. Review `.github/RELEASE_TEMPLATE.md` and document limitations honestly.
7. **Merge the release changes to `main` first.** Tagging a commit that is not
   contained in `main` is rejected by the release workflow.
8. Create and push a tag named `vMAJOR.MINOR.PATCH` on the intended release commit.
9. GitHub Actions verifies, in order:
   - the tagged commit is an ancestor of `main`
   - the tag matches `pyproject.toml`
   - tests pass
   - the changelog contains the version
   - the Python package builds and the expected artifacts exist
   - the installed wheel passes the smoke test
10. If all gates pass, the workflow creates the GitHub Release and attaches the built package artifacts.

## Example

For version `0.2.0`, after the release branch is merged to `main`:

```bash
git checkout main && git pull
git tag v0.2.0
git push origin v0.2.0
```

Do not move or reuse published version tags. Do not tag a release branch
directly — the ancestry gate exists so an abandoned branch cannot be published.

## Planned release ladder

The roadmap is evidence-dependent, but the current working sequence is:

- `0.1.x` — routing foundation and reliability fixes
- `0.2.0` — verified scheduling plus experimental hybrid allocation
- `0.3.0` — backend capability registry
- `0.4.0` — evidence memory and automatic backend comparison
- `0.5.0` — MCP / agent integration
- `1.0.0` — stable interfaces and production-grade release guarantees

Quantum research runs as a parallel track rather than a release milestone; see
`docs/ROADMAP.md`. Milestones may move if experiments show a different order is
more useful, but this ladder and `docs/ROADMAP.md` must be changed together.
