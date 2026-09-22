from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from typing import Any, Mapping, Sequence

from runtime.noumenon.state import NoumenonState


SCHEMA = "savant://noumenon/development/1"


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


def _bounded(
    value: float,
    minimum: float = -1.0,
    maximum: float = 1.0,
) -> float:
    return max(
        minimum,
        min(maximum, float(value)),
    )


@dataclass(frozen=True, slots=True)
class MeaningLayer:
    event_ref: str
    interpretation_ref: str
    significance: Mapping[str, float]
    predecessor_ref: str | None = None
    uncertainty: Mapping[str, float] | None = None
    dormant: bool = False

    def __post_init__(self) -> None:
        if not self.event_ref:
            raise ValueError("event_ref is required")

        if not self.interpretation_ref:
            raise ValueError(
                "interpretation_ref is required"
            )

    def projection(self) -> dict[str, Any]:
        return {
            "event_ref": self.event_ref,
            "interpretation_ref": (
                self.interpretation_ref
            ),
            "significance": {
                key: _bounded(value)
                for key, value
                in sorted(
                    self.significance.items()
                )
            },
            "predecessor_ref": (
                self.predecessor_ref
            ),
            "uncertainty": {
                key: max(
                    0.0,
                    min(1.0, float(value)),
                )
                for key, value
                in sorted(
                    (
                        self.uncertainty
                        or {}
                    ).items()
                )
            },
            "dormant": self.dormant,
        }

    @property
    def id(self) -> str:
        return (
            "meaning-layer:"
            + _digest(self.projection())
        )


@dataclass(frozen=True, slots=True)
class SelfExplanation:
    state_digest: str
    claim: str
    confidence: float
    evidence_refs: tuple[str, ...] = ()
    alternatives: tuple[str, ...] = ()
    counterevidence_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.state_digest:
            raise ValueError(
                "state_digest is required"
            )

        if not self.claim:
            raise ValueError("claim is required")

        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(
                "confidence must be between 0 and 1"
            )

    def projection(self) -> dict[str, Any]:
        return {
            "schema": (
                "savant://noumenon/"
                "self-explanation/1"
            ),
            "state_digest": self.state_digest,
            "claim": self.claim,
            "confidence": self.confidence,
            "evidence_refs": list(
                self.evidence_refs
            ),
            "alternatives": list(
                self.alternatives
            ),
            "counterevidence_refs": list(
                self.counterevidence_refs
            ),
            "authoritative_causal_access": False,
        }

    @property
    def id(self) -> str:
        return (
            "self-explanation:"
            + _digest(self.projection())
        )


@dataclass(frozen=True, slots=True)
class PossibleSelf:
    kind: str
    dimensions: Mapping[str, float]
    evidence_refs: tuple[str, ...] = ()
    confidence: float = 0.0

    def __post_init__(self) -> None:
        if self.kind not in {
            "ideal",
            "feared",
            "expected",
            "rejected",
            "projected",
        }:
            raise ValueError(
                "unsupported possible-self kind"
            )

        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(
                "confidence must be between 0 and 1"
            )

    def projection(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "dimensions": {
                key: _bounded(value)
                for key, value
                in sorted(
                    self.dimensions.items()
                )
            },
            "evidence_refs": list(
                self.evidence_refs
            ),
            "confidence": self.confidence,
        }


@dataclass(frozen=True, slots=True)
class DevelopmentMetrics:
    velocity: Mapping[str, float]
    acceleration: Mapping[str, float]
    entropy: float

    def projection(self) -> dict[str, Any]:
        return {
            "schema": SCHEMA,
            "velocity": dict(
                sorted(self.velocity.items())
            ),
            "acceleration": dict(
                sorted(self.acceleration.items())
            ),
            "entropy": float(self.entropy),
        }


def reinterpret(
    prior: MeaningLayer,
    *,
    interpretation_ref: str,
    significance: Mapping[str, float],
    uncertainty: Mapping[str, float] | None = None,
    dormant: bool = False,
) -> MeaningLayer:
    return MeaningLayer(
        event_ref=prior.event_ref,
        interpretation_ref=interpretation_ref,
        significance=dict(significance),
        predecessor_ref=prior.id,
        uncertainty=dict(
            uncertainty or {}
        ),
        dormant=dormant,
    )


