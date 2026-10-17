
"""Deterministic edifice and kindred projections.

This module does not own composition authority.
Callers supply admitted instance identities and direct
parent-to-child composition relationships.

The output is derived and may be discarded and rebuilt.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Iterable, Mapping


EDIFICES = frozenset({
    "identity",
    "utility",
    "programming",
})

UTILITY_LEVELS = (
    "glyph",
    "iota",
    "spasm",
    "vagary",
    "epiphany",
    "tactic",
    "artifice",
    "agenda",
    "oeuvre",
)

PROGRAMMING_LEVELS = (
    "glyph",
    "line",
    "segment",
    "snippet",
    "script",
    "engine",
    "subsystem",
    "system",
    "application",
)


class ProjectionError(ValueError):
    """Invalid or inconsistent projection input."""


@dataclass(frozen=True, slots=True)
class Element:
    identity: str
    edifice: str
    level: int | None = None
    name: str | None = None


@dataclass(frozen=True, slots=True)
class Composition:
    parent: str
    child: str


@dataclass(frozen=True, slots=True)
class KindredLabel:
    ascending: str
    current: str
    descending: str

    @property
    def value(self) -> str:
        return (
            f"{self.ascending} · "
            f"{self.current} · "
            f"{self.descending}"
        )


@dataclass(frozen=True, slots=True)
class ElementProjection:
    identity: str
    edifice: str
    level: int | None
    name: str | None
    kindred: KindredLabel
    parents: tuple[str, ...]
    children: tuple[str, ...]
    ancestors: tuple[str, ...]
    descendants: tuple[str, ...]


def _require_identity(value: str) -> str:
    if not isinstance(value, str) or not value:
        raise ProjectionError("element identity must be nonempty")
    return value


def _label(
    has_parent: bool,
    has_child: bool,
) -> KindredLabel:
    if has_parent and has_child:
        return KindredLabel(
            "child", "intermediate", "parent"
        )
    if has_parent:
        return KindredLabel(
            "child", "descendant", "none"
        )
    if has_child:
        return KindredLabel(
            "none", "ancestor", "parent"
        )
    return KindredLabel(
        "none", "independent", "none"
    )


def _reachable(
    origin: str,
    adjacency: Mapping[str, set[str]],
) -> tuple[str, ...]:
    visited: set[str] = set()
    pending = list(adjacency.get(origin, ()))

    while pending:
        current = pending.pop()
        if current == origin:
            raise ProjectionError(
                f"composition cycle involving {origin}"
            )
        if current in visited:
            continue
        visited.add(current)
        pending.extend(adjacency.get(current, ()))

    return tuple(sorted(visited))


def project(
    elements: Iterable[Element],
    compositions: Iterable[Composition],
    *,
    context: str | None = None,
    strict_levels: bool = False,
) -> tuple[ElementProjection, ...]:
    """Project one contextual kindred label per element.

    Elements are canonical references supplied by the caller.
    Compositions are direct parent-to-child relationships.

    The optional context restricts the projection to the
    selected element and its structural descendants.

    When strict_levels is enabled, relationships within
    the same edifice must descend in level number.
    Cross-edifice relationships are not assigned an
    invented numerical ordering.
    """
    index: dict[str, Element] = {}

    for element in elements:
        identity = _require_identity(element.identity)

        if element.edifice not in EDIFICES:
            raise ProjectionError(
                f"unknown edifice: {element.edifice}"
            )

        if element.level is not None:
            if (
                not isinstance(element.level, int)
                or isinstance(element.level, bool)
                or not 1 <= element.level <= 9
            ):
                raise ProjectionError(
                    f"invalid level for {identity}"
                )

        if identity in index:
            if index[identity] != element:
                raise ProjectionError(
                    f"conflicting identity: {identity}"
                )
            raise ProjectionError(
                f"duplicate identity: {identity}"
            )

        index[identity] = element

    forward: dict[str, set[str]] = defaultdict(set)
    reverse: dict[str, set[str]] = defaultdict(set)

    for relation in compositions:
        parent = _require_identity(relation.parent)
        child = _require_identity(relation.child)

        if parent not in index or child not in index:
            raise ProjectionError(
                f"unresolved composition: {parent} -> {child}"
            )

        if parent == child:
            raise ProjectionError(
                f"self-composition: {parent}"
            )

        source = index[parent]
        target = index[child]

        if (
            strict_levels
            and source.edifice == target.edifice
            and source.level is not None
            and target.level is not None
            and source.level <= target.level
        ):
            raise ProjectionError(
                f"invalid level direction: {parent} -> {child}"
            )

        forward[parent].add(child)
        reverse[child].add(parent)

    for identity in sorted(index):
        _reachable(identity, forward)

    if context is None:
        selected = set(index)
    else:
        if context not in index:
            raise ProjectionError(
                f"unknown composition context: {context}"
            )
        selected = {
            context,
            *_reachable(context, forward),
        }

    scoped_forward = {
        identity: forward[identity] & selected
        for identity in selected
    }
    scoped_reverse = {
        identity: reverse[identity] & selected
        for identity in selected
    }

    result: list[ElementProjection] = []

    for identity in sorted(selected):
        element = index[identity]
        parents = tuple(sorted(scoped_reverse[identity]))
        children = tuple(sorted(scoped_forward[identity]))

        result.append(
            ElementProjection(
                identity=identity,
                edifice=element.edifice,
                level=element.level,
                name=element.name,
                kindred=_label(
                    bool(parents),
                    bool(children),
                ),
                parents=parents,
                children=children,
                ancestors=_reachable(
                    identity,
                    scoped_reverse,
                ),
                descendants=_reachable(
                    identity,
                    scoped_forward,
                ),
            )
        )

    return tuple(result)


def as_metadata(
    projection: ElementProjection,
) -> dict[str, object]:
    """Serialize derived metadata without storing new authority."""
    return {
        "identity": projection.identity,
        "edifice": projection.edifice,
        "level": projection.level,
        "name": projection.name,
        "kindred": {
            "ascending": projection.kindred.ascending,
            "current": projection.kindred.current,
            "descending": projection.kindred.descending,
            "label": projection.kindred.value,
        },
        "parents": list(projection.parents),
        "children": list(projection.children),
        "ancestors": list(projection.ancestors),
        "descendants": list(projection.descendants),
    }
