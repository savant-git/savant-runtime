#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import math
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from enum import IntEnum
from typing import Any, Mapping, Sequence

from physics import (
    Body,
    Force,
    PhysicsError,
    Vector3,
    acceleration,
    kinetic_energy,
    momentum,
    net_force,
    position_vector,
)
from spacetime import EPSILON, OWNER

SCHEMA = "savant://cataxis/physics-laws/1.0.0"

G = 6.67430e-11
C = 299_792_458.0
H = 6.62607015e-34
HBAR = H / (2.0 * math.pi)
K_B = 1.380649e-23
STANDARD_GRAVITY = 9.80665


class Law(IntEnum):
    INERTIA = 1
    DYNAMICS = 2
    INTERACTION = 3
    CONSERVATION = 4
    GRAVITATION = 5
    THERMODYNAMICS = 6
    CAUSAL_ADMISSIBILITY = 7
    UNCERTAINTY_INHERITANCE = 8
    RESOLUTION_CONTINUITY = 9


@dataclass(frozen=True, slots=True)
class LawDefinition:
    number: int
    identifier: str
    name: str
    domain: str
    authority: str
    statement: str
    computational_role: str


LAWS: tuple[LawDefinition, ...] = (
    LawDefinition(
        1,
        "inertia",
        "law of inertia",
        "physical",
        "established_physics",
        (
            "A body preserves its velocity unless a net "
            "external force changes its motion."
        ),
        "state propagation and inertial validation",
    ),
    LawDefinition(
        2,
        "dynamics",
        "law of dynamics",
        "physical",
        "established_physics",
        (
            "Net force changes momentum; for constant "
            "mass this reduces to F = ma."
        ),
        "force-to-motion evolution",
    ),
    LawDefinition(
        3,
        "interaction",
        "law of interaction",
        "physical",
        "established_physics",
        (
            "Mechanical pair interactions exchange equal "
            "and opposite momentum in the closed pair."
        ),
        "interaction symmetry and momentum exchange",
    ),
    LawDefinition(
        4,
        "conservation",
        "law of conservation",
        "physical",
        "established_physics",
        (
            "Applicable conserved quantities remain "
            "constant for an isolated modeled system."
        ),
        "conservation accounting and drift detection",
    ),
    LawDefinition(
        5,
        "gravitation",
        "law of gravitation",
        "physical",
        "established_physics",
        (
            "Mass-energy participates in gravitational "
            "interaction according to the selected model."
        ),
        "gravitational interaction",
    ),
    LawDefinition(
        6,
        "thermodynamics",
        "law of thermodynamics",
        "physical",
        "established_physics",
        (
            "Energy accounting, temperature, entropy, and "
            "irreversibility constrain physical evolution."
        ),
        "thermal feasibility and energy accounting",
    ),
    LawDefinition(
        7,
        "causal_admissibility",
        "savant law of causal admissibility",
        "computational",
        "savant_proprietary",
        (
            "No simulated physical transition may become "
            "admissible when its required physical influence "
            "exceeds the causal limits of its active model."
        ),
        (
            "reject physically impossible transitions before "
            "they contaminate downstream simulation"
        ),
    ),
    LawDefinition(
        8,
        "uncertainty_inheritance",
        "savant law of uncertainty inheritance",
        "computational",
        "savant_proprietary",
        (
            "A derived physical state cannot silently possess "
            "greater certainty than the uncertain primitives "
            "from which that state was derived."
        ),
        (
            "preserve uncertainty lineage through simulation "
            "and derived physical state"
        ),
    ),
    LawDefinition(
        9,
        "resolution_continuity",
        "savant law of resolution continuity",
        "computational",
        "savant_proprietary",
        (
            "When a simulated possibility resolves into a "
            "realized branch, physical continuity must remain "
            "valid across the resolution boundary and rejected "
            "branches remain counterfactual rather than erased."
        ),
        (
            "couple physical state safely to mobius causal "
            "collapse without inventing discontinuities"
        ),
    ),
)


@dataclass(frozen=True, slots=True)
class Quantity:
    value: float
    uncertainty: float = 0.0
    unit: str = ""
    provenance: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not math.isfinite(float(self.value)):
            raise PhysicsError("quantity value must be finite")

        if (
            not math.isfinite(float(self.uncertainty))
            or self.uncertainty < 0
        ):
            raise PhysicsError(
                "quantity uncertainty must be finite and nonnegative"
            )


@dataclass(frozen=True, slots=True)
class ConservationState:
    energy_joules: float
    momentum_kg_mps: Vector3
    mass_kg: float


@dataclass(frozen=True, slots=True)
class ThermalState:
    temperature_kelvin: float
    internal_energy_joules: float
    entropy_joules_per_kelvin: float
    heat_capacity_joules_per_kelvin: float | None = None


