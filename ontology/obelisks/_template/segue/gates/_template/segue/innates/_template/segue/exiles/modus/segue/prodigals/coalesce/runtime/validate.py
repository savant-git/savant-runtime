#!/usr/bin/env python3

from __future__ import annotations

import json
from typing import Any

from .health import health
from .runtime_bridge import (
    RuntimeBridgeError,
    legacy_callables,
    status,
    v2_dispatch,
)


def validate() -> dict[str, Any]:
    checks: dict[str, bool] = {}

    try:
        bridge = status()
        checks["runtime_bridge"] = True
    except RuntimeBridgeError:
        bridge = {}
        checks["runtime_bridge"] = False

    try:
        callables = legacy_callables()
        checks["legacy_preserved"] = bool(
            callables
        )
    except RuntimeBridgeError:
        callables = ()
        checks["legacy_preserved"] = False

    try:
        v2 = v2_dispatch(
            "status",
            {},
        )
        checks["v2_runtime"] = bool(
            v2.get(
                "ok",
                True,
            )
        )
    except RuntimeBridgeError:
        v2 = {}
        checks["v2_runtime"] = False

    runtime_health = health()

    checks["health"] = bool(
        runtime_health.get(
            "healthy"
        )
    )

    checks["owner"] = (
        bridge.get(
            "owner"
        )
        == "prodigal:modus:coalesce"
    )

    checks["authority_effect_none"] = (
        bridge.get(
            "authority_effect"
        )
        == "none"
    )

    checks["legacy_not_replaced"] = (
        bridge.get(
            "replacement_performed"
        )
        is False
    )

    checks["composition_extension"] = (
        bridge.get(
            "composition_extension"
        )
        is True
    )

    return {
        "schema": (
            "savant://assurance/"
            "coalesce/runtime/1"
        ),
        "owner": (
            "prodigal:modus:coalesce"
        ),
        "valid": all(
            checks.values()
        ),
        "checks": checks,
        "legacy_callable_count": len(
            callables
        ),
        "health": runtime_health,
        "v2": v2,
    }


if __name__ == "__main__":
    print(
        json.dumps(
            validate(),
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
            default=str,
        )
    )
