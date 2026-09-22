#!/usr/bin/env python3
from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, dataclass, field
from typing import Any, Mapping

from runtime.lineage.model import stable_hash


class KindredError(Exception):
    """Base functional-kindred error."""


class KindredValidationError(KindredError):
    """Raised when authoritative kindred data is invalid."""


class KindredLookupError(KindredError):
    """Raised when a node or relationship cannot be resolved."""


VALID_RELATIONSHIP_PLANES = {
    "lineage",
    "alliance",
    "governance",
    "functional",
}


def _mapping(
    value: Any,
) -> dict[str, Any]:
    if isinstance(
        value,
        Mapping,
    ):
        return deepcopy(
            dict(value)
        )

    return {}


def _strings(
    value: Any,
) -> tuple[str, ...]:
    if value is None:
        return ()

    if isinstance(
        value,
        str,
    ):
        stripped = value.strip()

        return (
            (stripped,)
            if stripped
            else ()
        )

    if not isinstance(
        value,
        (list, tuple, set),
    ):
        return ()

    result: list[str] = []

    for item in value:
        normalized = str(
            item
        ).strip()

        if (
            normalized
            and normalized not in result
        ):
            result.append(
                normalized
            )

    return tuple(
        result
    )


@dataclass(frozen=True, slots=True)
class KindredNode:
    id: str
    label: str
    kind: str = "instance"
    canonical_id: str = ""
    authority: bool = False
    path: str | None = None
    metadata: Mapping[str, Any] = field(
        default_factory=dict
    )
    provenance: Mapping[str, Any] = field(
        default_factory=dict
    )

    def to_dict(
        self,
    ) -> dict[str, Any]:
        return {
            "id": self.id,
            "canonical_id": (
                self.canonical_id
                or self.id
            ),
            "label": self.label,
            "kind": self.kind,
            "authority": self.authority,
            "path": self.path,
            "metadata": _mapping(
                self.metadata
            ),
            "provenance": _mapping(
                self.provenance
            ),
        }


@dataclass(frozen=True, slots=True)
class DirectLineageEdge:
    id: str
    parent: str
    child: str
    role: str
    axis: str
    domain: str
    parent_profile: str
    child_profile: str
    continuation: str = "neutral"
    scope: str = "global"
    order: int = 0
    status: str = "active"
    inheritance: Mapping[str, Any] = field(
        default_factory=dict
    )
    propagation: Mapping[str, Any] = field(
        default_factory=dict
    )
    contribution: Mapping[str, Any] = field(
        default_factory=dict
    )
    generation_event: str | None = None
    provenance: Mapping[str, Any] = field(
        default_factory=dict
    )
    metadata: Mapping[str, Any] = field(
        default_factory=dict
    )

    def to_dict(
        self,
    ) -> dict[str, Any]:
        return {
            "id": self.id,
            "relationship_plane": (
                "lineage"
            ),
            "parent": self.parent,
            "child": self.child,
            "role": self.role,
            "axis": self.axis,
            "domain": self.domain,
            "kindred": {
                "parent_profile": (
                    self.parent_profile
                ),
                "child_profile": (
                    self.child_profile
                ),
                "generation_event": (
                    self.generation_event
                ),
            },
            "continuation": (
                self.continuation
            ),
            "scope": self.scope,
            "order": self.order,
            "status": self.status,
            "inheritance": _mapping(
                self.inheritance
            ),
            "propagation": _mapping(
                self.propagation
            ),
            "contribution": _mapping(
                self.contribution
            ),
            "provenance": _mapping(
                self.provenance
            ),
            "metadata": _mapping(
                self.metadata
            ),
        }


@dataclass(frozen=True, slots=True)
class AllianceContract:
    id: str
    partners: tuple[str, ...]
    profile: str = "partner"
    domains: tuple[str, ...] = ()
    status: str = "active"
    contract: Mapping[str, Any] = field(
        default_factory=dict
    )
    provenance: Mapping[str, Any] = field(
        default_factory=dict
    )
    metadata: Mapping[str, Any] = field(
        default_factory=dict
    )

    def __post_init__(
        self,
    ) -> None:
        if len(
            self.partners
        ) < 2:
            raise KindredValidationError(
                "alliance requires at least "
                "two partners"
            )

        if len(
            set(
                self.partners
            )
        ) != len(
            self.partners
        ):
            raise KindredValidationError(
                "alliance partners must "
                "be unique"
            )

    def to_dict(
        self,
    ) -> dict[str, Any]:
        return {
            "id": self.id,
            "relationship_plane": (
                "alliance"
            ),
            "partners": list(
                self.partners
            ),
            "alliance_profile": (
                self.profile
            ),
            "domains": list(
                self.domains
            ),
            "status": self.status,
            "contract": _mapping(
                self.contract
            ),
            "provenance": _mapping(
                self.provenance
            ),
            "metadata": _mapping(
                self.metadata
            ),
        }


