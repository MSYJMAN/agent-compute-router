# Contributing

Thanks for helping improve Agent Compute Router.

## Contribution rule

A new backend or routing rule should answer:

> Why is this computation better suited to the proposed backend than to the existing alternatives?

Prefer focused changes that can be tested and compared.

## Before opening a PR

```bash
python -m unittest discover -s tests -v
```

Please include tests for routing changes.

## Quantum-related contributions

Do not describe a quantum backend as superior without a reproducible comparison against an appropriate classical baseline. Experimental quantum adapters are welcome; unsupported performance claims are not.