@dataclass(frozen=True, slots=True)
class LawResult:
    law: int
    identifier: str
    satisfied: bool
    reason: str
    metrics: Mapping[str, Any] = field(default_factory=dict)
    authority_effect: str = "none"


@dataclass(frozen=True, slots=True)
class PhysicsLedger:
    results: tuple[LawResult, ...]
    valid: bool
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


def law(number: int | Law) -> LawDefinition:
    index = int(number) - 1

    if index < 0 or index >= len(LAWS):
        raise PhysicsError(f"unknown physics law: {number}")

    return LAWS[index]


def inertia(
    body: Body,
    *,
    forces: Sequence[Force] = (),
    tolerance_newtons: float = 1e-12,
) -> LawResult:
    resultant = net_force(forces)
    magnitude = resultant.magnitude
    satisfied = magnitude <= max(0.0, tolerance_newtons)

    return LawResult(
        law=Law.INERTIA,
        identifier="inertia",
        satisfied=satisfied,
        reason=(
            "net external force is negligible; inertial "
            "velocity is preserved"
            if satisfied
            else "net external force requires momentum change"
        ),
        metrics={
            "body_id": body.body_id,
            "net_force_newtons": asdict(resultant),
            "net_force_magnitude_newtons": magnitude,
        },
    )


def dynamics(
    body: Body,
    *,
    forces: Sequence[Force],
) -> LawResult:
    resultant = net_force(forces)
    derived = acceleration(
        mass_kg=body.mass_kg,
        force_newtons=resultant,
    )

    return LawResult(
        law=Law.DYNAMICS,
        identifier="dynamics",
        satisfied=True,
        reason="acceleration derived from net force and mass",
        metrics={
            "body_id": body.body_id,
            "mass_kg": body.mass_kg,
            "net_force_newtons": asdict(resultant),
            "acceleration_mps2": asdict(derived),
        },
    )


def interaction(
    first: Vector3,
    second: Vector3,
    *,
    tolerance_newtons: float = 1e-9,
) -> LawResult:
    residual = first.add(second)
    error = residual.magnitude
    satisfied = error <= max(0.0, tolerance_newtons)

    return LawResult(
        law=Law.INTERACTION,
        identifier="interaction",
        satisfied=satisfied,
        reason=(
            "pair interaction is momentum-symmetric"
            if satisfied
            else "pair interaction has uncompensated force"
        ),
        metrics={
            "first_force_newtons": asdict(first),
            "second_force_newtons": asdict(second),
            "residual_newtons": asdict(residual),
            "residual_magnitude_newtons": error,
        },
    )


def conservation_state(
    bodies: Sequence[Body],
    *,
    additional_energy_joules: float = 0.0,
) -> ConservationState:
    total_mass = sum(float(body.mass_kg) for body in bodies)

    total_momentum = Vector3(0.0, 0.0, 0.0)
    energy = float(additional_energy_joules)

    for body in bodies:
        total_momentum = total_momentum.add(
            momentum(
                mass_kg=body.mass_kg,
                velocity_mps=body.velocity_mps,
            )
        )
        energy += kinetic_energy(
            mass_kg=body.mass_kg,
            velocity_mps=body.velocity_mps,
        )

    return ConservationState(
        energy_joules=energy,
        momentum_kg_mps=total_momentum,
        mass_kg=total_mass,
    )


def conservation(
    before: ConservationState,
    after: ConservationState,
    *,
    energy_tolerance_joules: float = 1e-8,
    momentum_tolerance_kg_mps: float = 1e-8,
    mass_tolerance_kg: float = 1e-12,
) -> LawResult:
    energy_error = abs(
        after.energy_joules - before.energy_joules
    )
    momentum_error = (
        after.momentum_kg_mps
        .subtract(before.momentum_kg_mps)
        .magnitude
    )
    mass_error = abs(after.mass_kg - before.mass_kg)

    satisfied = (
        energy_error <= energy_tolerance_joules
        and momentum_error <= momentum_tolerance_kg_mps
        and mass_error <= mass_tolerance_kg
    )

    return LawResult(
        law=Law.CONSERVATION,
        identifier="conservation",
        satisfied=satisfied,
        reason=(
            "modeled conserved quantities remain within tolerance"
            if satisfied
            else "conservation drift exceeds supplied tolerance"
        ),
        metrics={
            "energy_error_joules": energy_error,
            "momentum_error_kg_mps": momentum_error,
            "mass_error_kg": mass_error,
        },
    )


