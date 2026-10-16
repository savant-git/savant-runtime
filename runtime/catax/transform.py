from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from typing import Any, Mapping, Sequence

from runtime.catax.core import (
    TemporalCoordinate,
    TemporalGeometry,
)


SCHEMA = "savant://catax/transform/1"

TRANSFORMS = frozenset(
    {
        "identity",
        "translate",
        "scale",
        "reflect",
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
class TemporalTransform:
    transform_ref: str
    kind: str
    offset: float = 0.0
    factor: float = 1.0
    pivot: float = 0.0
    provenance_refs: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = ()
    authority_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.transform_ref:
            raise ValueError(
                "transform_ref is required"
            )

        if self.kind not in TRANSFORMS:
            raise ValueError(
                "unsupported temporal transform"
            )

        if (
            self.kind == "scale"
            and self.factor == 0.0
        ):
            raise ValueError(
                "scale factor cannot be zero"
            )

    def projection(self) -> dict[str, Any]:
        body: dict[str, Any] = {
            "schema": SCHEMA,
            "transform_ref": self.transform_ref,
            "kind": self.kind,
            "offset": float(self.offset),
            "factor": float(self.factor),
            "pivot": float(self.pivot),
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
            "external_chronology_claimed": False,
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
            "catax-transform:"
            + self.digest
        )


@dataclass(frozen=True, slots=True)
class TransformedCoordinate:
    source_ref: str
    transform_ref: str
    frame_ref: str
    source_phase: float
    projected_phase: float
    uncertainty: float

    def projection(self) -> dict[str, Any]:
        body: dict[str, Any] = {
            "schema": SCHEMA,
            "source_ref": self.source_ref,
            "transform_ref": (
                self.transform_ref
            ),
            "frame_ref": self.frame_ref,
            "source_phase": float(
                self.source_phase
            ),
            "projected_phase": float(
                self.projected_phase
            ),
            "uncertainty": float(
                self.uncertainty
            ),
            "source_mutated": False,
            "derived": True,
            "authoritative": False,
            "authority_effect": "none",
        }

        body["digest"] = _digest(body)
        return body


def apply_transform(
    coordinate: TemporalCoordinate,
    transform: TemporalTransform,
) -> TransformedCoordinate:
    if coordinate.phase is None:
        raise ValueError(
            "coordinate phase is required"
        )

    source = float(coordinate.phase)

    if transform.kind == "identity":
        projected = source

    elif transform.kind == "translate":
        projected = (
            source
            + transform.offset
        )

    elif transform.kind == "scale":
        projected = (
            transform.pivot
            + (
                source
                - transform.pivot
            )
            * transform.factor
        )

    elif transform.kind == "reflect":
        projected = (
            2.0 * transform.pivot
            - source
        )

    else:
        raise ValueError(
            "unsupported temporal transform"
        )

    return TransformedCoordinate(
        source_ref=coordinate.id,
        transform_ref=transform.id,
        frame_ref=coordinate.frame_ref,
        source_phase=source,
        projected_phase=projected,
        uncertainty=float(
            coordinate.uncertainty
        ),
    )


def transform_geometry(
    left: TemporalCoordinate,
    right: TemporalCoordinate,
    transform: TemporalTransform,
) -> TemporalGeometry:
    projected_left = apply_transform(
        left,
        transform,
    )
    projected_right = apply_transform(
        right,
        transform,
    )

    uncertainty = (
        projected_left.uncertainty
        + projected_right.uncertainty
    )

    delta = (
        projected_right.projected_phase
        - projected_left.projected_phase
    )

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
        provenance_refs=(
            transform.id,
        ),
    )


def transform_projection(
    coordinates: Sequence[
        TemporalCoordinate
    ],
    transform: TemporalTransform,
) -> Mapping[str, Any]:
    projected = tuple(
        apply_transform(
            coordinate,
            transform,
        )
        for coordinate in coordinates
    )

    body: dict[str, Any] = {
        "schema": SCHEMA,
        "transform": (
            transform.projection()
        ),
        "coordinates": [
            item.projection()
            for item in projected
        ],
        "source_count": len(
            coordinates
        ),
        "projection_count": len(
            projected
        ),
        "source_mutated": False,
        "order_fabricated": False,
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
