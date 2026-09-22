from __future__ import annotations

from dataclasses import dataclass, field
from hashlib import sha256
import json
from typing import Any, Mapping, Sequence

from runtime.noumenon.state import NoumenonState


SCHEMA = "savant://noumenon/dynamics/1"


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


def _unit(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def _signed(value: float) -> float:
    return max(-1.0, min(1.0, float(value)))


@dataclass(frozen=True, slots=True)
class IdentityAttractor:
    dimension: str
    center: float
    strength: float
    evidence_refs: tuple[str, ...] = ()
    lineage_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.dimension:
            raise ValueError("dimension is required")

        if not -1.0 <= self.center <= 1.0:
            raise ValueError(
                "center must be between -1 and 1"
            )

        if not 0.0 <= self.strength <= 1.0:
            raise ValueError(
                "strength must be between 0 and 1"
            )

    def projection(self) -> dict[str, Any]:
        return {
            "dimension": self.dimension,
            "center": self.center,
            "strength": self.strength,
            "evidence_refs": list(
                self.evidence_refs
            ),
            "lineage_refs": list(
                self.lineage_refs
            ),
        }

    @property
    def id(self) -> str:
        return (
            "identity-attractor:"
            + _digest(self.projection())
        )


@dataclass(frozen=True, slots=True)
class IdentityRepulsor:
    dimension: str
    center: float
    strength: float
    evidence_refs: tuple[str, ...] = ()
    lineage_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.dimension:
            raise ValueError("dimension is required")

        if not -1.0 <= self.center <= 1.0:
            raise ValueError(
                "center must be between -1 and 1"
            )

        if not 0.0 <= self.strength <= 1.0:
            raise ValueError(
                "strength must be between 0 and 1"
            )

    def projection(self) -> dict[str, Any]:
        return {
            "dimension": self.dimension,
            "center": self.center,
            "strength": self.strength,
            "evidence_refs": list(
                self.evidence_refs
            ),
            "lineage_refs": list(
                self.lineage_refs
            ),
        }

    @property
    def id(self) -> str:
        return (
            "identity-repulsor:"
            + _digest(self.projection())
        )


@dataclass(frozen=True, slots=True)
class DimensionDynamics:
    inertia: float = 0.5
    plasticity: float = 0.5
    elasticity: float = 0.5
    bandwidth: float = 1.0
    threshold: float = 0.0

    def __post_init__(self) -> None:
        values = {
            "inertia": self.inertia,
            "plasticity": self.plasticity,
            "elasticity": self.elasticity,
            "bandwidth": self.bandwidth,
        }

        for name, value in values.items():
            if not 0.0 <= value <= 1.0:
                raise ValueError(
                    f"{name} must be between 0 and 1"
                )

        if not 0.0 <= self.threshold <= 1.0:
            raise ValueError(
                "threshold must be between 0 and 1"
            )

    def projection(self) -> dict[str, float]:
        return {
            "inertia": self.inertia,
            "plasticity": self.plasticity,
            "elasticity": self.elasticity,
            "bandwidth": self.bandwidth,
            "threshold": self.threshold,
        }


@dataclass(frozen=True, slots=True)
class DormantDisposition:
    dimension: str
    value: float
    activation_refs: tuple[str, ...]
    evidence_refs: tuple[str, ...] = ()
    active: bool = False

    def __post_init__(self) -> None:
        if not self.dimension:
            raise ValueError("dimension is required")

        if not self.activation_refs:
            raise ValueError(
                "activation_refs are required"
            )

    def projection(self) -> dict[str, Any]:
        return {
            "dimension": self.dimension,
            "value": _signed(self.value),
            "activation_refs": list(
                self.activation_refs
            ),
            "evidence_refs": list(
                self.evidence_refs
            ),
            "active": self.active,
        }

    @property
    def id(self) -> str:
        return (
            "dormant-disposition:"
            + _digest(self.projection())
        )


@dataclass(frozen=True, slots=True)
class DynamicsProfile:
    dimensions: Mapping[
        str,
        DimensionDynamics,
    ] = field(default_factory=dict)
    attractors: tuple[
        IdentityAttractor, ...
    ] = ()
    repulsors: tuple[
        IdentityRepulsor, ...
    ] = ()
    dormant: tuple[
        DormantDisposition, ...
    ] = ()

    def projection(self) -> dict[str, Any]:
        return {
            "schema": SCHEMA,
            "dimensions": {
                key: value.projection()
                for key, value
                in sorted(
                    self.dimensions.items()
                )
            },
            "attractors": [
                value.projection()
                for value in self.attractors
            ],
            "repulsors": [
                value.projection()
                for value in self.repulsors
            ],
            "dormant": [
                value.projection()
                for value in self.dormant
            ],
        }

    @property
    def digest(self) -> str:
        return _digest(self.projection())


def empty_profile() -> DynamicsProfile:
    return DynamicsProfile()


def apply_dimension_dynamics(
    *,
    current: float,
    proposed_delta: float,
    dynamics: DimensionDynamics,
    significance: float,
) -> float:
    significance_pressure = _unit(
        abs(significance)
    )

    if (
        significance_pressure
        < dynamics.threshold
    ):
        return 0.0

    plasticity = dynamics.plasticity
    resistance = 1.0 - dynamics.inertia

    effective = (
        proposed_delta
        * plasticity
        * resistance
        * dynamics.bandwidth
        * significance_pressure
    )

    return max(
        -dynamics.bandwidth,
        min(
            dynamics.bandwidth,
            effective,
        ),
    )


def attractor_pressure(
    *,
    current: float,
    attractor: IdentityAttractor,
) -> float:
    distance = attractor.center - current

    return (
        distance
        * attractor.strength
    )


def repulsor_pressure(
    *,
    current: float,
    repulsor: IdentityRepulsor,
) -> float:
    distance = current - repulsor.center

    if distance == 0.0:
        return 0.0

    direction = (
        1.0
        if distance > 0.0
        else -1.0
    )

    proximity = max(
        0.0,
        1.0 - abs(distance) / 2.0,
    )

    return (
        direction
        * proximity
        * repulsor.strength
    )


def homeostatic_pressure(
    state: NoumenonState,
    profile: DynamicsProfile,
) -> dict[str, float]:
    pressure: dict[str, float] = {}

    for attractor in profile.attractors:
        current = float(
            state.dimensions.get(
                attractor.dimension,
                0.0,
            )
        )

        pressure[attractor.dimension] = (
            pressure.get(
                attractor.dimension,
                0.0,
            )
            + attractor_pressure(
                current=current,
                attractor=attractor,
            )
        )

    for repulsor in profile.repulsors:
        current = float(
            state.dimensions.get(
                repulsor.dimension,
                0.0,
            )
        )

        pressure[repulsor.dimension] = (
            pressure.get(
                repulsor.dimension,
                0.0,
            )
            + repulsor_pressure(
                current=current,
                repulsor=repulsor,
            )
        )

    return {
        key: _signed(value)
        for key, value
        in sorted(pressure.items())
    }


def activate_dormant(
    profile: DynamicsProfile,
    *,
    context_refs: Sequence[str],
) -> tuple[DormantDisposition, ...]:
    context = frozenset(
        str(value)
        for value in context_refs
    )

    activated: list[
        DormantDisposition
    ] = []

    for disposition in profile.dormant:
        active = bool(
            context.intersection(
                disposition.activation_refs
            )
        )

        activated.append(
            DormantDisposition(
                dimension=(
                    disposition.dimension
                ),
                value=disposition.value,
                activation_refs=(
                    disposition.activation_refs
                ),
                evidence_refs=(
                    disposition.evidence_refs
                ),
                active=active,
            )
        )

    return tuple(activated)


def dormant_pressure(
    dispositions: Sequence[
        DormantDisposition
    ],
) -> dict[str, float]:
    pressure: dict[str, float] = {}

    for disposition in dispositions:
        if not disposition.active:
            continue

        pressure[disposition.dimension] = (
            pressure.get(
                disposition.dimension,
                0.0,
            )
            + disposition.value
        )

    return {
        key: _signed(value)
        for key, value
        in sorted(pressure.items())
    }


def developmental_conservation_check(
    *,
    proposed_deltas: Mapping[str, float],
    causal_refs: Sequence[str],
    significance: Mapping[str, float],
    maximum_unexplained_delta: float = 0.05,
) -> dict[str, Any]:
    failures: list[str] = []

    has_cause = bool(
        tuple(causal_refs)
    )

    significance_strength = max(
        (
            abs(float(value))
            for value
            in significance.values()
        ),
        default=0.0,
    )

    for dimension, delta in sorted(
        proposed_deltas.items()
    ):
        magnitude = abs(float(delta))

        if (
            magnitude
            > maximum_unexplained_delta
            and not has_cause
        ):
            failures.append(
                f"{dimension}:missing_causal_lineage"
            )

        if (
            magnitude > 0.5
            and significance_strength < 0.5
        ):
            failures.append(
                f"{dimension}:"
                "insufficient_significance"
            )

    return {
        "schema": (
            "savant://noumenon/"
            "developmental-conservation/1"
        ),
        "accepted": not failures,
        "failures": failures,
    }


def derive_profile_projection(
    profile: DynamicsProfile,
) -> dict[str, Any]:
    projection = profile.projection()
    projection["digest"] = profile.digest
    return projection
