from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from typing import Any, Mapping, Sequence


SCHEMA = "savant://noumenon/taste-emergence/1"


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
class TasteEvidence:
    subject_ref: str
    dimension: str
    response: float
    confidence: float
    significance: float
    causal_refs: tuple[str, ...]
    evidence_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.subject_ref:
            raise ValueError(
                "subject_ref is required"
            )

        if not self.dimension:
            raise ValueError(
                "dimension is required"
            )

        if not (
            -1.0
            <= float(self.response)
            <= 1.0
        ):
            raise ValueError(
                "response must be between "
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
                "taste evidence requires "
                "causal refs"
            )

    def projection(
        self,
    ) -> dict[str, Any]:
        return {
            "schema": SCHEMA,
            "subject_ref": self.subject_ref,
            "dimension": self.dimension,
            "response": float(
                self.response
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
            "noumenon-taste-evidence:"
            + self.digest
        )


@dataclass(frozen=True, slots=True)
class TasteDisposition:
    dimension: str
    preference: float
    confidence: float
    evidence_count: int
    evidence_refs: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.dimension:
            raise ValueError(
                "dimension is required"
            )

        if not (
            -1.0
            <= float(self.preference)
            <= 1.0
        ):
            raise ValueError(
                "preference must be between "
                "-1 and 1"
            )

        if not (
            0.0
            <= float(self.confidence)
            <= 1.0
        ):
            raise ValueError(
                "confidence must be between "
                "0 and 1"
            )

        if self.evidence_count < 1:
            raise ValueError(
                "evidence_count must be "
                "positive"
            )

    def projection(
        self,
    ) -> dict[str, Any]:
        return {
            "schema": SCHEMA,
            "dimension": self.dimension,
            "preference": float(
                self.preference
            ),
            "confidence": float(
                self.confidence
            ),
            "evidence_count": (
                self.evidence_count
            ),
            "evidence_refs": list(
                self.evidence_refs
            ),
            "derived": True,
            "authoritative": False,
        }


def derive_disposition(
    dimension: str,
    evidence: Sequence[TasteEvidence],
) -> TasteDisposition:
    relevant = tuple(
        item
        for item in evidence
        if item.dimension == dimension
    )

    if not relevant:
        raise ValueError(
            "taste disposition requires "
            "evidence"
        )

    weighted_sum = 0.0
    total_weight = 0.0

    for item in relevant:
        weight = (
            float(item.confidence)
            * (
                0.5
                + (
                    0.5
                    * float(
                        item.significance
                    )
                )
            )
        )

        weighted_sum += (
            float(item.response)
            * weight
        )

        total_weight += weight

    preference = (
        weighted_sum / total_weight
        if total_weight > 0.0
        else 0.0
    )

    evidence_support = _unit(
        total_weight
        / max(
            1.0,
            float(len(relevant)),
        )
    )

    diversity_support = _unit(
        len(
            {
                item.subject_ref
                for item in relevant
            }
        )
        / max(
            1.0,
            float(len(relevant)),
        )
    )

    confidence = _unit(
        (
            evidence_support
            + diversity_support
        )
        / 2.0
    )

    return TasteDisposition(
        dimension=dimension,
        preference=_signed(
            preference
        ),
        confidence=confidence,
        evidence_count=len(
            relevant
        ),
        evidence_refs=tuple(
            sorted(
                item.id
                for item in relevant
            )
        ),
    )


def taste_profile(
    evidence: Sequence[TasteEvidence],
) -> Mapping[
    str,
    TasteDisposition,
]:
    dimensions = sorted(
        {
            item.dimension
            for item in evidence
        }
    )

    return {
        dimension: derive_disposition(
            dimension,
            evidence,
        )
        for dimension in dimensions
    }


def taste_drift(
    predecessor: Mapping[
        str,
        TasteDisposition,
    ],
    successor: Mapping[
        str,
        TasteDisposition,
    ],
) -> Mapping[str, float]:
    dimensions = (
        set(predecessor)
        | set(successor)
    )

    return {
        dimension: _signed(
            (
                successor[
                    dimension
                ].preference
                if dimension
                in successor
                else 0.0
            )
            - (
                predecessor[
                    dimension
                ].preference
                if dimension
                in predecessor
                else 0.0
            )
        )
        for dimension
        in sorted(dimensions)
    }


def taste_projection(
    evidence: Sequence[TasteEvidence],
) -> Mapping[str, Any]:
    profile = taste_profile(
        evidence
    )

    return {
        "schema": SCHEMA,
        "profile": {
            dimension: (
                disposition.projection()
            )
            for dimension, disposition
            in sorted(
                profile.items()
            )
        },
        "evidence_refs": sorted(
            item.id
            for item in evidence
        ),
        "taste_is_inferred": True,
        "taste_is_authority": False,
        "single_response_defines_taste": (
            False
        ),
        "automatic_identity_mutation": False,
        "derived": True,
        "authoritative": False,
        "authority_effect": "none",
    }
