from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4


@dataclass(slots=True)
class ExecutionContext:
    id: str = field(default_factory=lambda: str(uuid4()))
    source: str = "runtime"
    target: str = "unknown"
    payload: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def as_dict(self):
        return {
            "id": self.id,
            "source": self.source,
            "target": self.target,
            "payload": self.payload,
            "metadata": self.metadata,
        }
