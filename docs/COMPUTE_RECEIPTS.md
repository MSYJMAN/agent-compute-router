# Compute Receipts

A **Compute Receipt** is ACR's machine-readable record of what computation was performed and why the result should or should not be trusted.

The receipt exists because an agent saying "the solver found a good answer" is not evidence.

For v0.2 a scheduling receipt records:

- a stable SHA-256 fingerprint of the normalized problem
- the routing decision
- the backend actually used
- solver status
- runtime
- objective name and value
- independently verified constraint status
- any violations
- the returned assignment schedule
- backend metrics such as branches and conflicts
- notes such as a missing optional backend
- the quantum-escalation decision

Example shape:

```json
{
  "schema_version": "1",
  "problem_type": "constrained_scheduling",
  "problem_sha256": "...",
  "route": {
    "classification": "constrained_scheduling",
    "recommended_backend": "cp-sat",
    "quantum_escalation": "NO"
  },
  "backend": "ortools-cp-sat",
  "solver_status": "OPTIMAL",
  "runtime_ms": 4.2,
  "objective": {
    "name": "minimize_makespan",
    "value": 7
  },
  "verified": true,
  "violations": [],
  "solution": {},
  "metrics": {},
  "notes": []
}
```

## Why fingerprints matter

The normalized problem is hashed before solving. Later benchmark layers can use that fingerprint to associate repeated runs with the same exact input without treating prose descriptions as stable identifiers.

The fingerprint is not intended to anonymize sensitive data. Do not assume hashing makes a proprietary problem safe to publish.

## Why verification is separate

ACR does not mark a schedule verified merely because CP-SAT returned `OPTIMAL` or `FEASIBLE`.

The verification layer independently checks the returned assignment against the original ACR problem contract, including:

- every required task is present
- no unknown task is introduced
- agent eligibility
- task duration
- dependency order
- same-agent overlap
- shared-file overlap

This separation is intentional. Future backends must earn trust through the same contract.

## Future use

Compute Receipts are designed to become the input to ACR's future benchmark and routing-intelligence layer. With comparable receipts, ACR can eventually answer a stronger question than "which solver usually fits this class?":

> For problems with this structure and budget, which available backend has actually produced the best verified outcomes?
