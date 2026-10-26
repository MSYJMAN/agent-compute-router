# Compute Receipts

A Compute Receipt is ACR's machine-readable evidence record for a routed computation.

## Why receipts exist

Agent narration is not enough to establish that a specialist backend was appropriate, ran successfully, or returned a result that satisfied the original contract. Receipts preserve comparable evidence that can later support benchmarking and empirical routing.

## Schema v2

A scheduling receipt records:

- problem type and stable SHA-256 fingerprint
- routing decision
- selected backend pipeline
- final solver status
- end-to-end runtime
- final makespan objective
- independent verification result
- final schedule and any violations
- the two winners (see below)
- summary metrics and notes
- an ordered list of compute stages

Each stage can record:

- stage name
- backend
- status
- runtime
- stage-specific objective
- independent verification status
- violations
- backend metrics
- notes

## v0.2 sprint stages

A classical sprint contains:

1. `classical_decomposed_allocation`
2. `classical_decomposed_sequencing`
3. `classical_joint_gold`

A hybrid-aware sprint adds:

4. `quantum_hybrid_allocation`
5. `hybrid_candidate_classical_sequencing` — only when the hybrid allocation
   was returned and passed independent validation

The hybrid stage is allocation-only. It may propose task-to-agent ownership, but it cannot set start/end times or bypass classical sequencing and final verification.

## Two winners

```json
"winners": {
  "research": "hybrid",
  "production": "classical_joint"
}
```

- **`research`** — the fair allocator-vs-allocator comparison. Both allocators
  hand a fixed ownership map to the identical classical sequencer, so the
  comparison isolates allocation quality. Values: `classical_decomposed`,
  `hybrid`, `tie`, `unavailable`.
- **`production`** — which path produced the strongest independently verified
  schedule. Values: `classical_joint`, `classical_decomposed`, `hybrid`,
  `unavailable`.

The receipt above is the honest reading of the §13 scenario: the hybrid
allocator beat the decomposed classical allocator, and lost to the strongest
classical baseline. The production winner is classical. `metrics` carries
`quantum_advantage_claimed: false` in every receipt ACR emits.

Per-path makespans and allocation scores are recorded as
`<path>_makespan` and `<path>_allocation_score` metrics so a reader can check
the decision rather than trust the winner fields.

## Selection evidence

The production decision is ordered and deterministic:

1. lowest independently verified makespan
2. lowest allocation score (better balance and fewer handoffs at equal speed)
3. a fixed conservative path order, so a full tie never depends on solver
   iteration order

A hybrid candidate can only be selected when its allocation passes classical
validation, CP-SAT can sequence the fixed ownership, the resulting schedule
passes independent verification, and it wins that ordering outright.

Otherwise the receipt records a classical path as the production winner and
preserves the hybrid attempt as stage evidence.

## Backend-reported values are not trusted

Allocation scores used for selection are recomputed locally from the allocation
itself. A backend cannot win the comparison by reporting a favourable number its
own allocation does not support. When a backend-reported score disagrees with
the locally recomputed score, the stage note records both and states which was
used.

## Remote execution evidence

If remote execution was not explicitly authorized, the hybrid stage records
`REMOTE_NOT_AUTHORIZED` rather than silently contacting a provider. Provider SDK
installation therefore does not imply network use, data egress, or spend.

Provider failures are recorded with a narrow state, because each implies a
different operator action:

| State | Meaning |
| --- | --- |
| `REMOTE_NOT_AUTHORIZED` | Hybrid selected, remote not authorized |
| `BACKEND_UNAVAILABLE` | Provider SDK not installed |
| `CREDENTIALS_MISSING` | No readable provider credentials |
| `AUTHENTICATION_FAILED` | Credentials presented and rejected |
| `PROVIDER_ACCESS_REQUIRED` | Account lacks entitlement for the solver |
| `PROVIDER_UNAVAILABLE` | Provider reachable, solver failed or offline |
| `NETWORK_FAILURE` | Transport-level failure or timeout |
| `NO_FEASIBLE_SAMPLE` | Provider returned no feasible sample |
| `INVALID_SAMPLE` | Returned sample did not decode to one agent per task |
| `EXECUTION_ERROR` | Unclassified failure — never treated as success |

A state in which the provider never answered yields
`research_winner: unavailable`, not a classical win. ACR does not report a
comparison that never happened.

## Receipts carry no secrets

Provider diagnostics can embed API tokens, signed URLs, and local filesystem
paths. Messages are sanitized before they are stored, replacing token-shaped and
path-shaped substrings with `[redacted]`. Receipts are intended to be shareable
evidence.

## Future use

Persistent receipt history can eventually answer a more useful routing question than "what solver sounds appropriate?":

> For problems with features like this one, which backend has actually produced the best verified outcomes under the user's latency, cost, privacy, and reliability constraints?

That evidence layer is intended to become the foundation of ACR's future per-instance routing policy.
