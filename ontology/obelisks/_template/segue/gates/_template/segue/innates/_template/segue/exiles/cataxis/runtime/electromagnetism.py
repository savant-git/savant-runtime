#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import math
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import Any, Mapping, Sequence

from physics import Vector3
from spacetime import EPSILON, OWNER

SCHEMA = "savant://cataxis/electromagnetism/1.0.0"

COULOMB_CONSTANT = 8.9875517923e9
VACUUM_PERMITTIVITY_F_M = 8.8541878128e-12
VACUUM_PERMEABILITY_H_M = 1.25663706212e-6
ELEMENTARY_CHARGE_C = 1.602176634e-19
C = 299_792_458.0


class ElectromagnetismError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class Charge:
    charge_id: str
    charge_coulombs: float
    position_meters: Vector3
    velocity_mps: Vector3 = field(
        default_factory=lambda: Vector3(
            0.0,
            0.0,
            0.0,
        )
    )
    metadata: Mapping[str, Any] = field(
        default_factory=dict
    )


@dataclass(frozen=True, slots=True)
class FieldSample:
    position_meters: Vector3
    electric_field_n_c: Vector3
    electric_potential_volts: float
    contributors: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ElectromagneticForce:
    electric_newtons: Vector3
    magnetic_newtons: Vector3
    total_newtons: Vector3


@dataclass(frozen=True, slots=True)
class ElectromagneticProjection:
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
        raise ElectromagnetismError(
            f"{name} must be numeric"
        ) from exc

    if not math.isfinite(number):
        raise ElectromagnetismError(
            f"{name} must be finite"
        )

    return number


def _positive(
    value: Any,
    name: str,
) -> float:
    number = _finite(value, name)

    if number <= 0:
        raise ElectromagnetismError(
            f"{name} must be positive"
        )

    return number


def dot(
    first: Vector3,
    second: Vector3,
) -> float:
    return (
        first.x * second.x
        + first.y * second.y
        + first.z * second.z
    )


def cross(
    first: Vector3,
    second: Vector3,
) -> Vector3:
    return Vector3(
        first.y * second.z
        - first.z * second.y,
        first.z * second.x
        - first.x * second.z,
        first.x * second.y
        - first.y * second.x,
    )


def electric_field_from_charge(
    source: Charge,
    *,
    at: Vector3,
) -> Vector3:
    displacement = at.subtract(
        source.position_meters
    )

    distance = displacement.magnitude

    if distance <= EPSILON:
        raise ElectromagnetismError(
            "point-charge field singularity"
        )

    magnitude = (
        COULOMB_CONSTANT
        * source.charge_coulombs
        / (distance * distance)
    )

    return (
        displacement.normalized()
        .scale(magnitude)
    )


def electric_field(
    sources: Sequence[Charge],
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
            electric_field_from_charge(
                source,
                at=at,
            )
        )

    return total


def electric_potential_from_charge(
    source: Charge,
    *,
    at: Vector3,
) -> float:
    distance = (
        at.subtract(
            source.position_meters
        ).magnitude
    )

    if distance <= EPSILON:
        raise ElectromagnetismError(
            "point-charge potential singularity"
        )

    return (
        COULOMB_CONSTANT
        * source.charge_coulombs
        / distance
    )


def electric_potential(
    sources: Sequence[Charge],
    *,
    at: Vector3,
) -> float:
    return sum(
        electric_potential_from_charge(
            source,
            at=at,
        )
        for source in sources
    )


def coulomb_force(
    first: Charge,
    second: Charge,
) -> Vector3:
    displacement = (
        first.position_meters
        .subtract(
            second.position_meters
        )
    )

    distance = displacement.magnitude

    if distance <= EPSILON:
        raise ElectromagnetismError(
            "coincident point charges"
        )

    magnitude = (
        COULOMB_CONSTANT
        * first.charge_coulombs
        * second.charge_coulombs
        / (distance * distance)
    )

    return (
        displacement.normalized()
        .scale(magnitude)
    )


def magnetic_force(
    *,
    charge_coulombs: float,
    velocity_mps: Vector3,
    magnetic_field_tesla: Vector3,
) -> Vector3:
    charge = _finite(
        charge_coulombs,
        "charge_coulombs",
    )

    return cross(
        velocity_mps,
        magnetic_field_tesla,
    ).scale(charge)


def lorentz_force(
    *,
    charge_coulombs: float,
    velocity_mps: Vector3,
    electric_field_n_c: Vector3,
    magnetic_field_tesla: Vector3,
) -> ElectromagneticForce:
    charge = _finite(
        charge_coulombs,
        "charge_coulombs",
    )

    electric = (
        electric_field_n_c
        .scale(charge)
    )

    magnetic = magnetic_force(
        charge_coulombs=charge,
        velocity_mps=velocity_mps,
        magnetic_field_tesla=(
            magnetic_field_tesla
        ),
    )

    return ElectromagneticForce(
        electric_newtons=electric,
        magnetic_newtons=magnetic,
        total_newtons=(
            electric.add(magnetic)
        ),
    )


def magnetic_field_straight_wire(
    *,
    current_amperes: float,
    radial_distance_meters: float,
) -> float:
    current = _finite(
        current_amperes,
        "current_amperes",
    )

    radius = _positive(
        radial_distance_meters,
        "radial_distance_meters",
    )

    return (
        VACUUM_PERMEABILITY_H_M
        * current
        / (2.0 * math.pi * radius)
    )


