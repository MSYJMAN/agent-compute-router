# Roadmap

## v0.1 — Routing seed

- [x] deterministic natural-language classifier
- [x] local CLI
- [x] JSON output
- [x] explicit quantum escalation gate
- [x] unit tests

## v0.2 — First verified execution loop

- [x] structured scheduling IR
- [x] stable problem fingerprint
- [x] OR-Tools / CP-SAT execution backend
- [x] multi-agent task assignment
- [x] precedence constraints
- [x] agent eligibility constraints
- [x] shared-file conflict constraints
- [x] independent result verification
- [x] machine-readable Compute Receipt
- [x] graceful optional-backend failure
- [x] PR/push CI with CP-SAT installed

v0.2 deliberately supports one executable problem family well instead of pretending arbitrary prose can be safely converted into solver constraints.

## v0.3 — Backend registry + second problem family

- [ ] backend capability registry
- [ ] explicit backend availability/health report
- [ ] deterministic graph backend
- [ ] Z3 / SMT backend
- [ ] stable backend execution protocol
- [ ] user-selectable execution budgets
- [ ] structured verification contracts per problem type

## v0.4 — Benchmark and compare

- [ ] `compute_compare`
- [ ] run multiple compatible backends against the same normalized problem
- [ ] compare runtime, feasibility, objective quality, and cost
- [ ] persist local Compute Receipt history
- [ ] routing decisions informed by historical evidence
- [ ] explicit abstain/no-evidence outcome

## v0.5 — Agent / MCP integration

- [ ] `compute_assess`
- [ ] `compute_solve`
- [ ] `compute_compare`
- [ ] `compute_verify`
- [ ] `compute_explain`
- [ ] compact agent-facing schemas
- [ ] permissions and spend policy

## v0.6 — Quantum/hybrid lab

Only after classical comparison and verification are mature:

- [ ] Qiskit simulator adapter
- [ ] D-Wave hybrid adapter
- [ ] IBM Quantum adapter
- [ ] explicit remote-execution permission
- [ ] spend limits
- [ ] classical-baseline enforcement
- [ ] no quantum-advantage claim without measured evidence

## Research track

- [ ] anonymous-safe problem feature extraction (without claiming hashes anonymize data)
- [ ] empirical per-instance solver selection
- [ ] multi-agent coding-sprint scheduler
- [ ] test-selection optimizer
- [ ] dependency-graph optimization benchmarks
- [ ] solver portfolio scheduling under a fixed compute budget
