from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from typing import Any, Mapping, Sequence


SCHEMA = "savant://catax/core/1"

RELATIONS = frozenset(
    {
        "precedes",
        "follows",
        "concurrent",
        "overlaps",
        "contains",
        "contained_by",
        "diverges",
        "converges",
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
class TemporalCoordinate:
    coordinate_ref: str
    frame_ref: str
    sequence: int | None = None
    phase: float | None = None
    uncertainty: float = 0.0
    provenance_refs: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = ()
    authority_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.coordinate_ref:
            raise ValueError(
                "coordinate_ref is required"
            )

        if not self.frame_ref:
            raise ValueError(
                "frame_ref is required"
            )

        if (
            self.sequence is not None
            and self.sequence < 0
        ):
            raise ValueError(
                "sequence must be nonnegative"
            )

        if self.uncertainty < 0:
            raise ValueError(
                "uncertainty must be nonnegative"
            )

    def projection(self) -> dict[str, Any]:
        body: dict[str, Any] = {
            "schema": SCHEMA,
            "coordinate_ref": (
                self.coordinate_ref
            ),
            "frame_ref": self.frame_ref,
            "sequence": self.sequence,
            "phase": self.phase,
            "uncertainty": float(
                self.uncertainty
            ),
            "provenance_refs": list(
                self.provenance_refs
            ),
            "evidence_refs": list(
                self.evidence_refs
            ),
            "authority_refs": list(
                self.authority_refs
            ),
            "temporal_geometry_is_projection": True,
            "external_chronology_claimed": False,
            "authority_transferred": False,
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
        return (
            "catax-coordinate:"
            + self.digest
        )


@dataclass(frozen=True, slots=True)
class TemporalGeometry:
    left_ref: str
    right_ref: str
    relation: str
    distance: float | None = None
    uncertainty: float = 0.0
    provenance_refs: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = ()
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

        if self.relation not in RELATIONS:
            raise ValueError(
                "unsupported temporal geometry relation"
            )

        if self.uncertainty < 0:
            raise ValueError(
                "uncertainty must be nonnegative"
            )

    def projection(self) -> dict[str, Any]:
        body: dict[str, Any] = {
            "schema": SCHEMA,
            "left_ref": self.left_ref,
            "right_ref": self.right_ref,
            "relation": self.relation,
            "distance": self.distance,
            "uncertainty": float(
                self.uncertainty
            ),
            "provenance_refs": list(
                self.provenance_refs
            ),
            "evidence_refs": list(
                self.evidence_refs
            ),
            "authority_refs": list(
                self.authority_refs
            ),
            "derived": True,
            "external_chronology_claimed": False,
            "authority_transferred": False,
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
        return (
            "catax-geometry:"
            + self.digest
        )


def relate(
    left: TemporalCoordinate,
    right: TemporalCoordinate,
) -> TemporalGeometry:
    uncertainty = (
        float(left.uncertainty)
        + float(right.uncertainty)
    )

    if (
        left.frame_ref
        != right.frame_ref
    ):
        return TemporalGeometry(
            left_ref=left.id,
            right_ref=right.id,
            relation="unknown",
            uncertainty=uncertainty,
        )

    if (
        left.sequence is not None
        and right.sequence is not None
    ):
        if left.sequence < right.sequence:
            relation = "precedes"
        elif left.sequence > right.sequence:
            relation = "follows"
        else:
            relation = "concurrent"

        return TemporalGeometry(
            left_ref=left.id,
            right_ref=right.id,
            relation=relation,
            distance=float(
                abs(
                    right.sequence
                    - left.sequence
                )
            ),
            uncertainty=uncertainty,
        )

    if (
        left.phase is not None
        and right.phase is not None
    ):
        delta = right.phase - left.phase

        if delta > uncertainty:
            relation = "precedes"
        elif delta < -uncertainty:
            relation = "follows"
        else:
            relation = "concurrent"

        return TemporalGeometry(
            left_ref=left.id,
            right_ref=right.id,
            relation=relation,
            distance=abs(delta),
            uncertainty=uncertainty,
        )

    return TemporalGeometry(
        left_ref=left.id,
        right_ref=right.id,
        relation="unknown",
        uncertainty=uncertainty,
    )


def geometry_projection(
    coordinates: Sequence[
        TemporalCoordinate
    ],
) -> Mapping[str, Any]:
    ordered = tuple(
        sorted(
            coordinates,
            key=lambda item: item.id,
        )
    )

    relations: list[
        TemporalGeometry
    ] = []

    for index, left in enumerate(
        ordered
    ):
        for right in ordered[
            index + 1:
        ]:
            relations.append(
                relate(left, right)
            )

    body: dict[str, Any] = {
        "schema": SCHEMA,
        "coordinates": [
            coordinate.projection()
            for coordinate in ordered
        ],
        "relations": [
            relation.projection()
            for relation in relations
        ],
        "coordinate_count": len(
            ordered
        ),
        "relation_count": len(
            relations
        ),
        "cross_frame_order_inferred": False,
        "unknowns_preserved": True,
        "temporal_geometry_is_projection": True,
        "external_chronology_claimed": False,
        "authority_transferred": False,
        "model_independent": True,
        "provider_independent": True,
        "derived": True,
        "authoritative": False,
        "authority_effect": "none",
    }

    body["digest"] = _digest(body)
    return body
