#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import importlib
import json
from datetime import UTC, datetime
from typing import Any

from spacetime import OWNER

SCHEMA = "savant://cataxis/physics-kernel/1.0.0"

MODULES = (
    "physics",
    "laws",
    "spacetime",
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
)


class PhysicsKernelError(RuntimeError):
    pass


def module_capabilities(
    module_name: str,
) -> dict[str, Any]:
    if module_name not in MODULES:
        raise PhysicsKernelError(
            f"unregistered physics module: {module_name}"
        )

    module = importlib.import_module(
        module_name
    )

    function = getattr(
        module,
        "capabilities",
        None,
    )

    if function is None:
        return {
            "module": module_name,
            "capabilities": [],
        }

    result = function()

    if not isinstance(result, dict):
        raise PhysicsKernelError(
            f"{module_name}.capabilities() "
            "must return a dictionary"
        )

    return result


def inventory() -> dict[str, Any]:
    modules = {
        module_name: module_capabilities(
            module_name
        )
        for module_name in MODULES
    }

    payload: dict[str, Any] = {
        "schema": SCHEMA,
        "owner": OWNER,
        "authority_effect": "none",
        "primitive": "physics",
        "modules": modules,
        "module_count": len(modules),
        "generated_at": (
            datetime.now(UTC).isoformat()
        ),
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


def capability_index() -> dict[str, tuple[str, ...]]:
    index: dict[str, list[str]] = {}

    for module_name in MODULES:
        manifest = module_capabilities(
            module_name
        )

        for capability in manifest.get(
            "capabilities",
            (),
        ):
            index.setdefault(
                str(capability),
                [],
            ).append(module_name)

    return {
        capability: tuple(modules)
        for capability, modules
        in sorted(index.items())
    }


def supports(
    capability: str,
) -> bool:
    return capability in capability_index()


def owners(
    capability: str,
) -> tuple[str, ...]:
    return capability_index().get(
        capability,
        (),
    )


def projection() -> dict[str, Any]:
    inventory_payload = inventory()

    return {
        "schema": SCHEMA,
        "owner": OWNER,
        "authority_effect": "none",
        "physics_owner": "cataxis",
        "kernel": inventory_payload,
        "capability_index": (
            capability_index()
        ),
        "principles": (
            "cataxis is the sole physics owner",
            "derived physics is projected from primitives",
            "simulation consumes physics without owning it",
            "continuity consumes consequences without owning physics",
            "physics projections do not mutate authority",
        ),
    }


def main() -> int:
    print(
        json.dumps(
            projection(),
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
