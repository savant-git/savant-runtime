#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import math
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import Any, Mapping, Sequence

from physics import Body, Vector3, position_vector
from spacetime import EPSILON, OWNER

SCHEMA = "savant://cataxis/collisions/1.0.0"


class CollisionError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class Contact:
    first_id: str
    second_id: str
    normal: Vector3
    separation_meters: float
    penetration_meters: float
    contact: bool


@dataclass(frozen=True, slots=True)
class CollisionResponse:
    first: Body
    second: Body
    contact: Contact
    impulse_newton_seconds: Vector3
    restitution: float
    kinetic_energy_before_joules: float
    kinetic_energy_after_joules: float
    dissipated_energy_joules: float
    accepted: bool
    diagnostics: Mapping[str, Any] = field(
        default_factory=dict
    )


@dataclass(frozen=True, slots=True)
class CollisionProjection:
    contacts: tuple[Contact, ...]
    collisions: tuple[CollisionResponse, ...]
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
        raise CollisionError(
            f"{name} must be numeric"
        ) from exc

    if not math.isfinite(number):
        raise CollisionError(
            f"{name} must be finite"
        )

    return number


def _radius(body: Body) -> float:
    radius = _finite(
        body.radius_meters,
        "radius_meters",
    )

    if radius < 0:
        raise CollisionError(
            "radius_meters must be nonnegative"
        )

    return radius


def _mass(body: Body) -> float:
    mass = _finite(
        body.mass_kg,
        "mass_kg",
    )

    if mass <= 0:
        raise CollisionError(
            "collision body mass must be positive"
        )

    return mass


def kinetic_energy(
    body: Body,
) -> float:
    return (
        0.5
        * _mass(body)
        * body.velocity_mps.magnitude
        * body.velocity_mps.magnitude
    )


def total_kinetic_energy(
    bodies: Sequence[Body],
) -> float:
    return sum(
        kinetic_energy(body)
        for body in bodies
    )


def momentum(
    body: Body,
) -> Vector3:
    return body.velocity_mps.scale(
        _mass(body)
    )


def total_momentum(
    bodies: Sequence[Body],
) -> Vector3:
    total = Vector3(
        0.0,
        0.0,
        0.0,
    )

    for body in bodies:
        total = total.add(
            momentum(body)
        )

    return total


def detect(
    first: Body,
    second: Body,
) -> Contact:
    first_position = position_vector(
        first.position
    )

    second_position = position_vector(
        second.position
    )

    delta = second_position.subtract(
        first_position
    )

    distance = delta.magnitude

    threshold = (
        _radius(first)
        + _radius(second)
    )

    if distance <= EPSILON:
        relative_velocity = (
            second.velocity_mps.subtract(
                first.velocity_mps
            )
        )

        if (
            relative_velocity.magnitude
            > EPSILON
        ):
            normal = (
                relative_velocity
                .normalized()
            )
        else:
            normal = Vector3(
                1.0,
                0.0,
                0.0,
            )
    else:
        normal = delta.scale(
            1.0 / distance
        )

    penetration = max(
        0.0,
        threshold - distance,
    )

    return Contact(
        first_id=first.body_id,
        second_id=second.body_id,
        normal=normal,
        separation_meters=distance,
        penetration_meters=penetration,
        contact=(
            distance
            <= threshold + EPSILON
        ),
    )


def detect_all(
    bodies: Sequence[Body],
) -> tuple[Contact, ...]:
    source = tuple(bodies)
    contacts: list[Contact] = []

    for index, first in enumerate(
        source
    ):
        for second in source[
            index + 1:
        ]:
            result = detect(
                first,
                second,
            )

            if result.contact:
                contacts.append(result)

    return tuple(contacts)


def _with_velocity(
    body: Body,
    velocity: Vector3,
) -> Body:
    return Body(
        body_id=body.body_id,
        mass_kg=body.mass_kg,
        position=body.position,
        velocity_mps=velocity,
        radius_meters=body.radius_meters,
        metadata=body.metadata,
    )


