from __future__ import annotations

import re

from .models import RoutingDecision


def _contains(text: str, *patterns: str) -> bool:
    return any(re.search(pattern, text, flags=re.IGNORECASE) for pattern in patterns)


def classify(text: str) -> RoutingDecision:
    """Classify a natural-language workload using transparent deterministic rules.

    v0.1 deliberately avoids an LLM classifier so routing decisions are inspectable,
    reproducible, and testable. Later versions can add learned routing as optional
    evidence, not as unquestioned authority.
    """
    normalized = " ".join(text.strip().split())

    if not normalized:
        raise ValueError("problem text must not be empty")

    # Explicit quantum-shaped mathematical formulations get REVIEW, never an
    # automatic QPU recommendation. A classical baseline remains required.
    if _contains(
        normalized,
        r"\bqubo\b",
        r"\bising\b",
        r"\bmax[- ]?cut\b",
        r"constrained quadratic model",
        r"\bcqm\b",
        r"\bqaoa\b",
    ):
        return RoutingDecision(
            classification="quantum_compatible_optimization",
            recommended_backend="classical-baseline-first",
            quantum_escalation="REVIEW",
            reason=(
                "The problem names a formulation commonly used in quantum or hybrid "
                "optimization. Establish and verify a classical baseline before any "
                "quantum/hybrid benchmark."
            ),
            alternatives=("cp-sat", "milp", "simulated-annealing", "quantum-hybrid"),
        )

    if _contains(
        normalized,
        r"\bschedul",
        r"precedence constraint",
        r"task allocation",
        r"assign .* agent",
        r"worktree conflict",
        r"resource allocation",
    ):
        return RoutingDecision(
            classification="constrained_scheduling",
            recommended_backend="cp-sat",
            quantum_escalation="NO",
            reason=(
                "Discrete scheduling, assignment, and precedence constraints map "
                "naturally to constraint programming before quantum escalation."
            ),
            alternatives=("milp", "heuristic-planner"),
        )

    if _contains(normalized, r"\bsat\b", r"\bsmt\b", r"satisfiability", r"logical constraints?"):
        return RoutingDecision(
            classification="logical_constraint_problem",
            recommended_backend="smt-solver",
            quantum_escalation="NO",
            reason="Logical satisfiability constraints are a direct fit for SAT/SMT solvers.",
            alternatives=("sat-solver", "cp-sat"),
        )

    if _contains(
        normalized,
        r"dependency graph",
        r"graph traversal",
        r"shortest path",
        r"strongly connected",
        r"topological sort",
        r"critical path",
    ):
        return RoutingDecision(
            classification="graph_problem",
            recommended_backend="graph-algorithm",
            quantum_escalation="NO",
            reason="The problem maps directly to well-understood deterministic graph algorithms.",
            alternatives=("constraint-solver",),
        )

    if _contains(
        normalized,
        r"minimi[sz]e",
        r"maximi[sz]e",
        r"optimal combination",
        r"bin packing",
        r"set cover",
        r"knapsack",
        r"vehicle routing",
    ):
        return RoutingDecision(
            classification="classical_optimization",
            recommended_backend="optimization-solver",
            quantum_escalation="NO",
            reason=(
                "The task expresses an optimization objective, but no evidence yet "
                "justifies a quantum formulation. Start with a specialized classical solver."
            ),
            alternatives=("cp-sat", "milp", "domain-algorithm"),
        )

    if _contains(
        normalized,
        r"matrix",
        r"gradient",
        r"numerical",
        r"continuous variables?",
        r"least squares",
    ):
        return RoutingDecision(
            classification="numerical_computation",
            recommended_backend="numerical-library",
            quantum_escalation="NO",
            reason="The problem appears numerical/continuous and should use deterministic numerical tooling first.",
            alternatives=("gpu-accelerator",),
        )

    return RoutingDecision(
        classification="general_agent_task",
        recommended_backend="llm-or-direct-code",
        quantum_escalation="NO",
        reason="No specialized mathematical structure was detected that justifies compute escalation.",
        alternatives=(),
    )
