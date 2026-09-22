from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
import math
from typing import Any, Mapping, Sequence


SCHEMA = "savant://noumenon/salience/1"


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
class SalienceSignal:
    subject_ref: str
    significance: float
    surprise: float = 0.0
    curiosity: float = 0.0
    commitment: float = 0.0
    residue: float = 0.0
    relational: float = 0.0
    unresolved: float = 0.0
    causal_refs: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.subject_ref:
            raise ValueError(
                "subject_ref is required"
            )

        values = (
            self.significance,
            self.surprise,
            self.curiosity,
            self.commitment,
            self.residue,
            self.relational,
            self.unresolved,
        )

        if any(
            not (
                0.0
                <= float(value)
                <= 1.0
            )
            for value in values
        ):
            raise ValueError(
                "salience signals must be "
                "between 0 and 1"
            )

    def projection(
        self,
    ) -> dict[str, Any]:
        return {
            "schema": SCHEMA,
            "subject_ref": (
                self.subject_ref
            ),
            "significance": float(
                self.significance
            ),
            "surprise": float(
                self.surprise
            ),
            "curiosity": float(
                self.curiosity
            ),
            "commitment": float(
                self.commitment
            ),
            "residue": float(
                self.residue
            ),
            "relational": float(
                self.relational
            ),
            "unresolved": float(
                self.unresolved
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
            "noumenon-salience:"
            + self.digest
        )


@dataclass(frozen=True, slots=True)
class SalienceWeights:
    significance: float = 1.0
    surprise: float = 1.0
    curiosity: float = 1.0
    commitment: float = 1.0
    residue: float = 1.0
    relational: float = 1.0
    unresolved: float = 1.0

    def __post_init__(self) -> None:
        values = (
            self.significance,
            self.surprise,
            self.curiosity,
            self.commitment,
            self.residue,
            self.relational,
            self.unresolved,
        )

        if any(
            float(value) < 0.0
            for value in values
        ):
            raise ValueError(
                "salience weights cannot "
                "be negative"
            )

        if math.isclose(
            sum(
                float(value)
                for value in values
            ),
            0.0,
            rel_tol=0.0,
            abs_tol=0.0,
        ):
            raise ValueError(
                "at least one salience weight "
                "must be positive"
            )

    def projection(
        self,
    ) -> dict[str, float]:
        return {
            "significance": float(
                self.significance
            ),
            "surprise": float(
                self.surprise
            ),
            "curiosity": float(
                self.curiosity
            ),
            "commitment": float(
                self.commitment
            ),
            "residue": float(
                self.residue
            ),
            "relational": float(
                self.relational
            ),
            "unresolved": float(
                self.unresolved
            ),
        }


@dataclass(frozen=True, slots=True)
class SalienceScore:
    signal_ref: str
    score: float
    contributions: Mapping[
        str,
        float,
    ]

    def __post_init__(self) -> None:
        if not self.signal_ref:
            raise ValueError(
                "signal_ref is required"
            )

        if not (
            0.0
            <= float(self.score)
            <= 1.0
        ):
            raise ValueError(
                "score must be between "
                "0 and 1"
            )

    def projection(
        self,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {
            "schema": SCHEMA,
            "signal_ref": (
                self.signal_ref
            ),
            "score": float(
                self.score
            ),
            "contributions": {
                key: float(value)
                for key, value
                in sorted(
                    self.contributions.items()
                )
            },
            "derived": True,
            "authoritative": False,
        }

        body["digest"] = _digest(
            body
        )

        return body


def score_salience(
    signal: SalienceSignal,
    weights: SalienceWeights,
) -> SalienceScore:
    signal_values = {
        "significance": (
            signal.significance
        ),
        "surprise": signal.surprise,
        "curiosity": signal.curiosity,
        "commitment": signal.commitment,
        "residue": signal.residue,
        "relational": signal.relational,
        "unresolved": signal.unresolved,
    }

    weight_values = (
        weights.projection()
    )

    denominator = sum(
        weight_values.values()
    )

    contributions = {
        key: (
            float(signal_values[key])
            * float(weight_values[key])
        )
        for key in signal_values
    }

    score = _unit(
        sum(
            contributions.values()
        )
        / denominator
    )

    return SalienceScore(
        signal_ref=signal.id,
        score=score,
        contributions=contributions,
    )


def compete(
    signals: Sequence[
        SalienceSignal
    ],
    *,
    weights: SalienceWeights,
    capacity: int,
) -> tuple[
    SalienceSignal,
    ...,
]:
    if capacity < 0:
        raise ValueError(
            "capacity cannot be negative"
        )

    ranked = sorted(
        signals,
        key=lambda signal: (
            -score_salience(
                signal,
                weights,
            ).score,
            signal.subject_ref,
            signal.id,
        ),
    )

    return tuple(
        ranked[:capacity]
    )


def salience_projection(
    signals: Sequence[
        SalienceSignal
    ],
    *,
    weights: SalienceWeights,
    capacity: int,
) -> Mapping[str, Any]:
    selected = compete(
        signals,
        weights=weights,
        capacity=capacity,
    )

    scores = {
        signal.id: score_salience(
            signal,
            weights,
        ).projection()
        for signal in signals
    }

    return {
        "schema": SCHEMA,
        "capacity": capacity,
        "weights": (
            weights.projection()
        ),
        "selected_refs": [
            signal.id
            for signal in selected
        ],
        "scores": scores,
        "derived": True,
        "authoritative": False,
    }
