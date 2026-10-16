from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
import math
from typing import Any, Mapping, Sequence

from runtime.cataxis.core import Catalyst


SCHEMA = "savant://cataxis/balance/1"


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
            "balance values must be finite"
        )

    return result


@dataclass(frozen=True, slots=True)
class PressureContribution:
    catalyst_ref: str
    weight: float = 1.0

    def __post_init__(self) -> None:
        if not self.catalyst_ref:
            raise ValueError(
                "catalyst_ref is required"
            )

        weight = _finite(self.weight)

        if weight < 0:
            raise ValueError(
                "weight must be nonnegative"
            )

    def projection(self) -> dict[str, Any]:
        return {
            "schema": SCHEMA,
            "catalyst_ref": (
                self.catalyst_ref
            ),
            "weight": float(
                self.weight
            ),
            "authority_effect": "none",
        }


@dataclass(frozen=True, slots=True)
class BalanceResult:
    total_pressure: float
    weighted_pressure: float
    mean_pressure: float
    net_polarity: float
    active_count: int
    dormant_count: int
    surge_total: float
    catalyst_refs: tuple[str, ...]

    def projection(self) -> dict[str, Any]:
        body: dict[str, Any] = {
            "schema": SCHEMA,
            "total_pressure": float(
                self.total_pressure
            ),
            "weighted_pressure": float(
                self.weighted_pressure
            ),
            "mean_pressure": float(
                self.mean_pressure
            ),
            "net_polarity": float(
                self.net_polarity
            ),
            "active_count": (
                self.active_count
            ),
            "dormant_count": (
                self.dormant_count
            ),
            "surge_total": float(
                self.surge_total
            ),
            "catalyst_refs": list(
                self.catalyst_refs
            ),
            "balance_is_projection": True,
            "activation_state_mutated": False,
            "pressure_mutated": False,
            "automatic_rebalancing": False,
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
            "cataxis-balance:"
            + self.digest
        )


def balance_pressure(
    catalysts: Sequence[Catalyst],
    contributions: Sequence[
        PressureContribution
    ] = (),
) -> BalanceResult:
    ordered = tuple(
        sorted(
            catalysts,
            key=lambda item: (
                item.catalyst_ref,
                item.id,
            ),
        )
    )

    weights: dict[str, float] = {}

    for contribution in contributions:
        if (
            contribution.catalyst_ref
            in weights
        ):
            raise ValueError(
                "duplicate pressure contribution"
            )

        weights[
            contribution.catalyst_ref
        ] = float(
            contribution.weight
        )

    known_refs = {
        catalyst.catalyst_ref
        for catalyst in ordered
    }

    unknown_refs = (
        set(weights)
        - known_refs
    )

    if unknown_refs:
        raise ValueError(
            "pressure contribution references "
            "unknown catalyst"
        )

    total_pressure = sum(
        float(catalyst.pressure)
        for catalyst in ordered
    )

    weighted_pressure = sum(
        float(catalyst.pressure)
        * weights.get(
            catalyst.catalyst_ref,
            1.0,
        )
        for catalyst in ordered
    )

    total_weight = sum(
        weights.get(
            catalyst.catalyst_ref,
            1.0,
        )
        for catalyst in ordered
    )

    mean_pressure = (
        weighted_pressure
        / total_weight
        if total_weight
        else 0.0
    )

    polarity_weight = sum(
        float(catalyst.pressure)
        for catalyst in ordered
    )

    net_polarity = (
        sum(
            float(catalyst.polarity)
            * float(catalyst.pressure)
            for catalyst in ordered
        )
        / polarity_weight
        if polarity_weight
        else 0.0
    )

    return BalanceResult(
        total_pressure=total_pressure,
        weighted_pressure=(
            weighted_pressure
        ),
        mean_pressure=mean_pressure,
        net_polarity=net_polarity,
        active_count=sum(
            1
            for catalyst in ordered
            if catalyst.activated
        ),
        dormant_count=sum(
            1
            for catalyst in ordered
            if not catalyst.activated
        ),
        surge_total=sum(
            catalyst.bounded_surge
            for catalyst in ordered
        ),
        catalyst_refs=tuple(
            catalyst.id
            for catalyst in ordered
        ),
    )


def balance_projection(
    catalysts: Sequence[Catalyst],
    contributions: Sequence[
        PressureContribution
    ] = (),
) -> Mapping[str, Any]:
    result = balance_pressure(
        catalysts,
        contributions,
    )

    body = result.projection()

    projection = dict(body)
    projection.update(
        {
            "model_independent": True,
            "provider_independent": True,
            "source_mutated": False,
            "automatic_reconciliation": False,
        }
    )

    projection.pop("digest", None)
    projection["digest"] = _digest(
        projection
    )

    return projection
