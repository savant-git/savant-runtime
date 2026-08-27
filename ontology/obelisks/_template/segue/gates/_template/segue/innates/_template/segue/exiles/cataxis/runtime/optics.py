#!/usr/bin/env python3
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

from spacetime import OWNER

SCHEMA = "savant://cataxis/optics/1.0.0"
C = 299_792_458.0


class OpticsError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class Refraction:
    incident_angle_radians: float
    refracted_angle_radians: float | None
    total_internal_reflection: bool


def refracted_angle(
    *,
    incident_angle_radians: float,
    initial_refractive_index: float,
    final_refractive_index: float,
) -> Refraction:
    if initial_refractive_index <= 0:
        raise OpticsError(
            "initial refractive index must be positive"
        )

    if final_refractive_index <= 0:
        raise OpticsError(
            "final refractive index must be positive"
        )

    sine = (
        initial_refractive_index
        / final_refractive_index
        * math.sin(
            incident_angle_radians
        )
    )

    if abs(sine) > 1.0:
        return Refraction(
            incident_angle_radians=(
                incident_angle_radians
            ),
            refracted_angle_radians=None,
            total_internal_reflection=True,
        )

    return Refraction(
        incident_angle_radians=(
            incident_angle_radians
        ),
        refracted_angle_radians=(
            math.asin(sine)
        ),
        total_internal_reflection=False,
    )


def critical_angle(
    *,
    initial_refractive_index: float,
    final_refractive_index: float,
) -> float | None:
    if (
        initial_refractive_index
        <= final_refractive_index
    ):
        return None

    return math.asin(
        final_refractive_index
        / initial_refractive_index
    )


def light_speed(
    refractive_index: float,
) -> float:
    if refractive_index <= 0:
        raise OpticsError(
            "refractive index must be positive"
        )

    return C / refractive_index


def thin_lens_image_distance(
    *,
    focal_length_meters: float,
    object_distance_meters: float,
) -> float:
    if focal_length_meters == 0:
        raise OpticsError(
            "focal length cannot be zero"
        )

    if object_distance_meters == 0:
        raise OpticsError(
            "object distance cannot be zero"
        )

    denominator = (
        1.0 / focal_length_meters
        - 1.0 / object_distance_meters
    )

    if abs(denominator) <= 1e-15:
        return math.inf

    return 1.0 / denominator


def magnification(
    *,
    image_distance_meters: float,
    object_distance_meters: float,
) -> float:
    if object_distance_meters == 0:
        raise OpticsError(
            "object distance cannot be zero"
        )

    return (
        -image_distance_meters
        / object_distance_meters
    )


def diffraction_grating_angle(
    *,
    wavelength_meters: float,
    slit_spacing_meters: float,
    order: int,
) -> float | None:
    if wavelength_meters <= 0:
        raise OpticsError(
            "wavelength must be positive"
        )

    if slit_spacing_meters <= 0:
        raise OpticsError(
            "slit spacing must be positive"
        )

    value = (
        order
        * wavelength_meters
        / slit_spacing_meters
    )

    if abs(value) > 1.0:
        return None

    return math.asin(value)


def brewster_angle(
    *,
    initial_refractive_index: float,
    final_refractive_index: float,
) -> float:
    if (
        initial_refractive_index <= 0
        or final_refractive_index <= 0
    ):
        raise OpticsError(
            "refractive indices must be positive"
        )

    return math.atan(
        final_refractive_index
        / initial_refractive_index
    )


def capabilities() -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "owner": OWNER,
        "primitive": "physics",
        "authority_effect": "none",
        "capabilities": [
            "reflection_support",
            "snell_refraction",
            "total_internal_reflection",
            "critical_angle",
            "medium_light_speed",
            "thin_lens_equation",
            "optical_magnification",
            "diffraction_grating",
            "brewster_angle",
        ],
    }
