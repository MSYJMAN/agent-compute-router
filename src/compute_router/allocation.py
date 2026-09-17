from __future__ import annotations

from itertools import combinations

from .ir import SchedulingProblem

HANDOFF_WEIGHT = 1
FILE_SPLIT_WEIGHT = 2


def dependency_pairs(problem: SchedulingProblem) -> tuple[tuple[str, str], ...]:
    return tuple(
        (dependency, task.id)
        for task in problem.tasks
        for dependency in task.depends_on
    )


def file_conflict_pairs(problem: SchedulingProblem) -> tuple[tuple[str, str], ...]:
    pairs: set[tuple[str, str]] = set()
    for left, right in combinations(problem.tasks, 2):
        if set(left.files) & set(right.files):
            pairs.add(tuple(sorted((left.id, right.id))))
    return tuple(sorted(pairs))


def primary_weight(problem: SchedulingProblem) -> int:
    max_secondary = (
        len(dependency_pairs(problem)) * HANDOFF_WEIGHT
        + len(file_conflict_pairs(problem)) * FILE_SPLIT_WEIGHT
    )
    return max_secondary + 1


def score_allocation(
    problem: SchedulingProblem,
    allocation: dict[str, str],
) -> dict[str, int]:
    loads = {agent: 0 for agent in problem.agents}
    task_by_id = {task.id: task for task in problem.tasks}

    for task_id, agent in allocation.items():
        task = task_by_id.get(task_id)
        if task is not None and agent in loads:
            loads[agent] += task.duration

    handoffs = sum(
        allocation.get(left) != allocation.get(right)
        for left, right in dependency_pairs(problem)
    )
    file_splits = sum(
        allocation.get(left) != allocation.get(right)
        for left, right in file_conflict_pairs(problem)
    )
    max_load = max(loads.values(), default=0)
    weighted = (
        primary_weight(problem) * max_load
        + HANDOFF_WEIGHT * handoffs
        + FILE_SPLIT_WEIGHT * file_splits
    )
    return {
        "max_agent_load": max_load,
        "dependency_handoffs": handoffs,
        "file_ownership_splits": file_splits,
        "weighted_score": weighted,
    }