@dataclass(frozen=True, slots=True)
class PathStep:
    edge_id: str
    source: str
    target: str
    direction: str
    role: str
    domain: str
    parent_profile: str
    child_profile: str

    def to_dict(
        self,
    ) -> dict[str, Any]:
        return asdict(
            self
        )


@dataclass(frozen=True, slots=True)
class KindredDetermination:
    subject: str
    relative: str
    relationship: str
    generation_offset: int
    domains: tuple[str, ...] = ()
    shared_ancestors: tuple[str, ...] = ()
    shared_parents: tuple[str, ...] = ()
    alliance_ids: tuple[str, ...] = ()
    path: tuple[PathStep, ...] = ()
    confidence: float = 1.0
    rule: str = ""
    operational_meaning: str = ""
    metadata: Mapping[str, Any] = field(
        default_factory=dict
    )

    @property
    def deterministic_hash(
        self,
    ) -> str:
        return stable_hash(
            self.to_dict(
                include_hash=False
            )
        )

    def to_dict(
        self,
        *,
        include_hash: bool = True,
    ) -> dict[str, Any]:
        payload = {
            "subject": self.subject,
            "relative": self.relative,
            "relationship": (
                self.relationship
            ),
            "generation_offset": (
                self.generation_offset
            ),
            "domains": list(
                self.domains
            ),
            "shared_ancestors": list(
                self.shared_ancestors
            ),
            "shared_parents": list(
                self.shared_parents
            ),
            "alliance_ids": list(
                self.alliance_ids
            ),
            "path": [
                step.to_dict()
                for step in self.path
            ],
            "confidence": (
                self.confidence
            ),
            "rule": self.rule,
            "operational_meaning": (
                self.operational_meaning
            ),
            "metadata": _mapping(
                self.metadata
            ),
        }

        if include_hash:
            payload[
                "deterministic_hash"
            ] = self.deterministic_hash

        return payload


@dataclass(slots=True)
class FamilyTreeProjection:
    focus: str
    nodes: list[dict[str, Any]]
    edges: list[dict[str, Any]]
    generations: Mapping[str, list[str]]
    determinations: list[dict[str, Any]]
    source_runtime_hash: str = ""
    source_lineage_hash: str = ""
    registry_id: str = ""
    registry_version: str = ""
    options: Mapping[str, Any] = field(
        default_factory=dict
    )
    schema: str = (
        "savant."
        "functional_family_tree.v1"
    )

    def deterministic_core(
        self,
    ) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "focus": self.focus,
            "nodes": deepcopy(
                self.nodes
            ),
            "edges": deepcopy(
                self.edges
            ),
            "generations": deepcopy(
                dict(
                    self.generations
                )
            ),
            "determinations": deepcopy(
                self.determinations
            ),
            "source_runtime_hash": (
                self.source_runtime_hash
            ),
            "source_lineage_hash": (
                self.source_lineage_hash
            ),
            "registry_id": (
                self.registry_id
            ),
            "registry_version": (
                self.registry_version
            ),
            "options": _mapping(
                self.options
            ),
        }

    @property
    def deterministic_hash(
        self,
    ) -> str:
        return stable_hash(
            self.deterministic_core()
        )

    def to_dict(
        self,
    ) -> dict[str, Any]:
        return {
            **self.deterministic_core(),
            "deterministic_hash": (
                self.deterministic_hash
            ),
            "node_count": len(
                self.nodes
            ),
            "edge_count": len(
                self.edges
            ),
            "determination_count": len(
                self.determinations
            ),
        }


def stable_alliance_id(
    partners: tuple[str, ...],
    profile: str,
    domains: tuple[str, ...],
) -> str:
    digest = stable_hash({
        "partners": sorted(
            partners
        ),
        "profile": profile,
        "domains": sorted(
            domains
        ),
    })[:20]

    return (
        f"alliance.{profile}."
        f"{digest}"
    )


__all__ = [
    "AllianceContract",
    "DirectLineageEdge",
    "FamilyTreeProjection",
    "KindredDetermination",
    "KindredError",
    "KindredLookupError",
    "KindredNode",
    "KindredValidationError",
    "PathStep",
    "VALID_RELATIONSHIP_PLANES",
    "stable_alliance_id",
]
