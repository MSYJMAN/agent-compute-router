from __future__ import annotations

from itertools import combinations

from .ir import SchedulingProblem
from .models import TaskAssignment


def _overlaps(left: TaskAssignment, right: TaskAssignment) -> bool:
    return max(left.start, right.start) < min(left.end, right.end)


def verify_schedule(
    problem: SchedulingProblem,
    assignments: dict[str, TaskAssignment],
) -> tuple[bool, tuple[str, ...]]:
    violations: list[str] = []
    task_by_id = {task.id: task for task in problem.tasks}
    expected = set(task_by_id)
    actual = set(assignments)

    for task_id in sorted(expected - actual):
        violations.append(f"missing assignment for task {task_id!r}")
    for task_id in sorted(actual - expected):
        violations.append(f"assignment references unknown task {task_id!r}")

    for task_id in sorted(expected & actual):
        task = task_by_id[task_id]
        assignment = assignments[task_id]
        if assignment.agent not in problem.agents:
            violations.append(f"task {task_id!r} uses unknown agent {assignment.agent!r}")
        elif assignment.agent not in task.eligible_agents:
            violations.append(
                f"task {task_id!r} is assigned to ineligible agent {assignment.agent!r}"
            )
        if assignment.start < 0:
            violations.append(f"task {task_id!r} starts before time zero")
        if assignment.end - assignment.start != task.duration:
            violations.append(
                f"task {task_id!r} duration mismatch: expected {task.duration}, "
                f"got {assignment.end - assignment.start}"
            )

    for task in problem.tasks:
        if task.id not in assignments:
            continue
        for dependency in task.depends_on:
            if dependency not in assignments:
                continue
            if assignments[task.id].start < assignments[dependency].end:
                violations.append(
                    f"dependency violation: task {task.id!r} starts before "
                    f"{dependency!r} completes"
                )

    assigned_items = [(task_id, assignments[task_id]) for task_id in sorted(expected & actual)]
    for (left_id, left), (right_id, right) in combinations(assigned_items, 2):
        if left.agent == right.agent and _overlaps(left, right):
            violations.append(
                f"agent overlap: {left.agent!r} runs {left_id!r} and {right_id!r} simultaneously"
            )

        shared_files = sorted(set(task_by_id[left_id].files) & set(task_by_id[right_id].files))
        if shared_files and _overlaps(left, right):
            violations.append(
                f"file conflict: {left_id!r} and {right_id!r} overlap on "
                f"{', '.join(shared_files)}"
            )

    return not violations, tuple(violations)
