from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from typing import Any, Mapping, Sequence


SCHEMA = "savant://noumenon/affect/1"


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
class AffectState:
    valence: float = 0.0
    arousal: float = 0.0
    threat: float = 0.0
    safety: float = 0.0
    attachment: float = 0.0
    curiosity: float = 0.0
    unresolved: float = 0.0
    causal_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        signed_values = (
            self.valence,
            self.attachment,
        )

        unit_values = (
            self.arousal,
            self.threat,
            self.safety,
            self.curiosity,
            self.unresolved,
        )

        if any(
            not (
                -1.0
                <= float(value)
                <= 1.0
            )
            for value in signed_values
        ):
            raise ValueError(
                "signed affect dimensions "
                "must be between -1 and 1"
            )

        if any(
            not (
                0.0
                <= float(value)
                <= 1.0
            )
            for value in unit_values
        ):
            raise ValueError(
                "unit affect dimensions "
                "must be between 0 and 1"
            )

    def projection(
        self,
    ) -> dict[str, Any]:
        return {
            "schema": SCHEMA,
            "valence": float(
                self.valence
            ),
            "arousal": float(
                self.arousal
            ),
            "threat": float(
                self.threat
            ),
            "safety": float(
                self.safety
            ),
            "attachment": float(
                self.attachment
            ),
            "curiosity": float(
                self.curiosity
            ),
            "unresolved": float(
                self.unresolved
            ),
            "causal_refs": list(
                self.causal_refs
            ),
            "derived": True,
            "authoritative": False,
        }

    @property
    def digest(self) -> str:
        return _digest(
            self.projection()
        )

    @property
    def id(self) -> str:
        return (
            "noumenon-affect:"
            + self.digest
        )


@dataclass(frozen=True, slots=True)
class AffectInfluence:
    source_ref: str
    valence: float = 0.0
    arousal: float = 0.0
    threat: float = 0.0
    safety: float = 0.0
    attachment: float = 0.0
    curiosity: float = 0.0
    unresolved: float = 0.0
    strength: float = 1.0
    causal_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.source_ref:
            raise ValueError(
                "source_ref is required"
            )

        if not (
            0.0
            <= float(self.strength)
            <= 1.0
        ):
            raise ValueError(
                "strength must be between "
                "0 and 1"
            )

        for value in (
            self.valence,
            self.arousal,
            self.threat,
            self.safety,
            self.attachment,
            self.curiosity,
            self.unresolved,
        ):
            if not (
                -1.0
                <= float(value)
                <= 1.0
            ):
                raise ValueError(
                    "influence dimensions "
                    "must be between -1 and 1"
                )


@dataclass(frozen=True, slots=True)
class AffectPolicy:
    persistence: float
    influence_gain: float

    def __post_init__(self) -> None:
        for value in (
            self.persistence,
            self.influence_gain,
        ):
            if not (
                0.0
                <= float(value)
                <= 1.0
            ):
                raise ValueError(
                    "affect policy values "
                    "must be between 0 and 1"
                )


def empty_affect() -> AffectState:
    return AffectState()


def update_affect(
    state: AffectState,
    influences: Sequence[
        AffectInfluence
    ],
    *,
    policy: AffectPolicy,
) -> AffectState:
    totals = {
        "valence": 0.0,
        "arousal": 0.0,
        "threat": 0.0,
        "safety": 0.0,
        "attachment": 0.0,
        "curiosity": 0.0,
        "unresolved": 0.0,
    }

    total_strength = 0.0
    causal_refs: list[str] = list(
        state.causal_refs
    )

    for influence in influences:
        strength = float(
            influence.strength
        )

        total_strength += strength

        for dimension in totals:
            totals[dimension] += (
                float(
                    getattr(
                        influence,
                        dimension,
                    )
                )
                * strength
            )

        causal_refs.append(
            influence.source_ref
        )

        causal_refs.extend(
            influence.causal_refs
        )

    if total_strength > 0.0:
        for dimension in totals:
            totals[dimension] /= (
                total_strength
            )

    persistence = float(
        policy.persistence
    )

    gain = float(
        policy.influence_gain
    )

    def blend_signed(
        current: float,
        incoming: float,
    ) -> float:
        return _signed(
            current * persistence
            + incoming * gain
        )

    def blend_unit(
        current: float,
        incoming: float,
    ) -> float:
        return _unit(
            current * persistence
            + incoming * gain
        )

    return AffectState(
        valence=blend_signed(
            state.valence,
            totals["valence"],
        ),
        arousal=blend_unit(
            state.arousal,
            totals["arousal"],
        ),
        threat=blend_unit(
            state.threat,
            totals["threat"],
        ),
        safety=blend_unit(
            state.safety,
            totals["safety"],
        ),
        attachment=blend_signed(
            state.attachment,
            totals["attachment"],
        ),
        curiosity=blend_unit(
            state.curiosity,
            totals["curiosity"],
        ),
        unresolved=blend_unit(
            state.unresolved,
            totals["unresolved"],
        ),
        causal_refs=tuple(
            dict.fromkeys(
                causal_refs
            )
        ),
    )


def cognition_modulation(
    state: AffectState,
) -> Mapping[str, float]:
    threat_attention = _unit(
        state.threat
        * (
            0.5
            + 0.5 * state.arousal
        )
    )

    exploratory_pressure = _unit(
        state.curiosity
        * (
            1.0
            - 0.5 * state.threat
        )
    )

    relational_attention = _unit(
        abs(state.attachment)
        * (
            0.5
            + 0.5 * state.arousal
        )
    )

    uncertainty_attention = _unit(
        state.unresolved
        * (
            0.5
            + 0.5 * state.curiosity
        )
    )

    defensive_pressure = _unit(
        state.threat
        * (
            1.0 - state.safety
        )
    )

    return {
        "threat_attention": (
            threat_attention
        ),
        "exploratory_pressure": (
            exploratory_pressure
        ),
        "relational_attention": (
            relational_attention
        ),
        "uncertainty_attention": (
            uncertainty_attention
        ),
        "defensive_pressure": (
            defensive_pressure
        ),
    }


def affect_projection(
    state: AffectState,
) -> Mapping[str, Any]:
    return {
        "schema": SCHEMA,
        "state": state.projection(),
        "cognition_modulation": dict(
            cognition_modulation(
                state
            )
        ),
        "derived": True,
        "authoritative": False,
        "authority_effect": "none",
    }
