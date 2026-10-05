#!/usr/bin/env python3

from __future__ import annotations

from typing import Any

from .runtime_bridge import (
    RuntimeBridgeError,
    legacy_callables,
    status,
)


def health() -> dict[str, Any]:
    checks: dict[str, bool] = {}

    try:
        bridge = status()
        checks["runtime_bridge"] = bool(bridge)
    except RuntimeBridgeError:
        bridge = {}
        checks["runtime_bridge"] = False

    try:
        callables = legacy_callables()
        checks["legacy_runtime"] = bool(callables)
    except RuntimeBridgeError:
        callables = ()
        checks["legacy_runtime"] = False

    checks["canonical_owner"] = (
        bridge.get("owner")
        in {
            None,
            "prodigal:modus:coalesce",
        }
    )

    checks["v2_runtime"] = bool(
        bridge.get("v2_runtime")
        or bridge.get("v2")
        or bridge.get("canonical_runtime")
    )

    return {
        "schema": "savant://coalesce/health/1",
        "owner": "prodigal:modus:coalesce",
        "healthy": all(checks.values()),
        "checks": checks,
        "legacy_callable_count": len(callables),
        "bridge": bridge,
    }


if __name__ == "__main__":
    import json

    print(
        json.dumps(
            health(),
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
            default=str,
        )
    )
