from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Mapping


PRIMITIVE_FIELDS = (
    "id", "kind", "canonical_name", "display_name", "description", "authority",
    "status", "version", "created_at", "updated_at", "lineage", "provenance",
    "relationships", "dependencies", "metadata",
)


def _freeze(value: Any) -> Any:
    if isinstance(value, Mapping):
        return MappingProxyType({str(k): _freeze(v) for k, v in value.items()})
    if isinstance(value, (list, tuple)):
        return tuple(_freeze(v) for v in value)
    return value


def _thaw(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {k: _thaw(v) for k, v in value.items()}
    if isinstance(value, tuple):
        return [_thaw(v) for v in value]
    return deepcopy(value)


@dataclass(frozen=True, slots=True)
class ConstitutionalObject:
    """The sole immutable constitutional architectural primitive."""

    id: str
    kind: str
    canonical_name: str
    display_name: str
    description: str
    authority: Mapping[str, Any]
    status: str
    version: str
    created_at: str
    updated_at: str
    lineage: Mapping[str, Any]
    provenance: Mapping[str, Any]
    relationships: tuple[Mapping[str, Any], ...]
    dependencies: tuple[str, ...]
    metadata: Mapping[str, Any]

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "ConstitutionalObject":
        missing = set(PRIMITIVE_FIELDS) - value.keys()
        if missing:
            raise ValueError(f"missing constitutional primitives: {', '.join(sorted(missing))}")
        unknown = set(value) - set(PRIMITIVE_FIELDS)
        if unknown:
            raise ValueError(f"non-primitive fields are not allowed: {', '.join(sorted(unknown))}")
        if not isinstance(value["id"], str) or not value["id"].strip():
            raise ValueError("id must be a non-empty string")
        return cls(
            id=value["id"], kind=value["kind"], canonical_name=value["canonical_name"],
            display_name=value["display_name"], description=value["description"],
            authority=_freeze(value["authority"]), status=value["status"], version=value["version"],
            created_at=value["created_at"], updated_at=value["updated_at"],
            lineage=_freeze(value["lineage"]), provenance=_freeze(value["provenance"]),
            relationships=tuple(_freeze(v) for v in value["relationships"]),
            dependencies=tuple(value["dependencies"]), metadata=_freeze(value["metadata"]),
        )

    def to_primitives(self) -> dict[str, Any]:
        return {field: _thaw(getattr(self, field)) for field in PRIMITIVE_FIELDS}
