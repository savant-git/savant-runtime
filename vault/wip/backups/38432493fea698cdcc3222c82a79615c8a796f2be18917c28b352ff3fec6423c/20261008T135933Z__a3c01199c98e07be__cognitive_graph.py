#!/usr/bin/env python3
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

from cognitive_primitives import (
    OWNER,
    SCHEMA,
    CognitiveTask,
    digest,
    stable_id,
    unique_strings,
)


@dataclass(frozen=True)
class CognitiveSegue:
    left_ref: str
    right_ref: str
    kind: str
    metadata: tuple[
        tuple[str, str],
        ...
    ] = ()

    @property
    def id(self) -> str:
        return stable_id(
            "opus-segue",
            {
                "left_ref": self.left_ref,
                "right_ref": self.right_ref,
                "kind": self.kind,
                "metadata": list(
                    self.metadata
                ),
            },
        )

    def projection(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "left_ref": self.left_ref,
            "right_ref": self.right_ref,
            "kind": self.kind,
            "metadata": dict(
                self.metadata
            ),
        }


class CognitiveGraph:
    def __init__(self) -> None:
        self.tasks: dict[
            str,
            CognitiveTask,
        ] = {}
        self.segues: dict[
            str,
            CognitiveSegue,
        ] = {}

    def add_task(
        self,
        task: CognitiveTask,
    ) -> CognitiveTask:
        self.tasks[task.id] = task

        for dependency_ref in (
            task.dependency_refs
        ):
            self.add_segue(
                CognitiveSegue(
                    left_ref=dependency_ref,
                    right_ref=task.id,
                    kind="depends_on",
                )
            )

        if task.parent_ref:
            self.add_segue(
                CognitiveSegue(
                    left_ref=(
                        task.parent_ref
                    ),
                    right_ref=task.id,
                    kind="decomposes_into",
                )
            )

        return task

    def add_segue(
        self,
        segue: CognitiveSegue,
    ) -> CognitiveSegue:
        self.segues[segue.id] = segue
        return segue

    def dependencies(
        self,
        task_ref: str,
    ) -> tuple[str, ...]:
        return unique_strings(
            segue.left_ref
            for segue
            in self.segues.values()
            if (
                segue.right_ref
                == task_ref
                and segue.kind
                == "depends_on"
            )
        )

    def dependents(
        self,
        task_ref: str,
    ) -> tuple[str, ...]:
        return unique_strings(
            segue.right_ref
            for segue
            in self.segues.values()
            if (
                segue.left_ref
                == task_ref
                and segue.kind
                == "depends_on"
            )
        )

    def ready(
        self,
        completed_refs: Iterable[str],
    ) -> tuple[CognitiveTask, ...]:
        completed = set(
            completed_refs
        )

        ready = []

        for task in self.tasks.values():
            if task.id in completed:
                continue

            if set(
                self.dependencies(task.id)
            ).issubset(completed):
                ready.append(task)

        return tuple(
            sorted(
                ready,
                key=lambda task: task.id,
            )
        )

    def projection(self) -> dict[str, Any]:
        result = {
            "schema": SCHEMA,
            "owner": OWNER,
            "tasks": [
                self.tasks[key].projection()
                for key in sorted(
                    self.tasks
                )
            ],
            "segues": [
                self.segues[key].projection()
                for key in sorted(
                    self.segues
                )
            ],
            "authority_effect": "none",
        }

        result["projection_digest"] = (
            digest(result)
        )
        return result
