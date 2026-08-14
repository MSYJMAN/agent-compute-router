# Agent Compute Router

**A small decision layer for matching AI-agent subproblems to suitable compute backends.**

Agent Compute Router (ACR) is an experimental decision layer for AI coding agents. It identifies when a task should stay with the LLM, move to a deterministic algorithm or specialized classical solver, or be considered for quantum/hybrid computation.

## Why this exists

AI coding agents are increasingly asked to plan, schedule, optimize, allocate resources, analyze dependency graphs, minimize test suites, and coordinate parallel work. Those are not always language problems. ACR gives an agent a small, inspectable routing layer so it can stop trying to solve every problem with natural-language reasoning.

ACR is intentionally skeptical of quantum computing. "Complex" is not a routing criterion. Quantum/hybrid escalation is considered only when a problem has an appropriate formal structure and a classical baseline can be established.

## v0.1 scope

The first release is deliberately small:

- deterministic workload classification
- evidence-based compute recommendations
- local CLI
- JSON output for agent/tool integration
- explicit quantum escalation gate
- zero required cloud accounts
- zero required quantum accounts
- no paid execution
- no claims of quantum advantage

**v0.1 assesses and routes; it does not yet execute external solvers or QPUs.**

## Quick start

Requires Python 3.11+.

```bash
python -m pip install -e .
compute-router assess "Allocate 40 coding tasks across 4 agents with dependency and file-conflict constraints"
```

JSON output:

```bash
compute-router assess --json "Find an optimal schedule for tasks with precedence constraints"
```

Example result:

```json
{
  "classification": "constrained_scheduling",
  "recommended_backend": "cp-sat",
  "quantum_escalation": "NO",
  "reason": "Discrete scheduling with precedence/assignment constraints maps naturally to constraint programming.",
  "alternatives": ["milp", "heuristic-planner"]
}
```

A true quantum-shaped input is treated differently:

```bash
compute-router assess --json "Formulate this Max-Cut graph optimization as a QUBO"
```

ACR may return `REVIEW`, not `YES`: the intent is to permit a quantum/hybrid benchmark **after** a classical baseline, not to assume quantum superiority.

## Mental model

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
   `--> real QPU (last escalation tier)
```

## Routing policy

1. Match the backend to the mathematical structure of the workload.
2. Complexity alone does not justify quantum execution.
3. Prefer the simplest backend that can solve the problem reliably.
4. Establish a classical baseline before quantum comparisons whenever practical.
5. Validate solver outputs against the original constraints.
6. Keep optional backends replaceable.
7. Explain routing decisions and record relevant measurements.

See [`docs/PRINCIPLES.md`](docs/PRINCIPLES.md).

## Intended integrations

ACR is designed to eventually sit behind a tiny tool surface such as:

```text
compute_assess
compute_solve
compute_compare
compute_verify
compute_explain
```

Potential integrations include coding agents, MCP-compatible clients, CI planners, repository intelligence tools, and multi-agent orchestration systems.

MCP support is on the roadmap; it is **not** claimed as implemented in v0.1.

## Repository layout

```text
src/compute_router/
  cli.py          CLI
  classifier.py   deterministic workload classification
  models.py       typed routing result
  router.py       routing policy

tests/            executable unit tests
docs/             architecture, principles, roadmap
examples/         example problem inputs
```

## Status

**Experimental / pre-alpha.** The current implementation is intentionally narrow and falsifiable. Contributions should prefer measurable routing improvements over adding impressive-sounding backends.

## Contributing

See [`CONTRIBUTING.md`](CONTRIBUTING.md).

## License

Apache-2.0. See [`LICENSE`](LICENSE).
