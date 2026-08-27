"""Scrybe: Savant living memory substrate."""

from .engine import (
    SCRYBE_ABILITIES,
    SCRYBE_HEALTH_DIMENSIONS,
    SCRYBE_PIPELINE,
    SCRYBE_PROJECTIONS,
    SCRYBE_VALIDATION_DIMENSIONS,
    Scrybe,
    ScrybeError,
)

from .instance import (
    ScrybeInstance,
    ScrybeInstanceError,
    load_instance,
)


__all__ = [
    "SCRYBE_ABILITIES",
    "SCRYBE_HEALTH_DIMENSIONS",
    "SCRYBE_PIPELINE",
    "SCRYBE_PROJECTIONS",
    "SCRYBE_VALIDATION_DIMENSIONS",
    "Scrybe",
    "ScrybeError",
    "ScrybeInstance",
    "ScrybeInstanceError",
    "load_instance",
]
