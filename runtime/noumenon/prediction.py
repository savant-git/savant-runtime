from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
import math
from typing import Any, Mapping, Sequence


SCHEMA = "savant://noumenon/prediction/1"


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


def _bounded(
    value: float,
) -> float:
    return max(
        -1.0,
        min(
            1.0,
            float(value),
        ),
    )


@dataclass(frozen=True, slots=True)
class Expectation:
    subject_ref: str
    dimensions: Mapping[str, float]
    confidence: float
    causal_refs: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.subject_ref:
            raise ValueError(
                "subject_ref is required"
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

        if not self.dimensions:
            raise ValueError(
                "dimensions are required"
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
                    "expectation values must "
                    "be between -1 and 1"
                )

    def projection(
        self,
    ) -> dict[str, Any]:
        return {
            "schema": SCHEMA,
            "subject_ref": (
                self.subject_ref
            ),
            "dimensions": {
                key: float(value)
                for key, value
                in sorted(
                    self.dimensions.items()
                )
            },
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
            "noumenon-expectation:"
            + self.digest
        )


@dataclass(frozen=True, slots=True)
class PredictionError:
    expectation_ref: str
    observed_ref: str
    errors: Mapping[str, float]
    weighted_error: float
    surprise: float
    curiosity_pressure: float

    def __post_init__(self) -> None:
        if not self.expectation_ref:
            raise ValueError(
                "expectation_ref is required"
            )

        if not self.observed_ref:
            raise ValueError(
                "observed_ref is required"
            )

        if not (
            0.0
            <= float(self.weighted_error)
            <= 2.0
        ):
            raise ValueError(
                "weighted_error must be "
                "between 0 and 2"
            )

        if not (
            0.0
            <= float(self.surprise)
            <= 1.0
        ):
            raise ValueError(
                "surprise must be between "
                "0 and 1"
            )

        if not (
            0.0
            <= float(
                self.curiosity_pressure
            )
            <= 1.0
        ):
            raise ValueError(
                "curiosity_pressure must be "
                "between 0 and 1"
            )

    def projection(
        self,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {
            "schema": SCHEMA,
            "expectation_ref": (
                self.expectation_ref
            ),
            "observed_ref": (
                self.observed_ref
            ),
            "errors": {
                key: float(value)
                for key, value
                in sorted(
                    self.errors.items()
                )
            },
            "weighted_error": float(
                self.weighted_error
            ),
            "surprise": float(
                self.surprise
            ),
            "curiosity_pressure": float(
                self.curiosity_pressure
            ),
            "derived": True,
            "authoritative": False,
        }

        body["digest"] = _digest(
            body
        )

        return body


def prediction_error(
    expectation: Expectation,
    *,
    observed_ref: str,
    observed_dimensions: Mapping[
        str,
        float,
    ],
) -> PredictionError:
    if not observed_ref:
        raise ValueError(
            "observed_ref is required"
        )

    dimensions = (
        set(expectation.dimensions)
        | set(observed_dimensions)
    )

    if not dimensions:
        raise ValueError(
            "prediction comparison requires "
            "dimensions"
        )

    errors: dict[str, float] = {}

    for dimension in sorted(
        dimensions
    ):
        expected = float(
            expectation.dimensions.get(
                dimension,
                0.0,
            )
        )

        observed = _bounded(
            float(
                observed_dimensions.get(
                    dimension,
                    0.0,
                )
            )
        )

        errors[dimension] = (
            observed - expected
        )

    mean_absolute_error = (
        sum(
            abs(value)
            for value in errors.values()
        )
        / len(errors)
    )

    weighted_error = (
        mean_absolute_error
        * float(expectation.confidence)
    )

    surprise = min(
        1.0,
        weighted_error / 2.0,
    )

    unresolved_fraction = (
        sum(
            1
            for value in errors.values()
            if not math.isclose(
                value,
                0.0,
                rel_tol=1e-12,
                abs_tol=1e-12,
            )
        )
        / len(errors)
    )

    curiosity_pressure = min(
        1.0,
        surprise
        * (
            0.5
            + (
                0.5
                * unresolved_fraction
            )
        ),
    )

    return PredictionError(
        expectation_ref=expectation.id,
        observed_ref=observed_ref,
        errors=errors,
        weighted_error=(
            weighted_error
        ),
        surprise=surprise,
        curiosity_pressure=(
            curiosity_pressure
        ),
    )


def update_expectation(
    expectation: Expectation,
    *,
    observed_dimensions: Mapping[
        str,
        float,
    ],
    learning_rate: float,
    causal_refs: Sequence[str] = (),
    evidence_refs: Sequence[str] = (),
) -> Expectation:
    rate = float(
        learning_rate
    )

    if not (
        0.0 <= rate <= 1.0
    ):
        raise ValueError(
            "learning_rate must be between "
            "0 and 1"
        )

    dimensions = (
        set(expectation.dimensions)
        | set(observed_dimensions)
    )

    updated: dict[str, float] = {}

    for dimension in sorted(
        dimensions
    ):
        before = float(
            expectation.dimensions.get(
                dimension,
                0.0,
            )
        )

        observed = _bounded(
            float(
                observed_dimensions.get(
                    dimension,
                    before,
                )
            )
        )

        updated[dimension] = _bounded(
            before
            + (
                observed - before
            )
            * rate
        )

    return Expectation(
        subject_ref=(
            expectation.subject_ref
        ),
        dimensions=updated,
        confidence=(
            expectation.confidence
        ),
        causal_refs=tuple(
            dict.fromkeys(
                (
                    *expectation.causal_refs,
                    expectation.id,
                    *causal_refs,
                )
            )
        ),
        evidence_refs=tuple(
            dict.fromkeys(
                (
                    *expectation.evidence_refs,
                    *evidence_refs,
                )
            )
        ),
    )
