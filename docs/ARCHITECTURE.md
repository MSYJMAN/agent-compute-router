# Architecture

## v0.2 execution boundary

ACR decomposes multi-agent development planning into allocation and sequencing,
and evaluates three paths so that no baseline is a strawman.

```text
                 SchedulingProblem
                         |
                         v
                  local validation
                         |
      +------------------+------------------+
      |                  |                  |
      v                  v                  v
CP-SAT allocation   CP-SAT joint      D-Wave Hybrid CQM
 (decomposed)       allocation+timing  allocation candidate
      |             "joint gold"        task -> agent only
      |                  |                  |
      +---------+--------+------------------+
                |
                v
     classical CP-SAT sequencing
 fixed ownership + precedence + file locks
                |
                v
     independent classical verifier
                |
                v
           Compute Receipt
```

### The three paths

| Path | What it is | Why it exists |
| --- | --- | --- |
| `classical_decomposed` | CP-SAT allocation, then CP-SAT sequencing | The fair allocator-vs-allocator comparison partner for the hybrid path |
| `classical_joint` | One CP-SAT model solving allocation and timing together | The strongest credible classical method, and the production yardstick |
| `hybrid` | D-Wave CQM allocation, then the *same* classical sequencer | The experimental allocation candidate |

The decomposed allocator minimizes maximum agent load without seeing precedence
timing, so it can be beaten. On the regression fixture in
`tests/test_baselines.py` it reaches makespan 12 where the joint model reaches 9.
Comparing a hybrid allocator only against the decomposed path would therefore
flatter it.

### Two winners

A receipt answers two separate questions, because conflating them is how a
hybrid result gets overstated.

- **`research_winner`** — who won the fair allocator comparison? Both allocators
  produce a fixed ownership map and hand it to an identical classical sequencer,
  so the comparison isolates allocation quality. Values: `classical_decomposed`,
  `hybrid`, `tie`, `unavailable`. The joint path is deliberately excluded: it is
  a different method class, not a different allocator.
- **`production_winner`** — who produced the strongest independently verified
  schedule? Values: `classical_joint`, `classical_decomposed`, `hybrid`,
  `unavailable`.

A hybrid allocator can win the research comparison and still lose production to
the joint classical baseline. That is a research result, not a quantum
advantage, and the receipt says so explicitly.

The production decision is ordered and deterministic: lowest verified makespan,
then lowest allocation score, then a fixed conservative path order. Nothing
depends on solver iteration order.

### Hybrid trust boundary

The remote CQM may contain binary task-to-agent variables, one auxiliary
maximum-load integer variable, assignment constraints, agent-load constraints,
and allocation-quality objective terms.

It must not contain start/end times, task intervals, precedence-time
constraints, file-lock timing, or final verification logic. The test suite
inspects this boundary directly and also solves the CQM exactly with
`dimod.ExactCQMSolver` to confirm the model means what ACR intends.

### Nothing a backend reports is trusted

A backend's self-reported objective value never decides selection. Allocation
scores are recomputed locally from the allocation itself, using the same
objective for all three paths. If a backend's reported score disagrees with the
recomputed score, the receipt records the disagreement as stage evidence.

Likewise, a sampler's feasibility claim is not trusted: every decoded
allocation is independently validated before it can be sequenced.

### Baseline-before-belief

A hybrid candidate is accepted only when its allocation passes local
validation, its fixed ownership can be sequenced by CP-SAT, the schedule passes
independent verification, and the verified outcome beats every classical path.

### Remote compute policy

Installing Ocean does not authorize remote execution.

```text
--allocator hybrid   (select the experiment)
      +
--allow-remote       (authorize provider contact)
      =
remote hybrid execution
```

Either one alone is insufficient. The gate is enforced twice: in the router, and
again at the backend boundary, so a direct library call cannot reach a provider
unintentionally. Credentials stay in Ocean's normal provider configuration and
never appear in ACR inputs or receipts.

### Provider states

Failures are classified narrowly, because each implies a different operator
action:

```text
REMOTE_NOT_AUTHORIZED     BACKEND_UNAVAILABLE
CREDENTIALS_MISSING       AUTHENTICATION_FAILED
PROVIDER_ACCESS_REQUIRED  PROVIDER_UNAVAILABLE
NETWORK_FAILURE           NO_FEASIBLE_SAMPLE
INVALID_SAMPLE            EXECUTION_ERROR
OPTIMAL                   FEASIBLE
```

A provider that never answered did not lose a comparison: those states yield
`research_winner = unavailable`, never `classical_decomposed`. An unknown
failure is `EXECUTION_ERROR`, never a success.
