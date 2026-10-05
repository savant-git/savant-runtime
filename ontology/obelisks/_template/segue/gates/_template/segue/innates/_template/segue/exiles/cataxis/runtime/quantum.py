#!/usr/bin/env python3
from __future__ import annotations

import cmath
import hashlib
import json
import math
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import Any, Mapping, Sequence

from spacetime import EPSILON, OWNER

SCHEMA = "savant://cataxis/quantum/1.0.0"

PLANCK_J_S = 6.62607015e-34
HBAR_J_S = PLANCK_J_S / (2.0 * math.pi)
C = 299_792_458.0
ELECTRON_VOLT_J = 1.602176634e-19


class QuantumError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class BasisState:
    state_id: str
    amplitude_real: float
    amplitude_imag: float = 0.0
    metadata: Mapping[str, Any] = field(default_factory=dict)

    @property
    def amplitude(self) -> complex:
        return complex(
            self.amplitude_real,
            self.amplitude_imag,
        )

    @property
    def probability(self) -> float:
        return abs(self.amplitude) ** 2


@dataclass(frozen=True, slots=True)
class QuantumState:
    state_id: str
    basis: tuple[BasisState, ...]
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class MeasurementOutcome:
    basis_id: str
    probability: float


@dataclass(frozen=True, slots=True)
class QuantumProjection:
    state: QuantumState
    normalized: bool
    norm: float
    outcomes: tuple[MeasurementOutcome, ...]
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
        raise QuantumError(
            f"{name} must be numeric"
        ) from exc

    if not math.isfinite(number):
        raise QuantumError(
            f"{name} must be finite"
        )

    return number


def _positive(value: Any, name: str) -> float:
    number = _finite(value, name)

    if number <= 0:
        raise QuantumError(
            f"{name} must be positive"
        )

    return number


def norm(state: QuantumState) -> float:
    return math.sqrt(
        sum(
            basis.probability
            for basis in state.basis
        )
    )


def normalize(state: QuantumState) -> QuantumState:
    magnitude = norm(state)

    if magnitude <= EPSILON:
        raise QuantumError(
            "zero quantum state cannot be normalized"
        )

    return QuantumState(
        state_id=state.state_id,
        basis=tuple(
            BasisState(
                state_id=basis.state_id,
                amplitude_real=(
                    basis.amplitude.real
                    / magnitude
                ),
                amplitude_imag=(
                    basis.amplitude.imag
                    / magnitude
                ),
                metadata=basis.metadata,
            )
            for basis in state.basis
        ),
        metadata=state.metadata,
    )


def probabilities(
    state: QuantumState,
) -> tuple[MeasurementOutcome, ...]:
    normalized = normalize(state)

    return tuple(
        MeasurementOutcome(
            basis_id=basis.state_id,
            probability=basis.probability,
        )
        for basis in normalized.basis
    )


def inner_product(
    first: QuantumState,
    second: QuantumState,
) -> complex:
    if len(first.basis) != len(second.basis):
        raise QuantumError(
            "basis dimensions differ"
        )

    return sum(
        (
            first_basis.amplitude.conjugate()
            * second_basis.amplitude
            for first_basis, second_basis
            in zip(
                first.basis,
                second.basis,
                strict=True,
            )
        ),
        0j,
    )


def orthogonal(
    first: QuantumState,
    second: QuantumState,
    *,
    tolerance: float = 1e-12,
) -> bool:
    return abs(
        inner_product(first, second)
    ) <= tolerance


def phase_evolve(
    state: QuantumState,
    *,
    energies_joules: Sequence[float],
    elapsed_seconds: float,
) -> QuantumState:
    if len(state.basis) != len(
        energies_joules
    ):
        raise QuantumError(
            "one energy is required per basis state"
        )

    elapsed = _finite(
        elapsed_seconds,
        "elapsed_seconds",
    )

    evolved: list[BasisState] = []

    for basis, energy in zip(
        state.basis,
        energies_joules,
        strict=True,
    ):
        energy_value = _finite(
            energy,
            "energy_joules",
        )

        phase = cmath.exp(
            -1j
            * energy_value
            * elapsed
            / HBAR_J_S
        )

        amplitude = (
            basis.amplitude
            * phase
        )

        evolved.append(
            BasisState(
                state_id=basis.state_id,
                amplitude_real=(
                    amplitude.real
                ),
                amplitude_imag=(
                    amplitude.imag
                ),
                metadata=basis.metadata,
            )
        )

    return QuantumState(
        state_id=state.state_id,
        basis=tuple(evolved),
        metadata=state.metadata,
    )


