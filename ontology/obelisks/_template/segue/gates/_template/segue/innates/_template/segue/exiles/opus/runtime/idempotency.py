from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping


schema = (
    "savant://runtime/opus/"
    "idempotency/1.0.0"
)

owner = "exile:opus"


class idempotency_error(
    ValueError
):
    pass


def _canonical_json(
    value: Any,
) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def _digest(
    value: Any,
) -> str:
    return hashlib.sha256(
        _canonical_json(value).encode(
            "utf-8"
        )
    ).hexdigest()


def _string(
    value: Any,
) -> str | None:
    if value is None:
        return None

    result = str(value).strip()

    return result or None


def project(
    request: Mapping[str, Any],
) -> dict[str, Any]:
    if not isinstance(
        request,
        Mapping,
    ):
        raise idempotency_error(
            "request must be an object"
        )

    supplied_key = _string(
        request.get(
            "idempotency_key"
        )
    )

    material = {
        "tenant_id": _string(
            request.get(
                "tenant_id"
            )
        ),
        "client_key_id": _string(
            request.get(
                "client_key_id"
            )
        ),
        "request_origin": _string(
            request.get(
                "request_origin"
            )
        ),
        "requested_model": _string(
            request.get(
                "requested_model"
            )
        ),
        "messages": request.get(
            "messages"
        )
        or [],
        "required_capabilities": (
            request.get(
                "required_capabilities"
            )
            or []
        ),
        "required_layers": (
            request.get(
                "required_layers"
            )
            or []
        ),
        "tools": request.get(
            "tools"
        )
        or [],
        "tool_choice": request.get(
            "tool_choice"
        ),
        "response_format": request.get(
            "response_format"
        ),
        "temperature": request.get(
            "temperature"
        ),
        "top_p": request.get(
            "top_p"
        ),
        "max_tokens": request.get(
            "max_tokens"
        ),
        "stop": request.get(
            "stop"
        ),
    }

    request_digest = _digest(
        material
    )

    if supplied_key:
        identity_material = {
            "tenant_id": material[
                "tenant_id"
            ],
            "client_key_id": material[
                "client_key_id"
            ],
            "idempotency_key": (
                supplied_key
            ),
        }

        mode = "explicit"

    else:
        identity_material = {
            "request_digest": (
                request_digest
            )
        }

        mode = "derived"

    identity = (
        "opusidem_"
        + _digest(
            identity_material
        )[:32]
    )

    projection = {
        "schema": schema,
        "owner": owner,
        "type": (
            "opus_idempotency_projection"
        ),
        "identity": identity,
        "mode": mode,
        "supplied_key": supplied_key,
        "request_digest": (
            request_digest
        ),
        "authority_effect": "none",
        "projection_only": True,
        "deterministic": True,
        "rebuildable": True,
        "boundaries": {
            "stores_result": False,
            "caches_result": False,
            "locks_request": False,
            "claims_exactly_once": False,
            "executes_request": False,
            "selects_provider": False,
            "creates_authority": False,
        },
    }

    projection[
        "digest"
    ] = _digest(
        projection
    )

    return projection


def equivalent(
    left: Mapping[str, Any],
    right: Mapping[str, Any],
) -> bool:
    return (
        project(left)[
            "identity"
        ]
        == project(right)[
            "identity"
        ]
    )
