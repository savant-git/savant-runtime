from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from typing import Any, Mapping, Sequence


SCHEMA = "savant://noumenon/coherence/1"


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
class CoherenceClaim:
    claim_ref: str
    dimension: str
    position: float
    confidence: float
    significance: float
    causal_refs: tuple[str, ...]
    evidence_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.claim_ref:
            raise ValueError(
                "claim_ref is required"
            )

        if not self.dimension:
            raise ValueError(
                "dimension is required"
            )

        if not (
            -1.0
            <= float(self.position)
            <= 1.0
        ):
            raise ValueError(
                "position must be between "
                "-1 and 1"
            )

        for value in (
            self.confidence,
            self.significance,
        ):
            if not (
                0.0
                <= float(value)
                <= 1.0
            ):
                raise ValueError(
                    "confidence and significance "
                    "must be between 0 and 1"
                )

        if not self.causal_refs:
            raise ValueError(
                "coherence claim requires "
                "causal refs"
            )

    def projection(
        self,
    ) -> dict[str, Any]:
        return {
            "schema": SCHEMA,
            "claim_ref": self.claim_ref,
            "dimension": self.dimension,
            "position": float(
                self.position
            ),
            "confidence": float(
                self.confidence
            ),
            "significance": float(
                self.significance
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
            "noumenon-coherence-claim:"
            + self.digest
        )


@dataclass(frozen=True, slots=True)
class DimensionCoherence:
    dimension: str
    center: float
    coherence: float
    contradiction: float
    diversity: float
    claim_refs: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.dimension:
            raise ValueError(
                "dimension is required"
            )

        if not (
            -1.0
            <= float(self.center)
            <= 1.0
        ):
            raise ValueError(
                "center must be between "
                "-1 and 1"
            )

        for value in (
            self.coherence,
            self.contradiction,
            self.diversity,
        ):
            if not (
                0.0
                <= float(value)
                <= 1.0
            ):
                raise ValueError(
                    "coherence values must be "
                    "between 0 and 1"
                )

    def projection(
        self,
    ) -> dict[str, Any]:
        return {
            "schema": SCHEMA,
            "dimension": self.dimension,
            "center": float(
                self.center
            ),
            "coherence": float(
                self.coherence
            ),
            "contradiction": float(
                self.contradiction
            ),
            "diversity": float(
                self.diversity
            ),
            "claim_refs": list(
                self.claim_refs
            ),
            "derived": True,
            "authoritative": False,
        }


def dimension_coherence(
    dimension: str,
    claims: Sequence[CoherenceClaim],
) -> DimensionCoherence:
    relevant = tuple(
        claim
        for claim in claims
        if claim.dimension == dimension
    )

    if not relevant:
        raise ValueError(
            "dimension requires claims"
        )

    weighted_sum = 0.0
    total_weight = 0.0

    for claim in relevant:
        weight = (
            float(claim.confidence)
            * (
                0.5
                + (
                    0.5
                    * float(
                        claim.significance
                    )
                )
            )
        )

        weighted_sum += (
            float(claim.position)
            * weight
        )

        total_weight += weight

    center = (
        weighted_sum / total_weight
        if total_weight > 0.0
        else 0.0
    )

    dispersion = (
        sum(
            abs(
                float(claim.position)
                - center
            )
            for claim in relevant
        )
        / (
            2.0
            * len(relevant)
        )
    )

    positive = any(
        float(claim.position) > 0.0
        for claim in relevant
    )

    negative = any(
        float(claim.position) < 0.0
        for claim in relevant
    )

    contradiction = _unit(
        dispersion
        * (
            1.0
            if positive and negative
            else 0.5
        )
    )

    diversity = _unit(
        len(
            {
                round(
                    float(claim.position),
                    6,
                )
                for claim in relevant
            }
        )
        / float(len(relevant))
    )

    coherence = _unit(
        1.0 - dispersion
    )

    return DimensionCoherence(
        dimension=dimension,
        center=_signed(center),
        coherence=coherence,
        contradiction=contradiction,
        diversity=diversity,
        claim_refs=tuple(
            sorted(
                claim.id
                for claim in relevant
            )
        ),
    )


def coherence_field(
    claims: Sequence[CoherenceClaim],
) -> Mapping[
    str,
    DimensionCoherence,
]:
    dimensions = sorted(
        {
            claim.dimension
            for claim in claims
        }
    )

    return {
        dimension: dimension_coherence(
            dimension,
            claims,
        )
        for dimension in dimensions
    }


def global_coherence(
    claims: Sequence[CoherenceClaim],
) -> float:
    field = coherence_field(
        claims
    )

    if not field:
        return 1.0

    return _unit(
        sum(
            value.coherence
            for value in field.values()
        )
        / len(field)
    )


def coherence_projection(
    claims: Sequence[CoherenceClaim],
) -> Mapping[str, Any]:
    field = coherence_field(
        claims
    )

    return {
        "schema": SCHEMA,
        "dimensions": {
            dimension: value.projection()
            for dimension, value
            in sorted(field.items())
        },
        "global_coherence": (
            global_coherence(claims)
        ),
        "contradictions_preserved": True,
        "diversity_preserved": True,
        "homogenization_required": False,
        "coherence_is_authority": False,
        "automatic_identity_mutation": False,
        "derived": True,
        "authoritative": False,
        "authority_effect": "none",
    }
