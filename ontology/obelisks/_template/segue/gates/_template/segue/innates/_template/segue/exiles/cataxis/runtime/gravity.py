#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import math
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import Any, Mapping, Sequence

from laws import G
from physics import Body, Force, Vector3, position_vector
from spacetime import EPSILON, OWNER

SCHEMA = "savant://cataxis/gravity/1.0.0"
C = 299_792_458.0
C2 = C * C


class GravityError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class GravitationalSource:
    source_id: str
    mass_kg: float
    position_meters: Vector3
    radius_meters: float = 0.0
    metadata: Mapping[str, Any] = field(
        default_factory=dict
    )


@dataclass(frozen=True, slots=True)
class GravitySample:
    position_meters: Vector3
    acceleration_mps2: Vector3
    potential_j_kg: float
    contributors: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class OrbitState:
    central_mass_kg: float
    radius_meters: float
    circular_velocity_mps: float
    escape_velocity_mps: float
    orbital_period_seconds: float
    specific_orbital_energy_j_kg: float


@dataclass(frozen=True, slots=True)
class GravityProjection:
    samples: tuple[GravitySample, ...]
    model: str
    assumptions: tuple[str, ...]
    metadata: Mapping[str, Any] = field(
        default_factory=dict
    )
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
        raise GravityError(
            f"{name} must be numeric"
        ) from exc

    if not math.isfinite(number):
        raise GravityError(
            f"{name} must be finite"
        )

    return number


def _positive(
    value: Any,
    name: str,
) -> float:
    number = _finite(value, name)

    if number <= 0:
        raise GravityError(
            f"{name} must be positive"
        )

    return number


def _nonnegative(
    value: Any,
    name: str,
) -> float:
    number = _finite(value, name)

    if number < 0:
        raise GravityError(
            f"{name} must be nonnegative"
        )

    return number


def source_from_body(
    body: Body,
) -> GravitationalSource:
    return GravitationalSource(
        source_id=body.body_id,
        mass_kg=body.mass_kg,
        position_meters=position_vector(
            body.position
        ),
        radius_meters=body.radius_meters,
        metadata=body.metadata,
    )


def validate_source(
    source: GravitationalSource,
) -> None:
    _nonnegative(
        source.mass_kg,
        "mass_kg",
    )

    _nonnegative(
        source.radius_meters,
        "radius_meters",
    )


def acceleration_from_source(
    source: GravitationalSource,
    *,
    at: Vector3,
) -> Vector3:
    validate_source(source)

    displacement = (
        source.position_meters
        .subtract(at)
    )

    distance = displacement.magnitude

    if distance <= EPSILON:
        raise GravityError(
            "point-source gravitational singularity"
        )

    acceleration = (
        G
        * source.mass_kg
        / (distance * distance)
    )

    return (
        displacement.normalized()
        .scale(acceleration)
    )


def potential_from_source(
    source: GravitationalSource,
    *,
    at: Vector3,
) -> float:
    validate_source(source)

    distance = (
        source.position_meters
        .subtract(at)
        .magnitude
    )

    if distance <= EPSILON:
        raise GravityError(
            "point-source gravitational singularity"
        )

    return (
        -G
        * source.mass_kg
        / distance
    )


def acceleration(
    sources: Sequence[GravitationalSource],
    *,
    at: Vector3,
) -> Vector3:
    total = Vector3(
        0.0,
        0.0,
        0.0,
    )

    for source in sources:
        total = total.add(
            acceleration_from_source(
                source,
                at=at,
            )
        )

    return total


def potential(
    sources: Sequence[GravitationalSource],
    *,
    at: Vector3,
) -> float:
    return sum(
        potential_from_source(
            source,
            at=at,
        )
        for source in sources
    )


