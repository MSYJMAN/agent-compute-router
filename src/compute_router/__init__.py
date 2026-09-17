"""Agent Compute Router."""

from .ir import SchedulingProblem
from .router import assess, solve_schedule

__all__ = ["SchedulingProblem", "assess", "solve_schedule"]
__version__ = "0.2.0"
