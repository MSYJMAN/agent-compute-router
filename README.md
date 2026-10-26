# Agent Compute Router

**Give AI agents better instincts about where computation belongs — and evidence for what happened next.**

Agent Compute Router (ACR) is an experimental, local-first routing and execution layer for AI coding agents.

## v0.2: verified sprint execution with experimental hybrid allocation

v0.2 decomposes multi-agent development planning and evaluates **three** paths,
so no baseline is a strawman:

```text
                  structured sprint IR
                           |
                           v
                     hard validation
                           |
      +--------------------+--------------------+
      |                    |                    |
      v                    v                    v
CP-SAT allocation     CP-SAT joint        D-Wave Hybrid CQM
  (decomposed)      allocation+timing     allocation candidate
      |              "joint gold"          TASK -> AGENT ONLY
      |                    |                    |
      +----------+---------+--------------------+
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

No quantum-advantage claim is made. Every receipt carries
`quantum_advantage_claimed: false`.

### Two winners, because they are different questions

- **Research winner** — who won the fair allocator comparison? The decomposed
  classical allocator and the hybrid allocator both hand a fixed ownership map
  to the *identical* classical sequencer, so the comparison isolates allocation
  quality.
- **Production winner** — who produced the strongest independently verified
  schedule, including the joint classical model?

A hybrid allocator can beat the decomposed classical allocator and still lose to
the strongest classical baseline. That is a research result, not a quantum
advantage, and ACR reports it as exactly that.

The decomposed allocator minimizes maximum agent load without seeing precedence
timing, so it is beatable: on the repository's regression fixture it reaches
makespan 12 where the joint model reaches 9. Benchmarking a hybrid allocator
only against the decomposed path would flatter it, which is why the joint path
exists.

## Allocation objective

All allocators use the same coding-oriented objective:

1. minimize maximum agent workload,
2. reduce dependency handoffs between agents,
3. reduce ownership splits for tasks touching the same files.

Scores are always recomputed locally from the allocation itself. A backend
cannot win the comparison by reporting a number its own allocation does not
support.

## Quick start

Classical execution is the default:

```bash
python -m pip install -e ".[cp-sat]"
compute-router solve examples/scheduling.json
```

Machine-readable receipt:

```bash
compute-router solve examples/scheduling.json --json
```

Add the experimental hybrid path. Without remote authorization the hybrid stage
records `REMOTE_NOT_AUTHORIZED` and no provider is contacted:

```bash
compute-router solve examples/scheduling.json --allocator hybrid
```

Install D-Wave support:

```bash
python -m pip install -e ".[full]"
```

After configuring normal D-Wave Ocean/Leap credentials, explicitly authorize remote execution:

```bash
compute-router solve examples/scheduling.json --allocator hybrid --allow-remote
```

Remote hybrid execution requires **both** flags:

```text
--allocator hybrid  (select the experiment)
       +
--allow-remote      (authorize provider contact)
```

Either alone is insufficient. Installing the D-Wave dependency does not authorize data egress or provider usage.

## Compute Receipts

Receipt schema v2 records every stage, including both classical paths, hybrid candidate status, classical sequencing result, independent verification, per-path makespans, the two winners, and the declared quantum boundary.

Provider failures are recorded with a narrow state — `CREDENTIALS_MISSING`, `AUTHENTICATION_FAILED`, `PROVIDER_ACCESS_REQUIRED`, `PROVIDER_UNAVAILABLE`, `NETWORK_FAILURE` and others — because each implies a different operator action. Provider messages are sanitized, so receipts carry no tokens or local paths.

The long-term goal is to use verified receipt history for empirical per-instance routing rather than relying on agent confidence.

## Natural-language assessment

The transparent v0.1 assessor remains available:

```bash
compute-router assess "Schedule 50 tasks across 4 agents with precedence constraints"
```

It is a routing hint, not a compiler for hard optimization constraints.

## Design rules

- classical baseline before hybrid belief
- compare against the *strongest* classical method, not the most convenient one
- smallest justified remote subproblem
- explicit remote authorization, enforced at more than one layer
- identical downstream classical sequencing for fair comparison
- independent final verification
- never trust a backend's self-reported score
- retain classical when hybrid does not improve the verified outcome
- no claim of quantum advantage without benchmark evidence

## Status

Experimental / pre-alpha.

v0.2.0 is implemented and verified locally; it is **not yet merged, tagged, or
released**. See `AGENTS.md` for current release state and blockers.

Apache-2.0. See `LICENSE`.
