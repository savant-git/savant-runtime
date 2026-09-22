from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
import math
from typing import Any, Mapping, Sequence

from runtime.cataxis.core import Catalyst


SCHEMA = "savant://cataxis/activation/1"

STATES = (
    "dormant",
    "threshold",
    "active",
)


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
            "activation values must be finite"
        )

    return result


@dataclass(frozen=True, slots=True)
class ActivationState:
    catalyst_ref: str
    catalyst_id: str
    state: str
    pressure: float
    threshold: float
    margin: float
    activation_ratio: float | None

    def __post_init__(self) -> None:
        if self.state not in STATES:
            raise ValueError(
                "unsupported activation state"
            )

    def projection(self) -> dict[str, Any]:
        body: dict[str, Any] = {
            "schema": SCHEMA,
            "catalyst_ref": (
                self.catalyst_ref
            ),
            "catalyst_id": (
                self.catalyst_id
            ),
            "state": self.state,
            "pressure": float(
                self.pressure
            ),
            "threshold": float(
                self.threshold
            ),
            "margin": float(
                self.margin
            ),
            "activation_ratio": (
                self.activation_ratio
            ),
            "activation_is_observation": True,
            "activation_side_effect": False,
            "source_mutated": False,
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
            "cataxis-activation:"
            + self.digest
        )


def activation_state(
    catalyst: Catalyst,
) -> ActivationState:
    pressure = _finite(
        catalyst.pressure
    )
    threshold = _finite(
        catalyst.threshold
    )

    margin = pressure - threshold

    if pressure < threshold:
        state = "dormant"
    elif pressure == threshold:
        state = "threshold"
    else:
        state = "active"

    ratio: float | None

    if threshold == 0.0:
        ratio = (
            0.0
            if pressure == 0.0
            else None
        )
    else:
        ratio = pressure / threshold

    return ActivationState(
        catalyst_ref=(
            catalyst.catalyst_ref
        ),
        catalyst_id=catalyst.id,
        state=state,
        pressure=pressure,
        threshold=threshold,
        margin=margin,
        activation_ratio=ratio,
    )


def activation_projection(
    catalysts: Sequence[Catalyst],
) -> Mapping[str, Any]:
    states = tuple(
        sorted(
            (
                activation_state(
                    catalyst
                )
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
        "dormant_count": sum(
            1
            for state in states
            if state.state == "dormant"
        ),
        "threshold_count": sum(
            1
            for state in states
            if state.state == "threshold"
        ),
        "active_count": sum(
            1
            for state in states
            if state.state == "active"
        ),
        "activation_is_projection": True,
        "activation_side_effect": False,
        "source_mutated": False,
        "automatic_reconciliation": False,
        "authority_transferred": False,
        "model_independent": True,
        "provider_independent": True,
        "derived": True,
        "authoritative": False,
        "authority_effect": "none",
    }

    body["digest"] = _digest(body)
    return body
