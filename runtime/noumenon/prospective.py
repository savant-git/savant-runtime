from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from typing import Any, Mapping, Sequence


SCHEMA = "savant://noumenon/prospective-identity/1"


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
class PossibleSelf:
    possible_self_ref: str
    dimensions: Mapping[str, float]
    plausibility: float
    desirability: float
    commitment: float
    continuity: float
    causal_refs: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.possible_self_ref:
            raise ValueError(
                "possible_self_ref is required"
            )

        if not self.dimensions:
            raise ValueError(
                "dimensions are required"
            )

        for key, value in (
            self.dimensions.items()
        ):
            if not key:
                raise ValueError(
                    "dimension is required"
                )

            if not (
                -1.0
                <= float(value)
                <= 1.0
            ):
                raise ValueError(
                    "dimension values must be "
                    "between -1 and 1"
                )

        for value in (
            self.plausibility,
            self.desirability,
            self.commitment,
            self.continuity,
        ):
            if not (
                0.0
                <= float(value)
                <= 1.0
            ):
                raise ValueError(
                    "possible-self values must "
                    "be between 0 and 1"
                )

    def projection(
        self,
    ) -> dict[str, Any]:
        return {
            "schema": SCHEMA,
            "possible_self_ref": (
                self.possible_self_ref
            ),
            "dimensions": {
                key: float(value)
                for key, value
                in sorted(
                    self.dimensions.items()
                )
            },
            "plausibility": float(
                self.plausibility
            ),
            "desirability": float(
                self.desirability
            ),
            "commitment": float(
                self.commitment
            ),
            "continuity": float(
                self.continuity
            ),
            "causal_refs": list(
                self.causal_refs
            ),
            "evidence_refs": list(
                self.evidence_refs
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
            "noumenon-possible-self:"
            + self.digest
        )


@dataclass(frozen=True, slots=True)
class ProspectivePressure:
    possible_self_ref: str
    attraction: float
    commitment_gravity: float
    continuity_support: float
    pressure: float
    causal_refs: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.possible_self_ref:
            raise ValueError(
                "possible_self_ref is required"
            )

        for value in (
            self.attraction,
            self.commitment_gravity,
            self.continuity_support,
            self.pressure,
        ):
            if not (
                0.0
                <= float(value)
                <= 1.0
            ):
                raise ValueError(
                    "prospective pressure values "
                    "must be between 0 and 1"
                )

    def projection(
        self,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {
            "schema": SCHEMA,
            "possible_self_ref": (
                self.possible_self_ref
            ),
            "attraction": float(
                self.attraction
            ),
            "commitment_gravity": float(
                self.commitment_gravity
            ),
            "continuity_support": float(
                self.continuity_support
            ),
            "pressure": float(
                self.pressure
            ),
            "causal_refs": list(
                self.causal_refs
            ),
            "derived": True,
            "authoritative": False,
        }

        body["digest"] = _digest(
            body
        )

        return body


@dataclass(frozen=True, slots=True)
class PossibleSelfEcology:
    selves: tuple[PossibleSelf, ...]
    pressures: tuple[
        ProspectivePressure,
        ...
    ]

    def __post_init__(self) -> None:
        self_ids = tuple(
            item.id
            for item in self.selves
        )

        if len(self_ids) != len(
            set(self_ids)
        ):
            raise ValueError(
                "duplicate possible selves"
            )

        pressure_refs = {
            item.possible_self_ref
            for item in self.pressures
        }

        if not pressure_refs.issubset(
            set(self_ids)
        ):
            raise ValueError(
                "pressure references unknown "
                "possible self"
            )

    def projection(
        self,
    ) -> dict[str, Any]:
        ranked = sorted(
            self.pressures,
            key=lambda item: (
                -item.pressure,
                item.possible_self_ref,
            ),
        )

        return {
            "schema": SCHEMA,
            "selves": [
                item.projection()
                for item in self.selves
            ],
            "pressures": [
                item.projection()
                for item in ranked
            ],
            "dominant_possible_self_ref": (
                ranked[0]
                .possible_self_ref
                if ranked
                else None
            ),
            "derived": True,
            "authoritative": False,
            "authority_effect": "none",
        }


def prospective_pressure(
    possible_self: PossibleSelf,
) -> ProspectivePressure:
    attraction = _unit(
        (
            float(
                possible_self.plausibility
            )
            + float(
                possible_self.desirability
            )
        )
        / 2.0
    )

    commitment_gravity = _unit(
        possible_self.commitment
    )

    continuity_support = _unit(
        possible_self.continuity
    )

    pressure = _unit(
        attraction
        * (
            0.5
            + (
                0.5
                * commitment_gravity
            )
        )
        * (
            0.5
            + (
                0.5
                * continuity_support
            )
        )
    )

    return ProspectivePressure(
        possible_self_ref=(
            possible_self.id
        ),
        attraction=attraction,
        commitment_gravity=(
            commitment_gravity
        ),
        continuity_support=(
            continuity_support
        ),
        pressure=pressure,
        causal_refs=tuple(
            dict.fromkeys(
                (
                    possible_self.id,
                    *possible_self.causal_refs,
                )
            )
        ),
    )


def build_ecology(
    possible_selves: Sequence[
        PossibleSelf
    ],
) -> PossibleSelfEcology:
    selves = tuple(
        possible_selves
    )

    pressures = tuple(
        prospective_pressure(
            possible_self
        )
        for possible_self in selves
    )

    return PossibleSelfEcology(
        selves=selves,
        pressures=pressures,
    )


def prospective_dimension_pressure(
    ecology: PossibleSelfEcology,
) -> Mapping[str, float]:
    totals: dict[str, float] = {}
    weights: dict[str, float] = {}

    by_id = {
        item.id: item
        for item in ecology.selves
    }

    for pressure in ecology.pressures:
        possible_self = by_id[
            pressure.possible_self_ref
        ]

        weight = float(
            pressure.pressure
        )

        for dimension, value in (
            possible_self
            .dimensions
            .items()
        ):
            totals[dimension] = (
                totals.get(
                    dimension,
                    0.0,
                )
                + float(value) * weight
            )

            weights[dimension] = (
                weights.get(
                    dimension,
                    0.0,
                )
                + weight
            )

    return {
        dimension: (
            max(
                -1.0,
                min(
                    1.0,
                    totals[dimension]
                    / weights[dimension],
                ),
            )
            if weights[dimension] > 0.0
            else 0.0
        )
        for dimension
        in sorted(totals)
    }


def prospective_projection(
    possible_selves: Sequence[
        PossibleSelf
    ],
) -> Mapping[str, Any]:
    ecology = build_ecology(
        possible_selves
    )

    projection = (
        ecology.projection()
    )

    return {
        **projection,
        "dimension_pressure": dict(
            prospective_dimension_pressure(
                ecology
            )
        ),
        "future_is_prediction": False,
        "future_is_authority": False,
        "automatic_identity_mutation": False,
    }
