from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping


SCHEMA = (
    "savant://runtime/opus/"
    "failure-taxonomy/1.0.0"
)

OWNER = "exile:opus"


class failure_taxonomy_error(
    ValueError
):
    pass


_CATEGORIES = {
    "deadline": {
        "retryable": False,
        "http_status": 408,
        "public_type": "timeout_error",
    },
    "cancelled": {
        "retryable": False,
        "http_status": 499,
        "public_type": "cancelled_error",
    },
    "authentication": {
        "retryable": False,
        "http_status": 401,
        "public_type": "authentication_error",
    },
    "authorization": {
        "retryable": False,
        "http_status": 403,
        "public_type": "authorization_error",
    },
    "invalid_request": {
        "retryable": False,
        "http_status": 400,
        "public_type": "invalid_request_error",
    },
    "capability_mismatch": {
        "retryable": False,
        "http_status": 422,
        "public_type": "capability_error",
    },
    "model_mismatch": {
        "retryable": False,
        "http_status": 422,
        "public_type": "model_error",
    },
    "provider_unavailable": {
        "retryable": True,
        "http_status": 503,
        "public_type": "provider_unavailable_error",
    },
    "provider_throttled": {
        "retryable": True,
        "http_status": 429,
        "public_type": "rate_limit_error",
    },
    "provider_timeout": {
        "retryable": True,
        "http_status": 504,
        "public_type": "provider_timeout_error",
    },
    "provider_rejected": {
        "retryable": False,
        "http_status": 502,
        "public_type": "provider_rejection_error",
    },
    "provider_malformed_response": {
        "retryable": False,
        "http_status": 502,
        "public_type": "provider_response_error",
    },
    "transport_error": {
        "retryable": True,
        "http_status": 503,
        "public_type": "transport_error",
    },
    "internal_execution": {
        "retryable": False,
        "http_status": 500,
        "public_type": "internal_error",
    },
}


def _canonical_json(
    value: Any,
) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(
            ",",
            ":",
        ),
        allow_nan=False,
    )


def _digest(
    value: Any,
) -> str:
    return hashlib.sha256(
        _canonical_json(
            value
        ).encode(
            "utf-8"
        )
    ).hexdigest()


def _string(
    value: Any,
) -> str:
    return str(
        value
        if value is not None
        else ""
    ).strip()


def categories() -> tuple[str, ...]:
    return tuple(
        sorted(
            _CATEGORIES
        )
    )


def project(
    category: str,
    *,
    code: str | None = None,
    message: str | None = None,
    provenance: Mapping[str, Any]
    | None = None,
) -> dict[str, Any]:
    normalized_category = (
        _string(
            category
        ).lower()
    )

    if (
        normalized_category
        not in _CATEGORIES
    ):
        raise failure_taxonomy_error(
            "unknown failure category"
        )

    rule = _CATEGORIES[
        normalized_category
    ]

    normalized_code = _string(
        code
    )

    safe_message = _string(
        message
    )

    if len(
        safe_message
    ) > 512:
        safe_message = (
            safe_message[
                :512
            ]
        )

    source = {}

    if provenance is not None:
        if not isinstance(
            provenance,
            Mapping,
        ):
            raise failure_taxonomy_error(
                "provenance must be "
                "an object"
            )

        for field in (
            "request_id",
            "trace_id",
            "provider",
            "model",
            "route",
            "attempt",
        ):
            if field in provenance:
                source[
                    field
                ] = provenance[
                    field
                ]

    projection = {
        "schema": SCHEMA,
        "owner": OWNER,
        "authority_effect": "none",
        "projection_only": True,
        "deterministic": True,
        "rebuildable": True,
        "category": (
            normalized_category
        ),
        "retryable": bool(
            rule[
                "retryable"
            ]
        ),
        "http_status": int(
            rule[
                "http_status"
            ]
        ),
        "public_type": str(
            rule[
                "public_type"
            ]
        ),
        "code": (
            normalized_code
            or normalized_category
        ),
        "message": (
            safe_message
            or normalized_category.replace(
                "_",
                " ",
            )
        ),
        "provenance": source,
        "boundaries": {
            "selects_provider": False,
            "selects_model": False,
            "owns_credentials": False,
            "mutates_registry": False,
            "creates_authority": False,
            "declares_truth": False,
        },
    }

    projection[
        "digest"
    ] = _digest(
        projection
    )

    return projection
