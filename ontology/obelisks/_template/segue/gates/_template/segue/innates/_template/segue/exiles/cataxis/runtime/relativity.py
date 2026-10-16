#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import math
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import Any, Mapping

from spacetime import EPSILON, OWNER

SCHEMA = "savant://cataxis/relativity/1.0.0"

C = 299_792_458.0
C2 = C * C


class RelativityError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class Event:
    event_id: str
    time_seconds: float
    x_meters: float
    y_meters: float = 0.0
    z_meters: float = 0.0
    metadata: Mapping[str, Any] = field(
        default_factory=dict
    )


@dataclass(frozen=True, slots=True)
class FourVector:
    ct_meters: float
    x_meters: float
    y_meters: float
    z_meters: float


@dataclass(frozen=True, slots=True)
class Interval:
    interval_squared_m2: float
    classification: str
    proper_time_seconds: float | None
    proper_distance_meters: float | None


@dataclass(frozen=True, slots=True)
class RelativisticState:
    rest_mass_kg: float
    velocity_mps: float
    beta: float
    gamma: float
    momentum_kg_mps: float
    total_energy_joules: float
    kinetic_energy_joules: float


@dataclass(frozen=True, slots=True)
class LorentzResult:
    original: Event
    transformed: Event
    frame_velocity_mps: float
    gamma: float


