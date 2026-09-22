#!/usr/bin/env python3

from __future__ import annotations

import os
from typing import Any, Dict

from providers import universal_text
from providers.base import ProviderError


PROVIDER_ID = "venice_uncensored_text"
PROFILE_ID = "venice_uncensored"


def available() -> bool:
    return bool(
        str(
            os.getenv(
                "VENICE_API_KEY",
                "",
            )
            or ""
        ).strip()
    )


def infer(
    request: Dict[str, Any],
    provider: Dict[str, Any],
) -> Dict[str, Any]:
    if not isinstance(
        request,
        dict,
    ):
        raise ProviderError(
            "request must be an object"
        )

    if not available():
        raise ProviderError(
            "VENICE_API_KEY missing"
        )

    delegated = dict(
        request
    )

    delegated[
        "provider_profile"
    ] = PROFILE_ID

    result = universal_text.infer(
        delegated,
        provider,
    )

    if not isinstance(
        result,
        dict,
    ):
        raise ProviderError(
            "venice provider returned non-object result"
        )

    result[
        "provider"
    ] = PROVIDER_ID

    result[
        "provider_profile"
    ] = PROFILE_ID

    result[
        "inference_latitude"
    ] = "maximum_provider_permitted"

    result[
        "owner"
    ] = "opus"

    result[
        "authority_effect"
    ] = "none"

    return result
