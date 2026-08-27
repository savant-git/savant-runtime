"""Pryme: Savant living authority substrate."""

from .engine import (
    PRYME_ABILITIES,
    PRYME_HEALTH_DIMENSIONS,
    PRYME_PIPELINE,
    PRYME_PROJECTIONS,
    PRYME_VALIDATION_DIMENSIONS,
    AuthorityRecord,
    Pryme,
    PrymeError,
)

from .authority_binding import (
    ConstitutionalBinding,
    PrymeAuthorityBinding,
    PrymeAuthorityBindingError,
    bind,
    bind_registry,
    record_from_object,
    registry_values,
)


__all__ = [
    "PRYME_ABILITIES",
    "PRYME_HEALTH_DIMENSIONS",
    "PRYME_PIPELINE",
    "PRYME_PROJECTIONS",
    "PRYME_VALIDATION_DIMENSIONS",
    "AuthorityRecord",
    "Pryme",
    "PrymeError",
    "ConstitutionalBinding",
    "PrymeAuthorityBinding",
    "PrymeAuthorityBindingError",
    "bind",
    "bind_registry",
    "record_from_object",
    "registry_values",
]