def resolve_spherical(
    first: Body,
    second: Body,
    *,
    restitution: float = 1.0,
) -> CollisionResponse:
    coefficient = _finite(
        restitution,
        "restitution",
    )

    if not 0.0 <= coefficient <= 1.0:
        raise CollisionError(
            "restitution must lie between 0 and 1"
        )

    first_mass = _mass(first)
    second_mass = _mass(second)

    contact = detect(
        first,
        second,
    )

    before_energy = (
        kinetic_energy(first)
        + kinetic_energy(second)
    )

    before_momentum = total_momentum(
        (first, second)
    )

    if not contact.contact:
        return CollisionResponse(
            first=first,
            second=second,
            contact=contact,
            impulse_newton_seconds=Vector3(
                0.0,
                0.0,
                0.0,
            ),
            restitution=coefficient,
            kinetic_energy_before_joules=(
                before_energy
            ),
            kinetic_energy_after_joules=(
                before_energy
            ),
            dissipated_energy_joules=0.0,
            accepted=True,
            diagnostics={
                "resolved": False,
                "reason": "no_contact",
            },
        )

    relative_velocity = (
        second.velocity_mps.subtract(
            first.velocity_mps
        )
    )

    normal_speed = (
        relative_velocity.x
        * contact.normal.x
        + relative_velocity.y
        * contact.normal.y
        + relative_velocity.z
        * contact.normal.z
    )

    if normal_speed >= 0.0:
        return CollisionResponse(
            first=first,
            second=second,
            contact=contact,
            impulse_newton_seconds=Vector3(
                0.0,
                0.0,
                0.0,
            ),
            restitution=coefficient,
            kinetic_energy_before_joules=(
                before_energy
            ),
            kinetic_energy_after_joules=(
                before_energy
            ),
            dissipated_energy_joules=0.0,
            accepted=True,
            diagnostics={
                "resolved": False,
                "reason": "separating",
            },
        )

    inverse_mass_sum = (
        1.0 / first_mass
        + 1.0 / second_mass
    )

    impulse_scalar = (
        -(1.0 + coefficient)
        * normal_speed
        / inverse_mass_sum
    )

    impulse = contact.normal.scale(
        impulse_scalar
    )

    first_velocity = (
        first.velocity_mps.subtract(
            impulse.scale(
                1.0 / first_mass
            )
        )
    )

    second_velocity = (
        second.velocity_mps.add(
            impulse.scale(
                1.0 / second_mass
            )
        )
    )

    evolved_first = _with_velocity(
        first,
        first_velocity,
    )

    evolved_second = _with_velocity(
        second,
        second_velocity,
    )

    after_energy = (
        kinetic_energy(evolved_first)
        + kinetic_energy(evolved_second)
    )

    after_momentum = total_momentum(
        (
            evolved_first,
            evolved_second,
        )
    )

    momentum_drift = (
        after_momentum.subtract(
            before_momentum
        )
    )

    dissipated = max(
        0.0,
        before_energy - after_energy,
    )

    accepted = (
        momentum_drift.magnitude
        <= max(
            1e-9,
            before_momentum.magnitude
            * 1e-12,
        )
        and after_energy
        <= before_energy
        + max(
            1e-9,
            before_energy * 1e-12,
        )
    )

    return CollisionResponse(
        first=evolved_first,
        second=evolved_second,
        contact=contact,
        impulse_newton_seconds=impulse,
        restitution=coefficient,
        kinetic_energy_before_joules=(
            before_energy
        ),
        kinetic_energy_after_joules=(
            after_energy
        ),
        dissipated_energy_joules=(
            dissipated
        ),
        accepted=accepted,
        diagnostics={
            "resolved": True,
            "normal_relative_velocity_mps": (
                normal_speed
            ),
            "impulse_magnitude_newton_seconds": (
                impulse.magnitude
            ),
            "momentum_drift_kg_mps": {
                "x": momentum_drift.x,
                "y": momentum_drift.y,
                "z": momentum_drift.z,
                "magnitude": (
                    momentum_drift.magnitude
                ),
            },
        },
    )


def time_of_impact(
    first: Body,
    second: Body,
    *,
    horizon_seconds: float,
) -> float | None:
    horizon = _finite(
        horizon_seconds,
        "horizon_seconds",
    )

    if horizon < 0:
        raise CollisionError(
            "horizon_seconds must be nonnegative"
        )

    relative_position = (
        position_vector(
            second.position
        ).subtract(
            position_vector(
                first.position
            )
        )
    )

    relative_velocity = (
        second.velocity_mps.subtract(
            first.velocity_mps
        )
    )

    combined_radius = (
        _radius(first)
        + _radius(second)
    )

    a = (
        relative_velocity.x ** 2
        + relative_velocity.y ** 2
        + relative_velocity.z ** 2
    )

    b = 2.0 * (
        relative_position.x
        * relative_velocity.x
        + relative_position.y
        * relative_velocity.y
        + relative_position.z
        * relative_velocity.z
    )

    c = (
        relative_position.x ** 2
        + relative_position.y ** 2
        + relative_position.z ** 2
        - combined_radius ** 2
    )

    if c <= 0:
        return 0.0

    if a <= EPSILON:
        return None

    discriminant = (
        b * b
        - 4.0 * a * c
    )

    if discriminant < 0:
        return None

    root = math.sqrt(
        max(
            0.0,
            discriminant,
        )
    )

    first_time = (
        -b - root
    ) / (2.0 * a)

    second_time = (
        -b + root
    ) / (2.0 * a)

    candidates = [
        value
        for value in (
            first_time,
            second_time,
        )
        if (
            value >= -EPSILON
            and value
            <= horizon + EPSILON
        )
    ]

    if not candidates:
        return None

    return max(
        0.0,
        min(candidates),
    )


def capabilities() -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "owner": OWNER,
        "primitive": "physics",
        "authority_effect": "none",
        "capabilities": [
            "spherical_contact_detection",
            "multi_body_contact_detection",
            "penetration_measurement",
            "contact_normals",
            "collision_impulse",
            "elastic_collision",
            "inelastic_collision",
            "coefficient_of_restitution",
            "momentum_conservation_check",
            "kinetic_energy_check",
            "collision_energy_dissipation",
            "separating_contact_rejection",
            "continuous_collision_prediction",
            "time_of_impact",
            "relative_motion_collision_detection",
            "zero_separation_normal_resolution",
            "collision_receipts",
            "collision_admissibility",
            "carbon_collision_simulation",
            "mobius_collision_consequence_support",
            "deterministic_collision_projection",
        ],
    }
