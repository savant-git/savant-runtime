from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from typing import Any, Mapping, Sequence


SCHEMA = "savant://noumenon/relational-transference/1"


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
        _canonical_json(value).encode("utf-8")
    ).hexdigest()


def _unit(
    value: float,
) -> float:
    return max(
        0.0,
        min(1.0, float(value)),
    )


def _signed(
    value: float,
) -> float:
    return max(
        -1.0,
        min(1.0, float(value)),
    )


@dataclass(frozen=True, slots=True)
class RelationalPattern:
    relationship_ref: str
    dimensions: Mapping[str, float]
    significance: float
    confidence: float
    causal_refs: tuple[str, ...]
    evidence_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.relationship_ref:
            raise ValueError(
                "relationship_ref is required"
            )

        if not self.dimensions:
            raise ValueError(
                "dimensions are required"
            )

        if not self.causal_refs:
            raise ValueError(
                "relational pattern requires "
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
                -1.0 <= float(value) <= 1.0
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
                0.0 <= float(value) <= 1.0
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
            "relationship_ref": (
                self.relationship_ref
            ),
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
            "noumenon-relational-pattern:"
            + self.digest
        )


@dataclass(frozen=True, slots=True)
class TransferenceHypothesis:
    source_relationship_ref: str
    target_relationship_ref: str
    shared_dimensions: tuple[str, ...]
    similarity: float
    activation: float
    pressure: Mapping[str, float]
    causal_refs: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.source_relationship_ref:
            raise ValueError(
                "source relationship required"
            )

        if not self.target_relationship_ref:
            raise ValueError(
                "target relationship required"
            )

        if (
            self.source_relationship_ref
            == self.target_relationship_ref
        ):
            raise ValueError(
                "transference requires "
                "distinct relationships"
            )

        for value in (
            self.similarity,
            self.activation,
        ):
            if not (
                0.0 <= float(value) <= 1.0
            ):
                raise ValueError(
                    "hypothesis values must be "
                    "between 0 and 1"
                )

        for value in self.pressure.values():
            if not (
                -1.0 <= float(value) <= 1.0
            ):
                raise ValueError(
                    "pressure values must be "
                    "between -1 and 1"
                )

    def projection(
        self,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {
            "schema": SCHEMA,
            "source_relationship_ref": (
                self.source_relationship_ref
            ),
            "target_relationship_ref": (
                self.target_relationship_ref
            ),
            "shared_dimensions": list(
                self.shared_dimensions
            ),
            "similarity": float(
                self.similarity
            ),
            "activation": float(
                self.activation
            ),
            "pressure": {
                key: float(value)
                for key, value
                in sorted(
                    self.pressure.items()
                )
            },
            "causal_refs": list(
                self.causal_refs
            ),
            "hypothesis": True,
            "derived": True,
            "authoritative": False,
            "authority_effect": "none",
        }

        body["digest"] = _digest(body)

        return body


def hypothesize_transference(
    source: RelationalPattern,
    target: RelationalPattern,
) -> TransferenceHypothesis:
    if (
        source.relationship_ref
        == target.relationship_ref
    ):
        raise ValueError(
            "source and target must differ"
        )

    shared = tuple(
        sorted(
            set(source.dimensions)
            & set(target.dimensions)
        )
    )

    if not shared:
        similarity = 0.0
        activation = 0.0
        pressure: dict[str, float] = {}
    else:
        similarity_terms = []

        for dimension in shared:
            source_value = float(
                source.dimensions[dimension]
            )

            target_value = float(
                target.dimensions[dimension]
            )

            distance = abs(
                source_value - target_value
            ) / 2.0

            similarity_terms.append(
                1.0 - distance
            )

        similarity = _unit(
            sum(similarity_terms)
            / len(similarity_terms)
        )

        activation = _unit(
            similarity
            * float(source.significance)
            * float(source.confidence)
            * (
                0.5
                + (
                    0.5
                    * float(
                        target.significance
                    )
                )
            )
        )

        pressure = {
            dimension: _signed(
                float(
                    source.dimensions[
                        dimension
                    ]
                )
                * activation
            )
            for dimension in shared
        }

    return TransferenceHypothesis(
        source_relationship_ref=(
            source.relationship_ref
        ),
        target_relationship_ref=(
            target.relationship_ref
        ),
        shared_dimensions=shared,
        similarity=similarity,
        activation=activation,
        pressure=pressure,
        causal_refs=tuple(
            dict.fromkeys(
                (
                    source.id,
                    target.id,
                    *source.causal_refs,
                    *target.causal_refs,
                )
            )
        ),
    )


def transference_field(
    target: RelationalPattern,
    history: Sequence[RelationalPattern],
) -> tuple[
    TransferenceHypothesis,
    ...
]:
    hypotheses = tuple(
        hypothesize_transference(
            source,
            target,
        )
        for source in history
        if (
            source.relationship_ref
            != target.relationship_ref
        )
    )

    return tuple(
        sorted(
            hypotheses,
            key=lambda item: (
                -item.activation,
                -item.similarity,
                item.source_relationship_ref,
            ),
        )
    )


def aggregate_pressure(
    hypotheses: Sequence[
        TransferenceHypothesis
    ],
) -> Mapping[str, float]:
    totals: dict[str, float] = {}
    weights: dict[str, float] = {}

    for hypothesis in hypotheses:
        weight = float(
            hypothesis.activation
        )

        if weight <= 0.0:
            continue

        for dimension, value in (
            hypothesis.pressure.items()
        ):
            totals[dimension] = (
                totals.get(
                    dimension,
                    0.0,
                )
                + float(value)
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


def transference_projection(
    target: RelationalPattern,
    history: Sequence[RelationalPattern],
) -> Mapping[str, Any]:
    hypotheses = transference_field(
        target,
        history,
    )

    return {
        "schema": SCHEMA,
        "target_relationship_ref": (
            target.relationship_ref
        ),
        "hypotheses": [
            item.projection()
            for item in hypotheses
        ],
        "aggregate_pressure": dict(
            aggregate_pressure(
                hypotheses
            )
        ),
        "strongest_source_ref": (
            hypotheses[0]
            .source_relationship_ref
            if hypotheses
            else None
        ),
        "transference_is_hypothesis": True,
        "transference_is_fact": False,
        "transference_is_authority": False,
        "automatic_relationship_mutation": (
            False
        ),
        "derived": True,
        "authoritative": False,
        "authority_effect": "none",
    }
