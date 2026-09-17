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

## v0.2 hybrid sprint stages

A hybrid-aware sprint can contain:

1. `classical_allocation_baseline`
2. `classical_baseline_sequencing`
3. `quantum_hybrid_allocation`
4. `hybrid_candidate_classical_sequencing`

The hybrid stage is allocation-only. It may propose task-to-agent ownership, but it cannot set start/end times or bypass classical sequencing and final verification.

## Selection evidence

ACR always keeps a classical allocation baseline. A hybrid candidate is selected only when:

- the allocation passes classical validation,
- CP-SAT can sequence the fixed ownership,
- the resulting schedule passes independent verification, and
- the verified result beats the classical baseline under ACR's comparison rule.

Otherwise the final receipt records the classical allocation as selected and preserves the hybrid attempt as stage evidence.

## Remote execution evidence

If remote execution was not explicitly authorized, the hybrid stage records `REMOTE_NOT_AUTHORIZED` rather than silently contacting a provider.

Provider SDK installation therefore does not imply network use, data egress, or spend.

## Future use

Persistent receipt history can eventually answer a more useful routing question than "what solver sounds appropriate?":

> For problems with features like this one, which backend has actually produced the best verified outcomes under the user's latency, cost, privacy, and reliability constraints?

That evidence layer is intended to become the foundation of ACR's future per-instance routing policy.
