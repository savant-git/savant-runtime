from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from typing import Any, Mapping, Sequence

from runtime.oid.constraint import TemporalConstraint
from runtime.oid.core import TemporalRecord


SCHEMA = "savant://oid/bridge/1"

BRIDGE_RELATIONS = frozenset(
    {
        "before",
        "after",
        "equal",
        "overlaps",
        "contains",
        "contained_by",
        "concurrent",
        "conflicting",
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
class TemporalBridge:
    left_frame_ref: str
    left_record_ref: str
    right_frame_ref: str
    right_record_ref: str
    relation: str
    evidence_refs: tuple[str, ...] = ()
    provenance_refs: tuple[str, ...] = ()
    authority_refs: tuple[str, ...] = ()
    bridge_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.left_frame_ref:
            raise ValueError(
                "left_frame_ref is required"
            )

        if not self.right_frame_ref:
            raise ValueError(
                "right_frame_ref is required"
            )

        if not self.left_record_ref:
            raise ValueError(
                "left_record_ref is required"
            )

        if not self.right_record_ref:
            raise ValueError(
                "right_record_ref is required"
            )

        if (
            self.left_frame_ref
            == self.right_frame_ref
        ):
            raise ValueError(
                "oid bridge requires distinct frames"
            )

        if self.relation not in BRIDGE_RELATIONS:
            raise ValueError(
                "unsupported bridge relation"
            )

    def projection(self) -> dict[str, Any]:
        body: dict[str, Any] = {
            "schema": SCHEMA,
            "left_frame_ref": (
                self.left_frame_ref
            ),
            "left_record_ref": (
                self.left_record_ref
            ),
            "right_frame_ref": (
                self.right_frame_ref
            ),
            "right_record_ref": (
                self.right_record_ref
            ),
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
            "bridge_refs": list(
                self.bridge_refs
            ),
            "cross_frame": True,
            "authority_transferred": False,
            "derived": False,
            "authoritative": False,
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
        return "oid-bridge:" + self.digest


@dataclass(frozen=True, slots=True)
class BridgeConflict:
    bridge_refs: tuple[str, ...]
    endpoint_refs: tuple[str, ...]
    reason: str

    def projection(self) -> dict[str, Any]:
        body: dict[str, Any] = {
            "schema": SCHEMA,
            "bridge_refs": list(
                self.bridge_refs
            ),
            "endpoint_refs": list(
                self.endpoint_refs
            ),
            "reason": self.reason,
            "automatically_resolved": False,
            "authority_transferred": False,
            "derived": True,
            "authoritative": False,
            "authority_effect": "none",
        }

        body["digest"] = _digest(body)
        return body


def validate_bridge_records(
    bridge: TemporalBridge,
    records: Sequence[TemporalRecord],
) -> bool:
    by_id = {
        record.id: record
        for record in records
    }

    left = by_id.get(
        bridge.left_record_ref
    )

    right = by_id.get(
        bridge.right_record_ref
    )

    if left is None or right is None:
        return False

    if (
        left.frame_ref
        != bridge.left_frame_ref
    ):
        return False

    if (
        right.frame_ref
        != bridge.right_frame_ref
    ):
        return False

    return True


def detect_bridge_conflicts(
    bridges: Sequence[TemporalBridge],
) -> tuple[BridgeConflict, ...]:
    grouped: dict[
        tuple[
            tuple[str, str],
            tuple[str, str],
        ],
        list[TemporalBridge],
    ] = {}

    for bridge in bridges:
        left = (
            bridge.left_frame_ref,
            bridge.left_record_ref,
        )

        right = (
            bridge.right_frame_ref,
            bridge.right_record_ref,
        )

        key = tuple(
            sorted(
                (
                    left,
                    right,
                )
            )
        )

        grouped.setdefault(
            key,
            [],
        ).append(bridge)

    conflicts: list[BridgeConflict] = []

    for endpoints, items in sorted(
        grouped.items()
    ):
        normalized: set[
            tuple[
                tuple[str, str],
                tuple[str, str],
            ]
        ] = set()

        nonordering: set[str] = set()

        for item in items:
            left = (
                item.left_frame_ref,
                item.left_record_ref,
            )

            right = (
                item.right_frame_ref,
                item.right_record_ref,
            )

            if item.relation == "before":
                normalized.add(
                    (left, right)
                )

            elif item.relation == "after":
                normalized.add(
                    (right, left)
                )

            elif item.relation in {
                "equal",
                "concurrent",
                "conflicting",
            }:
                nonordering.add(
                    item.relation
                )

        contradictory = (
            len(normalized) > 1
            or (
                bool(normalized)
                and bool(nonordering)
            )
            or len(nonordering) > 1
        )

        if contradictory:
            conflicts.append(
                BridgeConflict(
                    bridge_refs=tuple(
                        sorted(
                            item.id
                            for item in items
                        )
                    ),
                    endpoint_refs=tuple(
                        sorted(
                            {
                                (
                                    frame_ref
                                    + "::"
                                    + record_ref
                                )
                                for frame_ref,
                                record_ref
                                in endpoints
                            }
                        )
                    ),
                    reason=(
                        "incompatible_cross_frame_relations"
                    ),
                )
            )

    return tuple(conflicts)


def bridge_constraint(
    bridge: TemporalBridge,
) -> TemporalConstraint | None:
    if bridge.relation not in {
        "before",
        "after",
        "equal",
        "concurrent",
        "unknown",
    }:
        return None

    return TemporalConstraint(
        left_ref=bridge.left_record_ref,
        right_ref=bridge.right_record_ref,
        relation=bridge.relation,
        evidence_refs=bridge.evidence_refs,
        provenance_refs=(
            bridge.provenance_refs
        ),
        authority_refs=bridge.authority_refs,
    )


def bridge_projection(
    bridges: Sequence[TemporalBridge],
) -> Mapping[str, Any]:
    ordered = tuple(
        sorted(
            bridges,
            key=lambda item: item.id,
        )
    )

    conflicts = detect_bridge_conflicts(
        ordered
    )

    body: dict[str, Any] = {
        "schema": SCHEMA,
        "bridges": [
            bridge.projection()
            for bridge in ordered
        ],
        "bridge_count": len(ordered),
        "conflicts": [
            conflict.projection()
            for conflict in conflicts
        ],
        "conflict_count": len(conflicts),
        "cross_frame_order_requires_bridge": True,
        "implicit_cross_frame_order": False,
        "automatic_reconciliation": False,
        "authority_transferred": False,
        "derived": True,
        "authoritative": False,
        "authority_effect": "none",
    }

    body["digest"] = _digest(body)
    return body
