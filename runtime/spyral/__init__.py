"""Spyral: Savant living evolution substrate."""

from .engine import (
    SPYRAL_ABILITIES,
    SPYRAL_HEALTH_DIMENSIONS,
    SPYRAL_PIPELINE,
    SPYRAL_PROJECTIONS,
    SPYRAL_VALIDATION_DIMENSIONS,
    Compatibility,
    Transition,
    Spyral,
    SpyralError,
)

from .coda_binding import (
    CodaTransitionRequest,
    SpyralCodaBinding,
    SpyralCodaBindingError,
    bind_coda,
)


__all__ = [
    "SPYRAL_ABILITIES",
    "SPYRAL_HEALTH_DIMENSIONS",
    "SPYRAL_PIPELINE",
    "SPYRAL_PROJECTIONS",
    "SPYRAL_VALIDATION_DIMENSIONS",
    "Compatibility",
    "Transition",
    "Spyral",
    "SpyralError",
    "CodaTransitionRequest",
    "SpyralCodaBinding",
    "SpyralCodaBindingError",
    "bind_coda",
]
