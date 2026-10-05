from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from typing import Any, Mapping, Sequence

from runtime.noumenon.state import (
    DevelopmentalConsequence,
    TransitionCandidate,
)


SCHEMA = "savant://noumenon/bandwidth/1"


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


@dataclass(frozen=True, slots=True)
class BandwidthPolicy:
    maximum_consequences: int = 8
    maximum_absolute_delta: float = 1.0
    maximum_total_pressure: float = 2.0

    def __post_init__(self) -> None:
        if self.maximum_consequences < 1:
            raise ValueError(
                "maximum_consequences must "
                "be positive"
            )

        if (
            self.maximum_absolute_delta
            <= 0.0
        ):
            raise ValueError(
                "maximum_absolute_delta must "
                "be positive"
            )

        if (
            self.maximum_total_pressure
            <= 0.0
        ):
            raise ValueError(
                "maximum_total_pressure must "
                "be positive"
            )

    def projection(
        self,
    ) -> dict[str, Any]:
        return {
            "maximum_consequences": (
                self.maximum_consequences
            ),
            "maximum_absolute_delta": (
                self.maximum_absolute_delta
            ),
            "maximum_total_pressure": (
                self.maximum_total_pressure
            ),
        }


@dataclass(frozen=True, slots=True)
class BandwidthDecision:
    admitted: bool
    reason: str
    original_count: int
    retained_count: int
    original_pressure: float
    retained_pressure: float
    retained_dimensions: tuple[
        str,
        ...,
    ]

    def projection(
        self,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {
            "schema": SCHEMA,
            "admitted": self.admitted,
            "reason": self.reason,
            "original_count": (
                self.original_count
            ),
            "retained_count": (
                self.retained_count
            ),
            "original_pressure": (
                self.original_pressure
            ),
            "retained_pressure": (
                self.retained_pressure
            ),
            "retained_dimensions": list(
                self.retained_dimensions
            ),
            "authority_effect": "none",
        }

        body["digest"] = _digest(
            body
        )

        return body


def consequence_pressure(
    consequence: DevelopmentalConsequence,
) -> float:
    return abs(
        float(consequence.delta)
    )


def candidate_pressure(
    candidate: TransitionCandidate,
) -> float:
    return sum(
        consequence_pressure(
            consequence
        )
        for consequence
        in candidate.consequences
    )


def _ranked_consequences(
    consequences: Sequence[
        DevelopmentalConsequence
    ],
) -> tuple[
    DevelopmentalConsequence,
    ...,
]:
    return tuple(
        sorted(
            consequences,
            key=lambda consequence: (
                -consequence_pressure(
                    consequence
                ),
                consequence.dimension,
                consequence.projection().__repr__(),
            ),
        )
    )


def apply_bandwidth(
    candidate: TransitionCandidate,
    policy: BandwidthPolicy,
) -> tuple[
    TransitionCandidate,
    BandwidthDecision,
]:
    original = tuple(
        candidate.consequences
    )

    original_pressure = sum(
        consequence_pressure(
            consequence
        )
        for consequence in original
    )

    bounded: list[
        DevelopmentalConsequence
    ] = []

    pressure = 0.0

    for consequence in (
        _ranked_consequences(original)
    ):
        if (
            len(bounded)
            >= policy.maximum_consequences
        ):
            break

        delta = float(
            consequence.delta
        )

        if (
            abs(delta)
            > policy.maximum_absolute_delta
        ):
            continue

        next_pressure = (
            pressure
            + abs(delta)
        )

        if (
            next_pressure
            > policy.maximum_total_pressure
        ):
            continue

        bounded.append(
            consequence
        )

        pressure = next_pressure

    retained = tuple(
        sorted(
            bounded,
            key=lambda consequence: (
                consequence.dimension,
                consequence.projection().__repr__(),
            ),
        )
    )

    admitted = bool(
        retained
    ) or not original

    if not original:
        reason = "no_consequences"
    elif len(retained) == len(original):
        reason = "within_bandwidth"
    elif retained:
        reason = "bounded"
    else:
        reason = "bandwidth_exhausted"

    bounded_candidate = (
        TransitionCandidate(
            predecessor=(
                candidate.predecessor
            ),
            experience=(
                candidate.experience
            ),
            significance=(
                candidate.significance
            ),
            consequences=retained,
        )
    )

    decision = BandwidthDecision(
        admitted=admitted,
        reason=reason,
        original_count=len(original),
        retained_count=len(retained),
        original_pressure=(
            original_pressure
        ),
        retained_pressure=pressure,
        retained_dimensions=tuple(
            consequence.dimension
            for consequence in retained
        ),
    )

    return (
        bounded_candidate,
        decision,
    )


def bandwidth_projection(
    candidate: TransitionCandidate,
    policy: BandwidthPolicy,
) -> Mapping[str, Any]:
    bounded, decision = apply_bandwidth(
        candidate,
        policy,
    )

    return {
        "schema": SCHEMA,
        "policy": policy.projection(),
        "decision": (
            decision.projection()
        ),
        "retained_consequences": [
            consequence.projection()
            for consequence
            in bounded.consequences
        ],
        "derived": True,
        "authoritative": False,
    }
