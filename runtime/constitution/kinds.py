from __future__ import annotations

import json
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping


class KindRegistry:
    """Registry-driven semantic identities; no kind behavior is hardcoded."""

    def __init__(self, definitions: list[Mapping[str, Any]] | None = None):
        self._definitions: dict[str, Mapping[str, Any]] = {}
        for definition in definitions or []:
            self.register(definition)

    @classmethod
    def discover(cls, root: Path) -> "KindRegistry":
        path = root / "canon-system/authority/constitution/kinds.json"
        payload = json.loads(path.read_text(encoding="utf-8"))
        return cls(payload["kinds"])

    def register(self, definition: Mapping[str, Any]) -> None:
        kind = str(definition["id"])
        if kind in self._definitions:
            raise ValueError(f"kind already registered: {kind}")
        self._definitions[kind] = MappingProxyType(dict(definition))

    def contains(self, kind: str) -> bool:
        return kind in self._definitions

    def get(self, kind: str) -> Mapping[str, Any]:
        return self._definitions[kind]

    @property
    def ids(self) -> tuple[str, ...]:
        return tuple(sorted(self._definitions))
