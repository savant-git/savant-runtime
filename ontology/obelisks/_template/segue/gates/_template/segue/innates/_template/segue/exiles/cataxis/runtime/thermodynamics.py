#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import math
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import Any, Mapping, Sequence

from spacetime import EPSILON, OWNER

SCHEMA = "savant://cataxis/thermodynamics/1.0.0"
BOLTZMANN_CONSTANT_J_K = 1.380649e-23
GAS_CONSTANT_J_MOL_K = 8.31446261815324
STEFAN_BOLTZMANN_W_M2_K4 = 5.670374419e-8


class ThermodynamicsError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class ThermalBody:
    body_id: str
    mass_kg: float
    temperature_kelvin: float
    specific_heat_j_kgk: float
    entropy_j_k: float = 0.0
    metadata: Mapping[str, Any] = field(
        default_factory=dict
    )


@dataclass(frozen=True, slots=True)
class HeatTransfer:
    source_id: str
    target_id: str
    energy_joules: float
    duration_seconds: float
    mechanism: str
    entropy_generation_j_k: float


@dataclass(frozen=True, slots=True)
class ThermalEquilibrium:
    final_temperature_kelvin: float
    energy_before_joules: float
    energy_after_joules: float
    energy_drift_joules: float
    entropy_change_j_k: float
    bodies: tuple[ThermalBody, ...]


@dataclass(frozen=True, slots=True)
class IdealGasState:
    pressure_pa: float
    volume_m3: float
    amount_moles: float
    temperature_kelvin: float


