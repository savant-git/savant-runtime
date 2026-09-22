from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from typing import Any, Mapping, Sequence


SCHEMA = "savant://noumenon/developmental-tension/1"

TENSION_KINDS = frozenset(
    {
        "contradiction",
        "commitment",
        "relational",
        "moral",
        "identity",
        "expectation",
        "unresolved",
    }
)


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
        min(
            1.0,
            float(value),
        ),
    )


@dataclass(frozen=True, slots=True)
class DevelopmentalTension:
    tension_ref: str
    kind: str
    pressure: float
    persistence: float
    uncertainty: float
    resolvability: float
    causal_refs: tuple[str, ...]
    evidence_refs: tuple[str, ...] = ()
    authority_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.tension_ref:
            raise ValueError(
                "tension_ref is required"
            )

        if self.kind not in TENSION_KINDS:
            raise ValueError(
                "unsupported tension kind"
            )

        if not self.causal_refs:
            raise ValueError(
                "tension requires causal refs"
            )

        for value in (
            self.pressure,
            self.persistence,
            self.uncertainty,
            self.resolvability,
        ):
            if not (
                0.0
                <= float(value)
                <= 1.0
            ):
                raise ValueError(
                    "tension values must be "
                    "between 0 and 1"
                )

    def projection(
        self,
    ) -> dict[str, Any]:
        return {
            "schema": SCHEMA,
            "tension_ref": self.tension_ref,
            "kind": self.kind,
            "pressure": float(
                self.pressure
            ),
            "persistence": float(
                self.persistence
            ),
            "uncertainty": float(
                self.uncertainty
            ),
            "resolvability": float(
                self.resolvability
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
            "noumenon-tension:"
            + self.digest
        )


@dataclass(frozen=True, slots=True)
class TensionResolution:
    tension_ref: str
    resolution_ref: str
    acknowledgment: float
    action: float
    consequence_change: float
    evidence_support: float
    causal_refs: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.tension_ref:
            raise ValueError(
                "tension_ref is required"
            )

        if not self.resolution_ref:
            raise ValueError(
                "resolution_ref is required"
            )

        for value in (
            self.acknowledgment,
            self.action,
            self.consequence_change,
            self.evidence_support,
        ):
            if not (
                0.0
                <= float(value)
                <= 1.0
            ):
                raise ValueError(
                    "resolution values must be "
                    "between 0 and 1"
                )

    def projection(
        self,
    ) -> dict[str, Any]:
        return {
            "schema": SCHEMA,
            "tension_ref": self.tension_ref,
            "resolution_ref": (
                self.resolution_ref
            ),
            "acknowledgment": float(
                self.acknowledgment
            ),
            "action": float(
                self.action
            ),
            "consequence_change": float(
                self.consequence_change
            ),
            "evidence_support": float(
                self.evidence_support
            ),
            "causal_refs": list(
                self.causal_refs
            ),
            "evidence_refs": list(
                self.evidence_refs
            ),
            "authority_effect": "none",
        }


@dataclass(frozen=True, slots=True)
class TensionState:
    origin: DevelopmentalTension
    current_pressure: float
    resolution_refs: tuple[str, ...] = ()
    causal_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not (
            0.0
            <= float(self.current_pressure)
            <= 1.0
        ):
            raise ValueError(
                "current pressure must be "
                "between 0 and 1"
            )

    def projection(
        self,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {
            "schema": SCHEMA,
            "origin": self.origin.projection(),
            "current_pressure": float(
                self.current_pressure
            ),
            "resolution_refs": list(
                self.resolution_refs
            ),
            "causal_refs": list(
                self.causal_refs
            ),
            "resolved": (
                self.current_pressure == 0.0
            ),
            "origin_erased": False,
            "derived": True,
            "authoritative": False,
        }

        body["digest"] = _digest(body)

        return body


def establish_tension(
    tension: DevelopmentalTension,
) -> TensionState:
    return TensionState(
        origin=tension,
        current_pressure=tension.pressure,
        causal_refs=tuple(
            dict.fromkeys(
                (
                    tension.id,
                    *tension.causal_refs,
                )
            )
        ),
    )


def resolution_effectiveness(
    tension: DevelopmentalTension,
    resolution: TensionResolution,
) -> float:
    if (
        resolution.tension_ref
        != tension.id
    ):
        raise ValueError(
            "resolution tension mismatch"
        )

    substantive = (
        float(resolution.acknowledgment)
        + float(resolution.action)
        + float(
            resolution.consequence_change
        )
        + float(
            resolution.evidence_support
        )
    ) / 4.0

    return _unit(
        substantive
        * float(tension.resolvability)
        * (
            1.0
            - (
                0.5
                * float(tension.uncertainty)
            )
        )
    )


def apply_resolution(
    state: TensionState,
    resolution: TensionResolution,
) -> TensionState:
    effectiveness = (
        resolution_effectiveness(
            state.origin,
            resolution,
        )
    )

    reduction = (
        float(state.current_pressure)
        * effectiveness
    )

    remaining = _unit(
        float(state.current_pressure)
        - reduction
    )

    return TensionState(
        origin=state.origin,
        current_pressure=remaining,
        resolution_refs=tuple(
            dict.fromkeys(
                (
                    *state.resolution_refs,
                    resolution.resolution_ref,
                )
            )
        ),
        causal_refs=tuple(
            dict.fromkeys(
                (
                    *state.causal_refs,
                    resolution.resolution_ref,
                    *resolution.causal_refs,
                )
            )
        ),
    )


def tension_debt(
    states: Sequence[TensionState],
) -> float:
    if not states:
        return 0.0

    survival = 1.0

    for state in states:
        weighted = _unit(
            float(state.current_pressure)
            * (
                0.5
                + (
                    0.5
                    * float(
                        state.origin.persistence
                    )
                )
            )
        )

        survival *= (
            1.0 - weighted
        )

    return _unit(
        1.0 - survival
    )


def tension_competition(
    states: Sequence[TensionState],
) -> tuple[TensionState, ...]:
    return tuple(
        sorted(
            states,
            key=lambda state: (
                -(
                    float(
                        state.current_pressure
                    )
                    * (
                        0.5
                        + (
                            0.5
                            * float(
                                state.origin.persistence
                            )
                        )
                    )
                ),
                state.origin.tension_ref,
                state.origin.id,
            ),
        )
    )


def tension_projection(
    states: Sequence[TensionState],
) -> Mapping[str, Any]:
    ranked = tension_competition(
        states
    )

    return {
        "schema": SCHEMA,
        "states": [
            state.projection()
            for state in ranked
        ],
        "developmental_debt": (
            tension_debt(states)
        ),
        "dominant_tension_ref": (
            ranked[0].origin.id
            if ranked
            else None
        ),
        "resolution_erases_origin": False,
        "unresolved_is_authority": False,
        "automatic_identity_mutation": False,
        "derived": True,
        "authoritative": False,
        "authority_effect": "none",
    }
