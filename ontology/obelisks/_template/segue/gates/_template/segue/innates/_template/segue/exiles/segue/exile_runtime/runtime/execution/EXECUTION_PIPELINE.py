from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass(slots=True)
class Step:
    id: str
    fn: Callable[[dict[str, Any]], dict[str, Any]]


@dataclass(slots=True)
class Pipeline:
    id: str
    steps: list[Step] = field(default_factory=list)

    def add(self, step: Step):
        self.steps.append(step)
        return self

    def run(self, context: dict[str, Any] | None = None):
        ctx = context or {}

        for step in self.steps:
            ctx = step.fn(ctx)

        return ctx
