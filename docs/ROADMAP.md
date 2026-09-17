# Roadmap

## v0.1 — Routing seed

- [x] deterministic classifier
- [x] local CLI
- [x] JSON output
- [x] explicit quantum escalation gate
- [x] unit tests

## v0.2 — Verified hybrid sprint pipeline

- [x] structured scheduling IR
- [x] stable problem fingerprint
- [x] classical task-allocation baseline
- [x] D-Wave Leap Hybrid CQM allocation candidate
- [x] allocation-only quantum/hybrid boundary
- [x] fixed-allocation classical CP-SAT sequencing
- [x] independent allocation verification
- [x] independent schedule verification
- [x] Compute Receipt schema v2 with stage evidence
- [x] explicit remote-compute authorization
- [x] keep classical baseline when hybrid does not improve the verified result

## v0.3 — Capability registry

- [ ] backend health/capability discovery
- [ ] graph-algorithm execution backend
- [ ] Z3 / SMT backend
- [ ] backend abstention reasons
- [ ] provider cost / remote / privacy metadata

## v0.4 — Evidence memory

- [ ] persist local Compute Receipt history
- [ ] compare compatible backends automatically
- [ ] benchmark runtime, quality, feasibility, and cost
- [ ] problem-feature fingerprints
- [ ] evidence-informed per-instance routing

## v0.5 — Agent/MCP integration

- [ ] `compute_assess`
- [ ] `compute_solve`
- [ ] `compute_compare`
- [ ] `compute_verify`
- [ ] `compute_explain`

## Quantum research track

Production routing stays classical-first while research can proceed in parallel:

- [x] ACR Quantum Challenge 001 formulation: multi-agent task allocation
- [x] D-Wave Hybrid CQM adapter with strict allocation-only boundary
- [ ] reproducible benchmark suite across task count, agent count, dependency density, file-conflict density, and eligibility sparsity
- [ ] persistent comparison receipts
- [ ] IBM/QAOA allocation experiment
- [ ] warm-start QAOA from a classical relaxation
- [ ] direct QPU work only after baseline, verifier, cost policy, and meaningful experiment exist

## Later research candidates

- test-selection optimization under CI budget
- compute-backend assignment under cost/latency/privacy constraints
- dependency-graph partitioning
- multi-worktree conflict minimization
