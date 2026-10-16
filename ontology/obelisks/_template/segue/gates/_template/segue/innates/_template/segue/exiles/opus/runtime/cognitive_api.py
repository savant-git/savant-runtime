#!/usr/bin/env python3

from __future__ import annotations

from typing import Any, Dict, Mapping

from cognitive_entrypoint import execute
from cognitive_features import manifest


def execute_text(
    request: Mapping[str, Any],
    *,
    route_data: Mapping[str, Any],
    provider_data: Mapping[str, Any],
    policy_data: Mapping[str, Any],
    provider_lookup,
) -> Dict[str, Any]:
    return execute(
        request,
        route_data=route_data,
        provider_data=provider_data,
        policy_data=policy_data,
        provider_lookup=provider_lookup,
    )


def capabilities() -> Dict[str, Any]:
    return manifest()
