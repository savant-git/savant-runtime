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
from spacetime import EPSILON, OWNER, Point3

SCHEMA = "savant://cataxis/fields/1.0.0"
COULOMB_CONSTANT = 8.9875517923e9


class FieldError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class ChargedBody:
    body: Body
    charge_coulombs: float = 0.0


@dataclass(frozen=True, slots=True)
class FieldSample:
    position: Point3
    gravitational_acceleration_mps2: Vector3
    electric_field_newtons_per_coulomb: Vector3
    gravitational_potential_joules_per_kg: float
    electric_potential_volts: float
    contributors: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class FieldProjection:
    samples: tuple[FieldSample, ...]
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
        raise FieldError(
            f"{name} must be numeric"
        ) from exc

    if not math.isfinite(number):
        raise FieldError(
            f"{name} must be finite"
        )

    return number


def _displacement(
    source: Point3,
    target: Point3,
) -> Vector3:
    return (
        position_vector(target)
        .subtract(position_vector(source))
    )


def gravitational_field(
    *,
    source: Body,
    at: Point3,
    gravitational_constant: float = G,
) -> Vector3:
    mass = _finite(
        source.mass_kg,
        "mass_kg",
    )

    if mass < 0:
        raise FieldError(
            "mass_kg must be nonnegative"
        )

    displacement = _displacement(
        at,
        source.position,
    )

    radius = displacement.magnitude

    if radius <= EPSILON:
        raise FieldError(
            "point-mass field singularity"
        )

    magnitude = (
        gravitational_constant
        * mass
        / (radius * radius)
    )

    return (
        displacement.normalized()
        .scale(magnitude)
    )


def gravitational_potential(
    *,
    source: Body,
    at: Point3,
    gravitational_constant: float = G,
) -> float:
    mass = _finite(
        source.mass_kg,
        "mass_kg",
    )

    radius = _displacement(
        source.position,
        at,
    ).magnitude

    if radius <= EPSILON:
        raise FieldError(
            "point-mass potential singularity"
        )

    return (
        -gravitational_constant
        * mass
        / radius
    )


def electric_field(
    *,
    source: ChargedBody,
    at: Point3,
    coulomb_constant: float = (
        COULOMB_CONSTANT
    ),
) -> Vector3:
    charge = _finite(
        source.charge_coulombs,
        "charge_coulombs",
    )

    displacement = _displacement(
        source.body.position,
        at,
    )

    radius = displacement.magnitude

    if radius <= EPSILON:
        raise FieldError(
            "point-charge field singularity"
        )

    magnitude = (
        coulomb_constant
        * charge
        / (radius * radius)
    )

    return (
        displacement.normalized()
        .scale(magnitude)
    )


def electric_potential(
    *,
    source: ChargedBody,
    at: Point3,
    coulomb_constant: float = (
        COULOMB_CONSTANT
    ),
) -> float:
    radius = _displacement(
        source.body.position,
        at,
    ).magnitude

    if radius <= EPSILON:
        raise FieldError(
            "point-charge potential singularity"
        )

    return (
        coulomb_constant
        * source.charge_coulombs
        / radius
    )


def superposed_gravity(
    *,
    sources: Sequence[Body],
    at: Point3,
) -> Vector3:
    total = Vector3(
        0.0,
        0.0,
        0.0,
    )

    for source in sources:
        total = total.add(
            gravitational_field(
                source=source,
                at=at,
            )
        )

    return total


def superposed_electric(
    *,
    sources: Sequence[ChargedBody],
    at: Point3,
) -> Vector3:
    total = Vector3(
        0.0,
        0.0,
        0.0,
    )

    for source in sources:
        total = total.add(
            electric_field(
                source=source,
                at=at,
            )
        )

    return total


def force_from_gravity(
    *,
    target: Body,
    sources: Sequence[Body],
) -> Force:
    field_vector = superposed_gravity(
        sources=sources,
        at=target.position,
    )

    return Force(
        force_id=(
            f"gravity-field->{target.body_id}"
        ),
        vector_newtons=field_vector.scale(
            target.mass_kg
        ),
        source="cataxis.gravity",
        metadata={
            "contributors": [
                source.body_id
                for source in sources
            ]
        },
    )


