"""Agent Compute Router."""

from .ir import SchedulingProblem, TaskSpec
from .router import assess, solve_schedule

__all__ = ["SchedulingProblem", "TaskSpec", "assess", "solve_schedule"]
__version__ = "0.2.0"
