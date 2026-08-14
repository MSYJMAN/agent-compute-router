# Roadmap

## v0.1 — Routing seed

- [x] deterministic classifier
- [x] local CLI
- [x] JSON output
- [x] explicit quantum escalation gate
- [x] unit tests

## v0.2 — Structured problem IR

- [ ] typed variables, constraints, objectives
- [ ] JSON input schema
- [ ] explicit evidence fields
- [ ] explainable routing rules

## v0.3 — First executable classical backends

- [ ] graph algorithms
- [ ] OR-Tools / CP-SAT adapter
- [ ] Z3 adapter
- [ ] independent constraint verification

## v0.4 — Benchmark layer

- [ ] run multiple compatible backends
- [ ] compare runtime, feasibility, objective quality, and cost
- [ ] persist local benchmark history

## v0.5 — Agent/MCP integration

- [ ] `compute_assess`
- [ ] `compute_solve`
- [ ] `compute_compare`
- [ ] `compute_verify`
- [ ] `compute_explain`

## v0.6 — Quantum/hybrid adapters

Only after the classical benchmark and verification layers exist:

- [ ] Qiskit simulator adapter
- [ ] D-Wave hybrid adapter
- [ ] IBM Quantum adapter
- [ ] explicit spend/permission policy
- [ ] classical-baseline enforcement

## Research track

- [ ] anonymous problem fingerprints
- [ ] empirical routing model learned from benchmark history
- [ ] multi-agent coding-sprint scheduler
- [ ] test-selection optimizer
- [ ] dependency-graph optimization benchmarks
