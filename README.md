# Agent Compute Router

**Give AI agents better instincts about where computation belongs.**

Agent Compute Router (ACR) is an experimental routing layer for AI coding agents. It helps an agent recognize when a problem should stay with the LLM, move to a deterministic algorithm, use a specialized classical solver, or be evaluated for quantum/hybrid computation.

> AI agents are good at reasoning. They should not have to solve every problem by reasoning alone.

## The problem

Modern coding agents are being asked to do much more than write code. They plan implementation work, schedule tasks, analyze dependency graphs, allocate resources, reduce test suites, coordinate parallel agents, and search large configuration spaces.

Some of those are language problems.

Some are not.

A constrained scheduling problem may belong in CP-SAT. A dependency problem may belong in a graph algorithm. A satisfiability problem may belong in Z3. A numerical search may belong in an optimizer. And, in a much smaller set of cases, a problem may be worth benchmarking on quantum or quantum-hybrid infrastructure.

ACR is designed to make that distinction explicit.

## What ACR does

ACR sits between an AI agent and the compute tools available to it:

```text
AI agent
   |
   v
Agent Compute Router
   |
   +--> direct deterministic method
   +--> graph algorithm
   +--> SAT / SMT
   +--> constraint solver
   +--> numerical optimizer
   +--> GPU / accelerator
   +--> quantum simulator
   +--> hybrid quantum solver
   `--> real QPU
```

The goal is simple:

**Match the problem to the right kind of computation before spending more reasoning, time, money, or infrastructure than necessary.**

## Why this is useful

Without a routing layer, an AI agent may try to reason heuristically through a problem that already has a much better computational tool available.

For example:

```text
"Allocate 40 implementation tasks across 4 agents while respecting
file conflicts, dependencies, and execution order."
```

That is not primarily a prose-generation problem. It is a constrained scheduling problem.

ACR can classify it accordingly:

```json
{
  "classification": "constrained_scheduling",
  "recommended_backend": "cp-sat",
  "quantum_escalation": "NO",
  "reason": "Discrete scheduling with precedence and assignment constraints maps naturally to constraint programming.",
  "alternatives": ["milp", "heuristic-planner"]
}
```

The agent can then spend its reasoning on understanding the task and interpreting the result instead of manually searching the solution space.

## Quantum is not the product

ACR is **not** a "send hard problems to a quantum computer" wrapper.

Complexity alone is not evidence that quantum hardware is appropriate.

A quantum or quantum-hybrid backend should only be considered when the problem has a compatible mathematical structure and there is a meaningful reason to benchmark it against classical methods.

For example:

```bash
compute-router assess --json "Formulate this Max-Cut graph optimization as a QUBO"
```

ACR may identify that as a quantum-compatible candidate, but the expected workflow is still:

```text
formalize problem
      |
      v
establish classical baseline
      |
      v
consider quantum / hybrid candidate
      |
      v
compare results
      |
      v
verify constraints
```

A QPU has to **earn the escalation**.

## v0.1

The first release intentionally keeps the surface area small.

Current capabilities:

- deterministic workload classification
- explainable compute recommendations
- local CLI
- JSON output for agent/tool integration
- explicit quantum-escalation gate
- no required cloud account
- no required quantum account
- no paid execution
- no unsupported claims of quantum advantage

**v0.1 assesses and routes. It does not yet execute external solvers, GPUs, hybrid services, or QPUs.**

That limitation is deliberate: first make routing inspectable and testable, then add execution backends.

## Quick start

Requires Python 3.11+.

```bash
python -m pip install -e .
```

Assess a problem:

```bash
compute-router assess "Allocate 40 coding tasks across 4 agents with dependency and file-conflict constraints"
```

Request machine-readable output:

```bash
compute-router assess --json "Find an optimal schedule for tasks with precedence constraints"
```

## Example workloads

ACR is aimed at problems such as:

- multi-agent task scheduling
- dependency-aware build planning
- test-suite selection
- resource allocation
- graph partitioning
- assignment problems
- routing problems
- bin packing
- set cover
- SAT / SMT-style constraints
- configuration search
- numerical optimization
- selected quantum-compatible formulations such as QUBO / Ising problems

It is **not** intended to replace the LLM for ordinary coding, debugging, documentation, UI generation, or general reasoning.

## Design principles

ACR follows a few core rules:

1. **Use the simplest backend that fits the problem.**
2. **Do not confuse difficulty with quantum suitability.**
3. **Prefer deterministic and classical methods when they are sufficient.**
4. **Establish a classical baseline before making quantum comparisons.**
5. **Verify solver outputs against the original constraints.**
6. **Keep backends replaceable instead of coupling the router to one provider.**
7. **Explain why a route was chosen.**
8. **Measure before claiming an advantage.**

See [`docs/PRINCIPLES.md`](docs/PRINCIPLES.md).

## Where this could go

The long-term idea is a small compute-selection layer that coding agents can call automatically:

```text
compute_assess
compute_solve
compute_compare
compute_verify
compute_explain
```

Potential integrations include:

- AI coding agents
- MCP-compatible clients
- CI and test planners
- repository intelligence systems
- multi-agent coding orchestration
- local optimization toolchains
- classical solver services
- GPU compute
- quantum simulators
- hybrid quantum services
- real QPUs

The important part is not how many backends are supported.

The important part is whether the router can reliably answer:

> **What kind of computation should solve this part of the problem?**

## Roadmap

Near-term priorities:

1. structured problem intermediate representation (IR)
2. explicit variables, objectives, and constraints
3. OR-Tools / CP-SAT backend
4. Z3 backend
5. result verification layer
6. backend benchmarking
7. MCP tool interface
8. optional quantum simulator and hybrid-provider adapters

See [`docs/ROADMAP.md`](docs/ROADMAP.md).

## Repository layout

```text
src/compute_router/
  cli.py          CLI
  classifier.py   workload classification
  models.py       typed routing result
  router.py       routing policy

tests/            executable unit tests
docs/             architecture, principles, roadmap
examples/         example problem inputs
```

## Project status

**Experimental / pre-alpha.**

The current implementation is intentionally narrow. The project is looking for evidence that compute routing improves agent workflows before expanding the backend catalog.

If you are interested in AI agents, optimization, solver selection, heterogeneous compute, or practical quantum experimentation, contributions and critique are welcome.

## Contributing

See [`CONTRIBUTING.md`](CONTRIBUTING.md).

Useful contributions include:

- better workload classification
- reproducible routing benchmarks
- new structured problem types
- classical solver adapters
- verification strategies
- MCP integration
- carefully justified accelerator or quantum backends

## License

Apache-2.0. See [`LICENSE`](LICENSE).