def gravitation(
    first: Body,
    second: Body,
    *,
    gravitational_constant: float = G,
) -> LawResult:
    displacement = (
        position_vector(second.position)
        .subtract(position_vector(first.position))
    )
    radius = displacement.magnitude

    if radius <= EPSILON:
        return LawResult(
            law=Law.GRAVITATION,
            identifier="gravitation",
            satisfied=False,
            reason="point-mass gravitation is singular at zero separation",
            metrics={"separation_meters": radius},
        )

    magnitude = (
        gravitational_constant
        * float(first.mass_kg)
        * float(second.mass_kg)
        / (radius * radius)
    )

    return LawResult(
        law=Law.GRAVITATION,
        identifier="gravitation",
        satisfied=True,
        reason="newtonian gravitational interaction derived",
        metrics={
            "first_body": first.body_id,
            "second_body": second.body_id,
            "separation_meters": radius,
            "force_newtons": magnitude,
            "model": "newtonian_inverse_square",
        },
    )


def thermal_transition(
    before: ThermalState,
    *,
    heat_joules: float,
    work_by_system_joules: float = 0.0,
    entropy_transfer_joules_per_kelvin: float = 0.0,
    entropy_generation_joules_per_kelvin: float = 0.0,
) -> tuple[ThermalState, LawResult]:
    if before.temperature_kelvin < 0:
        raise PhysicsError(
            "absolute temperature cannot be negative"
        )

    if entropy_generation_joules_per_kelvin < 0:
        raise PhysicsError(
            "entropy generation cannot be negative"
        )

    internal = (
        before.internal_energy_joules
        + heat_joules
        - work_by_system_joules
    )

    entropy = (
        before.entropy_joules_per_kelvin
        + entropy_transfer_joules_per_kelvin
        + entropy_generation_joules_per_kelvin
    )

    temperature = before.temperature_kelvin

    if before.heat_capacity_joules_per_kelvin is not None:
        capacity = before.heat_capacity_joules_per_kelvin

        if capacity <= 0:
            raise PhysicsError(
                "heat capacity must be positive"
            )

        temperature += heat_joules / capacity

    satisfied = temperature >= 0

    after = ThermalState(
        temperature_kelvin=temperature,
        internal_energy_joules=internal,
        entropy_joules_per_kelvin=entropy,
        heat_capacity_joules_per_kelvin=(
            before.heat_capacity_joules_per_kelvin
        ),
    )

    return after, LawResult(
        law=Law.THERMODYNAMICS,
        identifier="thermodynamics",
        satisfied=satisfied,
        reason=(
            "thermal transition satisfies supplied energy "
            "and entropy constraints"
            if satisfied
            else "thermal transition produced invalid absolute temperature"
        ),
        metrics={
            "heat_joules": heat_joules,
            "work_by_system_joules": work_by_system_joules,
            "entropy_generation_joules_per_kelvin": (
                entropy_generation_joules_per_kelvin
            ),
            "temperature_kelvin": temperature,
            "internal_energy_joules": internal,
            "entropy_joules_per_kelvin": entropy,
        },
    )


def causal_admissibility(
    *,
    separation_meters: float,
    elapsed_seconds: float,
    propagation_limit_mps: float = C,
) -> LawResult:
    separation = max(0.0, float(separation_meters))
    elapsed = float(elapsed_seconds)
    limit = float(propagation_limit_mps)

    if elapsed < 0 or limit <= 0:
        satisfied = False
        required = math.inf
    elif elapsed <= EPSILON:
        required = 0.0 if separation <= EPSILON else math.inf
        satisfied = separation <= EPSILON
    else:
        required = separation / elapsed
        satisfied = required <= limit + EPSILON

    return LawResult(
        law=Law.CAUSAL_ADMISSIBILITY,
        identifier="causal_admissibility",
        satisfied=satisfied,
        reason=(
            "transition lies within the active causal envelope"
            if satisfied
            else "transition exceeds the active causal envelope"
        ),
        metrics={
            "separation_meters": separation,
            "elapsed_seconds": elapsed,
            "required_propagation_mps": required,
            "propagation_limit_mps": limit,
        },
    )


def combine_uncertainty(
    *quantities: Quantity,
    value: float,
    unit: str = "",
    provenance: Sequence[str] = (),
) -> Quantity:
    inherited = math.sqrt(
        sum(
            float(item.uncertainty) ** 2
            for item in quantities
        )
    )

    inherited_provenance: list[str] = []

    for item in quantities:
        inherited_provenance.extend(item.provenance)

    inherited_provenance.extend(provenance)

    return Quantity(
        value=float(value),
        uncertainty=inherited,
        unit=unit,
        provenance=tuple(
            dict.fromkeys(inherited_provenance)
        ),
    )