@dataclass(frozen=True, slots=True)
class RelativityProjection:
    accepted: bool
    operation: str
    result: Mapping[str, Any]
    assumptions: tuple[str, ...]
    owner: str = OWNER
    authority_effect: str = "none"

    def projection(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["schema"] = SCHEMA
        payload["generated_at"] = (
            datetime.now(UTC).isoformat()
        )
        payload["digest"] = hashlib.sha256(
            json.dumps(
                payload,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
                default=str,
            ).encode("utf-8")
        ).hexdigest()
        return payload


def _finite(
    value: Any,
    name: str,
) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise RelativityError(
            f"{name} must be numeric"
        ) from exc

    if not math.isfinite(number):
        raise RelativityError(
            f"{name} must be finite"
        )

    return number


def _velocity(
    value: Any,
    name: str = "velocity_mps",
) -> float:
    velocity = _finite(value, name)

    if abs(velocity) >= C:
        raise RelativityError(
            f"{name} must satisfy |v| < c"
        )

    return velocity


def lorentz_factor(
    velocity_mps: float,
) -> float:
    velocity = _velocity(
        velocity_mps
    )

    beta = velocity / C

    return 1.0 / math.sqrt(
        1.0 - beta * beta
    )


def beta(
    velocity_mps: float,
) -> float:
    return _velocity(
        velocity_mps
    ) / C


def time_dilation(
    *,
    proper_time_seconds: float,
    velocity_mps: float,
) -> float:
    proper = _finite(
        proper_time_seconds,
        "proper_time_seconds",
    )

    if proper < 0:
        raise RelativityError(
            "proper_time_seconds must be nonnegative"
        )

    return (
        lorentz_factor(velocity_mps)
        * proper
    )


def proper_time(
    *,
    coordinate_time_seconds: float,
    velocity_mps: float,
) -> float:
    coordinate = _finite(
        coordinate_time_seconds,
        "coordinate_time_seconds",
    )

    if coordinate < 0:
        raise RelativityError(
            "coordinate_time_seconds must be nonnegative"
        )

    return (
        coordinate
        / lorentz_factor(velocity_mps)
    )


def length_contraction(
    *,
    proper_length_meters: float,
    velocity_mps: float,
) -> float:
    length = _finite(
        proper_length_meters,
        "proper_length_meters",
    )

    if length < 0:
        raise RelativityError(
            "proper_length_meters must be nonnegative"
        )

    return (
        length
        / lorentz_factor(velocity_mps)
    )


def relativistic_momentum(
    *,
    rest_mass_kg: float,
    velocity_mps: float,
) -> float:
    mass = _finite(
        rest_mass_kg,
        "rest_mass_kg",
    )

    if mass < 0:
        raise RelativityError(
            "rest_mass_kg must be nonnegative"
        )

    velocity = _velocity(
        velocity_mps
    )

    return (
        lorentz_factor(velocity)
        * mass
        * velocity
    )


def total_energy(
    *,
    rest_mass_kg: float,
    velocity_mps: float,
) -> float:
    mass = _finite(
        rest_mass_kg,
        "rest_mass_kg",
    )

    if mass < 0:
        raise RelativityError(
            "rest_mass_kg must be nonnegative"
        )

    return (
        lorentz_factor(
            velocity_mps
        )
        * mass
        * C2
    )


def rest_energy(
    rest_mass_kg: float,
) -> float:
    mass = _finite(
        rest_mass_kg,
        "rest_mass_kg",
    )

    if mass < 0:
        raise RelativityError(
            "rest_mass_kg must be nonnegative"
        )

    return mass * C2


def kinetic_energy(
    *,
    rest_mass_kg: float,
    velocity_mps: float,
) -> float:
    return (
        total_energy(
            rest_mass_kg=rest_mass_kg,
            velocity_mps=velocity_mps,
        )
        - rest_energy(rest_mass_kg)
    )


def state(
    *,
    rest_mass_kg: float,
    velocity_mps: float,
) -> RelativisticState:
    velocity = _velocity(
        velocity_mps
    )

    factor = lorentz_factor(
        velocity
    )

    return RelativisticState(
        rest_mass_kg=rest_mass_kg,
        velocity_mps=velocity,
        beta=velocity / C,
        gamma=factor,
        momentum_kg_mps=(
            factor
            * rest_mass_kg
            * velocity
        ),
        total_energy_joules=(
            factor
            * rest_mass_kg
            * C2
        ),
        kinetic_energy_joules=(
            (factor - 1.0)
            * rest_mass_kg
            * C2
        ),
    )


def four_vector(
    event: Event,
) -> FourVector:
    return FourVector(
        ct_meters=(
            C * event.time_seconds
        ),
        x_meters=event.x_meters,
        y_meters=event.y_meters,
        z_meters=event.z_meters,
    )


def interval(
    first: Event,
    second: Event,
) -> Interval:
    dt = (
        second.time_seconds
        - first.time_seconds
    )

    dx = (
        second.x_meters
        - first.x_meters
    )

    dy = (
        second.y_meters
        - first.y_meters
    )

    dz = (
        second.z_meters
        - first.z_meters
    )

    spatial_squared = (
        dx * dx
        + dy * dy
        + dz * dz
    )

    interval_squared = (
        C2 * dt * dt
        - spatial_squared
    )

    scale = max(
        C2 * dt * dt,
        spatial_squared,
        1.0,
    )

    tolerance = (
        EPSILON * scale
    )

    if interval_squared > tolerance:
        classification = "timelike"
        proper_time_value = (
            math.sqrt(
                interval_squared
            )
            / C
        )
        proper_distance = None

    elif interval_squared < -tolerance:
        classification = "spacelike"
        proper_time_value = None
        proper_distance = math.sqrt(
            -interval_squared
        )

    else:
        classification = "lightlike"
        proper_time_value = 0.0
        proper_distance = 0.0

    return Interval(
        interval_squared_m2=(
            interval_squared
        ),
        classification=classification,
        proper_time_seconds=(
            proper_time_value
        ),
        proper_distance_meters=(
            proper_distance
        ),
    )


def lorentz_transform(
    event: Event,
    *,
    frame_velocity_mps: float,
) -> LorentzResult:
    velocity = _velocity(
        frame_velocity_mps,
        "frame_velocity_mps",
    )

    gamma = lorentz_factor(
        velocity
    )

    transformed_x = gamma * (
        event.x_meters
        - velocity
        * event.time_seconds
    )

    transformed_time = gamma * (
        event.time_seconds
        - (
            velocity
            * event.x_meters
            / C2
        )
    )

    transformed = Event(
        event_id=event.event_id,
        time_seconds=transformed_time,
        x_meters=transformed_x,
        y_meters=event.y_meters,
        z_meters=event.z_meters,
        metadata={
            **dict(event.metadata),
            "lorentz_transformed": True,
        },
    )

    return LorentzResult(
        original=event,
        transformed=transformed,
        frame_velocity_mps=velocity,
        gamma=gamma,
    )


def velocity_addition(
    *,
    velocity_mps: float,
    frame_velocity_mps: float,
) -> float:
    velocity = _velocity(
        velocity_mps
    )

    frame = _velocity(
        frame_velocity_mps,
        "frame_velocity_mps",
    )

    denominator = (
        1.0
        - velocity * frame / C2
    )

    if abs(denominator) <= EPSILON:
        raise RelativityError(
            "velocity transformation denominator vanished"
        )

    result = (
        velocity - frame
    ) / denominator

    if abs(result) >= C:
        if abs(abs(result) - C) <= 1e-7:
            return math.copysign(
                math.nextafter(C, 0.0),
                result,
            )

        raise RelativityError(
            "transformed velocity exceeded c"
        )

    return result


def energy_momentum_invariant(
    *,
    energy_joules: float,
    momentum_kg_mps: float,
) -> float:
    energy = _finite(
        energy_joules,
        "energy_joules",
    )

    momentum = _finite(
        momentum_kg_mps,
        "momentum_kg_mps",
    )

    invariant = (
        energy * energy
        - (
            momentum
            * C
        ) ** 2
    )

    return invariant


def invariant_mass(
    *,
    energy_joules: float,
    momentum_kg_mps: float,
) -> float:
    invariant = (
        energy_momentum_invariant(
            energy_joules=energy_joules,
            momentum_kg_mps=(
                momentum_kg_mps
            ),
        )
    )

    scale = max(
        energy_joules
        * energy_joules,
        1.0,
    )

    if invariant < 0:
        if abs(invariant) <= (
            EPSILON * scale
        ):
            invariant = 0.0
        else:
            raise RelativityError(
                "energy-momentum state has "
                "negative mass invariant"
            )

    return (
        math.sqrt(invariant)
        / C2
    )


def causal_reachable(
    first: Event,
    second: Event,
) -> bool:
    relation = interval(
        first,
        second,
    )

    return relation.classification in {
        "timelike",
        "lightlike",
    }


def light_travel_time_seconds(
    distance_meters: float,
) -> float:
    distance = _finite(
        distance_meters,
        "distance_meters",
    )

    if distance < 0:
        raise RelativityError(
            "distance_meters must be nonnegative"
        )

    return distance / C


def gravitational_time_dilation_schwarzschild(
    *,
    coordinate_time_seconds: float,
    radius_meters: float,
    central_mass_kg: float,
    gravitational_constant: float = (
        6.67430e-11
    ),
) -> float:
    coordinate = _finite(
        coordinate_time_seconds,
        "coordinate_time_seconds",
    )

    radius = _finite(
        radius_meters,
        "radius_meters",
    )

    mass = _finite(
        central_mass_kg,
        "central_mass_kg",
    )

    gravitational_constant = _finite(
        gravitational_constant,
        "gravitational_constant",
    )

    if coordinate < 0:
        raise RelativityError(
            "coordinate time must be nonnegative"
        )

    if radius <= 0:
        raise RelativityError(
            "radius_meters must be positive"
        )

    if mass < 0:
        raise RelativityError(
            "central_mass_kg must be nonnegative"
        )

    schwarzschild_radius = (
        2.0
        * gravitational_constant
        * mass
        / C2
    )

    if radius <= schwarzschild_radius:
        raise RelativityError(
            "static Schwarzschild observer "
            "requires radius above horizon"
        )

    factor = math.sqrt(
        1.0
        - schwarzschild_radius
        / radius
    )

    return coordinate * factor


def capabilities() -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "owner": OWNER,
        "primitive": "physics",
        "authority_effect": "none",
        "capabilities": [
            "speed_of_light_boundary",
            "lorentz_factor",
            "relativistic_beta",
            "time_dilation",
            "proper_time",
            "length_contraction",
            "relativistic_momentum",
            "rest_energy",
            "total_relativistic_energy",
            "relativistic_kinetic_energy",
            "energy_momentum_invariant",
            "invariant_mass",
            "four_vectors",
            "spacetime_intervals",
            "timelike_classification",
            "spacelike_classification",
            "lightlike_classification",
            "lorentz_transform",
            "relativistic_velocity_addition",
            "causal_reachability",
            "light_travel_time",
            "schwarzschild_time_dilation",
            "event_frame_projection",
            "relativistic_state_receipts",
            "carbon_relativistic_simulation",
            "mobius_relativistic_continuity",
        ],
    }
