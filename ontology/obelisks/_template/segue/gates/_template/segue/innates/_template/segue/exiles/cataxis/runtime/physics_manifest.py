#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import importlib
import json
from datetime import UTC, datetime
from typing import Any

from spacetime import OWNER

SCHEMA = "savant://cataxis/physics-manifest/1.0.0"

MODULES = (
    "physics",
    "laws",
    "spacetime",
    "constants",
    "materials",
    "fluids",
    "waves",
    "thermodynamics",
    "collisions",
    "relativity",
    "gravity",
    "electromagnetism",
    "quantum",
    "oscillators",
    "optics",
    "statistical_mechanics",
    "integrator",
    "admissibility",
)


def build() -> dict[str, Any]:
    modules: dict[str, Any] = {}

    for name in MODULES:
        module = importlib.import_module(
            name
        )

        capabilities_function = getattr(
            module,
            "capabilities",
            None,
        )

        if capabilities_function is None:
            capabilities = ()
        else:
            manifest = (
                capabilities_function()
            )

            capabilities = tuple(
                manifest.get(
                    "capabilities",
                    (),
                )
            )

        modules[name] = {
            "module": name,
            "capabilities": capabilities,
        }

    payload: dict[str, Any] = {
        "schema": SCHEMA,
        "owner": OWNER,
        "physics_owner": "cataxis",
        "authority_effect": "none",
        "module_count": len(modules),
        "modules": modules,
        "generated_at": (
            datetime.now(UTC).isoformat()
        ),
        "integration": {
            "carbon": (
                "consumes cataxis physics "
                "for simulation"
            ),
            "mobius": (
                "consumes projected physical "
                "consequences for continuity"
            ),
            "lore": (
                "canon may constrain worlds "
                "without transferring physics ownership"
            ),
            "notary": (
                "may evidence physics receipts "
                "without becoming physics authority"
            ),
        },
    }

    payload["digest"] = hashlib.sha256(
        json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            default=str,
        ).encode("utf-8")
    ).hexdigest()

    return payload


def main() -> int:
    print(
        json.dumps(
            build(),
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
        )
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
