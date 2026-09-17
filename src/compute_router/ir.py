from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any


def _unique_strings(value: Any, field: str, *, allow_empty: bool = True) -> tuple[str, ...]:
    if not isinstance(value, list):
        raise ValueError(f"{field} must be a JSON array")
    items: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise ValueError(f"{field} must contain non-empty strings")
        if item in items:
            raise ValueError(f"{field} contains duplicate value {item!r}")
        items.append(item)
    if not allow_empty and not items:
        raise ValueError(f"{field} must not be empty")
    return tuple(items)


@dataclass(frozen=True)
class TaskSpec:
    id: str
    duration: int
    depends_on: tuple[str, ...]
    eligible_agents: tuple[str, ...]
    files: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "duration": self.duration,
            "depends_on": list(self.depends_on),
            "eligible_agents": list(self.eligible_agents),
            "files": list(self.files),
        }


@dataclass(frozen=True)
class SchedulingProblem:
    agents: tuple[str, ...]
    tasks: tuple[TaskSpec, ...]
    objective: str = "minimize_makespan"

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SchedulingProblem":
        if not isinstance(data, dict):
            raise ValueError("scheduling problem must be a JSON object")

        agents = _unique_strings(data.get("agents"), "agents", allow_empty=False)
        raw_tasks = data.get("tasks")
        if not isinstance(raw_tasks, list) or not raw_tasks:
            raise ValueError("tasks must be a non-empty JSON array")

        tasks: list[TaskSpec] = []
        seen_ids: set[str] = set()
        for index, raw in enumerate(raw_tasks):
            if not isinstance(raw, dict):
                raise ValueError(f"tasks[{index}] must be a JSON object")

            task_id = raw.get("id")
            if not isinstance(task_id, str) or not task_id.strip():
                raise ValueError(f"tasks[{index}].id must be a non-empty string")
            if task_id in seen_ids:
                raise ValueError(f"duplicate task id {task_id!r}")
            seen_ids.add(task_id)

            duration = raw.get("duration")
            if type(duration) is not int or duration <= 0:
                raise ValueError(f"task {task_id!r} duration must be a positive integer")

            depends_on = _unique_strings(raw.get("depends_on", []), f"task {task_id!r}.depends_on")
            files = _unique_strings(raw.get("files", []), f"task {task_id!r}.files")

            if "eligible_agents" in raw:
                eligible_agents = _unique_strings(
                    raw["eligible_agents"],
                    f"task {task_id!r}.eligible_agents",
                    allow_empty=False,
                )
            else:
                eligible_agents = agents

            unknown_agents = sorted(set(eligible_agents) - set(agents))
            if unknown_agents:
                raise ValueError(
                    f"task {task_id!r} references unknown eligible agents: {', '.join(unknown_agents)}"
                )

            tasks.append(
                TaskSpec(
                    id=task_id,
                    duration=duration,
                    depends_on=depends_on,
                    eligible_agents=eligible_agents,
                    files=files,
                )
            )

        task_ids = {task.id for task in tasks}
        for task in tasks:
            unknown_dependencies = sorted(set(task.depends_on) - task_ids)
            if unknown_dependencies:
                raise ValueError(
                    f"task {task.id!r} references unknown dependencies: {', '.join(unknown_dependencies)}"
                )
            if task.id in task.depends_on:
                raise ValueError(f"task {task.id!r} cannot depend on itself")

        _reject_dependency_cycles(tasks)

        objective = data.get("objective", "minimize_makespan")
        if objective != "minimize_makespan":
            raise ValueError("v0.2 supports only objective='minimize_makespan'")

        return cls(agents=agents, tasks=tuple(tasks), objective=objective)

    @classmethod
    def from_json(cls, text: str) -> "SchedulingProblem":
        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            raise ValueError(f"invalid JSON: {exc.msg}") from exc
        return cls.from_dict(data)

    def to_dict(self) -> dict[str, Any]:
        return {
            "agents": list(self.agents),
            "tasks": [task.to_dict() for task in self.tasks],
            "objective": self.objective,
        }

    def fingerprint(self) -> str:
        canonical = json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _reject_dependency_cycles(tasks: list[TaskSpec]) -> None:
    dependencies = {task.id: task.depends_on for task in tasks}
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(task_id: str) -> None:
        if task_id in visited:
            return
        if task_id in visiting:
            raise ValueError("task dependency graph contains a cycle")
        visiting.add(task_id)
        for dependency in dependencies[task_id]:
            visit(dependency)
        visiting.remove(task_id)
        visited.add(task_id)

    for task in tasks:
        visit(task.id)
