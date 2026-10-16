#!/usr/bin/env python3
from __future__ import annotations

import math
from typing import Any, Sequence

from spacetime import OWNER

SCHEMA = "savant://cataxis/statistical_mechanics/1.0.0"

BOLTZMANN_J_K = 1.380649e-23


class StatisticalMechanicsError(
    RuntimeError
):
    pass


def boltzmann_factor(
    *,
    energy_joules: float,
    temperature_kelvin: float,
) -> float:
    if temperature_kelvin <= 0:
        raise StatisticalMechanicsError(
            "temperature must be positive"
        )

    return math.exp(
        -energy_joules
        / (
            BOLTZMANN_J_K
            * temperature_kelvin
        )
    )


def partition_function(
    *,
    energies_joules: Sequence[float],
    temperature_kelvin: float,
) -> float:
    if not energies_joules:
        raise StatisticalMechanicsError(
            "energies are required"
        )

    return sum(
        boltzmann_factor(
            energy_joules=energy,
            temperature_kelvin=(
                temperature_kelvin
            ),
        )
        for energy in energies_joules
    )


def canonical_probabilities(
    *,
    energies_joules: Sequence[float],
    temperature_kelvin: float,
) -> tuple[float, ...]:
    partition = partition_function(
        energies_joules=energies_joules,
        temperature_kelvin=(
            temperature_kelvin
        ),
    )

    return tuple(
        boltzmann_factor(
            energy_joules=energy,
            temperature_kelvin=(
                temperature_kelvin
            ),
        )
        / partition
        for energy in energies_joules
    )


def mean_energy(
    *,
    energies_joules: Sequence[float],
    temperature_kelvin: float,
) -> float:
    probabilities = (
        canonical_probabilities(
            energies_joules=energies_joules,
            temperature_kelvin=(
                temperature_kelvin
            ),
        )
    )

    return sum(
        probability * energy
        for probability, energy
        in zip(
            probabilities,
            energies_joules,
            strict=True,
        )
    )


def entropy_from_probabilities(
    probabilities: Sequence[float],
) -> float:
    total = sum(probabilities)

    if total <= 0:
        raise StatisticalMechanicsError(
            "probability mass must be positive"
        )

    entropy = 0.0

    for probability in probabilities:
        normalized = (
            probability / total
        )

        if normalized > 0:
            entropy -= (
                BOLTZMANN_J_K
                * normalized
                * math.log(normalized)
            )

    return entropy


def multiplicity_entropy(
    multiplicity: float,
) -> float:
    if multiplicity < 1:
        raise StatisticalMechanicsError(
            "multiplicity must be at least one"
        )

    return (
        BOLTZMANN_J_K
        * math.log(multiplicity)
    )


def capabilities() -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "owner": OWNER,
        "primitive": "physics",
        "authority_effect": "none",
        "capabilities": [
            "boltzmann_factor",
            "partition_function",
            "canonical_distribution",
            "mean_energy",
            "gibbs_entropy",
            "boltzmann_entropy",
            "microstate_multiplicity",
        ],
    }
