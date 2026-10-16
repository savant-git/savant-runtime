from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from typing import Any, Mapping, Sequence


SCHEMA = "savant://oid/constraint/1"

RELATIONS = frozenset(
    {
        "before",
        "after",
        "equal",
        "concurrent",
        "unknown",
    }
)


def _canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def _digest(value: Any) -> str:
    return sha256(
        _canonical_json(value).encode("utf-8")
    ).hexdigest()


@dataclass(frozen=True, slots=True)
class TemporalConstraint:
    left_ref: str
    right_ref: str
    relation: str
    evidence_refs: tuple[str, ...] = ()
    provenance_refs: tuple[str, ...] = ()
    authority_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.left_ref:
            raise ValueError(
                "left_ref is required"
            )

        if not self.right_ref:
            raise ValueError(
                "right_ref is required"
            )

        if self.left_ref == self.right_ref:
            if self.relation not in {
                "equal",
                "unknown",
            }:
                raise ValueError(
                    "self constraint cannot impose "
                    "strict temporal order"
                )

        if self.relation not in RELATIONS:
            raise ValueError(
                "unsupported temporal constraint"
            )

    def projection(self) -> dict[str, Any]:
        body: dict[str, Any] = {
            "schema": SCHEMA,
            "left_ref": self.left_ref,
            "right_ref": self.right_ref,
            "relation": self.relation,
            "evidence_refs": list(
                self.evidence_refs
            ),
            "provenance_refs": list(
                self.provenance_refs
            ),
            "authority_refs": list(
                self.authority_refs
            ),
            "authority_effect": "none",
        }

        body["digest"] = _digest(body)
        return body

    @property
    def digest(self) -> str:
        return str(
            self.projection()["digest"]
        )

    @property
    def id(self) -> str:
        return "oid-constraint:" + self.digest


@dataclass(frozen=True, slots=True)
class ConstraintConflict:
    constraint_refs: tuple[str, ...]
    subject_refs: tuple[str, ...]
    reason: str

    def projection(self) -> dict[str, Any]:
        body: dict[str, Any] = {
            "schema": SCHEMA,
            "constraint_refs": list(
                self.constraint_refs
            ),
            "subject_refs": list(
                self.subject_refs
            ),
            "reason": self.reason,
            "automatically_resolved": False,
            "derived": True,
            "authoritative": False,
            "authority_effect": "none",
        }

        body["digest"] = _digest(body)
        return body


def _strict_edges(
    constraints: Sequence[
        TemporalConstraint
    ],
) -> dict[str, set[str]]:
    edges: dict[str, set[str]] = {}

    for constraint in constraints:
        if constraint.relation == "before":
            edges.setdefault(
                constraint.left_ref,
                set(),
            ).add(
                constraint.right_ref
            )

        elif constraint.relation == "after":
            edges.setdefault(
                constraint.right_ref,
                set(),
            ).add(
                constraint.left_ref
            )

    return edges


def _reachable(
    edges: Mapping[str, set[str]],
    start: str,
    target: str,
) -> bool:
    pending = [start]
    visited: set[str] = set()

    while pending:
        current = pending.pop()

        if current == target:
            return True

        if current in visited:
            continue

        visited.add(current)

        pending.extend(
            sorted(
                edges.get(
                    current,
                    set(),
                ),
                reverse=True,
            )
        )

    return False


def relation_from_constraints(
    left_ref: str,
    right_ref: str,
    constraints: Sequence[
        TemporalConstraint
    ],
) -> str:
    if left_ref == right_ref:
        return "equal"

    edges = _strict_edges(constraints)

    left_before_right = _reachable(
        edges,
        left_ref,
        right_ref,
    )

    right_before_left = _reachable(
        edges,
        right_ref,
        left_ref,
    )

    if (
        left_before_right
        and right_before_left
    ):
        return "unknown"

    if left_before_right:
        return "before"

    if right_before_left:
        return "after"

    explicit = {
        constraint.relation
        for constraint in constraints
        if (
            constraint.left_ref == left_ref
            and constraint.right_ref
            == right_ref
        )
    }

    if explicit == {"equal"}:
        return "equal"

    if explicit == {"concurrent"}:
        return "concurrent"

    return "unknown"