def sample(
    sources: Sequence[GravitationalSource],
    *,
    at: Vector3,
) -> GravitySample:
    return GravitySample(
        position_meters=at,
        acceleration_mps2=acceleration(
            sources,
            at=at,
        ),
        potential_j_kg=potential(
            sources,
            at=at,
        ),
        contributors=tuple(
            source.source_id
            for source in sources
        ),
    )


def pair_force(
    *,
    first: Body,
    second: Body,
) -> Force:
    first_mass = _positive(
        first.mass_kg,
        "first.mass_kg",
    )

    second_mass = _positive(
        second.mass_kg,
        "second.mass_kg",
    )

    displacement = (
        position_vector(
            second.position
        )
        .subtract(
            position_vector(
                first.position
            )
        )
    )

    distance = displacement.magnitude

    minimum_distance = max(
        first.radius_meters
        + second.radius_meters,
        EPSILON,
    )

    effective_distance = max(
        distance,
        minimum_distance,
    )

    if distance <= EPSILON:
        raise GravityError(
            "gravitational direction undefined "
            "for coincident centers"
        )

    magnitude = (
        G
        * first_mass
        * second_mass
        / (
            effective_distance
            * effective_distance
        )
    )

    return Force(
        force_id=(
            f"gravity:{second.body_id}"
            f"->{first.body_id}"
        ),
        vector_newtons=(
            displacement
            .normalized()
            .scale(magnitude)
        ),
        source="cataxis.gravity",
        metadata={
            "first": first.body_id,
            "second": second.body_id,
            "center_distance_meters": distance,
            "effective_distance_meters": (
                effective_distance
            ),
        },
    )


def forces_for_body(
    target: Body,
    bodies: Sequence[Body],
) -> tuple[Force, ...]:
    return tuple(
        pair_force(
            first=target,
            second=other,
        )
        for other in bodies
        if other.body_id != target.body_id
    )


def circular_orbit_velocity(
    *,
    central_mass_kg: float,
    radius_meters: float,
) -> float:
    mass = _nonnegative(
        central_mass_kg,
        "central_mass_kg",
    )

    radius = _positive(
        radius_meters,
        "radius_meters",
    )

    return math.sqrt(
        G * mass / radius
    )


def escape_velocity(
    *,
    central_mass_kg: float,
    radius_meters: float,
) -> float:
    mass = _nonnegative(
        central_mass_kg,
        "central_mass_kg",
    )

    radius = _positive(
        radius_meters,
        "radius_meters",
    )

    return math.sqrt(
        2.0 * G * mass / radius
    )


def orbital_period(
    *,
    central_mass_kg: float,
    semi_major_axis_meters: float,
) -> float:
    mass = _positive(
        central_mass_kg,
        "central_mass_kg",
    )

    axis = _positive(
        semi_major_axis_meters,
        "semi_major_axis_meters",
    )

    return (
        2.0
        * math.pi
        * math.sqrt(
            axis ** 3
            / (G * mass)
        )
    )


def specific_orbital_energy(
    *,
    central_mass_kg: float,
    radius_meters: float,
    velocity_mps: float,
) -> float:
    mass = _nonnegative(
        central_mass_kg,
        "central_mass_kg",
    )

    radius = _positive(
        radius_meters,
        "radius_meters",
    )

    velocity = _finite(
        velocity_mps,
        "velocity_mps",
    )

    return (
        0.5 * velocity * velocity
        - G * mass / radius
    )


def orbit_state(
    *,
    central_mass_kg: float,
    radius_meters: float,
) -> OrbitState:
    velocity = circular_orbit_velocity(
        central_mass_kg=central_mass_kg,
        radius_meters=radius_meters,
    )

    return OrbitState(
        central_mass_kg=central_mass_kg,
        radius_meters=radius_meters,
        circular_velocity_mps=velocity,
        escape_velocity_mps=(
            escape_velocity(
                central_mass_kg=central_mass_kg,
                radius_meters=radius_meters,
            )
        ),
        orbital_period_seconds=(
            orbital_period(
                central_mass_kg=central_mass_kg,
                semi_major_axis_meters=(
                    radius_meters
                ),
            )
        ),
        specific_orbital_energy_j_kg=(
            specific_orbital_energy(
                central_mass_kg=central_mass_kg,
                radius_meters=radius_meters,
                velocity_mps=velocity,
            )
        ),
    )


