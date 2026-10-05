#!/usr/bin/env python3

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any

from .health import health
from .runtime_bridge import (
    RuntimeBridgeError,
    legacy_callables,
    status,
)


OWNER = "prodigal:modus:coalesce"
SCHEMA = "savant://coalesce/runtime-receipt/1"


def canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )


def digest(value: Any) -> str:
    return hashlib.sha256(
        canonical_json(value).encode("utf-8")
    ).hexdigest()


def receipt() -> dict[str, Any]:
    try:
        bridge = status()
        bridge_error = None
    except RuntimeBridgeError as exc:
        bridge = {}
        bridge_error = str(exc)

    try:
        callables = legacy_callables()
        legacy_error = None
    except RuntimeBridgeError as exc:
        callables = ()
        legacy_error = str(exc)

    runtime_health = health()

    payload: dict[str, Any] = {
        "schema": SCHEMA,
        "owner": OWNER,
        "generated_at": datetime.now(
            timezone.utc
        ).isoformat(),
        "runtime": {
            "bridge": bridge,
            "bridge_error": bridge_error,
            "legacy_callable_count": len(
                callables
            ),
            "legacy_error": legacy_error,
        },
        "health": runtime_health,
        "authority": {
            "mutation": False,
            "manufacture": False,
            "replacement": False,
        },
        "composition": {
            "source_substance_copied": False,
            "reference_composition": True,
            "extension_preserved": True,
        },
    }

    payload["digest"] = digest(payload)

    return payload


if __name__ == "__main__":
    print(
        json.dumps(
            receipt(),
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
            default=str,
        )
    )