def developmental_velocity(
    predecessor: NoumenonState,
    successor: NoumenonState,
) -> dict[str, float]:
    keys = set(predecessor.dimensions)
    keys.update(successor.dimensions)

    return {
        key: (
            float(
                successor.dimensions.get(
                    key,
                    0.0,
                )
            )
            - float(
                predecessor.dimensions.get(
                    key,
                    0.0,
                )
            )
        )
        for key in sorted(keys)
    }


def developmental_acceleration(
    previous_velocity: Mapping[str, float],
    current_velocity: Mapping[str, float],
) -> dict[str, float]:
    keys = set(previous_velocity)
    keys.update(current_velocity)

    return {
        key: (
            float(
                current_velocity.get(
                    key,
                    0.0,
                )
            )
            - float(
                previous_velocity.get(
                    key,
                    0.0,
                )
            )
        )
        for key in sorted(keys)
    }


def identity_entropy(
    state: NoumenonState,
) -> float:
    if not state.dimensions:
        return 0.0

    magnitudes = [
        abs(float(value))
        for value
        in state.dimensions.values()
        if float(value) != 0.0
    ]

    if not magnitudes:
        return 0.0

    total = sum(magnitudes)

    probabilities = [
        value / total
        for value in magnitudes
    ]

    import math

    raw = -sum(
        probability
        * math.log(probability)
        for probability in probabilities
    )

    maximum = math.log(
        len(probabilities)
    )

    if maximum == 0.0:
        return 0.0

    return raw / maximum


def metrics(
    predecessor: NoumenonState,
    successor: NoumenonState,
    *,
    previous_velocity: Mapping[str, float] | None = None,
) -> DevelopmentMetrics:
    velocity = developmental_velocity(
        predecessor,
        successor,
    )

    acceleration = (
        developmental_acceleration(
            previous_velocity or {},
            velocity,
        )
    )

    return DevelopmentMetrics(
        velocity=velocity,
        acceleration=acceleration,
        entropy=identity_entropy(successor),
    )


def continuity_challenge(
    predecessor: NoumenonState,
    successor: NoumenonState,
) -> dict[str, Any]:
    failures: list[str] = []

    if (
        successor.predecessor_id
        != predecessor.noumenon_id
    ):
        failures.append(
            "predecessor_identity_mismatch"
        )

    if (
        successor.generation
        != predecessor.generation + 1
    ):
        failures.append(
            "generation_discontinuity"
        )

    if (
        len(successor.lineage_refs)
        < len(predecessor.lineage_refs)
    ):
        failures.append(
            "lineage_truncation"
        )

    if (
        successor.lineage_refs[
            : len(predecessor.lineage_refs)
        ]
        != predecessor.lineage_refs
    ):
        failures.append(
            "lineage_ancestry_mismatch"
        )

    return {
        "schema": (
            "savant://noumenon/"
            "continuity-challenge/1"
        ),
        "continuous": not failures,
        "predecessor_id": (
            predecessor.noumenon_id
        ),
        "successor_id": successor.noumenon_id,
        "failures": failures,
    }


def counterlife_comparison(
    actual: NoumenonState,
    counterlife_dimensions: Mapping[str, float],
    *,
    fork_ref: str,
    simulation_ref: str,
) -> dict[str, Any]:
    if not fork_ref:
        raise ValueError("fork_ref is required")

    if not simulation_ref:
        raise ValueError(
            "simulation_ref is required"
        )

    keys = set(actual.dimensions)
    keys.update(counterlife_dimensions)

    deltas = {
        key: (
            float(
                actual.dimensions.get(
                    key,
                    0.0,
                )
            )
            - float(
                counterlife_dimensions.get(
                    key,
                    0.0,
                )
            )
        )
        for key in sorted(keys)
    }

    body = {
        "schema": (
            "savant://noumenon/"
            "counterlife-comparison/1"
        ),
        "actual_state_digest": (
            actual.state_digest
        ),
        "fork_ref": fork_ref,
        "simulation_ref": simulation_ref,
        "authoritative": False,
        "dimension_deltas": deltas,
    }

    body["digest"] = _digest(body)
    return body