def magnetic_field_loop_center(
    *,
    current_amperes: float,
    radius_meters: float,
    turns: int = 1,
) -> float:
    current = _finite(
        current_amperes,
        "current_amperes",
    )

    radius = _positive(
        radius_meters,
        "radius_meters",
    )

    if turns < 1:
        raise ElectromagnetismError(
            "turns must be positive"
        )

    return (
        VACUUM_PERMEABILITY_H_M
        * turns
        * current
        / (2.0 * radius)
    )


def capacitor_parallel_plate(
    *,
    area_m2: float,
    separation_meters: float,
    relative_permittivity: float = 1.0,
) -> float:
    area = _positive(
        area_m2,
        "area_m2",
    )

    separation = _positive(
        separation_meters,
        "separation_meters",
    )

    relative = _positive(
        relative_permittivity,
        "relative_permittivity",
    )

    return (
        VACUUM_PERMITTIVITY_F_M
        * relative
        * area
        / separation
    )


def capacitor_energy(
    *,
    capacitance_farads: float,
    voltage_volts: float,
) -> float:
    capacitance = _positive(
        capacitance_farads,
        "capacitance_farads",
    )

    voltage = _finite(
        voltage_volts,
        "voltage_volts",
    )

    return (
        0.5
        * capacitance
        * voltage
        * voltage
    )


def resistor_power(
    *,
    current_amperes: float,
    resistance_ohms: float,
) -> float:
    current = _finite(
        current_amperes,
        "current_amperes",
    )

    resistance = _positive(
        resistance_ohms,
        "resistance_ohms",
    )

    return (
        current
        * current
        * resistance
    )


def ohms_law_voltage(
    *,
    current_amperes: float,
    resistance_ohms: float,
) -> float:
    return (
        _finite(
            current_amperes,
            "current_amperes",
        )
        * _positive(
            resistance_ohms,
            "resistance_ohms",
        )
    )


def induced_emf(
    *,
    initial_flux_webers: float,
    final_flux_webers: float,
    duration_seconds: float,
    turns: int = 1,
) -> float:
    initial = _finite(
        initial_flux_webers,
        "initial_flux_webers",
    )

    final = _finite(
        final_flux_webers,
        "final_flux_webers",
    )

    duration = _positive(
        duration_seconds,
        "duration_seconds",
    )

    if turns < 1:
        raise ElectromagnetismError(
            "turns must be positive"
        )

    return (
        -float(turns)
        * (final - initial)
        / duration
    )


def electromagnetic_energy_density(
    *,
    electric_field_v_m: Vector3,
    magnetic_field_tesla: Vector3,
) -> float:
    electric_squared = dot(
        electric_field_v_m,
        electric_field_v_m,
    )

    magnetic_squared = dot(
        magnetic_field_tesla,
        magnetic_field_tesla,
    )

    return (
        0.5
        * VACUUM_PERMITTIVITY_F_M
        * electric_squared
        + magnetic_squared
        / (
            2.0
            * VACUUM_PERMEABILITY_H_M
        )
    )


def poynting_vector(
    *,
    electric_field_v_m: Vector3,
    magnetic_field_tesla: Vector3,
) -> Vector3:
    return cross(
        electric_field_v_m,
        magnetic_field_tesla,
    ).scale(
        1.0
        / VACUUM_PERMEABILITY_H_M
    )


def electromagnetic_wave_relation(
    *,
    electric_field_amplitude_v_m: float,
) -> dict[str, float]:
    electric = abs(
        _finite(
            electric_field_amplitude_v_m,
            "electric_field_amplitude_v_m",
        )
    )

    magnetic = electric / C

    intensity = (
        0.5
        * C
        * VACUUM_PERMITTIVITY_F_M
        * electric
        * electric
    )

    return {
        "electric_field_amplitude_v_m": electric,
        "magnetic_field_amplitude_t": magnetic,
        "intensity_w_m2": intensity,
        "propagation_speed_mps": C,
    }


def sample(
    sources: Sequence[Charge],
    *,
    at: Vector3,
) -> FieldSample:
    return FieldSample(
        position_meters=at,
        electric_field_n_c=(
            electric_field(
                sources,
                at=at,
            )
        ),
        electric_potential_volts=(
            electric_potential(
                sources,
                at=at,
            )
        ),
        contributors=tuple(
            source.charge_id
            for source in sources
        ),
    )


def project(
    *,
    sources: Sequence[Charge],
    points: Sequence[Vector3],
    metadata: Mapping[str, Any] | None = None,
) -> ElectromagneticProjection:
    return ElectromagneticProjection(
        samples=tuple(
            sample(
                sources,
                at=point,
            )
            for point in points
        ),
        model=(
            "classical_electromagnetism"
        ),
        assumptions=(
            "classical_fields",
            "point_charge_sources",
            "linear_field_superposition",
            "vacuum_constants_by_default",
            "finite_signal_speed_c",
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
            "electric_charge",
            "coulomb_force",
            "electric_field",
            "electric_potential",
            "electric_superposition",
            "magnetic_force",
            "lorentz_force",
            "straight_wire_magnetic_field",
            "current_loop_magnetic_field",
            "parallel_plate_capacitance",
            "capacitor_energy",
            "ohms_law",
            "resistive_power",
            "faraday_induction",
            "lenz_direction",
            "electromagnetic_energy_density",
            "poynting_vector",
            "electromagnetic_wave_relation",
            "vacuum_permittivity",
            "vacuum_permeability",
            "finite_light_speed",
            "field_sampling",
            "field_projection",
            "carbon_electromagnetic_simulation",
            "mobius_signal_continuity_support",
            "deterministic_field_receipts",
        ],
    }
