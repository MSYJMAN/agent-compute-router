# Architecture

## v0.2 execution boundary

ACR decomposes multi-agent development planning into allocation and sequencing.

```text
SchedulingProblem
      |
      v
local validation
      |
      +-----------------------+
      |                       |
      v                       v
CP-SAT allocation       D-Wave Hybrid CQM
classical baseline      allocation candidate
      |                 task -> agent only
      +-----------+-----------+
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

### Hybrid trust boundary

The remote CQM may contain binary task-to-agent variables, an auxiliary maximum-load variable, assignment constraints, agent-load constraints, and allocation-quality objective terms.

It must not contain start/end times, task intervals, precedence-time constraints, file-lock timing, or final verification logic. CI inspects this boundary.

### Baseline-before-belief

A hybrid candidate is accepted only when its allocation passes local validation, its fixed ownership can be sequenced by CP-SAT, the schedule passes independent verification, and the verified outcome beats the classical allocation baseline.

### Remote compute policy

Installing Ocean does not authorize remote execution. `--allow-remote` is required before Leap can be contacted. Credentials remain in Ocean's normal provider configuration rather than ACR inputs or receipts.
