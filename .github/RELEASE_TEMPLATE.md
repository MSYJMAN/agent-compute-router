# Agent Compute Router Release

Use this template for every GitHub Release.

## What's New

Summarize the user-visible or developer-visible changes.

## Why It Matters

Explain what this release makes possible or improves.

## Evidence

Include the validation that justifies the release:

- tests run
- benchmarks run
- regression checks
- solver comparisons, when relevant
- quantum/classical comparison, when relevant

Do not claim an advantage that was not measured.

## Known Limitations

State what still does not work, remains experimental, or lacks evidence.

## Breaking Changes

State migration requirements or write `None`.

## Upgrade

Provide concise upgrade instructions if needed.

## Next

State the next trustworthy milestone, not a speculative feature dump.

---

### Release gate

Before publishing, confirm:

- [ ] `pyproject.toml` version matches the release tag.
- [ ] `CHANGELOG.md` contains the release entry.
- [ ] Relevant tests pass.
- [ ] Known regressions are documented.
- [ ] New capability has evidence, not only implementation.
- [ ] No unsupported quantum-advantage claim is present.
- [ ] Breaking changes are explicit.
