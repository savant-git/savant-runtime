#!/usr/bin/env python3
from __future__ import annotations

import importlib
import json
from typing import Any

from engine import (
    PHYSICS_MODULES,
    PhysicsRequest,
    execute,
)
from spacetime import OWNER

SCHEMA = "savant://cataxis/selfcheck/1.0.0"


def run() -> dict[str, Any]:
    modules: dict[str, Any] = {}
    failures: list[str] = []

    for name in PHYSICS_MODULES:
        try:
            module = importlib.import_module(
                name
            )

            modules[name] = {
                "imported": True,
                "schema": getattr(
                    module,
                    "SCHEMA",
                    None,
                ),
            }

        except Exception as exc:
            modules[name] = {
                "imported": False,
                "error": (
                    f"{type(exc).__name__}: "
                    f"{exc}"
                ),
            }
            failures.append(name)

    smoke = execute(
        PhysicsRequest(
            module="constants",
            operation="get",
            arguments={
                "name": (
                    "speed_of_light_m_s"
                ),
            },
            consumer="carbon",
        )
    )

    if not smoke.accepted:
        failures.append(
            "engine_dispatch"
        )

    return {
        "schema": SCHEMA,
        "owner": OWNER,
        "authority_effect": "none",
        "accepted": not failures,
        "failures": tuple(failures),
        "modules": modules,
        "dispatch": smoke.projection(),
    }


def main() -> int:
    result = run()

    print(
        json.dumps(
            result,
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
            default=str,
        )
    )

    return (
        0
        if result["accepted"]
        else 1
    )


if __name__ == "__main__":
    raise SystemExit(main())
