# Contributing

Thanks for helping improve Agent Compute Router.

## Contribution rule

A new backend or routing rule should answer:

> Why is this computation better suited to the proposed backend than to the existing alternatives?

Prefer focused changes that can be tested and compared.

## Before opening a PR

```bash
python -m pip install -e ".[full]"
python -m unittest discover -s tests -v
```

Please include tests for routing changes. `AGENTS.md` records the architectural
invariants the suite enforces — read it before changing the hybrid boundary,
the selection policy, or the provider states.

No test may contact a remote provider. Use a local fake or
`dimod.ExactCQMSolver`.

## Quantum-related contributions

Do not describe a quantum backend as superior without a reproducible comparison against an appropriate classical baseline. Experimental quantum adapters are welcome; unsupported performance claims are not.

"Beat the decomposed classical allocator" is not the same claim as "beat the
strongest classical method". ACR evaluates a joint classical baseline precisely
so the difference stays visible, and receipts report the two outcomes
separately.
