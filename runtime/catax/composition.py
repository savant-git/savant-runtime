from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from typing import Any, Mapping, Sequence

from runtime.catax.core import (
    TemporalCoordinate,
)
from runtime.catax.transform import (
    TemporalTransform,
    apply_transform,
)


SCHEMA = "savant://catax/composition/1"


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
class TransformChain:
    chain_ref: str
    transforms: tuple[
        TemporalTransform,
        ...
    ]
    provenance_refs: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = ()
    authority_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.chain_ref:
            raise ValueError(
                "chain_ref is required"
            )

        if not self.transforms:
            raise ValueError(
                "transform chain cannot be empty"
            )

        ids = tuple(
            transform.id
            for transform in self.transforms
        )

        if len(ids) != len(set(ids)):
            raise ValueError(
                "duplicate transform instance"
            )

    def projection(self) -> dict[str, Any]:
        body: dict[str, Any] = {
            "schema": SCHEMA,
            "chain_ref": self.chain_ref,
            "transform_refs": [
                transform.id
                for transform
                in self.transforms
            ],
            "provenance_refs": list(
                self.provenance_refs
            ),
            "evidence_refs": list(
                self.evidence_refs
            ),
            "authority_refs": list(
                self.authority_refs
            ),
            "ordered_composition": True,
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
            "catax-chain:"
            + self.digest
        )


@dataclass(frozen=True, slots=True)
class CompositionResult:
    source_ref: str
    chain_ref: str
    frame_ref: str
    source_phase: float
    projected_phase: float
    uncertainty: float
    step_phases: tuple[float, ...]

    def projection(self) -> dict[str, Any]:
        body: dict[str, Any] = {
            "schema": SCHEMA,
            "source_ref": self.source_ref,
            "chain_ref": self.chain_ref,
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
            "step_phases": [
                float(value)
                for value
                in self.step_phases
            ],
            "source_mutated": False,
            "intermediate_states_preserved": True,
            "external_chronology_claimed": False,
            "authority_transferred": False,
            "derived": True,
            "authoritative": False,
            "authority_effect": "none",
        }

        body["digest"] = _digest(body)
        return body


def apply_chain(
    coordinate: TemporalCoordinate,
    chain: TransformChain,
) -> CompositionResult:
    if coordinate.phase is None:
        raise ValueError(
            "coordinate phase is required"
        )

    current = coordinate
    phases: list[float] = []

    for index, transform in enumerate(
        chain.transforms
    ):
        result = apply_transform(
            current,
            transform,
        )

        phases.append(
            result.projected_phase
        )

        current = TemporalCoordinate(
            coordinate_ref=(
                f"{coordinate.coordinate_ref}:"
                f"projection:{index}"
            ),
            frame_ref=coordinate.frame_ref,
            sequence=coordinate.sequence,
            phase=result.projected_phase,
            uncertainty=(
                coordinate.uncertainty
            ),
            provenance_refs=(
                *coordinate.provenance_refs,
                transform.id,
            ),
            evidence_refs=(
                coordinate.evidence_refs
            ),
            authority_refs=(
                coordinate.authority_refs
            ),
        )

    return CompositionResult(
        source_ref=coordinate.id,
        chain_ref=chain.id,
        frame_ref=coordinate.frame_ref,
        source_phase=float(
            coordinate.phase
        ),
        projected_phase=float(
            current.phase
        ),
        uncertainty=float(
            coordinate.uncertainty
        ),
        step_phases=tuple(phases),
    )


def composition_projection(
    coordinates: Sequence[
        TemporalCoordinate
    ],
    chain: TransformChain,
) -> Mapping[str, Any]:
    results = tuple(
        apply_chain(
            coordinate,
            chain,
        )
        for coordinate in coordinates
    )

    body: dict[str, Any] = {
        "schema": SCHEMA,
        "chain": chain.projection(),
        "results": [
            result.projection()
            for result in results
        ],
        "source_count": len(
            coordinates
        ),
        "result_count": len(
            results
        ),
        "composition_order_preserved": True,
        "source_mutated": False,
        "intermediate_states_preserved": True,
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
