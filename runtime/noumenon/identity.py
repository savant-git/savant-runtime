from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from typing import Any, Mapping, Sequence

from runtime.noumenon.state import NoumenonState


SCHEMA = "savant://noumenon/identity/1"


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
class IdentityLayer:
    layer_id: str
    generation: int
    dimensions: Mapping[str, float]
    causal_refs: tuple[str, ...]
    supersedes_ref: str | None = None
    dormant: bool = False

    def __post_init__(self) -> None:
        if not self.layer_id:
            raise ValueError(
                "layer_id is required"
            )

        if self.generation < 0:
            raise ValueError(
                "generation cannot be negative"
            )

        if not self.causal_refs:
            raise ValueError(
                "causal_refs are required"
            )

    def projection(self) -> dict[str, Any]:
        return {
            "schema": (
                "savant://noumenon/"
                "identity-layer/1"
            ),
            "layer_id": self.layer_id,
            "generation": self.generation,
            "dimensions": {
                str(key): float(value)
                for key, value
                in sorted(
                    self.dimensions.items()
                )
            },
            "causal_refs": list(
                self.causal_refs
            ),
            "supersedes_ref": (
                self.supersedes_ref
            ),
            "dormant": self.dormant,
        }

    @property
    def digest(self) -> str:
        return _digest(
            self.projection()
        )


@dataclass(frozen=True, slots=True)
class IdentityPalimpsest:
    noumenon_id: str
    layers: tuple[IdentityLayer, ...]

    def __post_init__(self) -> None:
        if not self.noumenon_id:
            raise ValueError(
                "noumenon_id is required"
            )

        generations = [
            layer.generation
            for layer in self.layers
        ]

        if generations != sorted(
            generations
        ):
            raise ValueError(
                "identity layers must be "
                "generation ordered"
            )

    def projection(self) -> dict[str, Any]:
        return {
            "schema": SCHEMA,
            "noumenon_id": self.noumenon_id,
            "layers": [
                layer.projection()
                for layer in self.layers
            ],
            "historical_layers_preserved": True,
        }

    @property
    def digest(self) -> str:
        return _digest(
            self.projection()
        )


@dataclass(frozen=True, slots=True)
class DevelopmentalDebt:
    kind: str
    ref: str
    causal_refs: tuple[str, ...]
    pressure: float
    resolved: bool = False
    resolution_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.kind not in {
            "commitment",
            "rupture",
            "contradiction",
            "promise",
            "question",
            "consequence",
        }:
            raise ValueError(
                "unsupported developmental "
                "debt kind"
            )

        if not self.ref:
            raise ValueError(
                "ref is required"
            )

        if not self.causal_refs:
            raise ValueError(
                "causal_refs are required"
            )

        if not 0.0 <= self.pressure <= 1.0:
            raise ValueError(
                "pressure must be between "
                "0 and 1"
            )

        if (
            self.resolved
            and not self.resolution_refs
        ):
            raise ValueError(
                "resolved debt requires "
                "resolution_refs"
            )

    def projection(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "ref": self.ref,
            "causal_refs": list(
                self.causal_refs
            ),
            "pressure": self.pressure,
            "resolved": self.resolved,
            "resolution_refs": list(
                self.resolution_refs
            ),
        }

    @property
    def id(self) -> str:
        return (
            "developmental-debt:"
            + _digest(self.projection())
        )


def append_identity_layer(
    palimpsest: IdentityPalimpsest,
    *,
    state: NoumenonState,
    causal_refs: Sequence[str],
    dormant: bool = False,
) -> IdentityPalimpsest:
    if (
        state.noumenon_id
        != palimpsest.noumenon_id
    ):
        raise ValueError(
            "noumenon identity mismatch"
        )

    predecessor = (
        palimpsest.layers[-1].digest
        if palimpsest.layers
        else None
    )

    layer = IdentityLayer(
        layer_id=(
            "identity-layer:"
            + state.state_digest
        ),
        generation=state.generation,
        dimensions=dict(
            state.dimensions
        ),
        causal_refs=tuple(
            causal_refs
        ),
        supersedes_ref=predecessor,
        dormant=dormant,
    )

    return IdentityPalimpsest(
        noumenon_id=(
            palimpsest.noumenon_id
        ),
        layers=(
            palimpsest.layers
            + (layer,)
        ),
    )


def empty_palimpsest(
    noumenon_id: str,
) -> IdentityPalimpsest:
    return IdentityPalimpsest(
        noumenon_id=noumenon_id,
        layers=(),
    )


def active_debt(
    debts: Sequence[DevelopmentalDebt],
) -> tuple[DevelopmentalDebt, ...]:
    return tuple(
        debt
        for debt in debts
        if not debt.resolved
    )


def debt_pressure(
    debts: Sequence[DevelopmentalDebt],
) -> float:
    active = active_debt(
        debts
    )

    if not active:
        return 0.0

    residual = 1.0

    for debt in active:
        residual *= (
            1.0 - debt.pressure
        )

    return 1.0 - residual


def resolve_debt(
    debt: DevelopmentalDebt,
    *,
    resolution_refs: Sequence[str],
) -> DevelopmentalDebt:
    refs = tuple(
        str(value)
        for value in resolution_refs
    )

    if not refs:
        raise ValueError(
            "resolution_refs are required"
        )

    return DevelopmentalDebt(
        kind=debt.kind,
        ref=debt.ref,
        causal_refs=debt.causal_refs,
        pressure=debt.pressure,
        resolved=True,
        resolution_refs=refs,
    )


def palimpsest_projection(
    palimpsest: IdentityPalimpsest,
    debts: Sequence[
        DevelopmentalDebt
    ] = (),
) -> dict[str, Any]:
    body = {
        "schema": (
            "savant://noumenon/"
            "palimpsest-projection/1"
        ),
        "identity": (
            palimpsest.projection()
        ),
        "developmental_debt": [
            debt.projection()
            for debt in debts
        ],
        "active_debt_pressure": (
            debt_pressure(debts)
        ),
        "historical_identity_erased": False,
    }

    body["digest"] = _digest(body)
    return body
