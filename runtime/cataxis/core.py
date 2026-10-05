from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
import math
from typing import Any, Mapping, Sequence


SCHEMA = "savant://cataxis/core/1"


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
            "catalyst values must be finite"
        )

    return result


@dataclass(frozen=True, slots=True)
class Catalyst:
    catalyst_ref: str
    pressure: float
    threshold: float
    polarity: float = 0.0
    surge_limit: float = 1.0
    provenance_refs: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = ()
    authority_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.catalyst_ref:
            raise ValueError(
                "catalyst_ref is required"
            )

        pressure = _finite(
            self.pressure
        )
        threshold = _finite(
            self.threshold
        )
        polarity = _finite(
            self.polarity
        )
        surge_limit = _finite(
            self.surge_limit
        )

        if pressure < 0:
            raise ValueError(
                "pressure must be nonnegative"
            )

        if threshold < 0:
            raise ValueError(
                "threshold must be nonnegative"
            )

        if not -1.0 <= polarity <= 1.0:
            raise ValueError(
                "polarity must be between -1 and 1"
            )

        if surge_limit < 0:
            raise ValueError(
                "surge_limit must be nonnegative"
            )

    @property
    def activated(self) -> bool:
        return (
            self.pressure
            >= self.threshold
        )

    @property
    def excess_pressure(self) -> float:
        return max(
            0.0,
            float(self.pressure)
            - float(self.threshold),
        )

    @property
    def bounded_surge(self) -> float:
        return min(
            self.excess_pressure,
            float(self.surge_limit),
        )

    def projection(self) -> dict[str, Any]:
        body: dict[str, Any] = {
            "schema": SCHEMA,
            "catalyst_ref": (
                self.catalyst_ref
            ),
            "pressure": float(
                self.pressure
            ),
            "threshold": float(
                self.threshold
            ),
            "polarity": float(
                self.polarity
            ),
            "surge_limit": float(
                self.surge_limit
            ),
            "activated": self.activated,
            "excess_pressure": (
                self.excess_pressure
            ),
            "bounded_surge": (
                self.bounded_surge
            ),
            "provenance_refs": list(
                self.provenance_refs
            ),
            "evidence_refs": list(
                self.evidence_refs
            ),
            "authority_refs": list(
                self.authority_refs
            ),
            "source_mutated": False,
            "automatic_activation_side_effect": False,
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
            "cataxis-catalyst:"
            + self.digest
        )


def catalyst_registry(
    catalysts: Sequence[Catalyst],
) -> Mapping[str, Any]:
    ordered = tuple(
        sorted(
            catalysts,
            key=lambda item: (
                item.catalyst_ref,
                item.id,
            ),
        )
    )

    refs = [
        catalyst.catalyst_ref
        for catalyst in ordered
    ]

    duplicate_refs = sorted(
        {
            ref
            for ref in refs
            if refs.count(ref) > 1
        }
    )

    body: dict[str, Any] = {
        "schema": SCHEMA,
        "catalysts": [
            catalyst.projection()
            for catalyst in ordered
        ],
        "catalyst_count": len(
            ordered
        ),
        "activated_count": sum(
            1
            for catalyst in ordered
            if catalyst.activated
        ),
        "duplicate_refs": (
            duplicate_refs
        ),
        "conflicts_preserved": True,
        "registry_is_projection": True,
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
