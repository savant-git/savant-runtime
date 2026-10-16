#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import math
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import Any, Mapping, Sequence

from spacetime import EPSILON, OWNER, Point3, convert

SCHEMA = "savant://cataxis/physics/1.0.0"


class PhysicsError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class Vector3:
    x: float
    y: float
    z: float = 0.0

    @property
    def magnitude(self) -> float:
        return math.sqrt(
            self.x * self.x
            + self.y * self.y
            + self.z * self.z
        )

    def normalized(self) -> Vector3:
        magnitude = self.magnitude

        if magnitude <= EPSILON:
            return Vector3(0.0, 0.0, 0.0)

        return Vector3(
            self.x / magnitude,
            self.y / magnitude,
            self.z / magnitude,
        )

    def scale(self, scalar: float) -> Vector3:
        return Vector3(
            self.x * scalar,
            self.y * scalar,
            self.z * scalar,
        )

    def add(self, other: Vector3) -> Vector3:
        return Vector3(
            self.x + other.x,
            self.y + other.y,
            self.z + other.z,
        )

    def subtract(
        self,
        other: Vector3,
    ) -> Vector3:
        return Vector3(
            self.x - other.x,
            self.y - other.y,
            self.z - other.z,
        )

    def dot(self, other: Vector3) -> float:
        return (
            self.x * other.x
            + self.y * other.y
            + self.z * other.z
        )


@dataclass(frozen=True, slots=True)
class Body:
    body_id: str
    mass_kg: float
    position: Point3
    velocity_mps: Vector3 = field(
        default_factory=lambda: Vector3(
            0.0,
            0.0,
            0.0,
        )
    )
    radius_meters: float = 0.0
    metadata: Mapping[str, Any] = field(
        default_factory=dict
    )


@dataclass(frozen=True, slots=True)
class Force:
    force_id: str
    vector_newtons: Vector3
    source: str | None = None
    metadata: Mapping[str, Any] = field(
        default_factory=dict
    )


@dataclass(frozen=True, slots=True)
class BodyState:
    body_id: str
    position: Point3
    velocity_mps: Vector3
    acceleration_mps2: Vector3
    momentum_kg_mps: Vector3
    kinetic_energy_joules: float


@dataclass(frozen=True, slots=True)
class CollisionAssessment:
    colliding: bool
    separation_meters: float
    contact_distance_meters: float
    penetration_meters: float


@dataclass(frozen=True, slots=True)
class PhysicsProjection:
    valid: bool
    states: tuple[BodyState, ...]
    violations: tuple[str, ...]
    metrics: Mapping[str, Any]
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
        raise PhysicsError(
            f"{name} must be numeric"
        ) from exc

    if not math.isfinite(number):
        raise PhysicsError(
            f"{name} must be finite"
        )

    return number


def _nonnegative(
    value: Any,
    name: str,
) -> float:
    number = _finite(value, name)

    if number < 0:
        raise PhysicsError(
            f"{name} must be nonnegative"
        )

    return number


def _positive(
    value: Any,
    name: str,
) -> float:
    number = _finite(value, name)

    if number <= 0:
        raise PhysicsError(
            f"{name} must be positive"
        )

    return number


def position_vector(
    point: Point3,
) -> Vector3:
    x, y, z = point.meters()

    return Vector3(x, y, z)


def point_from_vector(
    vector: Vector3,
) -> Point3:
    return Point3(
        x=vector.x,
        y=vector.y,
        z=vector.z,
        unit="m",
    )


def net_force(
    forces: Sequence[Force],
) -> Vector3:
    total = Vector3(0.0, 0.0, 0.0)

    for force in forces:
        total = total.add(
            force.vector_newtons
        )

    return total


def acceleration(
    *,
    mass_kg: float,
    force_newtons: Vector3,
) -> Vector3:
    mass = _positive(
        mass_kg,
        "mass_kg",
    )

    return force_newtons.scale(
        1.0 / mass
    )


def momentum(
    *,
    mass_kg: float,
    velocity_mps: Vector3,
) -> Vector3:
    mass = _nonnegative(
        mass_kg,
        "mass_kg",
    )

    return velocity_mps.scale(mass)


def kinetic_energy(
    *,
    mass_kg: float,
    velocity_mps: Vector3,
) -> float:
    mass = _nonnegative(
        mass_kg,
        "mass_kg",
    )

    speed = velocity_mps.magnitude

    return 0.5 * mass * speed * speed


def gravitational_force(
    *,
    first: Body,
    second: Body,
    gravitational_constant: float = (
        6.67430e-11
    ),
) -> Force:
    first_mass = _nonnegative(
        first.mass_kg,
        "first.mass_kg",
    )
    second_mass = _nonnegative(
        second.mass_kg,
        "second.mass_kg",
    )

    first_position = position_vector(
        first.position
    )
    second_position = position_vector(
        second.position
    )

    displacement = (
        second_position.subtract(
            first_position
        )
    )

    separation = displacement.magnitude

    if separation <= EPSILON:
        raise PhysicsError(
            "gravitational force undefined "
            "at zero separation"
        )

    magnitude = (
        gravitational_constant
        * first_mass
        * second_mass
        / (separation * separation)
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
        source=second.body_id,
    )


