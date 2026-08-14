# Architecture

## v0.1

```text
problem text
    |
    v
transparent deterministic classifier
    |
    v
routing policy
    |
    v
RoutingDecision
    |
    +--> human-readable CLI
    `--> JSON for agent integration
```

No remote calls occur in v0.1.

## Target architecture

```text
AI agent / MCP client
        |
        v
  problem normalizer
        |
        v
 structured problem IR
        |
        v
   compute router
        |
   +----+---------+---------+----------+
   |              |         |          |
 graph          SAT/SMT   CP/MILP   numerical
   |              |         |          |
   +--------------+----+----+----------+
                       |
                       v
                 benchmark layer
                       |
             +---------+---------+
             |                   |
         classical          quantum/hybrid
             |                   |
             +---------+---------+
                       |
                       v
                  verifier
                       |
                       v
                    agent
```

## Required backend contract (planned)

A future backend should expose conceptually:

- `capabilities()`
- `health()`
- `estimate_cost(problem)`
- `solve(problem)`
- `verify(result)` or provide enough data for an independent verifier
- `benchmark(problem)`

Provider-specific credentials should remain outside model context.
