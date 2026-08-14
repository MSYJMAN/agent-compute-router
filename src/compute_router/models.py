from dataclasses import asdict, dataclass
from typing import Literal

QuantumEscalation = Literal["NO", "REVIEW"]


@dataclass(frozen=True)
class RoutingDecision:
    classification: str
    recommended_backend: str
    quantum_escalation: QuantumEscalation
    reason: str
    alternatives: tuple[str, ...] = ()

    def to_dict(self) -> dict:
        data = asdict(self)
        data["alternatives"] = list(self.alternatives)
        return data
