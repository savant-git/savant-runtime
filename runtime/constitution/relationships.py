from __future__ import annotations

import json
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping


class RelationshipTypeRegistry:
    """Authority-backed registry of relationship semantics."""

    def __init__(self, definitions: list[Mapping[str, Any]]):
        self._definitions = {str(d["id"]): MappingProxyType(dict(d)) for d in definitions}
        if len(self._definitions) != len(definitions):
            raise ValueError("relationship type ids must be unique")

    @classmethod
    def discover(cls, root: Path) -> "RelationshipTypeRegistry":
        payload = json.loads((root / "canon-system/authority/constitution/relationships.json").read_text())
        return cls(payload["relationships"])

    def contains(self, relationship_type: str) -> bool: return relationship_type in self._definitions
    def get(self, relationship_type: str) -> Mapping[str, Any]: return self._definitions[relationship_type]
    @property
    def ids(self) -> tuple[str, ...]: return tuple(sorted(self._definitions))
