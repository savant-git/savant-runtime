from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
import math
from typing import Any, Mapping, Sequence


SCHEMA = "savant://noumenon/orientation/1"


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


def _finite(value: float) -> float:
    result = float(value)

    if not math.isfinite(result):
        raise ValueError(
            "orientation values must be finite"
        )

    return result


@dataclass(frozen=True, slots=True)
class OrientationInfluence:
    significance_ref: str
    dimension: str
    magnitude: float
    weight: float = 1.0
    provenance_refs: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = ()
    authority_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.significance_ref:
            raise ValueError(
                "significance_ref is required"
            )

        if not self.dimension:
            raise ValueError(
                "dimension is required"
            )

        _finite(self.magnitude)

        weight = _finite(self.weight)

        if weight < 0:
            raise ValueError(
                "weight must be nonnegative"
            )

    @property
    def weighted_magnitude(self) -> float:
        return (
            _finite(self.magnitude)
            * _finite(self.weight)
        )

    def projection(self) -> dict[str, Any]:
        body: dict[str, Any] = {
            "schema": SCHEMA,
            "significance_ref": (
                self.significance_ref
            ),
            "dimension": self.dimension,
            "magnitude": float(
                self.magnitude
            ),
            "weight": float(self.weight),
            "weighted_magnitude": (
                self.weighted_magnitude
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
            "source_mutated": False,
            "authority_transferred": False,
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
            "noumenon-orientation-influence:"
            + self.digest
        )


@dataclass(frozen=True, slots=True)
class OrientationDimension:
    dimension: str
    magnitude: float
    influence_count: int
    influence_refs: tuple[str, ...]

    def projection(self) -> dict[str, Any]:
        body: dict[str, Any] = {
            "schema": SCHEMA,
            "dimension": self.dimension,
            "magnitude": float(
                self.magnitude
            ),
            "influence_count": (
                self.influence_count
            ),
            "influence_refs": list(
                self.influence_refs
            ),
            "projection_only": True,
            "authority_effect": "none",
        }

        body["digest"] = _digest(body)
        return body


def derive_orientation(
    influences: Sequence[
        OrientationInfluence
    ],
) -> tuple[OrientationDimension, ...]:
    ordered = tuple(
        sorted(
            influences,
            key=lambda influence: (
                influence.dimension,
                influence.significance_ref,
                influence.id,
            ),
        )
    )

    grouped: dict[
        str,
        list[OrientationInfluence],
    ] = {}

    for influence in ordered:
        grouped.setdefault(
            influence.dimension,
            [],
        ).append(influence)

    dimensions = []

    for dimension in sorted(grouped):
        members = grouped[dimension]

        magnitude = sum(
            member.weighted_magnitude
            for member in members
        )

        dimensions.append(
            OrientationDimension(
                dimension=dimension,
                magnitude=magnitude,
                influence_count=len(
                    members
                ),
                influence_refs=tuple(
                    member.id
                    for member in members
                ),
            )
        )

    return tuple(dimensions)


def orientation_projection(
    influences: Sequence[
        OrientationInfluence
    ],
) -> Mapping[str, Any]:
    dimensions = derive_orientation(
        influences
    )

    body: dict[str, Any] = {
        "schema": SCHEMA,
        "semantic_scope": (
            "significance-derived orientation "
            "of becoming"
        ),
        "dimensions": [
            dimension.projection()
            for dimension in dimensions
        ],
        "dimension_count": len(
            dimensions
        ),
        "influence_count": len(
            influences
        ),
        "orientation_is_derived": True,
        "orientation_is_authority": False,
        "orientation_is_external_truth": False,
        "significance_authority_replaced": False,
        "becoming_authority_replaced": False,
        "automatic_action": False,
        "automatic_reconciliation": False,
        "source_mutated": False,
        "authority_transferred": False,
        "model_independent": True,
        "provider_independent": True,
        "deterministic": True,
        "historical_pivot_kernel": (
            "directional orientation"
        ),
        "historical_pivot_authority": False,
        "historical_pivot_runtime_required": False,
        "derived": True,
        "authoritative": False,
        "authority_effect": "none",
    }

    body["digest"] = _digest(body)
    return body
