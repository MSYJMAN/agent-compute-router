# Routing Policy

Agent Compute Router uses a conservative escalation policy: choose the simplest compute method that fits the structure of the problem, and require measurable evidence before recommending a more specialized backend.

## Core policy

- Keep ordinary language and coding tasks with the agent unless a clearer computational method exists.
- Prefer explicit algorithms and specialized solvers for problems they are designed to solve.
- Treat quantum and hybrid backends as optional experimental targets, not defaults.
- Complexity alone is not evidence that quantum execution is appropriate.
- Compare specialized backends against a credible baseline when practical.
- Validate solver outputs against the original constraints before accepting them.
- Keep optional integrations replaceable so the core router remains usable without them.
- Report why a backend was selected and what alternatives were considered.

## Evidence order

When deciding between backends, prefer evidence from:

1. measured runtime behavior
2. reproducible tests and benchmarks
3. solver capability and problem-formulation fit
4. source/configuration inspection
5. official technical documentation
6. clearly labeled inference

## Quantum policy

A quantum or hybrid backend should only be considered when the problem can be expressed in a formulation supported by that backend and there is a useful reason to benchmark it.

`REVIEW` means the workload may justify a controlled comparison. It does not mean a quantum backend is expected to outperform classical methods.