def force_from_electric_field(
    *,
    target: ChargedBody,
    sources: Sequence[ChargedBody],
) -> Force:
    field_vector = superposed_electric(
        sources=sources,
        at=target.body.position,
    )

    return Force(
        force_id=(
            "electric-field->"
            f"{target.body.body_id}"
        ),
        vector_newtons=field_vector.scale(
            target.charge_coulombs
        ),
        source="cataxis.electric",
        metadata={
            "contributors": [
                source.body.body_id
                for source in sources
            ]
        },
    )


def lorentz_force(
    *,
    charge_coulombs: float,
    velocity_mps: Vector3,
    electric_field_vector: Vector3,
    magnetic_field_tesla: Vector3,
) -> Vector3:
    charge = _finite(
        charge_coulombs,
        "charge_coulombs",
    )

    magnetic_component = Vector3(
        (
            velocity_mps.y
            * magnetic_field_tesla.z
            - velocity_mps.z
            * magnetic_field_tesla.y
        ),
        (
            velocity_mps.z
            * magnetic_field_tesla.x
            - velocity_mps.x
            * magnetic_field_tesla.z
        ),
        (
            velocity_mps.x
            * magnetic_field_tesla.y
            - velocity_mps.y
            * magnetic_field_tesla.x
        ),
    )

    return (
        electric_field_vector
        .add(magnetic_component)
        .scale(charge)
    )


def sample(
    *,
    at: Point3,
    masses: Sequence[Body] = (),
    charges: Sequence[ChargedBody] = (),
) -> FieldSample:
    gravity = superposed_gravity(
        sources=masses,
        at=at,
    )

    electric = superposed_electric(
        sources=charges,
        at=at,
    )

    gravitational_potential_total = sum(
        gravitational_potential(
            source=source,
            at=at,
        )
        for source in masses
    )

    electric_potential_total = sum(
        electric_potential(
            source=source,
            at=at,
        )
        for source in charges
    )

    contributors = tuple(
        dict.fromkeys(
            [
                source.body_id
                for source in masses
            ]
            + [
                source.body.body_id
                for source in charges
            ]
        )
    )

    return FieldSample(
        position=at,
        gravitational_acceleration_mps2=(
            gravity
        ),
        electric_field_newtons_per_coulomb=(
            electric
        ),
        gravitational_potential_joules_per_kg=(
            gravitational_potential_total
        ),
        electric_potential_volts=(
            electric_potential_total
        ),
        contributors=contributors,
    )


def project(
    *,
    points: Sequence[Point3],
    masses: Sequence[Body] = (),
    charges: Sequence[ChargedBody] = (),
    metadata: Mapping[str, Any] | None = None,
) -> FieldProjection:
    return FieldProjection(
        samples=tuple(
            sample(
                at=point,
                masses=masses,
                charges=charges,
            )
            for point in points
        ),
        model=(
            "classical_gravitational_"
            "electromagnetic_superposition"
        ),
        assumptions=(
            "newtonian_gravity",
            "electrostatic_point_charges",
            "linear_superposition",
            "euclidean_three_space",
            "finite_nonzero_source_separation",
        ),
        metadata=dict(
            metadata or {}
        ),
    )


def capabilities() -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "owner": OWNER,
        "primitive": "spacetime",
        "authority_effect": "none",
        "capabilities": [
            "gravitational_fields",
            "gravitational_potential",
            "electric_fields",
            "electric_potential",
            "point_mass_sources",
            "point_charge_sources",
            "field_superposition",
            "gravity_force_projection",
            "electrostatic_force_projection",
            "lorentz_force",
            "magnetic_force_component",
            "three_dimensional_fields",
            "field_sampling",
            "field_projection",
            "source_provenance",
            "singularity_rejection",
            "physical_constant_binding",
            "carbon_environment_fields",
            "mobius_field_consequence_support",
            "deterministic_field_receipts",
            "extensible_field_backend",
        ],
    }
