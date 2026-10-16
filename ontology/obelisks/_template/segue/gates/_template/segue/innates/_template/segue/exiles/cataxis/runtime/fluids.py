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

SCHEMA = "savant://cataxis/fluids/1.0.0"


class FluidError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class Fluid:
    fluid_id: str
    density_kg_m3: float
    dynamic_viscosity_pa_s: float
    bulk_modulus_pa: float | None = None
    surface_tension_n_m: float | None = None
    vapor_pressure_pa: float | None = None
    specific_heat_j_kgk: float | None = None
    thermal_conductivity_w_mk: float | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class FlowState:
    velocity_mps: Vector3
    pressure_pa: float
    temperature_kelvin: float | None = None
    density_kg_m3: float | None = None


@dataclass(frozen=True, slots=True)
class FlowRegime:
    reynolds_number: float
    regime: str
    inertial_to_viscous_ratio: float


@dataclass(frozen=True, slots=True)
class PipeFlow:
    reynolds_number: float
    regime: str
    friction_factor: float | None
    pressure_drop_pa: float
    volumetric_flow_m3_s: float
    mass_flow_kg_s: float


@dataclass(frozen=True, slots=True)
class BuoyancyResult:
    displaced_volume_m3: float
    buoyant_force_newtons: float
    weight_newtons: float
    net_vertical_force_newtons: float
    floats: bool


