#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import math
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import Any, Mapping

from physics import Vector3
from spacetime import EPSILON, OWNER

SCHEMA = "savant://cataxis/materials/1.0.0"


class MaterialError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class Material:
    material_id: str
    density_kg_m3: float
    young_modulus_pa: float | None = None
    shear_modulus_pa: float | None = None
    bulk_modulus_pa: float | None = None
    poisson_ratio: float | None = None
    yield_strength_pa: float | None = None
    ultimate_strength_pa: float | None = None
    fracture_toughness_pa_sqrt_m: float | None = None
    restitution: float = 0.0
    static_friction: float = 0.0
    kinetic_friction: float = 0.0
    thermal_conductivity_w_mk: float | None = None
    specific_heat_j_kgk: float | None = None
    thermal_expansion_per_k: float | None = None
    melting_point_kelvin: float | None = None
    boiling_point_kelvin: float | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class StressState:
    normal_pa: Vector3
    shear_pa: Vector3

    @property
    def maximum_normal_pa(self) -> float:
        return max(
            abs(self.normal_pa.x),
            abs(self.normal_pa.y),
            abs(self.normal_pa.z),
        )

    @property
    def maximum_shear_pa(self) -> float:
        return max(
            abs(self.shear_pa.x),
            abs(self.shear_pa.y),
            abs(self.shear_pa.z),
        )


@dataclass(frozen=True, slots=True)
class MaterialResponse:
    material_id: str
    elastic: bool
    yielded: bool
    failed: bool
    strain: Vector3
    stress: StressState
    safety_factor: float | None
    failure_modes: tuple[str, ...]
    metrics: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ContactResponse:
    normal_force_newtons: float
    friction_force_newtons: float
    friction_regime: str
    coefficient: float
    dissipated_energy_joules: float


@dataclass(frozen=True, slots=True)
class ThermalResponse:
    final_temperature_kelvin: float
    temperature_change_kelvin: float
    thermal_strain: float | None
    phase: str
    absorbed_energy_joules: float