@dataclass(frozen=True, slots=True)
class ThermodynamicProjection:
    accepted: bool
    bodies: tuple[ThermalBody, ...]
    transfers: tuple[HeatTransfer, ...] = ()
    diagnostics: Mapping[str, Any] = field(
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
        raise ThermodynamicsError(
            f"{name} must be numeric"
        ) from exc

    if not math.isfinite(number):
        raise ThermodynamicsError(
            f"{name} must be finite"
        )

    return number


def _positive(
    value: Any,
    name: str,
) -> float:
    number = _finite(value, name)

    if number <= 0:
        raise ThermodynamicsError(
            f"{name} must be positive"
        )

    return number


def _nonnegative(
    value: Any,
    name: str,
) -> float:
    number = _finite(value, name)

    if number < 0:
        raise ThermodynamicsError(
            f"{name} must be nonnegative"
        )

    return number


def validate_body(
    body: ThermalBody,
) -> None:
    _positive(
        body.mass_kg,
        "mass_kg",
    )

    _nonnegative(
        body.temperature_kelvin,
        "temperature_kelvin",
    )

    _positive(
        body.specific_heat_j_kgk,
        "specific_heat_j_kgk",
    )

    _finite(
        body.entropy_j_k,
        "entropy_j_k",
    )


def thermal_capacity_j_k(
    body: ThermalBody,
) -> float:
    validate_body(body)

    return (
        body.mass_kg
        * body.specific_heat_j_kgk
    )


def sensible_energy_joules(
    body: ThermalBody,
    *,
    reference_temperature_kelvin: float = 0.0,
) -> float:
    validate_body(body)

    reference = _nonnegative(
        reference_temperature_kelvin,
        "reference_temperature_kelvin",
    )

    return (
        thermal_capacity_j_k(body)
        * (
            body.temperature_kelvin
            - reference
        )
    )


def add_heat(
    body: ThermalBody,
    *,
    energy_joules: float,
) -> ThermalBody:
    validate_body(body)

    energy = _finite(
        energy_joules,
        "energy_joules",
    )

    delta_temperature = (
        energy
        / thermal_capacity_j_k(body)
    )

    final_temperature = (
        body.temperature_kelvin
        + delta_temperature
    )

    if final_temperature < -EPSILON:
        raise ThermodynamicsError(
            "heat transfer crosses absolute zero"
        )

    final_temperature = max(
        0.0,
        final_temperature,
    )

    entropy_delta = 0.0

    if (
        abs(energy) > EPSILON
        and body.temperature_kelvin > EPSILON
        and final_temperature > EPSILON
    ):
        entropy_delta = (
            thermal_capacity_j_k(body)
            * math.log(
                final_temperature
                / body.temperature_kelvin
            )
        )

    return ThermalBody(
        body_id=body.body_id,
        mass_kg=body.mass_kg,
        temperature_kelvin=final_temperature,
        specific_heat_j_kgk=(
            body.specific_heat_j_kgk
        ),
        entropy_j_k=(
            body.entropy_j_k
            + entropy_delta
        ),
        metadata=body.metadata,
    )


def equilibrium_temperature(
    bodies: Sequence[ThermalBody],
) -> float:
    if not bodies:
        raise ThermodynamicsError(
            "equilibrium requires bodies"
        )

    numerator = 0.0
    denominator = 0.0

    for body in bodies:
        capacity = thermal_capacity_j_k(
            body
        )

        numerator += (
            capacity
            * body.temperature_kelvin
        )
        denominator += capacity

    if denominator <= EPSILON:
        raise ThermodynamicsError(
            "thermal capacity is zero"
        )

    return numerator / denominator


def equilibrate(
    bodies: Sequence[ThermalBody],
) -> ThermalEquilibrium:
    source = tuple(bodies)

    if not source:
        raise ThermodynamicsError(
            "equilibrium requires bodies"
        )

    final_temperature = (
        equilibrium_temperature(source)
    )

    before_energy = sum(
        sensible_energy_joules(body)
        for body in source
    )

    before_entropy = sum(
        body.entropy_j_k
        for body in source
    )

    evolved: list[ThermalBody] = []

    for body in source:
        evolved.append(
            add_heat(
                body,
                energy_joules=(
                    thermal_capacity_j_k(body)
                    * (
                        final_temperature
                        - body.temperature_kelvin
                    )
                ),
            )
        )

    after = tuple(evolved)

    after_energy = sum(
        sensible_energy_joules(body)
        for body in after
    )

    after_entropy = sum(
        body.entropy_j_k
        for body in after
    )

    return ThermalEquilibrium(
        final_temperature_kelvin=(
            final_temperature
        ),
        energy_before_joules=before_energy,
        energy_after_joules=after_energy,
        energy_drift_joules=(
            after_energy - before_energy
        ),
        entropy_change_j_k=(
            after_entropy - before_entropy
        ),
        bodies=after,
    )


def conduction_rate_watts(
    *,
    thermal_conductivity_w_mk: float,
    area_m2: float,
    hot_temperature_kelvin: float,
    cold_temperature_kelvin: float,
    thickness_meters: float,
) -> float:
    conductivity = _positive(
        thermal_conductivity_w_mk,
        "thermal_conductivity_w_mk",
    )

    area = _nonnegative(
        area_m2,
        "area_m2",
    )

    hot = _nonnegative(
        hot_temperature_kelvin,
        "hot_temperature_kelvin",
    )

    cold = _nonnegative(
        cold_temperature_kelvin,
        "cold_temperature_kelvin",
    )

    thickness = _positive(
        thickness_meters,
        "thickness_meters",
    )

    return (
        conductivity
        * area
        * (hot - cold)
        / thickness
    )


def convection_rate_watts(
    *,
    heat_transfer_coefficient_w_m2k: float,
    area_m2: float,
    surface_temperature_kelvin: float,
    fluid_temperature_kelvin: float,
) -> float:
    coefficient = _nonnegative(
        heat_transfer_coefficient_w_m2k,
        "heat_transfer_coefficient_w_m2k",
    )

    area = _nonnegative(
        area_m2,
        "area_m2",
    )

    surface = _nonnegative(
        surface_temperature_kelvin,
        "surface_temperature_kelvin",
    )

    fluid = _nonnegative(
        fluid_temperature_kelvin,
        "fluid_temperature_kelvin",
    )

    return (
        coefficient
        * area
        * (surface - fluid)
    )


def radiation_rate_watts(
    *,
    area_m2: float,
    temperature_kelvin: float,
    environment_temperature_kelvin: float,
    emissivity: float = 1.0,
) -> float:
    area = _nonnegative(
        area_m2,
        "area_m2",
    )

    temperature = _nonnegative(
        temperature_kelvin,
        "temperature_kelvin",
    )

    environment = _nonnegative(
        environment_temperature_kelvin,
        "environment_temperature_kelvin",
    )

    emission = _nonnegative(
        emissivity,
        "emissivity",
    )

    if emission > 1.0:
        raise ThermodynamicsError(
            "emissivity cannot exceed 1"
        )

    return (
        emission
        * STEFAN_BOLTZMANN_W_M2_K4
        * area
        * (
            temperature ** 4
            - environment ** 4
        )
    )


def ideal_gas_pressure(
    *,
    amount_moles: float,
    temperature_kelvin: float,
    volume_m3: float,
) -> float:
    amount = _nonnegative(
        amount_moles,
        "amount_moles",
    )

    temperature = _nonnegative(
        temperature_kelvin,
        "temperature_kelvin",
    )

    volume = _positive(
        volume_m3,
        "volume_m3",
    )

    return (
        amount
        * GAS_CONSTANT_J_MOL_K
        * temperature
        / volume
    )


def ideal_gas_state(
    *,
    amount_moles: float,
    temperature_kelvin: float,
    volume_m3: float,
) -> IdealGasState:
    return IdealGasState(
        pressure_pa=ideal_gas_pressure(
            amount_moles=amount_moles,
            temperature_kelvin=(
                temperature_kelvin
            ),
            volume_m3=volume_m3,
        ),
        volume_m3=volume_m3,
        amount_moles=amount_moles,
        temperature_kelvin=(
            temperature_kelvin
        ),
    )


def reversible_isothermal_work_joules(
    *,
    amount_moles: float,
    temperature_kelvin: float,
    initial_volume_m3: float,
    final_volume_m3: float,
) -> float:
    amount = _nonnegative(
        amount_moles,
        "amount_moles",
    )

    temperature = _nonnegative(
        temperature_kelvin,
        "temperature_kelvin",
    )

    initial = _positive(
        initial_volume_m3,
        "initial_volume_m3",
    )

    final = _positive(
        final_volume_m3,
        "final_volume_m3",
    )

    return (
        amount
        * GAS_CONSTANT_J_MOL_K
        * temperature
        * math.log(final / initial)
    )


def carnot_efficiency(
    *,
    hot_temperature_kelvin: float,
    cold_temperature_kelvin: float,
) -> float:
    hot = _positive(
        hot_temperature_kelvin,
        "hot_temperature_kelvin",
    )

    cold = _nonnegative(
        cold_temperature_kelvin,
        "cold_temperature_kelvin",
    )

    if cold > hot:
        raise ThermodynamicsError(
            "cold reservoir exceeds hot reservoir"
        )

    return 1.0 - cold / hot


def entropy_transfer_j_k(
    *,
    reversible_heat_joules: float,
    temperature_kelvin: float,
) -> float:
    heat = _finite(
        reversible_heat_joules,
        "reversible_heat_joules",
    )

    temperature = _positive(
        temperature_kelvin,
        "temperature_kelvin",
    )

    return heat / temperature


def entropy_generation_two_reservoirs(
    *,
    heat_joules: float,
    hot_temperature_kelvin: float,
    cold_temperature_kelvin: float,
) -> float:
    heat = _nonnegative(
        heat_joules,
        "heat_joules",
    )

    hot = _positive(
        hot_temperature_kelvin,
        "hot_temperature_kelvin",
    )

    cold = _positive(
        cold_temperature_kelvin,
        "cold_temperature_kelvin",
    )

    if cold > hot:
        raise ThermodynamicsError(
            "cold reservoir exceeds hot reservoir"
        )

    return (
        heat / cold
        - heat / hot
    )


def first_law_internal_energy_change(
    *,
    heat_into_system_joules: float,
    work_done_by_system_joules: float,
) -> float:
    return (
        _finite(
            heat_into_system_joules,
            "heat_into_system_joules",
        )
        - _finite(
            work_done_by_system_joules,
            "work_done_by_system_joules",
        )
    )


def second_law_admissible(
    *,
    total_entropy_change_j_k: float,
    tolerance_j_k: float = 1e-12,
) -> bool:
    change = _finite(
        total_entropy_change_j_k,
        "total_entropy_change_j_k",
    )

    tolerance = _nonnegative(
        tolerance_j_k,
        "tolerance_j_k",
    )

    return change >= -tolerance


def capabilities() -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "owner": OWNER,
        "primitive": "physics",
        "authority_effect": "none",
        "capabilities": [
            "thermal_bodies",
            "absolute_temperature",
            "thermal_capacity",
            "sensible_energy",
            "heat_application",
            "thermal_equilibrium",
            "energy_conservation_projection",
            "entropy_tracking",
            "entropy_generation",
            "second_law_admissibility",
            "first_law_energy_balance",
            "fourier_conduction",
            "newtonian_convection",
            "stefan_boltzmann_radiation",
            "ideal_gas_state",
            "ideal_gas_pressure",
            "isothermal_work",
            "carnot_efficiency",
            "reversible_entropy_transfer",
            "absolute_zero_guard",
            "temperature_gradient_direction",
            "equilibrium_projection",
            "thermal_receipts",
            "carbon_thermal_environment_support",
            "mobius_thermodynamic_consequence_support",
            "deterministic_thermal_projection",
        ],
    }
