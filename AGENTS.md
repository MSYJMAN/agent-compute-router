# Agent Compute Router — agent operating notes

Persistent state for autonomous agents working on this repository. Keep it
current: the next agent should not need to re-derive any of this.

## Project purpose

ACR is an experimental, local-first compute routing and execution layer for AI
coding agents. It decides where a subproblem belongs, executes it on a real
solver, verifies the result independently, and emits a Compute Receipt as
machine-readable evidence.

The project's central claim is evidential, not performance-based: **no quantum
advantage is claimed anywhere**, and the code is structured so such a claim
cannot be made accidentally.

## Current release target

`v0.2.0` — verified scheduling plus experimental hybrid allocation.

- Implemented: yes
- Verified locally: yes (see Test commands)
- Merged to `main`: **no**
- Tagged: **no**
- Released: **no**

Work happens on `release/v0.2.0`, tracked by PR #3. Do **not** create the
`v0.2.0` tag until the branch is merged to `main`; the release workflow now
rejects a tag that is not an ancestor of `main`.

## Architectural invariants

Do not weaken these without recording the decision here.

```
SchedulingProblem (validated IR)
        |
        v
 +---------------------+-------------------------+
 |                     |                         |
 v                     v                         v
CP-SAT allocation   CP-SAT joint             D-Wave Hybrid CQM
(decomposed)        allocation + timing      allocation candidate
 |                  "classical_joint_gold"   TASK -> AGENT ONLY
 |                     |                         |
 +----------+----------+-------------------------+
            v
   classical CP-SAT sequencing (fixed ownership)
            v
   independent classical verifier
            v
       Compute Receipt
```

1. **Allocation-only hybrid boundary.** The CQM may contain task-to-agent binary
   variables and one auxiliary max-load integer variable. It must never contain
   start times, end times, intervals, precedence timing, file-lock timing, or
   verification logic. Enforced by `tests/test_cqm_semantics.py`.
2. **Classical is the default.** `solve_schedule(allocator="classical")` and
   `compute-router solve` default to classical. Hybrid requires
   `--allocator hybrid` **and** `--allow-remote`. Either alone is insufficient,
   and the gate is enforced in both the router and the backend.
3. **Three paths, two winners.** `research_winner` answers the fair
   allocator-vs-allocator comparison (decomposed vs hybrid, identical
   downstream sequencer). `production_winner` answers which path produced the
   strongest verified schedule, including `classical_joint`. A hybrid research
   win must never be reported as a production win.
4. **Never trust a backend's self-reported score.** Allocation scores used for
   selection are always recomputed locally from the allocation itself.
   Disagreements are recorded as stage evidence.
5. **Receipts carry no secrets.** Provider messages are sanitized at exception
   construction (`src/compute_router/provider.py`), stripping token-shaped and
   path-shaped substrings.
6. **Provider states stay narrow.** A missing credential, a denied entitlement,
   and an offline solver are different facts. Do not collapse them back into a
   single `BACKEND_UNAVAILABLE`.

## Verification evidence (last full run)

| Gate | Result |
| --- | --- |
| Full local suite | **99 tests, 0 failures, 0 skipped** |
| Environment | Python 3.13.15, ortools 9.15.6755, dwave-ocean-sdk 9.5.0, dimod 0.12.22 |
| Package build | sdist + wheel built |
| Fresh-wheel smoke | 4/4 checks passed against a clean-venv install |
| GitHub Actions | never executed — billing blocked |
| Live D-Wave | never executed — provider entitlement |

The test count is not a target; it is whatever the architectural evidence
requires. Do not preserve a number.

## Test commands

```bash
python -m pip install -e ".[full]"
python -m unittest discover -s tests -v
```

`tests/test_release_metadata.py` duplicates the release workflow's gates
(version/changelog agreement, licence completeness, classifier/matrix
agreement, secret hygiene) so they are verifiable locally while CI is blocked.

Packaging and installed-behaviour evidence:

```bash
python -m build
python -m venv /tmp/smoke
/tmp/smoke/bin/python -m pip install "$(ls dist/*.whl)[full]"
python scripts/smoke_installed_wheel.py /tmp/smoke/bin/compute-router
```

On Windows use `.venv/Scripts/python.exe` and a **short** venv path; the
default scratch paths exceed the Windows venv path limit.

## Release commands

See `docs/RELEASING.md`. Gates enforced by `.github/workflows/release.yml`:
tag is an ancestor of `main`, tag matches `pyproject.toml`, changelog contains
the version, tests pass, artifacts build and exist, installed wheel smoke
passes.

## Current blockers

| Blocker | State | Notes |
| --- | --- | --- |
| GitHub Actions | `BLOCKED_BY_ACCOUNT_BILLING` | Previously observed failing jobs started no runner and ran no steps, so they were not evidence of source failure. Re-verify before trusting any CI result. |
| Live D-Wave hybrid | `BLOCKED_BY_PROVIDER_ACCESS` | Trial account lacked solver API entitlement. Challenge 001C stays blocked; 001A covers CQM semantics locally. |
| `gh` authentication | needs human | `gh` 2.103.2 is installed; `gh auth login` requires browser/MFA and cannot be automated. |

External blockers do not block the rest of the sprint. Route around them.

## Provider access state

- Ocean SDK installed locally (`dwave-ocean-sdk` 9.5.0, `dimod` 0.12.22).
- **Installing the SDK does not authorize remote execution.** No test contacts a
  provider; unit tests use local fakes or `dimod.ExactCQMSolver`.
- Live hybrid submission has never been executed from this repository.

## Important decisions

- **Dependency ranges kept wide.** `ortools>=9.10,<10` retained even though
  9.10–9.12 ship no cp313 wheels; pip resolves 9.13+ on Python 3.13, and
  narrowing the floor would drop working 3.11/3.12 installs.
- **Python 3.13 added** to CI and classifiers on local evidence (full suite
  passes on 3.13.15 with ortools 9.15.6755).
- **CI no longer triggers on `push: release/**`** — those commits were running
  twice, once for push and once for the pull request.
- **`INVALID_SAMPLE` is reachable only via an untrusted sampleset.** A genuine
  CQM marks malformed samples infeasible first, so that path is tested with a
  sampler that falsely claims feasibility.
- **`agent/release-system` carries no unique work.** `git diff main
  origin/agent/release-system` is empty; its four commits were already merged
  into main's "Set up evidence-based release system". It is safe to delete, but
  deletion is a shared-state action left to the repository owner. Re-verify the
  empty diff before deleting.
- **CQM construction is hash-seed independent.** Verified identical variable
  order, energy and allocation under `PYTHONHASHSEED` 0/1/12345/99999. Set
  iteration in `build_cqm` is sorted anyway, because that independence
  currently relies on variables being registered earlier in a deterministic
  loop.

## Known defects / open work

- GitHub CI has never executed these workflows; action major versions
  (`checkout@v7`, `setup-python@v7`) are verified to exist and the YAML parses,
  but are **unverified by execution**.
- Minimum-dependency-version testing is untested locally (only Python 3.13.15
  is installed on the development machine).
- Challenge 001B (local annealing/QUBO experimentation) is not started and is
  optional.

## Next trustworthy move

Merge `release/v0.2.0` into `main` via PR #3, then tag `v0.2.0` so the release
workflow's ancestry gate is satisfied. Both steps need GitHub access.
