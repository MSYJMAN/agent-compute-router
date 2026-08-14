from .classifier import classify
from .models import RoutingDecision


def assess(problem: str) -> RoutingDecision:
    """Return an inspectable routing recommendation for a problem description."""
    return classify(problem)
