from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4


@dataclass(slots=True)
class ExecutionResult:
    id: str = field(default_factory=lambda: str(uuid4()))
    ok: bool = True
    payload: dict[str, Any] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)

    def as_dict(self):
        return {
            "id": self.id,
            "ok": self.ok,
            "payload": self.payload,
            "errors": self.errors,
        }
