from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from typing import Any, Mapping, Sequence


SCHEMA = "savant://noumenon/meaning-inheritance/1"


def _canonical_json(
    value: Any,
) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def _digest(
    value: Any,
) -> str:
    return sha256(
        _canonical_json(value).encode(
            "utf-8"
        )
    ).hexdigest()


def _signed(
    value: float,
) -> float:
    return max(
        -1.0,
        min(
            1.0,
            float(value),
        ),
    )


def _unit(
    value: float,
) -> float:
    return max(
        0.0,
        min(
            1.0,
            float(value),
        ),
    )


@dataclass(frozen=True, slots=True)
class MeaningSource:
    source_ref: str
    dimensions: Mapping[str, float]
    significance: float
    confidence: float
    causal_refs: tuple[str, ...]
    evidence_refs: tuple[str, ...] = ()
    authority_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.source_ref:
            raise ValueError(
                "source_ref is required"
            )

        if not self.dimensions:
            raise ValueError(
                "dimensions are required"
            )

        if not self.causal_refs:
            raise ValueError(
                "meaning source requires "
                "causal refs"
            )

        for dimension, value in (
            self.dimensions.items()
        ):
            if not dimension:
                raise ValueError(
                    "dimension is required"
                )

            if not (
                -1.0
                <= float(value)
                <= 1.0
            ):
                raise ValueError(
                    "dimension values must be "
                    "between -1 and 1"
                )

        for value in (
            self.significance,
            self.confidence,
        ):
            if not (
                0.0
                <= float(value)
                <= 1.0
            ):
                raise ValueError(
                    "significance and confidence "
                    "must be between 0 and 1"
                )

    def projection(
        self,
    ) -> dict[str, Any]:
        return {
            "schema": SCHEMA,
            "source_ref": self.source_ref,
            "dimensions": {
                key: float(value)
                for key, value
                in sorted(
                    self.dimensions.items()
                )
            },
            "significance": float(
                self.significance
            ),
            "confidence": float(
                self.confidence
            ),
            "causal_refs": list(
                self.causal_refs
            ),
            "evidence_refs": list(
                self.evidence_refs
            ),
            "authority_refs": list(
                self.authority_refs
            ),
            "authority_effect": "none",
        }

    @property
    def digest(self) -> str:
        return _digest(
            self.projection()
        )

    @property
    def id(self) -> str:
        return (
            "noumenon-meaning-source:"
            + self.digest
        )


@dataclass(frozen=True, slots=True)
class MeaningInheritance:
    source_ref: str
    successor_ref: str
    inherited_dimensions: Mapping[
        str,
        float,
    ]
    inheritance_strength: float
    revision_pressure: float
    causal_refs: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.source_ref:
            raise ValueError(
                "source_ref is required"
            )

        if not self.successor_ref:
            raise ValueError(
                "successor_ref is required"
            )

        for value in (
            self.inheritance_strength,
            self.revision_pressure,
        ):
            if not (
                0.0
                <= float(value)
                <= 1.0
            ):
                raise ValueError(
                    "inheritance values must be "
                    "between 0 and 1"
                )

        for value in (
            self.inherited_dimensions
            .values()
        ):
            if not (
                -1.0
                <= float(value)
                <= 1.0
            ):
                raise ValueError(
                    "inherited dimensions must "
                    "be between -1 and 1"
                )

    def projection(
        self,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {
            "schema": SCHEMA,
            "source_ref": self.source_ref,
            "successor_ref": (
                self.successor_ref
            ),
            "inherited_dimensions": {
                key: float(value)
                for key, value
                in sorted(
                    self
                    .inherited_dimensions
                    .items()
                )
            },
            "inheritance_strength": float(
                self.inheritance_strength
            ),
            "revision_pressure": float(
                self.revision_pressure
            ),
            "causal_refs": list(
                self.causal_refs
            ),
            "derived": True,
            "authoritative": False,
            "authority_effect": "none",
        }

        body["digest"] = _digest(body)

        return body


def inherit_meaning(
    source: MeaningSource,
    *,
    successor_ref: str,
    continuity: float,
    reinterpretation: float,
    causal_refs: Sequence[str] = (),
) -> MeaningInheritance:
    if not successor_ref:
        raise ValueError(
            "successor_ref is required"
        )

    if not (
        0.0
        <= float(continuity)
        <= 1.0
    ):
        raise ValueError(
            "continuity must be between "
            "0 and 1"
        )

    if not (
        0.0
        <= float(reinterpretation)
        <= 1.0
    ):
        raise ValueError(
            "reinterpretation must be "
            "between 0 and 1"
        )

    inheritance_strength = _unit(
        float(source.significance)
        * float(source.confidence)
        * float(continuity)
    )

    revision_pressure = _unit(
        float(reinterpretation)
        * (
            1.0
            - (
                0.5
                * inheritance_strength
            )
        )
    )

    retained = _unit(
        inheritance_strength
        * (
            1.0
            - revision_pressure
        )
    )

    dimensions = {
        dimension: _signed(
            float(value)
            * retained
        )
        for dimension, value
        in source.dimensions.items()
    }

    return MeaningInheritance(
        source_ref=source.id,
        successor_ref=successor_ref,
        inherited_dimensions=dimensions,
        inheritance_strength=(
            inheritance_strength
        ),
        revision_pressure=(
            revision_pressure
        ),
        causal_refs=tuple(
            dict.fromkeys(
                (
                    source.id,
                    *source.causal_refs,
                    *causal_refs,
                )
            )
        ),
    )


def inherited_field(
    inheritances: Sequence[
        MeaningInheritance
    ],
) -> Mapping[str, float]:
    totals: dict[str, float] = {}
    weights: dict[str, float] = {}

    for inheritance in inheritances:
        weight = float(
            inheritance.inheritance_strength
        )

        if weight <= 0.0:
            continue

        for dimension, value in (
            inheritance
            .inherited_dimensions
            .items()
        ):
            totals[dimension] = (
                totals.get(
                    dimension,
                    0.0,
                )
                + float(value)
                * weight
            )

            weights[dimension] = (
                weights.get(
                    dimension,
                    0.0,
                )
                + weight
            )

    return {
        dimension: _signed(
            totals[dimension]
            / weights[dimension]
        )
        for dimension
        in sorted(totals)
        if weights[dimension] > 0.0
    }


def inheritance_projection(
    inheritances: Sequence[
        MeaningInheritance
    ],
) -> Mapping[str, Any]:
    return {
        "schema": SCHEMA,
        "inheritances": [
            inheritance.projection()
            for inheritance
            in inheritances
        ],
        "field": dict(
            inherited_field(
                inheritances
            )
        ),
        "meaning_can_be_revised": True,
        "inheritance_is_identity": False,
        "inheritance_is_authority": False,
        "source_history_erased": False,
        "automatic_identity_mutation": False,
        "derived": True,
        "authoritative": False,
        "authority_effect": "none",
    }
