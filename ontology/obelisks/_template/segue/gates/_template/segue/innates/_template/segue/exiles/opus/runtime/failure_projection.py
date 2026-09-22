from __future__ import annotations

import hashlib
import json
import math
from typing import Any, Mapping

from .failure_taxonomy import (
    failure_taxonomy_error,
    project as project_taxonomy,
)


SCHEMA = (
    "savant://runtime/opus/"
    "failure-projection/1.0.0"
)

OWNER = "exile:opus"


class failure_projection_error(
    ValueError
):
    pass


_ALLOWED_PROVENANCE = (
    "request_id",
    "trace_id",
    "tenant_id",
    "execution_id",
    "provider",
    "model",
    "route",
    "attempt",
)


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
    *,
    maximum: int,
) -> str:
    text = str(
        value
        if value is not None
        else ""
    ).strip()

    if len(
        text
    ) > maximum:
        text = text[
            :maximum
        ]

    return text


def _retry_after(
    value: Any,
) -> float | None:
    if value is None:
        return None

    if isinstance(
        value,
        bool,
    ):
        raise failure_projection_error(
            "retry_after_seconds "
            "must be numeric"
        )

    try:
        number = float(
            value
        )

    except (
        TypeError,
        ValueError,
    ) as exc:
        raise failure_projection_error(
            "retry_after_seconds "
            "must be numeric"
        ) from exc

    if (
        not math.isfinite(
            number
        )
        or number < 0.0
    ):
        raise failure_projection_error(
            "retry_after_seconds "
            "must be finite and "
            "nonnegative"
        )

    return number


def _provenance(
    value: Mapping[str, Any]
    | None,
) -> dict[str, Any]:
    if value is None:
        return {}

    if not isinstance(
        value,
        Mapping,
    ):
        raise failure_projection_error(
            "provenance must be "
            "an object"
        )

    projection = {}

    for field in (
        _ALLOWED_PROVENANCE
    ):
        if field not in value:
            continue

        item = value[
            field
        ]

        if field == "attempt":
            if (
                isinstance(
                    item,
                    bool,
                )
                or not isinstance(
                    item,
                    int,
                )
                or item < 0
            ):
                raise failure_projection_error(
                    "attempt must be a "
                    "nonnegative integer"
                )

            projection[
                field
            ] = item

            continue

        text = _string(
            item,
            maximum=256,
        )

        if text:
            projection[
                field
            ] = text

    return projection


def project(
    category: str,
    *,
    code: str | None = None,
    message: str | None = None,
    retry_after_seconds: Any = None,
    provenance: Mapping[str, Any]
    | None = None,
) -> dict[str, Any]:
    normalized_provenance = (
        _provenance(
            provenance
        )
    )

    try:
        taxonomy = project_taxonomy(
            category,
            code=code,
            message=message,
            provenance=(
                normalized_provenance
            ),
        )

    except failure_taxonomy_error as exc:
        raise failure_projection_error(
            str(
                exc
            )
        ) from exc

    retry_after = _retry_after(
        retry_after_seconds
    )

    projection = {
        "schema": SCHEMA,
        "owner": OWNER,
        "authority_effect": "none",
        "projection_only": True,
        "deterministic": True,
        "rebuildable": True,
        "category": taxonomy[
            "category"
        ],
        "code": taxonomy[
            "code"
        ],
        "message": taxonomy[
            "message"
        ],
        "retryable": taxonomy[
            "retryable"
        ],
        "terminal": not taxonomy[
            "retryable"
        ],
        "http_status": taxonomy[
            "http_status"
        ],
        "public_type": taxonomy[
            "public_type"
        ],
        "retry_after_seconds": (
            retry_after
        ),
        "provenance": (
            normalized_provenance
        ),
        "lineage": {
            "taxonomy_schema": (
                taxonomy[
                    "schema"
                ]
            ),
            "taxonomy_digest": (
                taxonomy[
                    "digest"
                ]
            ),
        },
        "boundaries": {
            "selects_provider": False,
            "selects_model": False,
            "executes_provider": False,
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


def public_error(
    failure: Mapping[str, Any],
) -> dict[str, Any]:
    if not isinstance(
        failure,
        Mapping,
    ):
        raise failure_projection_error(
            "failure must be an object"
        )

    if (
        failure.get(
            "schema"
        )
        != SCHEMA
    ):
        raise failure_projection_error(
            "failure schema mismatch"
        )

    return {
        "error": {
            "message": _string(
                failure.get(
                    "message"
                ),
                maximum=512,
            ),
            "type": _string(
                failure.get(
                    "public_type"
                ),
                maximum=128,
            ),
            "param": None,
            "code": _string(
                failure.get(
                    "code"
                ),
                maximum=128,
            ),
        }
    }