def expectation_diagonal(
    state: QuantumState,
    *,
    eigenvalues: Sequence[float],
) -> float:
    normalized = normalize(state)

    if len(normalized.basis) != len(
        eigenvalues
    ):
        raise QuantumError(
            "one eigenvalue is required per basis state"
        )

    return sum(
        basis.probability
        * _finite(
            eigenvalue,
            "eigenvalue",
        )
        for basis, eigenvalue in zip(
            normalized.basis,
            eigenvalues,
            strict=True,
        )
    )


def uncertainty_diagonal(
    state: QuantumState,
    *,
    eigenvalues: Sequence[float],
) -> float:
    normalized = normalize(state)

    mean = expectation_diagonal(
        normalized,
        eigenvalues=eigenvalues,
    )

    mean_square = sum(
        basis.probability
        * (
            _finite(
                eigenvalue,
                "eigenvalue",
            )
            ** 2
        )
        for basis, eigenvalue in zip(
            normalized.basis,
            eigenvalues,
            strict=True,
        )
    )

    variance = max(
        0.0,
        mean_square - mean * mean,
    )

    return math.sqrt(variance)


def de_broglie_wavelength(
    momentum_kg_mps: float,
) -> float:
    momentum = abs(
        _finite(
            momentum_kg_mps,
            "momentum_kg_mps",
        )
    )

    if momentum <= EPSILON:
        raise QuantumError(
            "momentum magnitude must be positive"
        )

    return PLANCK_J_S / momentum


def photon_energy(
    frequency_hz: float,
) -> float:
    frequency = _positive(
        frequency_hz,
        "frequency_hz",
    )

    return PLANCK_J_S * frequency


def photon_momentum(
    frequency_hz: float,
) -> float:
    return (
        photon_energy(frequency_hz)
        / C
    )


def energy_frequency(
    energy_joules: float,
) -> float:
    energy = _positive(
        energy_joules,
        "energy_joules",
    )

    return energy / PLANCK_J_S


def uncertainty_minimum_position(
    momentum_uncertainty_kg_mps: float,
) -> float:
    momentum = _positive(
        momentum_uncertainty_kg_mps,
        "momentum_uncertainty_kg_mps",
    )

    return HBAR_J_S / (
        2.0 * momentum
    )


def tunneling_probability_rectangular(
    *,
    particle_mass_kg: float,
    barrier_height_joules: float,
    particle_energy_joules: float,
    barrier_width_meters: float,
) -> float:
    mass = _positive(
        particle_mass_kg,
        "particle_mass_kg",
    )

    barrier = _positive(
        barrier_height_joules,
        "barrier_height_joules",
    )

    energy = _finite(
        particle_energy_joules,
        "particle_energy_joules",
    )

    width = _positive(
        barrier_width_meters,
        "barrier_width_meters",
    )

    if energy >= barrier:
        return 1.0

    if energy < 0:
        raise QuantumError(
            "particle energy cannot be negative"
        )

    kappa = math.sqrt(
        2.0
        * mass
        * (barrier - energy)
    ) / HBAR_J_S

    return math.exp(
        -2.0 * kappa * width
    )


def project(
    state: QuantumState,
) -> QuantumProjection:
    normalized_state = normalize(state)

    return QuantumProjection(
        state=normalized_state,
        normalized=True,
        norm=norm(normalized_state),
        outcomes=probabilities(
            normalized_state
        ),
    )


def capabilities() -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "owner": OWNER,
        "primitive": "physics",
        "authority_effect": "none",
        "capabilities": [
            "complex_probability_amplitudes",
            "quantum_state_normalization",
            "born_probabilities",
            "state_inner_product",
            "orthogonality",
            "unitary_energy_phase_evolution",
            "diagonal_expectation_values",
            "diagonal_uncertainty",
            "planck_relation",
            "photon_energy",
            "photon_momentum",
            "de_broglie_wavelength",
            "heisenberg_position_bound",
            "rectangular_barrier_tunneling",
            "quantum_state_projection",
            "carbon_quantum_simulation_support",
            "mobius_quantum_consequence_support",
        ],
    }
