from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from .object import ConstitutionalObject, PRIMITIVE_FIELDS


class SchemaValidationError(ValueError):
    pass


class ConstitutionalSchemaRegistry:
    """Versioned, inheritable schemas discovered from authority files."""

    def __init__(self, schemas: list[Mapping[str, Any]]):
        self._schemas = {str(s["id"]): dict(s) for s in schemas}
        if len(self._schemas) != len(schemas):
            raise SchemaValidationError("schema ids must be unique")
        self._validate_inheritance()

    @classmethod
    def discover(cls, root: Path) -> "ConstitutionalSchemaRegistry":
        directory = root / "canon-system/authority/constitution/schemas"
        schemas = [json.loads(p.read_text(encoding="utf-8")) for p in sorted(directory.glob("*.schema.json"))]
        return cls(schemas)

    def _validate_inheritance(self) -> None:
        for schema_id in self._schemas:
            seen: set[str] = set()
            cursor: str | None = schema_id
            while cursor:
                if cursor in seen:
                    raise SchemaValidationError(f"schema inheritance cycle: {cursor}")
                seen.add(cursor)
                parent = self._schemas[cursor].get("inherits")
                if parent and parent not in self._schemas:
                    raise SchemaValidationError(f"unknown parent schema: {parent}")
                cursor = parent

    def schema_for_kind(self, kind: str) -> Mapping[str, Any]:
        matches = [s for s in self._schemas.values() if s.get("kind") in {kind, "*"}]
        return max(matches, key=lambda s: tuple(int(x) for x in str(s["version"]).split("."))) if matches else self._schemas["constitutional-object"]

    def by_version(self, version: str) -> tuple[Mapping[str, Any], ...]:
        return tuple(dict(s) for s in self._schemas.values() if str(s["version"]) == version)

    def validate(self, value: ConstitutionalObject | Mapping[str, Any]) -> None:
        data = value.to_primitives() if isinstance(value, ConstitutionalObject) else dict(value)
        schema = self.schema_for_kind(str(data.get("kind", "")))
        required: set[str] = set()
        cursor: Mapping[str, Any] | None = schema
        while cursor:
            required.update(cursor.get("required", []))
            cursor = self._schemas.get(cursor.get("inherits"))
        missing = required - data.keys()
        if missing:
            raise SchemaValidationError(f"missing schema fields: {', '.join(sorted(missing))}")
        if set(data) != set(PRIMITIVE_FIELDS):
            raise SchemaValidationError("constitutional objects may contain authoritative primitives only")

    def get(self, schema_id: str) -> Mapping[str, Any]:
        return dict(self._schemas[schema_id])

    @property
    def ids(self) -> tuple[str, ...]:
        return tuple(sorted(self._schemas))
