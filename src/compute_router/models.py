from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Literal

QuantumEscalation = Literal["NO", "REVIEW"]


@dataclass(frozen=True)
class RoutingDecision:
    classification: str
    recommended_backend: str
    quantum_escalation: QuantumEscalation
    reason: str
    alternatives: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["alternatives"] = list(self.alternatives)
        return data


@dataclass(frozen=True)
class TaskAssignment:
    agent: str
    start: int
    end: int


@dataclass(frozen=True)
class AllocationBackendResult:
    backend: str
    status: str
    allocation: dict[str, str]
    runtime_ms: float | None
    objective_value: int | float | None
    metrics: dict[str, int | float | str | bool]
    notes: tuple[str, ...] = ()


@dataclass(frozen=True)
class BackendResult:
    status: str
    assignments: dict[str, TaskAssignment]
    objective_value: int | None
    metrics: dict[str, int | float | str | bool]


@dataclass(frozen=True)
class ComputeStage:
    name: str
    backend: str
    status: str
    runtime_ms: float | None
    objective_name: str | None
    objective_value: int | float | None
    verified: bool | None
    violations: tuple[str, ...] = ()
    metrics: dict[str, int | float | str | bool] | None = None
    notes: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "backend": self.backend,
            "status": self.status,
            "runtime_ms": self.runtime_ms,
            "objective": (
                {"name": self.objective_name, "value": self.objective_value}
                if self.objective_name is not None
                else None
            ),
            "verified": self.verified,
            "violations": list(self.violations),
            "metrics": dict(self.metrics or {}),
            "notes": list(self.notes),
        }


@dataclass(frozen=True)
class ComputeReceipt:
    schema_version: str
    problem_type: str
    problem_sha256: str
    route: RoutingDecision
    backend: str
    solver_status: str
    runtime_ms: float | None
    objective_name: str
    objective_value: int | None
    verified: bool | None
    violations: tuple[str, ...]
    solution: dict[str, TaskAssignment]
    metrics: dict[str, int | float | str | bool]
    notes: tuple[str, ...] = ()
    stages: tuple[ComputeStage, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "problem_type": self.problem_type,
            "problem_sha256": self.problem_sha256,
            "route": self.route.to_dict(),
            "backend": self.backend,
            "solver_status": self.solver_status,
            "runtime_ms": self.runtime_ms,
            "objective": {"name": self.objective_name, "value": self.objective_value},
            "verified": self.verified,
            "violations": list(self.violations),
            "solution": {
                task_id: asdict(assignment)
                for task_id, assignment in sorted(self.solution.items())
            },
            "metrics": dict(self.metrics),
            "notes": list(self.notes),
            "stages": [stage.to_dict() for stage in self.stages],
        }
