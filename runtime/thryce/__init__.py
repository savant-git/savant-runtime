"""Thryce: Savant living assurance substrate."""

from .engine import (
    THRYCE_ABILITIES,
    THRYCE_HEALTH_DIMENSIONS,
    THRYCE_PIPELINE,
    THRYCE_PROJECTIONS,
    THRYCE_VALIDATION_DIMENSIONS,
    AssuranceCheck,
    AssuranceResult,
    Thryce,
    ThryceError,
)

from .notary_binding import (
    AssuranceRequest,
    AssuranceResult as NotaryAssuranceResult,
    ThryceNotaryBinding,
    ThryceNotaryBindingError,
    bind_notary,
)

from .notary_adapter import (
    NotaryAdapterError,
    NotaryAssuranceAdapter,
    NotaryAssurancePacket,
    adapter as notary_adapter,
)


__all__ = [
    "THRYCE_ABILITIES",
    "THRYCE_HEALTH_DIMENSIONS",
    "THRYCE_PIPELINE",
    "THRYCE_PROJECTIONS",
    "THRYCE_VALIDATION_DIMENSIONS",
    "AssuranceCheck",
    "AssuranceResult",
    "Thryce",
    "ThryceError",
    "AssuranceRequest",
    "NotaryAssuranceResult",
    "ThryceNotaryBinding",
    "ThryceNotaryBindingError",
    "bind_notary",
    "NotaryAdapterError",
    "NotaryAssuranceAdapter",
    "NotaryAssurancePacket",
    "notary_adapter",
]
