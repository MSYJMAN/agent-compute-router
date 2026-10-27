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
- Merged to `main`: **yes** — PR #3, fast-forward `2764fb7..719fac9` on
  2026-10-26. GitHub reports PR #3 `merged: true`, merge commit `719fac90`.
- Tagged: **yes** — annotated tag `v0.2.0` at `719fac9`, pushed.
- Released: **no** — no GitHub Release exists. The tag-triggered `Release`
  workflow run 40431188274 concluded `failure` in 4 seconds with an empty
  `runner` field and `steps executed: 0`, so its gates never ran. The release
  is verified **locally only**; see Current blockers.

A fast-forward was chosen deliberately so `main` is byte-identical to the
commit that passed the gates, rather than introducing an unverified merge
commit. `main` and `release/v0.2.0` are therefore both at `719fac9`.

The `v0.2.0` tag's ancestry gate is satisfied (the tag commit is contained in
`main`). To publish the release once billing is restored, re-run workflow run
40431188274 from the Actions UI; the tag does **not** need to be re-pushed.

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

Dependency-floor evidence (lowest versions installable on this interpreter,
rather than the resolved ceiling):

```bash
python -m venv /tmp/floor
/tmp/floor/bin/python -m pip install "ortools==9.12.4544" "dwave-ocean-sdk==9.4.0"
/tmp/floor/bin/python -m pip install --no-deps -e .
/tmp/floor/bin/python -m unittest discover -s tests
```

On Python 3.13 use `ortools==9.12.4544` (the lowest cp313 wheel). On 3.11/3.12
use `ortools==9.10.4067` to exercise the true declared floor — that path has
never been executed here for lack of an interpreter.

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
| GitHub Actions | `BLOCKED_BY_ACCOUNT_BILLING` | **Re-verified 2026-10-26** on run 40410271082 (head `1fec6d5`): all 4 jobs concluded `failure` in 3-4 seconds with an empty `runner` field and `steps executed: 0`. No runner was allocated and no step ran, so these failures are not evidence of source failure. Re-check `runner`/step count before trusting or blaming any CI result. |
| Live D-Wave hybrid | `BLOCKED_BY_PROVIDER_ACCESS` | Trial account lacked solver API entitlement. Challenge 001C stays blocked; 001A covers CQM semantics locally. |
| `gh` authentication | needs human | `gh` 2.103.2 is installed; `gh auth login` requires browser/MFA and cannot be automated. |

External blockers do not block the rest of the sprint. Route around them.

## Provider access state

- Ocean SDK installed locally (`dwave-ocean-sdk` 9.5.0, `dimod` 0.12.22).
- **Installing the SDK does not authorize remote execution.** No test contacts a
  provider; unit tests use local fakes or `dimod.ExactCQMSolver`.
- Live hybrid submission has never been executed from this repository.

## Important decisions

- **`agent/release-system` deleted, history archived.** The branch was deleted
  from `origin` on 2026-10-26. Its four commits had been squash-merged into
  `main`'s "Set up evidence-based release system", so they were **not** reachable
  from `main` and deleting the ref would have orphaned them. Before deletion
  they were preserved as the annotated tag `archive/agent-release-system`
  (verified to point at exactly the branch head `cf59df3`). Restore with:
  `git push origin archive/agent-release-system:refs/heads/agent/release-system`.
  Do not delete that tag. Note that a `git diff main agent/release-system` was
  empty only against the pre-merge `main`; after the v0.2 merge the branch reads
  as far behind `main`, which is expected and is not evidence of lost work.
- **Dependency ranges kept wide — floor now verified.** `ortools>=9.10,<10`
  retained, on evidence rather than assumption (2026-10-26):
  - Wheel tags from the PyPI JSON API: 9.10.4067 and 9.11.4210 ship
    `cp311`/`cp312` only; **9.12.4544 does ship `cp313`**, as does 9.13.4784.
    An earlier revision of this file claimed "9.10–9.12 ship no cp313 wheels",
    which was wrong about 9.12. The lowest cp313-installable ortools is
    **9.12.4544**, not 9.13.
  - Full suite **executed** against the floor on 3.13.15 — ortools 9.12.4544,
    dwave-ocean-sdk 9.4.0, dimod 0.12.22, protobuf 5.29.6 (vs 6.33.6 at the
    ceiling): **99 tests, 0 failures**.
  - For the 3.11/3.12 floor (9.10.4067) there is no local interpreter, so the
    suite could not be run. Instead the 9.10 cp312 wheel was inspected without
    installing: all 16 CP-SAT symbols this project uses are present
    (`add`, `add_exactly_one`, `add_max_equality`, `add_no_overlap`, `minimize`,
    `new_bool_var`, `new_int_var`, `new_interval_var`,
    `new_optional_interval_var`, `solve`, `value`, `status_name`,
    `num_branches`, `num_conflicts`, `wall_time`, and `parameters` as an
    attribute at cp_model.py:3131), as are the three `SatParameters` fields the
    code sets (`max_time_in_seconds`, `num_search_workers`, `random_seed`).
    This is static evidence, **not** an executed test: treat the 3.11/3.12
    floor as PARTIAL, not PASS.
  - The project uses the snake_case CP-SAT API throughout. That API already
    exists in 9.10, so the floor is not a PascalCase-era hazard.
- **Python 3.13 added** to CI and classifiers on local evidence (full suite
  passes on 3.13.15 with ortools 9.15.6755).
- **CI no longer triggers on `push: release/**`** — those commits were running
  twice, once for push and once for the pull request. **Confirmed effective:**
  commits `29cf16f` and `8484830` each produced two runs; the push of `1fec6d5`
  produced one (`pull_request` only).
- **The workflow definition is server-validated.** GitHub parsed the updated
  `ci.yml` and created the intended job graph (`test (3.11/3.12/3.13)` plus
  `package`), so the YAML and matrix are accepted. Only execution — and
  therefore the `@v7` action versions — remains unverified.
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
- Minimum-dependency-version testing is **done for Python 3.13** (floor suite
  passes; see Important decisions) but remains **PARTIAL overall**: Python 3.11
  and 3.12 are not installed on this machine, so the 9.10/9.11 floor is
  supported only by static wheel inspection, never by an executed test. CI
  would cover this if it could start a runner.
- Challenge 001B (local annealing/QUBO experimentation) is not started and is
  optional.

## Next trustworthy move

Publish the GitHub Release for `v0.2.0`. This is blocked only by Actions
billing: re-run run 40431188274 once billing is restored and let the workflow's
own gates produce the release and artifacts. Do not hand-create the release and
do not re-push the tag.

Two follow-ups need a GitHub token (`gh auth login`) and are otherwise ready:

- Post the v0.2.0 evidence ledger as a comment on merged PR #3.
- Post a scope-evolution status comment on Issue #2 and close it under the
  release policy. Issue #2's original title covers only "real classical solver
  execution"; v0.2 grew to include the joint-gold baseline, CQM semantic
  validation and the provider authorization boundary, so the comment should
  record that evolution rather than silently rewriting the issue.
