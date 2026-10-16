#!/usr/bin/env python3
from __future__ import annotations

from types import MappingProxyType
from typing import Any

from spacetime import OWNER

SCHEMA = "savant://cataxis/constants/1.0.0"

CONSTANTS = MappingProxyType({
    "speed_of_light_m_s": 299_792_458.0,
    "gravitational_constant_m3_kg_s2": 6.67430e-11,
    "planck_constant_j_s": 6.62607015e-34,
    "reduced_planck_constant_j_s": 1.054571817e-34,
    "elementary_charge_c": 1.602176634e-19,
    "boltzmann_constant_j_k": 1.380649e-23,
    "avogadro_constant_mol_inverse": 6.02214076e23,
    "gas_constant_j_mol_k": 8.31446261815324,
    "vacuum_permittivity_f_m": 8.8541878128e-12,
    "vacuum_permeability_h_m": 1.25663706212e-6,
    "stefan_boltzmann_w_m2_k4": 5.670374419e-8,
    "standard_gravity_m_s2": 9.80665,
})


def get(name: str) -> float:
    try:
        return CONSTANTS[name]
    except KeyError as exc:
        raise KeyError(
            f"unknown cataxis constant: {name}"
        ) from exc


def projection() -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "owner": OWNER,
        "authority_effect": "none",
        "constants": dict(CONSTANTS),
        "policy": (
            "immutable runtime reference values; "
            "laws remain authoritative over behavior"
        ),
    }


def capabilities() -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "owner": OWNER,
        "primitive": "physics",
        "authority_effect": "none",
        "capabilities": [
            "immutable_physical_constants",
            "si_reference_values",
            "deterministic_constant_lookup",
        ],
    }
