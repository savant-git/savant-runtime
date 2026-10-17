
"""Kindred adapter for admitted Savant composition relationships.

Consumes explicit, already-admitted instances and typed segues.
Does not create, persist, or supersede graph authority.

All returned metadata is a deterministic, rebuildable projection.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping, Any

from kindred_edifice_projection import (
    Composition,
    Element,
    ElementProjection,
    ProjectionError,
    as_metadata,
    project,
)


class KindredIntegrationError(ProjectionError):
    """Invalid integration input or incomplete relationship evidence."""


@dataclass(frozen=True, slots=True)
class AdmittedInstance:
    identity: str
    edifice: str
    level: int | None = None
    name: str | None = None


@dataclass(frozen=True, slots=True)
class AdmittedSegue:
    identity: str
    source: str
    target: str
    relation: str
    admitted: bool = True


@dataclass(frozen=True, slots=True)
class CompositionEvidence:
    context: str
    complete: bool
    source_revision: str | None = None


@dataclass(frozen=True, slots=True)
class KindredProjection:
    context: str
    source_revision: str | None
    elements: tuple[ElementProjection, ...]

    def metadata(self) -> tuple[dict[str, object], ...]:
        return tuple(
            as_metadata(element)
            for element in self.elements
        )

    def by_identity(
        self,
        identity: str,
    ) -> ElementProjection:
        for element in self.elements:
            if element.identity == identity:
                return element
        raise KeyError(identity)


def _nonempty(value: str, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise KindredIntegrationError(
            f"{field} must be a nonempty string"
        )
    return value


def _normalize_instances(
    instances: Iterable[AdmittedInstance],
) -> tuple[Element, ...]:
    result: list[Element] = []
    seen: set[str] = set()

    for instance in instances:
        identity = _nonempty(
            instance.identity,
            "instance identity",
        )

        if identity in seen:
            raise KindredIntegrationError(
                f"duplicate instance: {identity}"
            )

        seen.add(identity)

        result.append(
            Element(
                identity=identity,
                edifice=instance.edifice,
                level=instance.level,
                name=instance.name,
            )
        )

    return tuple(result)


def _normalize_compositions(
    segues: Iterable[AdmittedSegue],
    composition_relations: frozenset[str],
) -> tuple[Composition, ...]:
    result: list[Composition] = []
    seen_ids: set[str] = set()
    seen_edges: set[tuple[str, str]] = set()

    for segue in segues:
        identity = _nonempty(
            segue.identity,
            "segue identity",
        )

        if identity in seen_ids:
            raise KindredIntegrationError(
                f"duplicate segue identity: {identity}"
            )

        seen_ids.add(identity)

        if not isinstance(segue.admitted, bool):
            raise KindredIntegrationError(
                f"invalid admission status: {identity}"
            )

        if not segue.admitted:
            continue

        if segue.relation not in composition_relations:
            continue

        source = _nonempty(
            segue.source,
            "segue source",
        )
        target = _nonempty(
            segue.target,
            "segue target",
        )

        edge = (source, target)

        if edge in seen_edges:
            continue

        seen_edges.add(edge)
        result.append(
            Composition(
                parent=source,
                child=target,
            )
        )

    return tuple(result)


def project_kindred(
    instances: Iterable[AdmittedInstance],
    segues: Iterable[AdmittedSegue],
    evidence: CompositionEvidence,
    *,
    composition_relations: frozenset[str],
    strict_levels: bool = False,
) -> KindredProjection:
    """Derive one three-position label for each contextual instance.

    The caller must supply the relationship identifiers already
    accepted by Savant. This adapter does not invent their names.

    Evidence completeness is mandatory because an absent edge
    must not be mistaken for proof that no edge exists.

    The selected context and its descendants form the projection
    scope. Relationships outside that scope remain untouched.
    """
    if not isinstance(evidence, CompositionEvidence):
        raise KindredIntegrationError(
            "explicit composition evidence is required"
        )

    context = _nonempty(
        evidence.context,
        "composition context",
    )

    if evidence.complete is not True:
        raise KindredIntegrationError(
            "composition evidence is incomplete"
        )

    if (
        not isinstance(composition_relations, frozenset)
        or not composition_relations
        or any(
            not isinstance(value, str) or not value
            for value in composition_relations
        )
    ):
        raise KindredIntegrationError(
            "accepted composition relation identifiers required"
        )

    elements = _normalize_instances(instances)

    compositions = _normalize_compositions(
        segues,
        composition_relations,
    )

    projected = project(
        elements,
        compositions,
        context=context,
        strict_levels=strict_levels,
    )

    return KindredProjection(
        context=context,
        source_revision=evidence.source_revision,
        elements=projected,
    )


def project_metadata(
    instances: Iterable[AdmittedInstance],
    segues: Iterable[AdmittedSegue],
    evidence: CompositionEvidence,
    *,
    composition_relations: frozenset[str],
    strict_levels: bool = False,
) -> dict[str, object]:
    """Produce canonical-order, JSON-compatible derived metadata."""
    result = project_kindred(
        instances,
        segues,
        evidence,
        composition_relations=composition_relations,
        strict_levels=strict_levels,
    )

    return {
        "context": result.context,
        "source_revision": result.source_revision,
        "elements": list(result.metadata()),
    }
