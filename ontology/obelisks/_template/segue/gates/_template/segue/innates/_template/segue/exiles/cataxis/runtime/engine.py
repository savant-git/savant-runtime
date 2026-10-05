#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import importlib
import json
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import Any, Callable, Mapping, Sequence

from spacetime import OWNER

SCHEMA = "savant://cataxis/engine/1.0.0"

PHYSICS_MODULES = (
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

CONSUMERS = {
    "carbon": "simulation",
    "mobius": "continuity",
    "lore": "canon_constraints",
    "notary": "evidence",
}


class PhysicsEngineError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class PhysicsRequest:
    module: str
    operation: str
    arguments: Mapping[str, Any] = field(
        default_factory=dict
    )
    request_id: str | None = None
    consumer: str | None = None


@dataclass(frozen=True, slots=True)
class PhysicsReceipt:
    request_id: str
    module: str
    operation: str
    consumer: str | None
    accepted: bool
    result: Any
    error: str | None
    owner: str = OWNER
    authority_effect: str = "none"

    def projection(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["schema"] = SCHEMA
        payload["generated_at"] = (
            datetime.now(UTC).isoformat()
        )

        digest_source = {
            key: value
            for key, value in payload.items()
            if key != "generated_at"
        }

        payload["digest"] = hashlib.sha256(
            json.dumps(
                digest_source,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
                default=str,
            ).encode("utf-8")
        ).hexdigest()

        return payload


def _request_id(
    request: PhysicsRequest,
) -> str:
    if request.request_id:
        return request.request_id

    payload = {
        "module": request.module,
        "operation": request.operation,
        "arguments": dict(
            request.arguments
        ),
        "consumer": request.consumer,
    }

    return hashlib.sha256(
        json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            default=str,
        ).encode("utf-8")
    ).hexdigest()


def _module(
    name: str,
) -> Any:
    if name not in PHYSICS_MODULES:
        raise PhysicsEngineError(
            f"unregistered cataxis module: {name}"
        )

    return importlib.import_module(name)


def _operation(
    module: Any,
    name: str,
) -> Callable[..., Any]:
    if name.startswith("_"):
        raise PhysicsEngineError(
            "private operations are not callable"
        )

    operation = getattr(
        module,
        name,
        None,
    )

    if operation is None:
        raise PhysicsEngineError(
            f"unknown physics operation: {name}"
        )

    if not callable(operation):
        raise PhysicsEngineError(
            f"physics operation is not callable: {name}"
        )

    return operation


def execute(
    request: PhysicsRequest,
) -> PhysicsReceipt:
    request_id = _request_id(
        request
    )

    if (
        request.consumer is not None
        and request.consumer
        not in CONSUMERS
    ):
        return PhysicsReceipt(
            request_id=request_id,
            module=request.module,
            operation=request.operation,
            consumer=request.consumer,
            accepted=False,
            result=None,
            error=(
                "consumer is not registered "
                "for cataxis physics"
            ),
        )

    try:
        module = _module(
            request.module
        )

        operation = _operation(
            module,
            request.operation,
        )

        result = operation(
            **dict(request.arguments)
        )

    except Exception as exc:
        return PhysicsReceipt(
            request_id=request_id,
            module=request.module,
            operation=request.operation,
            consumer=request.consumer,
            accepted=False,
            result=None,
            error=(
                f"{type(exc).__name__}: {exc}"
            ),
        )

    return PhysicsReceipt(
        request_id=request_id,
        module=request.module,
        operation=request.operation,
        consumer=request.consumer,
        accepted=True,
        result=result,
        error=None,
    )


def execute_many(
    requests: Sequence[PhysicsRequest],
) -> tuple[PhysicsReceipt, ...]:
    return tuple(
        execute(request)
        for request in requests
    )


def capabilities() -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "owner": OWNER,
        "primitive": "physics",
        "authority_effect": "none",
        "modules": PHYSICS_MODULES,
        "consumers": CONSUMERS,
        "capabilities": [
            "single_physics_entrypoint",
            "deterministic_request_identity",
            "physics_operation_dispatch",
            "consumer_boundary_enforcement",
            "physics_receipts",
            "batch_physics_execution",
            "carbon_simulation_interface",
            "mobius_continuity_interface",
            "lore_constraint_interface",
            "notary_evidence_interface",
            "authority_preserving_projection",
        ],
    }
