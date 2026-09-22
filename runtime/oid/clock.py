from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from statistics import median
from typing import Any, Mapping, Sequence

from runtime.oid.core import ClockObservation


SCHEMA = "savant://oid/clock/1"


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
class ClockEstimate:
    source_clock_ref: str
    offset_seconds: float
    uncertainty_seconds: float
    observation_refs: tuple[str, ...]
    outlier_refs: tuple[str, ...]
    sample_count: int

    def projection(self) -> dict[str, Any]:
        body: dict[str, Any] = {
            "schema": SCHEMA,
            "source_clock_ref": (
                self.source_clock_ref
            ),
            "offset_seconds": float(
                self.offset_seconds
            ),
            "uncertainty_seconds": float(
                self.uncertainty_seconds
            ),
            "observation_refs": list(
                self.observation_refs
            ),
            "outlier_refs": list(
                self.outlier_refs
            ),
            "sample_count": self.sample_count,
            "clock_correction_is_fact": False,
            "source_timestamp_mutated": False,
            "authority_transferred": False,
            "derived": True,
            "authoritative": False,
            "authority_effect": "none",
        }

        body["digest"] = _digest(body)
        return body


@dataclass(frozen=True, slots=True)
class ClockSkewPolicy:
    outlier_multiplier: float = 3.0
    minimum_tolerance_seconds: float = 0.001

    def __post_init__(self) -> None:
        if self.outlier_multiplier <= 0.0:
            raise ValueError(
                "outlier_multiplier must be positive"
            )

        if self.minimum_tolerance_seconds < 0.0:
            raise ValueError(
                "minimum tolerance cannot be negative"
            )


def estimate_clock(
    observations: Sequence[ClockObservation],
    *,
    policy: ClockSkewPolicy = ClockSkewPolicy(),
) -> ClockEstimate:
    if not observations:
        raise ValueError(
            "clock estimate requires observations"
        )

    clocks = {
        item.source_clock_ref
        for item in observations
    }

    if len(clocks) != 1:
        raise ValueError(
            "clock estimate cannot combine clocks"
        )

    offsets = [
        float(item.observed_offset_seconds)
        for item in observations
    ]

    center = float(median(offsets))

    deviations = [
        abs(value - center)
        for value in offsets
    ]

    mad = float(median(deviations))

    tolerance = max(
        policy.minimum_tolerance_seconds,
        mad * policy.outlier_multiplier,
        max(
            float(item.uncertainty_seconds)
            for item in observations
        ),
    )

    retained: list[ClockObservation] = []
    outliers: list[ClockObservation] = []

    for observation in observations:
        if (
            abs(
                float(
                    observation
                    .observed_offset_seconds
                )
                - center
            )
            <= (
                tolerance
                + float(
                    observation
                    .uncertainty_seconds
                )
            )
        ):
            retained.append(observation)
        else:
            outliers.append(observation)

    if not retained:
        retained = list(observations)
        outliers = []

    retained_offsets = [
        float(item.observed_offset_seconds)
        for item in retained
    ]

    estimate = float(
        median(retained_offsets)
    )

    uncertainty = max(
        (
            abs(
                float(
                    item.observed_offset_seconds
                )
                - estimate
            )
            + float(
                item.uncertainty_seconds
            )
        )
        for item in retained
    )

    return ClockEstimate(
        source_clock_ref=(
            observations[0].source_clock_ref
        ),
        offset_seconds=estimate,
        uncertainty_seconds=uncertainty,
        observation_refs=tuple(
            sorted(
                item.observation_ref
                for item in retained
            )
        ),
        outlier_refs=tuple(
            sorted(
                item.observation_ref
                for item in outliers
            )
        ),
        sample_count=len(observations),
    )


def clock_field(
    observations: Sequence[ClockObservation],
    *,
    policy: ClockSkewPolicy = ClockSkewPolicy(),
) -> Mapping[str, ClockEstimate]:
    grouped: dict[
        str,
        list[ClockObservation],
    ] = {}

    for observation in observations:
        grouped.setdefault(
            observation.source_clock_ref,
            [],
        ).append(observation)

    return {
        clock_ref: estimate_clock(
            grouped[clock_ref],
            policy=policy,
        )
        for clock_ref in sorted(grouped)
    }


def clock_projection(
    observations: Sequence[ClockObservation],
    *,
    policy: ClockSkewPolicy = ClockSkewPolicy(),
) -> Mapping[str, Any]:
    field = clock_field(
        observations,
        policy=policy,
    )

    body: dict[str, Any] = {
        "schema": SCHEMA,
        "clocks": {
            clock_ref: estimate.projection()
            for clock_ref, estimate
            in sorted(field.items())
        },
        "clock_count": len(field),
        "observations_are_immutable": True,
        "outliers_are_preserved": True,
        "correction_is_projection_only": True,
        "clock_estimate_is_authority": False,
        "authority_transferred": False,
        "derived": True,
        "authoritative": False,
        "authority_effect": "none",
    }

    body["digest"] = _digest(body)
    return body