def schwarzschild_radius(
    mass_kg: float,
) -> float:
    mass = _nonnegative(
        mass_kg,
        "mass_kg",
    )

    return (
        2.0 * G * mass / C2
    )


def surface_gravity(
    *,
    mass_kg: float,
    radius_meters: float,
) -> float:
    mass = _nonnegative(
        mass_kg,
        "mass_kg",
    )

    radius = _positive(
        radius_meters,
        "radius_meters",
    )

    return (
        G * mass
        / (radius * radius)
    )


def gravitational_redshift(
    *,
    mass_kg: float,
    emission_radius_meters: float,
    observation_radius_meters: float | None = None,
) -> float:
    mass = _nonnegative(
        mass_kg,
        "mass_kg",
    )

    emission = _positive(
        emission_radius_meters,
        "emission_radius_meters",
    )

    rs = schwarzschild_radius(
        mass
    )

    if emission <= rs:
        raise GravityError(
            "emission radius must exceed "
            "Schwarzschild radius"
        )

    emission_factor = math.sqrt(
        1.0 - rs / emission
    )

    if observation_radius_meters is None:
        observation_factor = 1.0
    else:
        observation = _positive(
            observation_radius_meters,
            "observation_radius_meters",
        )

        if observation <= rs:
            raise GravityError(
                "observation radius must exceed "
                "Schwarzschild radius"
            )

        observation_factor = math.sqrt(
            1.0 - rs / observation
        )

    return (
        observation_factor
        / emission_factor
        - 1.0
    )


def tidal_acceleration(
    *,
    central_mass_kg: float,
    radius_meters: float,
    separation_meters: float,
) -> float:
    mass = _nonnegative(
        central_mass_kg,
        "central_mass_kg",
    )

    radius = _positive(
        radius_meters,
        "radius_meters",
    )

    separation = _nonnegative(
        separation_meters,
        "separation_meters",
    )

    return (
        2.0
        * G
        * mass
        * separation
        / (radius ** 3)
    )


def project(
    *,
    sources: Sequence[GravitationalSource],
    points: Sequence[Vector3],
    metadata: Mapping[str, Any] | None = None,
) -> GravityProjection:
    return GravityProjection(
        samples=tuple(
            sample(
                sources,
                at=point,
            )
            for point in points
        ),
        model=(
            "newtonian_gravity_with_"
            "schwarzschild_derived_observables"
        ),
        assumptions=(
            "newtonian_force_dynamics",
            "linear_field_superposition",
            "spherical_or_point_sources",
            "weak_field_for_newtonian_dynamics",
            "schwarzschild_static_observables",
            "no_frame_dragging",
        ),
        metadata=dict(
            metadata or {}
        ),
    )


def capabilities() -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "owner": OWNER,
        "primitive": "physics",
        "authority_effect": "none",
        "capabilities": [
            "gravitational_sources",
            "newtonian_gravity",
            "pairwise_gravitational_force",
            "multi_source_gravity",
            "gravitational_acceleration",
            "gravitational_potential",
            "field_superposition",
            "finite_body_distance_guard",
            "circular_orbit_velocity",
            "escape_velocity",
            "orbital_period",
            "specific_orbital_energy",
            "orbit_state",
            "surface_gravity",
            "tidal_acceleration",
            "schwarzschild_radius",
            "gravitational_redshift",
            "gravity_field_sampling",
            "gravity_projection",
            "gravity_source_provenance",
            "carbon_gravity_environment",
            "mobius_orbital_continuity",
            "deterministic_gravity_receipts",
        ],
    }