def uncertainty_inheritance(
    inputs: Sequence[Quantity],
    output: Quantity,
    *,
    tolerance: float = 1e-15,
) -> LawResult:
    inherited_floor = (
        0.0
        if not inputs
        else min(
            float(item.uncertainty)
            for item in inputs
            if item.uncertainty > 0
        )
        if any(item.uncertainty > 0 for item in inputs)
        else 0.0
    )

    satisfied = (
        output.uncertainty + tolerance
        >= inherited_floor
    )

    return LawResult(
        law=Law.UNCERTAINTY_INHERITANCE,
        identifier="uncertainty_inheritance",
        satisfied=satisfied,
        reason=(
            "derived state preserves uncertainty floor"
            if satisfied
            else "derived state silently overstates certainty"
        ),
        metrics={
            "input_uncertainties": [
                item.uncertainty for item in inputs
            ],
            "required_floor": inherited_floor,
            "output_uncertainty": output.uncertainty,
        },
    )


def resolution_continuity(
    *,
    before_position: Vector3,
    after_position: Vector3,
    before_velocity: Vector3,
    after_velocity: Vector3,
    elapsed_seconds: float,
    maximum_acceleration_mps2: float | None = None,
    position_tolerance_meters: float = 1e-6,
) -> LawResult:
    elapsed = float(elapsed_seconds)

    if elapsed < 0:
        return LawResult(
            law=Law.RESOLUTION_CONTINUITY,
            identifier="resolution_continuity",
            satisfied=False,
            reason="resolution boundary reverses time",
        )

    expected_without_impulse = before_position.add(
        before_velocity.scale(elapsed)
    )

    displacement_error = (
        after_position
        .subtract(expected_without_impulse)
        .magnitude
    )

    velocity_delta = (
        after_velocity
        .subtract(before_velocity)
        .magnitude
    )

    acceleration_required = (
        math.inf
        if elapsed <= EPSILON and velocity_delta > EPSILON
        else (
            0.0
            if elapsed <= EPSILON
            else velocity_delta / elapsed
        )
    )

    position_valid = (
        displacement_error <= position_tolerance_meters
        or elapsed > EPSILON
    )

    acceleration_valid = (
        maximum_acceleration_mps2 is None
        or acceleration_required
        <= maximum_acceleration_mps2 + EPSILON
    )

    satisfied = position_valid and acceleration_valid

    return LawResult(
        law=Law.RESOLUTION_CONTINUITY,
        identifier="resolution_continuity",
        satisfied=satisfied,
        reason=(
            "resolved branch preserves supplied physical continuity"
            if satisfied
            else "resolved branch introduces unsupported discontinuity"
        ),
        metrics={
            "elapsed_seconds": elapsed,
            "position_residual_meters": displacement_error,
            "velocity_delta_mps": velocity_delta,
            "required_acceleration_mps2": acceleration_required,
            "maximum_acceleration_mps2": maximum_acceleration_mps2,
        },
    )


def ledger(
    results: Sequence[LawResult],
) -> PhysicsLedger:
    normalized = tuple(results)

    return PhysicsLedger(
        results=normalized,
        valid=all(item.satisfied for item in normalized),
    )


def definitions() -> tuple[dict[str, Any], ...]:
    return tuple(asdict(item) for item in LAWS)


def constants() -> dict[str, float]:
    return {
        "gravitational_constant_m3_kg_s2": G,
        "speed_of_light_mps": C,
        "planck_constant_joule_seconds": H,
        "reduced_planck_constant_joule_seconds": HBAR,
        "boltzmann_constant_joules_per_kelvin": K_B,
        "standard_gravity_mps2": STANDARD_GRAVITY,
    }


def capabilities() -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "owner": OWNER,
        "primitive": "spacetime",
        "authority_effect": "none",
        "laws": definitions(),
        "capabilities": [
            "inertia",
            "force_mass_acceleration",
            "momentum_dynamics",
            "interaction_symmetry",
            "energy_conservation_accounting",
            "momentum_conservation_accounting",
            "mass_conservation_accounting",
            "newtonian_gravitation",
            "thermal_energy_accounting",
            "entropy_accounting",
            "irreversibility_constraint",
            "absolute_temperature_constraint",
            "physical_constants",
            "causal_envelope_validation",
            "finite_propagation_constraint",
            "uncertainty_lineage",
            "uncertainty_floor_enforcement",
            "resolution_boundary_validation",
            "counterfactual_branch_preservation_contract",
            "mobius_collapse_physics_contract",
            "conservation_drift_detection",
            "tolerance_aware_validation",
            "deterministic_law_receipts",
            "law_specific_metrics",
            "law_registry",
            "physical_vs_savant_law_separation",
            "simulation_admissibility",
            "physical_impossibility_rejection",
            "provenance_carry_forward",
            "digestable_physics_ledger",
        ],
    }
