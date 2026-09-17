# Agent Compute Router

**Give AI agents better instincts about where computation belongs — and evidence for what happened next.**

Agent Compute Router (ACR) is an experimental, local-first routing and execution layer for AI coding agents.

## v0.2: verified hybrid sprint execution

v0.2 decomposes multi-agent development planning into two different jobs:

```text
structured sprint IR
      |
      v
hard validation
      |
      +-----------------------+
      |                       |
      v                       v
classical allocation     D-Wave Hybrid CQM
baseline (CP-SAT)        allocation candidate
      |                  TASK -> AGENT ONLY
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

### Quantum/hybrid is allocation-only

The D-Wave stage may choose which eligible agent owns each task. It does **not** control task start times, end times, precedence timing, interval sequencing, shared-file locks, or final PASS/FAIL verification.

ACR always establishes an all-classical allocation baseline first. A hybrid allocation is retained only if it passes classical validation and produces a better independently verified classical schedule. Otherwise the classical baseline wins.

No quantum-advantage claim is made.

## Allocation objective

Both the classical and hybrid allocators use the same coding-oriented objective:

1. minimize maximum agent workload,
2. reduce dependency handoffs between agents,
3. reduce ownership splits for tasks touching the same files.

This keeps the benchmark fair and avoids comparing a hybrid solver against an intentionally weak baseline.

## Quick start

Classical execution:

```bash
python -m pip install -e ".[cp-sat]"
compute-router solve examples/scheduling.json --allocator classical
```

Hybrid-aware mode without remote authorization:

```bash
compute-router solve examples/scheduling.json
```

Install D-Wave support:

```bash
python -m pip install -e ".[full]"
```

After configuring normal D-Wave Ocean/Leap credentials, explicitly authorize remote execution:

```bash
compute-router solve examples/scheduling.json --allocator hybrid --allow-remote
```

Machine-readable receipt:

```bash
compute-router solve examples/scheduling.json --allocator hybrid --allow-remote --json
```

Installing the D-Wave dependency does not authorize data egress or provider usage; `--allow-remote` is required separately.

## Compute Receipts

Receipt schema v2 records every stage, including the classical baseline, hybrid candidate status, classical sequencing result, independent verification, chosen allocation backend, and declared quantum boundary.

The long-term goal is to use verified receipt history for empirical per-instance routing rather than relying on agent confidence.

## Natural-language assessment

The transparent v0.1 assessor remains available:

```bash
compute-router assess "Schedule 50 tasks across 4 agents with precedence constraints"
```

It is a routing hint, not a compiler for hard optimization constraints.

## Design rules

- classical baseline before hybrid belief
- smallest justified remote subproblem
- explicit remote authorization
- identical downstream classical sequencing for fair comparison
- independent final verification
- retain classical when hybrid does not improve the verified outcome
- no claim of quantum advantage without benchmark evidence

## Status

Experimental / pre-alpha.

Apache-2.0. See `LICENSE`.
