# Agent Compute Router

**Give AI agents better instincts about where computation belongs — and evidence for what happened next.**

Agent Compute Router (ACR) is an experimental, local-first routing and execution layer for AI coding agents. It helps an agent recognize when a problem should stay with the LLM, move to a deterministic algorithm, use a specialized classical solver, or later be evaluated for accelerator or quantum/hybrid computation.

> AI agents are good at reasoning. They should not have to solve every problem by reasoning alone.

## The problem

Coding agents increasingly plan implementation work, schedule tasks, analyze dependency graphs, allocate resources, reduce test suites, coordinate parallel workers, and search large configuration spaces.

Some of those are language problems.

Some are not.

A constrained schedule may belong in CP-SAT. A dependency problem may belong in a graph algorithm. A satisfiability problem may belong in Z3. A numerical search may belong in an optimizer. A much smaller set of problems may eventually justify a quantum or hybrid benchmark.

ACR makes that boundary explicit.

## What changed in v0.2

v0.1 could answer:

```text
"This looks like constrained scheduling. Try CP-SAT."
```

v0.2 can execute one problem family end-to-end:

```text
structured scheduling problem
        |
        v
validate problem contract
        |
        v
route to CP-SAT
        |
        v
solve
        |
        v
independently verify
        |
        v
emit Compute Receipt
```

The v0.2 scheduling model supports:

- multiple agents
- integer task durations
- task dependencies
- per-task eligible agents
- shared-file conflict prevention
- makespan minimization
- bounded solve time
- reproducible CP-SAT defaults

v0.2 intentionally solves **one structured problem family well** instead of pretending arbitrary natural language can be safely converted into optimization constraints.

## Compute Receipts

Every executable solve returns a **Compute Receipt**: a machine-readable evidence record containing:

- normalized problem SHA-256 fingerprint
- routing decision
- backend used
- solver status
- runtime
- objective value
- independent verification result
- constraint violations, if any
- returned solution
- backend metrics
- quantum-escalation decision

This is the foundation for future benchmarking and empirical routing.

See [`docs/COMPUTE_RECEIPTS.md`](docs/COMPUTE_RECEIPTS.md).

## Quick start

Requires Python 3.11+.

Install the lightweight routing core:

```bash
python -m pip install -e .
```

Assess a natural-language subproblem:

```bash
compute-router assess "Schedule 50 tasks across 4 agents with precedence constraints"
```

For executable scheduling, install the optional CP-SAT backend:

```bash
python -m pip install -e ".[cp-sat]"
```

Then solve the included example:

```bash
compute-router solve examples/scheduling.json
```

Machine-readable output:

```bash
compute-router solve examples/scheduling.json --json
```

## Scheduling input

v0.2 does **not** ask the classifier to invent hard constraints from prose.

The solver receives structured JSON:

```json
{
  "agents": ["dev-a", "dev-b"],
  "tasks": [
    {
      "id": "schema",
      "duration": 3,
      "files": ["src/schema.py"]
    },
    {
      "id": "api",
      "duration": 2,
      "depends_on": ["schema"],
      "eligible_agents": ["dev-a", "dev-b"],
      "files": ["src/api.py"]
    }
  ],
  "objective": "minimize_makespan"
}
```

If `eligible_agents` is omitted, all declared agents are eligible.

Input validation rejects unknown dependencies, dependency cycles, invalid durations, duplicate identifiers, and unknown agents before a solver runs.

## Independent verification

A solver returning `OPTIMAL` is not, by itself, ACR's definition of verified.

After CP-SAT returns a schedule, ACR independently checks:

- every expected task is assigned
- no unknown task appears
- assigned agents are valid and eligible
- durations match
- dependencies are respected
- one agent is not running overlapping tasks
- tasks touching the same declared file do not overlap

Only then does the receipt report `verified: true`.

## Why CP-SAT first

OR-Tools CP-SAT is designed for discrete constraint and scheduling problems. It gives ACR a real specialist backend for a problem class coding agents commonly encounter: allocating work under dependencies and conflicts.

The initial backend runs with one search worker and a fixed seed to favor reproducibility. Later benchmark work can evaluate faster parallel configurations.

## Quantum is not the product

ACR is **not** a "send hard problems to a quantum computer" wrapper.

Complexity alone is not evidence that quantum hardware is appropriate.

A quantum or quantum-hybrid backend should only be considered when:

1. the problem has a compatible mathematical formulation,
2. a classical baseline exists,
3. there is a meaningful experiment to run,
4. outputs can be independently verified,
5. cost and remote-execution policy permit it.

A QPU has to **earn the escalation**.

IBM/Qiskit already provides agent-facing access to quantum tooling through MCP. ACR's intended role is different: decide when specialized computation is justified, execute through replaceable backends, verify outcomes, and accumulate comparable evidence.

## Current architecture

```text
natural language
      |
      v
deterministic assessor
      |
      +-----------------------------+
                                    |
structured scheduling IR            |
      |                             |
      v                             |
validation                          |
      |                             |
      v                             |
routing decision <------------------+
      |
      v
OR-Tools CP-SAT
      |
      v
independent verifier
      |
      v
Compute Receipt
```

Current source layout:

```text
src/compute_router/
  classifier.py       transparent natural-language assessment
  ir.py               structured scheduling contract + fingerprint
  router.py           routing and execution policy
  verification.py     independent result verification
  models.py           routing/result/receipt models
  cli.py              command line interface
  backends/
    cp_sat.py         OR-Tools CP-SAT backend
```

## Design principles

1. Use the simplest backend that fits the problem.
2. Do not confuse difficulty with quantum suitability.
3. Keep natural-language understanding separate from hard solver constraints.
4. Prefer deterministic and classical methods when sufficient.
5. Independently verify computed results.
6. Keep backends replaceable.
7. Explain why a route was chosen.
8. Measure before claiming an advantage.
9. Preserve graceful degradation when optional backends are unavailable.
10. Emit evidence that future routing decisions can learn from.

## What ACR is not yet

ACR is still pre-alpha.

It does not yet provide:

- arbitrary natural-language-to-optimization compilation
- a backend capability registry
- Z3 execution
- graph execution backends
- solver portfolio comparison
- persistent benchmark history
- MCP tools
- GPU routing
- D-Wave integration
- Qiskit execution
- real QPU execution

Those omissions are intentional.

## Roadmap

**v0.3:** backend registry, health/capability reporting, graph + SMT backends.

**v0.4:** compare compatible backends, store local Compute Receipt history, and begin evidence-informed routing.

**v0.5:** MCP/agent interface.

**v0.6:** quantum/hybrid lab, only after classical benchmarking and verification are mature.

See [`docs/ROADMAP.md`](docs/ROADMAP.md).

## Tests

Run the base tests:

```bash
PYTHONPATH=src python -m unittest discover -s tests -v
```

To exercise the executable backend, install the CP-SAT extra first:

```bash
python -m pip install -e ".[cp-sat]"
python -m unittest discover -s tests -v
```

GitHub CI installs the CP-SAT extra and runs the full suite on Python 3.11 and 3.12.

## Project status

**Experimental / pre-alpha.**

The project is looking for evidence that compute routing improves agent workflows before expanding the backend catalog.

Contributions are especially useful around structured problem types, independent verification, benchmark methodology, classical solver adapters, agent integration, and carefully justified accelerator or quantum experiments.

## Contributing

See [`CONTRIBUTING.md`](CONTRIBUTING.md).

## License

Apache-2.0. See [`LICENSE`](LICENSE).
