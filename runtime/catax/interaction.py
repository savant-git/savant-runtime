from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from typing import Any, Mapping, Sequence

from runtime.catax.core import (
    TemporalCoordinate,
    TemporalGeometry,
    relate,
)


SCHEMA = "savant://catax/interaction/1"

INTERACTIONS = frozenset(
    {
        "aligned",
        "opposed",
        "coincident",
        "uncertain",
        "cross_frame",
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
class CataxInteraction:
    left_ref: str
    right_ref: str
    interaction: str
    geometry_relation: str
    magnitude: float | None
    uncertainty: float
    reasons: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.left_ref:
            raise ValueError(
                "left_ref is required"
            )

        if not self.right_ref:
            raise ValueError(
                "right_ref is required"
            )

        if self.interaction not in INTERACTIONS:
            raise ValueError(
                "unsupported catax interaction"
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
            "interaction": self.interaction,
            "geometry_relation": (
                self.geometry_relation
            ),
            "magnitude": self.magnitude,
            "uncertainty": float(
                self.uncertainty
            ),
            "reasons": list(self.reasons),
            "interaction_is_projection": True,
            "source_mutated": False,
            "external_chronology_claimed": False,
            "authority_transferred": False,
            "automatic_reconciliation": False,
            "derived": True,
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
            "catax-interaction:"
            + self.digest
        )


def classify_interaction(
    left: TemporalCoordinate,
    right: TemporalCoordinate,
) -> CataxInteraction:
    geometry: TemporalGeometry = relate(
        left,
        right,
    )

    if left.frame_ref != right.frame_ref:
        interaction = "cross_frame"
        reasons = (
            "distinct_temporal_frames",
            "implicit_cross_frame_order_forbidden",
        )

    elif geometry.relation == "unknown":
        interaction = "uncertain"
        reasons = (
            "insufficient_temporal_coordinates",
        )

    elif geometry.relation == "concurrent":
        interaction = "coincident"
        reasons = (
            "coordinates_temporally_concurrent",
        )

    elif geometry.relation in {
        "precedes",
        "follows",
    }:
        interaction = "aligned"
        reasons = (
            "directed_temporal_separation",
        )

    else:
        interaction = "uncertain"
        reasons = (
            "geometry_does_not_support"
            "_stronger_classification",
        )

    return CataxInteraction(
        left_ref=left.id,
        right_ref=right.id,
        interaction=interaction,
        geometry_relation=(
            geometry.relation
        ),
        magnitude=geometry.distance,
        uncertainty=geometry.uncertainty,
        reasons=reasons,
    )


def compare_interactions(
    first: CataxInteraction,
    second: CataxInteraction,
) -> CataxInteraction:
    if (
        first.left_ref != second.left_ref
        or first.right_ref
        != second.right_ref
    ):
        raise ValueError(
            "interaction endpoints differ"
        )

    if (
        first.interaction
        == second.interaction
        and first.geometry_relation
        == second.geometry_relation
    ):
        return first

    return CataxInteraction(
        left_ref=first.left_ref,
        right_ref=first.right_ref,
        interaction="opposed",
        geometry_relation="diverges",
        magnitude=None,
        uncertainty=max(
            first.uncertainty,
            second.uncertainty,
        ),
        reasons=(
            "incompatible_interaction_assertions",
            first.id,
            second.id,
        ),
    )


def interaction_projection(
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

    interactions: list[
        CataxInteraction
    ] = []

    for index, left in enumerate(
        ordered
    ):
        for right in ordered[
            index + 1:
        ]:
            interactions.append(
                classify_interaction(
                    left,
                    right,
                )
            )

    body: dict[str, Any] = {
        "schema": SCHEMA,
        "coordinate_refs": [
            coordinate.id
            for coordinate in ordered
        ],
        "interactions": [
            interaction.projection()
            for interaction
            in interactions
        ],
        "coordinate_count": len(
            ordered
        ),
        "interaction_count": len(
            interactions
        ),
        "cross_frame_order_inferred": False,
        "contradictions_preserved": True,
        "unknowns_preserved": True,
        "source_mutated": False,
        "automatic_reconciliation": False,
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
