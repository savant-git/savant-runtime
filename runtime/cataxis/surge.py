from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
import math
from typing import Any, Mapping, Sequence

from runtime.cataxis.activation import (
    ActivationState,
    activation_state,
)
from runtime.cataxis.core import Catalyst


SCHEMA = "savant://cataxis/surge/1"


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


def _finite(value: float) -> float:
    result = float(value)

    if not math.isfinite(result):
        raise ValueError(
            "surge values must be finite"
        )

    return result


@dataclass(frozen=True, slots=True)
class SurgeState:
    catalyst_ref: str
    catalyst_id: str
    activation_ref: str
    raw_surge: float
    surge_limit: float
    projected_surge: float
    clipped: bool
    polarity: float
    signed_surge: float

    def projection(self) -> dict[str, Any]:
        body: dict[str, Any] = {
            "schema": SCHEMA,
            "catalyst_ref": (
                self.catalyst_ref
            ),
            "catalyst_id": (
                self.catalyst_id
            ),
            "activation_ref": (
                self.activation_ref
            ),
            "raw_surge": float(
                self.raw_surge
            ),
            "surge_limit": float(
                self.surge_limit
            ),
            "projected_surge": float(
                self.projected_surge
            ),
            "clipped": self.clipped,
            "polarity": float(
                self.polarity
            ),
            "signed_surge": float(
                self.signed_surge
            ),
            "surge_is_projection": True,
            "pressure_mutated": False,
            "activation_mutated": False,
            "automatic_discharge": False,
            "authority_transferred": False,
            "derived": True,
            "authoritative": False,
            "authority_effect": "none",
        }

        body["digest"] = _digest(body)
        return body

    @property
    def digest(self) -> str:
        return str(
            self.projection()["digest"]
        )

    @property
    def id(self) -> str:
        return (
            "cataxis-surge:"
            + self.digest
        )


def surge_state(
    catalyst: Catalyst,
    activation: ActivationState | None = None,
) -> SurgeState:
    state = (
        activation
        if activation is not None
        else activation_state(catalyst)
    )

    if (
        state.catalyst_id
        != catalyst.id
    ):
        raise ValueError(
            "activation state does not "
            "belong to catalyst"
        )

    raw_surge = max(
        0.0,
        _finite(state.margin),
    )

    surge_limit = _finite(
        catalyst.surge_limit
    )

    projected_surge = min(
        raw_surge,
        surge_limit,
    )

    polarity = _finite(
        catalyst.polarity
    )

    return SurgeState(
        catalyst_ref=(
            catalyst.catalyst_ref
        ),
        catalyst_id=catalyst.id,
        activation_ref=state.id,
        raw_surge=raw_surge,
        surge_limit=surge_limit,
        projected_surge=(
            projected_surge
        ),
        clipped=(
            raw_surge
            > projected_surge
        ),
        polarity=polarity,
        signed_surge=(
            projected_surge
            * polarity
        ),
    )


def surge_projection(
    catalysts: Sequence[Catalyst],
) -> Mapping[str, Any]:
    states = tuple(
        sorted(
            (
                surge_state(catalyst)
                for catalyst
                in catalysts
            ),
            key=lambda item: (
                item.catalyst_ref,
                item.catalyst_id,
            ),
        )
    )

    body: dict[str, Any] = {
        "schema": SCHEMA,
        "states": [
            state.projection()
            for state in states
        ],
        "state_count": len(states),
        "raw_surge_total": sum(
            state.raw_surge
            for state in states
        ),
        "projected_surge_total": sum(
            state.projected_surge
            for state in states
        ),
        "signed_surge_total": sum(
            state.signed_surge
            for state in states
        ),
        "clipped_count": sum(
            1
            for state in states
            if state.clipped
        ),
        "surge_is_projection": True,
        "pressure_mutated": False,
        "activation_mutated": False,
        "automatic_discharge": False,
        "automatic_reconciliation": False,
        "source_mutated": False,
        "authority_transferred": False,
        "model_independent": True,
        "provider_independent": True,
        "derived": True,
        "authoritative": False,
        "authority_effect": "none",
    }

    body["digest"] = _digest(body)
    return body