@dataclass(frozen=True, slots=True)
class FluidProjection:
    fluid: Fluid
    state: FlowState | None = None
    regime: FlowRegime | None = None
    diagnostics: Mapping[str, Any] = field(default_factory=dict)
    owner: str = OWNER
    authority_effect: str = "none"

    def projection(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["schema"] = SCHEMA
        payload["generated_at"] = datetime.now(UTC).isoformat()
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


def _finite(value: Any, name: str) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise FluidError(
            f"{name} must be numeric"
        ) from exc

    if not math.isfinite(number):
        raise FluidError(
            f"{name} must be finite"
        )

    return number


def _positive(value: Any, name: str) -> float:
    number = _finite(value, name)

    if number <= 0:
        raise FluidError(
            f"{name} must be positive"
        )

    return number


def _nonnegative(value: Any, name: str) -> float:
    number = _finite(value, name)

    if number < 0:
        raise FluidError(
            f"{name} must be nonnegative"
        )

    return number


def validate(fluid: Fluid) -> None:
    _positive(
        fluid.density_kg_m3,
        "density_kg_m3",
    )
    _positive(
        fluid.dynamic_viscosity_pa_s,
        "dynamic_viscosity_pa_s",
    )

    for name in (
        "bulk_modulus_pa",
        "surface_tension_n_m",
        "specific_heat_j_kgk",
        "thermal_conductivity_w_mk",
    ):
        value = getattr(fluid, name)

        if value is not None:
            _positive(value, name)

    if fluid.vapor_pressure_pa is not None:
        _nonnegative(
            fluid.vapor_pressure_pa,
            "vapor_pressure_pa",
        )


def kinematic_viscosity(
    fluid: Fluid,
) -> float:
    validate(fluid)

    return (
        fluid.dynamic_viscosity_pa_s
        / fluid.density_kg_m3
    )


def reynolds_number(
    fluid: Fluid,
    *,
    velocity_mps: float,
    characteristic_length_meters: float,
) -> float:
    validate(fluid)

    speed = abs(
        _finite(
            velocity_mps,
            "velocity_mps",
        )
    )

    length = _positive(
        characteristic_length_meters,
        "characteristic_length_meters",
    )

    return (
        fluid.density_kg_m3
        * speed
        * length
        / fluid.dynamic_viscosity_pa_s
    )


def classify_flow(
    reynolds: float,
    *,
    laminar_limit: float = 2300.0,
    turbulent_limit: float = 4000.0,
) -> FlowRegime:
    value = _nonnegative(
        reynolds,
        "reynolds",
    )

    if value < laminar_limit:
        regime = "laminar"
    elif value < turbulent_limit:
        regime = "transitional"
    else:
        regime = "turbulent"

    return FlowRegime(
        reynolds_number=value,
        regime=regime,
        inertial_to_viscous_ratio=value,
    )


def dynamic_pressure(
    *,
    density_kg_m3: float,
    velocity_mps: float,
) -> float:
    density = _positive(
        density_kg_m3,
        "density_kg_m3",
    )

    velocity = _finite(
        velocity_mps,
        "velocity_mps",
    )

    return (
        0.5
        * density
        * velocity
        * velocity
    )


def hydrostatic_pressure(
    *,
    surface_pressure_pa: float,
    density_kg_m3: float,
    depth_meters: float,
    gravity_mps2: float = 9.80665,
) -> float:
    pressure = _finite(
        surface_pressure_pa,
        "surface_pressure_pa",
    )

    density = _positive(
        density_kg_m3,
        "density_kg_m3",
    )

    depth = _nonnegative(
        depth_meters,
        "depth_meters",
    )

    gravity = _nonnegative(
        gravity_mps2,
        "gravity_mps2",
    )

    return (
        pressure
        + density * gravity * depth
    )


def bernoulli_pressure(
    *,
    initial_pressure_pa: float,
    density_kg_m3: float,
    initial_velocity_mps: float,
    final_velocity_mps: float,
    initial_height_meters: float = 0.0,
    final_height_meters: float = 0.0,
    gravity_mps2: float = 9.80665,
    loss_pa: float = 0.0,
) -> float:
    density = _positive(
        density_kg_m3,
        "density_kg_m3",
    )

    pressure = _finite(
        initial_pressure_pa,
        "initial_pressure_pa",
    )

    v1 = _finite(
        initial_velocity_mps,
        "initial_velocity_mps",
    )

    v2 = _finite(
        final_velocity_mps,
        "final_velocity_mps",
    )

    h1 = _finite(
        initial_height_meters,
        "initial_height_meters",
    )

    h2 = _finite(
        final_height_meters,
        "final_height_meters",
    )

    gravity = _nonnegative(
        gravity_mps2,
        "gravity_mps2",
    )

    loss = _nonnegative(
        loss_pa,
        "loss_pa",
    )

    return (
        pressure
        + 0.5 * density * (v1 * v1 - v2 * v2)
        + density * gravity * (h1 - h2)
        - loss
    )


def volumetric_flow(
    *,
    area_m2: float,
    velocity_mps: float,
) -> float:
    area = _nonnegative(
        area_m2,
        "area_m2",
    )

    velocity = _finite(
        velocity_mps,
        "velocity_mps",
    )

    return area * velocity


def mass_flow(
    *,
    density_kg_m3: float,
    volumetric_flow_m3_s: float,
) -> float:
    density = _positive(
        density_kg_m3,
        "density_kg_m3",
    )

    flow = _finite(
        volumetric_flow_m3_s,
        "volumetric_flow_m3_s",
    )

    return density * flow


def continuity_velocity(
    *,
    initial_area_m2: float,
    initial_velocity_mps: float,
    final_area_m2: float,
) -> float:
    first_area = _positive(
        initial_area_m2,
        "initial_area_m2",
    )

    second_area = _positive(
        final_area_m2,
        "final_area_m2",
    )

    velocity = _finite(
        initial_velocity_mps,
        "initial_velocity_mps",
    )

    return (
        first_area
        * velocity
        / second_area
    )


def buoyancy(
    fluid: Fluid,
    *,
    displaced_volume_m3: float,
    body_mass_kg: float,
    gravity_mps2: float = 9.80665,
) -> BuoyancyResult:
    validate(fluid)

    volume = _nonnegative(
        displaced_volume_m3,
        "displaced_volume_m3",
    )

    body_mass = _nonnegative(
        body_mass_kg,
        "body_mass_kg",
    )

    gravity = _nonnegative(
        gravity_mps2,
        "gravity_mps2",
    )

    buoyant = (
        fluid.density_kg_m3
        * volume
        * gravity
    )

    weight = body_mass * gravity
    net = buoyant - weight

    return BuoyancyResult(
        displaced_volume_m3=volume,
        buoyant_force_newtons=buoyant,
        weight_newtons=weight,
        net_vertical_force_newtons=net,
        floats=net >= -EPSILON,
    )


def drag_force(
    *,
    density_kg_m3: float,
    velocity_mps: Vector3,
    drag_coefficient: float,
    reference_area_m2: float,
) -> Vector3:
    density = _positive(
        density_kg_m3,
        "density_kg_m3",
    )

    coefficient = _nonnegative(
        drag_coefficient,
        "drag_coefficient",
    )

    area = _nonnegative(
        reference_area_m2,
        "reference_area_m2",
    )

    speed = velocity_mps.magnitude

    if speed <= EPSILON:
        return Vector3(
            0.0,
            0.0,
            0.0,
        )

    magnitude = (
        0.5
        * density
        * speed
        * speed
        * coefficient
        * area
    )

    return (
        velocity_mps
        .normalized()
        .scale(-magnitude)
    )


def stokes_drag(
    fluid: Fluid,
    *,
    radius_meters: float,
    velocity_mps: Vector3,
) -> Vector3:
    validate(fluid)

    radius = _positive(
        radius_meters,
        "radius_meters",
    )

    coefficient = (
        6.0
        * math.pi
        * fluid.dynamic_viscosity_pa_s
        * radius
    )

    return velocity_mps.scale(
        -coefficient
    )


def mach_number(
    *,
    velocity_mps: float,
    sound_speed_mps: float,
) -> float:
    speed = abs(
        _finite(
            velocity_mps,
            "velocity_mps",
        )
    )

    sound = _positive(
        sound_speed_mps,
        "sound_speed_mps",
    )

    return speed / sound


def speed_of_sound_bulk(
    fluid: Fluid,
) -> float:
    validate(fluid)

    if fluid.bulk_modulus_pa is None:
        raise FluidError(
            "bulk_modulus_pa is required"
        )

    return math.sqrt(
        fluid.bulk_modulus_pa
        / fluid.density_kg_m3
    )


def cavitation_margin(
    fluid: Fluid,
    *,
    local_pressure_pa: float,
) -> dict[str, Any]:
    validate(fluid)

    if fluid.vapor_pressure_pa is None:
        raise FluidError(
            "vapor_pressure_pa is required"
        )

    local = _finite(
        local_pressure_pa,
        "local_pressure_pa",
    )

    margin = (
        local
        - fluid.vapor_pressure_pa
    )

    return {
        "cavitation_risk": (
            margin <= 0.0
        ),
        "local_pressure_pa": local,
        "vapor_pressure_pa": (
            fluid.vapor_pressure_pa
        ),
        "pressure_margin_pa": margin,
    }


def pipe_flow(
    fluid: Fluid,
    *,
    diameter_meters: float,
    length_meters: float,
    mean_velocity_mps: float,
    roughness_meters: float = 0.0,
) -> PipeFlow:
    validate(fluid)

    diameter = _positive(
        diameter_meters,
        "diameter_meters",
    )

    length = _nonnegative(
        length_meters,
        "length_meters",
    )

    velocity = abs(
        _finite(
            mean_velocity_mps,
            "mean_velocity_mps",
        )
    )

    roughness = _nonnegative(
        roughness_meters,
        "roughness_meters",
    )

    reynolds = reynolds_number(
        fluid,
        velocity_mps=velocity,
        characteristic_length_meters=diameter,
    )

    regime = classify_flow(
        reynolds
    )

    if reynolds <= EPSILON:
        factor = None
        pressure_drop = 0.0
    elif reynolds < 2300.0:
        factor = 64.0 / reynolds
        pressure_drop = (
            factor
            * (length / diameter)
            * dynamic_pressure(
                density_kg_m3=(
                    fluid.density_kg_m3
                ),
                velocity_mps=velocity,
            )
        )
    else:
        relative_roughness = (
            roughness / diameter
        )

        factor = 0.25 / (
            math.log10(
                relative_roughness / 3.7
                + 5.74
                / (
                    reynolds ** 0.9
                )
            )
            ** 2
        )

        pressure_drop = (
            factor
            * (length / diameter)
            * dynamic_pressure(
                density_kg_m3=(
                    fluid.density_kg_m3
                ),
                velocity_mps=velocity,
            )
        )

    area = (
        math.pi
        * diameter
        * diameter
        / 4.0
    )

    volume_flow = area * velocity

    return PipeFlow(
        reynolds_number=reynolds,
        regime=regime.regime,
        friction_factor=factor,
        pressure_drop_pa=pressure_drop,
        volumetric_flow_m3_s=volume_flow,
        mass_flow_kg_s=(
            fluid.density_kg_m3
            * volume_flow
        ),
    )


def capabilities() -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "owner": OWNER,
        "primitive": "physics",
        "authority_effect": "none",
        "capabilities": [
            "fluid_properties",
            "density",
            "dynamic_viscosity",
            "kinematic_viscosity",
            "reynolds_number",
            "flow_regime_classification",
            "laminar_flow",
            "transitional_flow",
            "turbulent_flow",
            "dynamic_pressure",
            "hydrostatic_pressure",
            "bernoulli_pressure",
            "volumetric_flow",
            "mass_flow",
            "continuity_equation",
            "buoyancy",
            "quadratic_drag",
            "stokes_drag",
            "mach_number",
            "bulk_sound_speed",
            "compressibility_support",
            "surface_tension_properties",
            "cavitation_detection",
            "darcy_weisbach_pressure_loss",
            "laminar_pipe_friction",
            "turbulent_pipe_friction_approximation",
            "pipe_flow",
            "thermal_fluid_properties",
            "carbon_fluid_environment_support",
            "mobius_fluid_consequence_support",
            "deterministic_fluid_projection",
        ],
    }
