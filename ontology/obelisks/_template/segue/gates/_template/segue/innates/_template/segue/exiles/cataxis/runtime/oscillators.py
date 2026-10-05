#!/usr/bin/env python3
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

from spacetime import EPSILON, OWNER

SCHEMA = "savant://cataxis/oscillators/1.0.0"


class OscillatorError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class Oscillator:
    mass_kg: float
    spring_constant_n_m: float
    damping_n_s_m: float = 0.0
    driving_force_newtons: float = 0.0
    driving_frequency_rad_s: float = 0.0


@dataclass(frozen=True, slots=True)
class OscillatorState:
    time_seconds: float
    displacement_meters: float
    velocity_mps: float
    acceleration_mps2: float
    mechanical_energy_joules: float


def natural_frequency(
    oscillator: Oscillator,
) -> float:
    if oscillator.mass_kg <= 0:
        raise OscillatorError(
            "mass_kg must be positive"
        )

    if oscillator.spring_constant_n_m <= 0:
        raise OscillatorError(
            "spring_constant_n_m must be positive"
        )

    return math.sqrt(
        oscillator.spring_constant_n_m
        / oscillator.mass_kg
    )


def damping_ratio(
    oscillator: Oscillator,
) -> float:
    return (
        oscillator.damping_n_s_m
        / (
            2.0
            * math.sqrt(
                oscillator.mass_kg
                * oscillator.spring_constant_n_m
            )
        )
    )


def damped_frequency(
    oscillator: Oscillator,
) -> float:
    omega = natural_frequency(
        oscillator
    )

    ratio = damping_ratio(
        oscillator
    )

    if ratio >= 1.0:
        return 0.0

    return omega * math.sqrt(
        1.0 - ratio * ratio
    )


def undamped_state(
    oscillator: Oscillator,
    *,
    amplitude_meters: float,
    phase_radians: float,
    time_seconds: float,
) -> OscillatorState:
    omega = natural_frequency(
        oscillator
    )

    angle = (
        omega * time_seconds
        + phase_radians
    )

    displacement = (
        amplitude_meters
        * math.cos(angle)
    )

    velocity = (
        -amplitude_meters
        * omega
        * math.sin(angle)
    )

    acceleration = (
        -omega * omega
        * displacement
    )

    energy = (
        0.5
        * oscillator.mass_kg
        * velocity * velocity
        + 0.5
        * oscillator.spring_constant_n_m
        * displacement * displacement
    )

    return OscillatorState(
        time_seconds=time_seconds,
        displacement_meters=displacement,
        velocity_mps=velocity,
        acceleration_mps2=acceleration,
        mechanical_energy_joules=energy,
    )


def driven_amplitude(
    oscillator: Oscillator,
) -> float:
    omega = oscillator.driving_frequency_rad_s
    omega_zero = natural_frequency(
        oscillator
    )

    denominator = math.sqrt(
        (
            oscillator.mass_kg
            * (
                omega_zero * omega_zero
                - omega * omega
            )
        )
        ** 2
        + (
            oscillator.damping_n_s_m
            * omega
        )
        ** 2
    )

    if denominator <= EPSILON:
        return math.inf

    return (
        abs(
            oscillator.driving_force_newtons
        )
        / denominator
    )


def quality_factor(
    oscillator: Oscillator,
) -> float:
    damping = oscillator.damping_n_s_m

    if damping <= EPSILON:
        return math.inf

    return (
        oscillator.mass_kg
        * natural_frequency(
            oscillator
        )
        / damping
    )


def capabilities() -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "owner": OWNER,
        "primitive": "physics",
        "authority_effect": "none",
        "capabilities": [
            "harmonic_motion",
            "natural_frequency",
            "damping_ratio",
            "damped_frequency",
            "undamped_evolution",
            "mechanical_energy",
            "driven_oscillation",
            "resonant_response",
            "quality_factor",
        ],
    }