def detect_constraint_conflicts(
    constraints: Sequence[
        TemporalConstraint
    ],
) -> tuple[ConstraintConflict, ...]:
    conflicts: list[
        ConstraintConflict
    ] = []

    grouped: dict[
        tuple[str, str],
        list[TemporalConstraint],
    ] = {}

    for constraint in constraints:
        key = tuple(
            sorted(
                (
                    constraint.left_ref,
                    constraint.right_ref,
                )
            )
        )

        grouped.setdefault(
            key,
            [],
        ).append(constraint)

    for subjects, items in sorted(
        grouped.items()
    ):
        directions: set[
            tuple[str, str]
        ] = set()

        equality = False
        concurrency = False

        for item in items:
            if item.relation == "before":
                directions.add(
                    (
                        item.left_ref,
                        item.right_ref,
                    )
                )

            elif item.relation == "after":
                directions.add(
                    (
                        item.right_ref,
                        item.left_ref,
                    )
                )

            elif item.relation == "equal":
                equality = True

            elif item.relation == "concurrent":
                concurrency = True

        contradictory = (
            len(directions) > 1
            or (
                equality
                and bool(directions)
            )
            or (
                concurrency
                and bool(directions)
            )
            or (
                equality
                and concurrency
            )
        )

        if contradictory:
            conflicts.append(
                ConstraintConflict(
                    constraint_refs=tuple(
                        sorted(
                            item.id
                            for item in items
                        )
                    ),
                    subject_refs=subjects,
                    reason=(
                        "incompatible_temporal_constraints"
                    ),
                )
            )

    edges = _strict_edges(constraints)

    nodes = sorted(
        {
            ref
            for constraint in constraints
            for ref in (
                constraint.left_ref,
                constraint.right_ref,
            )
        }
    )

    cycle_nodes = tuple(
        node
        for node in nodes
        if any(
            node in targets
            and _reachable(
                edges,
                node,
                source,
            )
            for source, targets
            in edges.items()
        )
    )

    if cycle_nodes:
        strict_refs = tuple(
            sorted(
                constraint.id
                for constraint in constraints
                if constraint.relation
                in {"before", "after"}
            )
        )

        conflicts.append(
            ConstraintConflict(
                constraint_refs=strict_refs,
                subject_refs=cycle_nodes,
                reason="strict_order_cycle",
            )
        )

    unique: dict[
        str,
        ConstraintConflict,
    ] = {}

    for conflict in conflicts:
        unique[
            str(
                conflict.projection()[
                    "digest"
                ]
            )
        ] = conflict

    return tuple(
        unique[key]
        for key in sorted(unique)
    )


def constraint_projection(
    constraints: Sequence[
        TemporalConstraint
    ],
) -> Mapping[str, Any]:
    ordered = tuple(
        sorted(
            constraints,
            key=lambda item: item.id,
        )
    )

    conflicts = (
        detect_constraint_conflicts(
            ordered
        )
    )

    body: dict[str, Any] = {
        "schema": SCHEMA,
        "constraints": [
            item.projection()
            for item in ordered
        ],
        "constraint_count": len(ordered),
        "conflicts": [
            conflict.projection()
            for conflict in conflicts
        ],
        "conflict_count": len(conflicts),
        "partial_order_preserved": True,
        "unknown_order_preserved": True,
        "concurrency_preserved": True,
        "automatic_reconciliation": False,
        "authority_transferred": False,
        "derived": True,
        "authoritative": False,
        "authority_effect": "none",
    }

    body["digest"] = _digest(body)
    return body
