#!/usr/bin/env python3

from __future__ import annotations

from typing import Any, Dict, Mapping

from cognitive_router_bridge import execute


def execute_from_router(
    request: Mapping[str, Any],
    *,
    route_data: Mapping[str, Any],
    provider_data: Mapping[str, Any],
    policy_data: Mapping[str, Any],
    provider_lookup,
) -> Dict[str, Any]:
    request_value = dict(
        request
    )

    enabled = request_value.get(
        "cognitive_orchestration"
    )

    if enabled is None:
        enabled = True

    if not bool(enabled):
        raise RuntimeError(
            "cognitive runtime called while disabled"
        )

    return execute(
        request_value,
        route_data=route_data,
        primary_provider=provider_data,
        policy_data=policy_data,
        provider_lookup=provider_lookup,
    )