def collision(
    first: Body,
    second: Body,
) -> CollisionAssessment:
    first_position = position_vector(
        first.position
    )
    second_position = position_vector(
        second.position
    )

    separation = (
        second_position
        .subtract(first_position)
        .magnitude
    )

    contact = (
        _nonnegative(
            first.radius_meters,
            "first.radius_meters",
        )
        + _nonnegative(
            second.radius_meters,
            "second.radius_meters",
        )
    )

    penetration = max(
        0.0,
        contact - separation,
    )

    return CollisionAssessment(
        colliding=(
            separation
            <= contact + EPSILON
        ),
        separation_meters=separation,
        contact_distance_meters=contact,
        penetration_meters=penetration,
    )


def propagate(
    body: Body,
    *,
    forces: Sequence[Force] = (),
    duration: float,
    duration_unit: str = "s",
) -> BodyState:
    seconds = convert(
        duration,
        from_unit=duration_unit,
        to_unit="s",
        dimension="duration",
    )

    if seconds < 0:
        raise PhysicsError(
            "duration must be nonnegative"
        )

    mass = _positive(
        body.mass_kg,
        "mass_kg",
    )

    force = net_force(forces)

    accel = acceleration(
        mass_kg=mass,
        force_newtons=force,
    )

    initial_velocity = (
        body.velocity_mps
    )

    final_velocity = (
        initial_velocity.add(
            accel.scale(seconds)
        )
    )

    initial_position = (
        position_vector(
            body.position
        )
    )

    displacement = (
        initial_velocity
        .scale(seconds)
        .add(
            accel.scale(
                0.5
                * seconds
                * seconds
            )
        )
    )

    final_position = (
        initial_position.add(
            displacement
        )
    )

    return BodyState(
        body_id=body.body_id,
        position=point_from_vector(
            final_position
        ),
        velocity_mps=final_velocity,
        acceleration_mps2=accel,
        momentum_kg_mps=momentum(
            mass_kg=mass,
            velocity_mps=final_velocity,
        ),
        kinetic_energy_joules=(
            kinetic_energy(
                mass_kg=mass,
                velocity_mps=(
                    final_velocity
                ),
            )
        ),
    )


def center_of_mass(
    bodies: Sequence[Body],
) -> Point3:
    if not bodies:
        raise PhysicsError(
            "center of mass requires bodies"
        )

    total_mass = 0.0
    weighted = Vector3(
        0.0,
        0.0,
        0.0,
    )

    for body in bodies:
        mass = _nonnegative(
            body.mass_kg,
            "mass_kg",
        )

        total_mass += mass

        weighted = weighted.add(
            position_vector(
                body.position
            ).scale(mass)
        )

    if total_mass <= EPSILON:
        raise PhysicsError(
            "total mass must be positive"
        )

    return point_from_vector(
        weighted.scale(
            1.0 / total_mass
        )
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
            momentum(
                mass_kg=body.mass_kg,
                velocity_mps=(
                    body.velocity_mps
                ),
            )
        )

    return total


def total_kinetic_energy(
    bodies: Sequence[Body],
) -> float:
    return sum(
        kinetic_energy(
            mass_kg=body.mass_kg,
            velocity_mps=(
                body.velocity_mps
            ),
        )
        for body in bodies
    )


def assess_system(
    bodies: Sequence[Body],
    *,
    collision_checks: bool = True,
) -> PhysicsProjection:
    violations: list[str] = []

    states = tuple(
        BodyState(
            body_id=body.body_id,
            position=body.position,
            velocity_mps=(
                body.velocity_mps
            ),
            acceleration_mps2=Vector3(
                0.0,
                0.0,
                0.0,
            ),
            momentum_kg_mps=momentum(
                mass_kg=body.mass_kg,
                velocity_mps=(
                    body.velocity_mps
                ),
            ),
            kinetic_energy_joules=(
                kinetic_energy(
                    mass_kg=body.mass_kg,
                    velocity_mps=(
                        body.velocity_mps
                    ),
                )
            ),
        )
        for body in bodies
    )

    collisions: list[
        dict[str, Any]
    ] = []

    if collision_checks:
        for index, first in enumerate(
            bodies
        ):
            for second in bodies[
                index + 1 :
            ]:
                result = collision(
                    first,
                    second,
                )

                if result.colliding:
                    collisions.append(
                        {
                            "first": (
                                first.body_id
                            ),
                            "second": (
                                second.body_id
                            ),
                            **asdict(result),
                        }
                    )

    return PhysicsProjection(
        valid=not violations,
        states=states,
        violations=tuple(violations),
        metrics={
            "body_count": len(bodies),
            "collision_count": len(
                collisions
            ),
            "collisions": collisions,
            "total_kinetic_energy_joules": (
                total_kinetic_energy(
                    bodies
                )
            ),
            "total_momentum_kg_mps": (
                asdict(
                    total_momentum(
                        bodies
                    )
                )
            ),
            "center_of_mass": (
                None
                if not bodies
                else asdict(
                    center_of_mass(
                        bodies
                    )
                )
            ),
        },
    )


def capabilities() -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "owner": OWNER,
        "primitive": "spacetime",
        "authority_effect": "none",
        "capabilities": [
            "vector_physics",
            "mass",
            "force",
            "net_force",
            "acceleration",
            "momentum",
            "kinetic_energy",
            "constant_acceleration_propagation",
            "three_dimensional_motion",
            "body_state",
            "body_radius",
            "collision_detection",
            "penetration_measurement",
            "center_of_mass",
            "system_momentum",
            "system_kinetic_energy",
            "newtonian_gravity",
            "physical_state_projection",
            "carbon_physics_support",
            "mobius_physical_consequence_support",
            "zero_quantitative_boundary",
        ],
    }
