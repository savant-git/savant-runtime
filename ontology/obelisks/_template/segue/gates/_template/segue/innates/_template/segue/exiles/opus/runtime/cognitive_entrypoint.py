#!/usr/bin/env python3

from __future__ import annotations

from typing import Any, Dict, Mapping

from cognitive_contract import (
    normalize_request,
    validate_result,
)
from cognitive_runtime import (
    execute_from_router,
)


def execute(
    request: Mapping[str, Any],
    *,
    route_data: Mapping[str, Any],
    provider_data: Mapping[str, Any],
    policy_data: Mapping[str, Any],
    provider_lookup,
) -> Dict[str, Any]:
    normalized = normalize_request(
        request
    )

    result = execute_from_router(
        normalized,
        route_data=route_data,
        provider_data=provider_data,
        policy_data=policy_data,
        provider_lookup=provider_lookup,
    )

    return validate_result(
        result
    )