@dataclass(frozen=True, slots=True)
class MaterialProjection:
    material: Material
    response: MaterialResponse | None = None
    contact: ContactResponse | None = None
    thermal: ThermalResponse | None = None
    owner: str = OWNER
    authority_effect: str = "none"

    def projection(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["schema"] = SCHEMA
        payload["generated_at"] = datetime.now(
            UTC
        ).isoformat()
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
        raise MaterialError(
            f"{name} must be numeric"
        ) from exc

    if not math.isfinite(number):
        raise MaterialError(
            f"{name} must be finite"
        )

    return number


def _positive(
    value: Any,
    name: str,
) -> float:
    number = _finite(value, name)

    if number <= 0:
        raise MaterialError(
            f"{name} must be positive"
        )

    return number


def _nonnegative(
    value: Any,
    name: str,
) -> float:
    number = _finite(value, name)

    if number < 0:
        raise MaterialError(
            f"{name} must be nonnegative"
        )

    return number


def validate(
    material: Material,
) -> None:
    _positive(
        material.density_kg_m3,
        "density_kg_m3",
    )

    for name in (
        "young_modulus_pa",
        "shear_modulus_pa",
        "bulk_modulus_pa",
        "yield_strength_pa",
        "ultimate_strength_pa",
        "fracture_toughness_pa_sqrt_m",
        "thermal_conductivity_w_mk",
        "specific_heat_j_kgk",
        "melting_point_kelvin",
        "boiling_point_kelvin",
    ):
        value = getattr(material, name)

        if value is not None:
            _positive(value, name)

    if material.poisson_ratio is not None:
        ratio = _finite(
            material.poisson_ratio,
            "poisson_ratio",
        )

        if not (-1.0 < ratio < 0.5):
            raise MaterialError(
                "poisson_ratio must lie between -1 and 0.5"
            )

    for name in (
        "restitution",
        "static_friction",
        "kinetic_friction",
    ):
        _nonnegative(
            getattr(material, name),
            name,
        )

    if material.restitution > 1.0:
        raise MaterialError(
            "restitution cannot exceed 1"
        )

    if (
        material.melting_point_kelvin is not None
        and material.boiling_point_kelvin is not None
        and material.boiling_point_kelvin
        <= material.melting_point_kelvin
    ):
        raise MaterialError(
            "boiling point must exceed melting point"
        )


def mass(
    material: Material,
    *,
    volume_m3: float,
) -> float:
    validate(material)

    volume = _nonnegative(
        volume_m3,
        "volume_m3",
    )

    return (
        material.density_kg_m3
        * volume
    )


def linear_elastic_response(
    material: Material,
    *,
    strain: Vector3,
    shear_strain: Vector3 | None = None,
) -> MaterialResponse:
    validate(material)

    if material.young_modulus_pa is None:
        raise MaterialError(
            "young_modulus_pa is required"
        )

    shear = shear_strain or Vector3(
        0.0,
        0.0,
        0.0,
    )

    normal_stress = strain.scale(
        material.young_modulus_pa
    )

    if material.shear_modulus_pa is None:
        shear_stress = Vector3(
            0.0,
            0.0,
            0.0,
        )
    else:
        shear_stress = shear.scale(
            material.shear_modulus_pa
        )

    stress = StressState(
        normal_pa=normal_stress,
        shear_pa=shear_stress,
    )

    equivalent = math.sqrt(
        (
            normal_stress.x
            * normal_stress.x
            + normal_stress.y
            * normal_stress.y
            + normal_stress.z
            * normal_stress.z
        )
        + 3.0
        * (
            shear_stress.x
            * shear_stress.x
            + shear_stress.y
            * shear_stress.y
            + shear_stress.z
            * shear_stress.z
        )
    )

    yielded = (
        material.yield_strength_pa is not None
        and equivalent
        >= material.yield_strength_pa
    )

    failed = (
        material.ultimate_strength_pa is not None
        and equivalent
        >= material.ultimate_strength_pa
    )

    safety_factor = None

    if (
        material.yield_strength_pa is not None
        and equivalent > EPSILON
    ):
        safety_factor = (
            material.yield_strength_pa
            / equivalent
        )

    modes: list[str] = []

    if yielded:
        modes.append("yield")

    if failed:
        modes.append(
            "ultimate_strength"
        )

    return MaterialResponse(
        material_id=material.material_id,
        elastic=not yielded,
        yielded=yielded,
        failed=failed,
        strain=strain,
        stress=stress,
        safety_factor=safety_factor,
        failure_modes=tuple(modes),
        metrics={
            "equivalent_stress_pa": equivalent,
        },
    )


def fracture_assessment(
    material: Material,
    *,
    applied_stress_pa: float,
    crack_half_length_meters: float,
    geometry_factor: float = 1.0,
) -> dict[str, Any]:
    validate(material)

    if (
        material.fracture_toughness_pa_sqrt_m
        is None
    ):
        raise MaterialError(
            "fracture toughness is required"
        )

    stress = _nonnegative(
        applied_stress_pa,
        "applied_stress_pa",
    )

    crack = _positive(
        crack_half_length_meters,
        "crack_half_length_meters",
    )

    geometry = _positive(
        geometry_factor,
        "geometry_factor",
    )

    intensity = (
        geometry
        * stress
        * math.sqrt(math.pi * crack)
    )

    toughness = (
        material.fracture_toughness_pa_sqrt_m
    )

    return {
        "fracture": intensity >= toughness,
        "stress_intensity_pa_sqrt_m": intensity,
        "fracture_toughness_pa_sqrt_m": toughness,
        "margin_pa_sqrt_m": toughness - intensity,
    }


def friction(
    material: Material,
    *,
    normal_force_newtons: float,
    tangential_force_newtons: float,
    sliding: bool = False,
    sliding_distance_meters: float = 0.0,
) -> ContactResponse:
    validate(material)

    normal = _nonnegative(
        normal_force_newtons,
        "normal_force_newtons",
    )

    tangential = _nonnegative(
        tangential_force_newtons,
        "tangential_force_newtons",
    )

    static_limit = (
        material.static_friction
        * normal
    )

    if (
        not sliding
        and tangential
        <= static_limit + EPSILON
    ):
        actual = tangential
        regime = "static"
        coefficient = (
            material.static_friction
        )
    else:
        actual = (
            material.kinetic_friction
            * normal
        )
        regime = "kinetic"
        coefficient = (
            material.kinetic_friction
        )

    distance = _nonnegative(
        sliding_distance_meters,
        "sliding_distance_meters",
    )

    dissipated = (
        actual * distance
        if regime == "kinetic"
        else 0.0
    )

    return ContactResponse(
        normal_force_newtons=normal,
        friction_force_newtons=actual,
        friction_regime=regime,
        coefficient=coefficient,
        dissipated_energy_joules=dissipated,
    )


def thermal_response(
    material: Material,
    *,
    mass_kg: float,
    initial_temperature_kelvin: float,
    heat_joules: float,
) -> ThermalResponse:
    validate(material)

    if material.specific_heat_j_kgk is None:
        raise MaterialError(
            "specific_heat_j_kgk is required"
        )

    body_mass = _positive(
        mass_kg,
        "mass_kg",
    )

    initial = _nonnegative(
        initial_temperature_kelvin,
        "initial_temperature_kelvin",
    )

    heat = _finite(
        heat_joules,
        "heat_joules",
    )

    delta = (
        heat
        / (
            body_mass
            * material.specific_heat_j_kgk
        )
    )

    final = initial + delta

    if final < 0:
        raise MaterialError(
            "thermal transition crosses absolute zero"
        )

    thermal_strain = None

    if (
        material.thermal_expansion_per_k
        is not None
    ):
        thermal_strain = (
            material.thermal_expansion_per_k
            * delta
        )

    phase = "unspecified"

    if (
        material.boiling_point_kelvin
        is not None
        and final
        >= material.boiling_point_kelvin
    ):
        phase = "gas_or_above"
    elif (
        material.melting_point_kelvin
        is not None
        and final
        >= material.melting_point_kelvin
    ):
        phase = "liquid_or_above"
    elif (
        material.melting_point_kelvin
        is not None
    ):
        phase = "solid_or_below"

    return ThermalResponse(
        final_temperature_kelvin=final,
        temperature_change_kelvin=delta,
        thermal_strain=thermal_strain,
        phase=phase,
        absorbed_energy_joules=heat,
    )


def elastic_collision_velocity(
    *,
    first_mass_kg: float,
    second_mass_kg: float,
    first_velocity_mps: float,
    second_velocity_mps: float,
    restitution: float,
) -> tuple[float, float]:
    first_mass = _positive(
        first_mass_kg,
        "first_mass_kg",
    )

    second_mass = _positive(
        second_mass_kg,
        "second_mass_kg",
    )

    coefficient = _nonnegative(
        restitution,
        "restitution",
    )

    if coefficient > 1.0:
        raise MaterialError(
            "restitution cannot exceed 1"
        )

    first_velocity = _finite(
        first_velocity_mps,
        "first_velocity_mps",
    )

    second_velocity = _finite(
        second_velocity_mps,
        "second_velocity_mps",
    )

    total_mass = (
        first_mass + second_mass
    )

    first_final = (
        (
            first_mass
            - coefficient * second_mass
        )
        * first_velocity
        + (
            (1.0 + coefficient)
            * second_mass
            * second_velocity
        )
    ) / total_mass

    second_final = (
        (
            second_mass
            - coefficient * first_mass
        )
        * second_velocity
        + (
            (1.0 + coefficient)
            * first_mass
            * first_velocity
        )
    ) / total_mass

    return (
        first_final,
        second_final,
    )


def capabilities() -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "owner": OWNER,
        "primitive": "physics",
        "authority_effect": "none",
        "capabilities": [
            "material_properties",
            "density",
            "mass_from_volume",
            "young_modulus",
            "shear_modulus",
            "bulk_modulus",
            "poisson_ratio",
            "linear_elasticity",
            "normal_stress",
            "shear_stress",
            "strain",
            "yield_detection",
            "ultimate_failure_detection",
            "safety_factor",
            "fracture_toughness",
            "stress_intensity",
            "crack_failure_assessment",
            "static_friction",
            "kinetic_friction",
            "frictional_energy_dissipation",
            "coefficient_of_restitution",
            "one_dimensional_collision_response",
            "thermal_capacity",
            "thermal_expansion",
            "phase_thresholds",
            "absolute_zero_guard",
            "material_validation",
            "material_response_receipts",
            "carbon_material_simulation",
            "mobius_material_consequence_support",
        ],
    }
