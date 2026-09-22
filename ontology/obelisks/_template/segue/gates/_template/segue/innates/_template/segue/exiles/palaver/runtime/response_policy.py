from __future__ import annotations

import hashlib
import json
from typing import Any


schema = (
    "savant://runtime/palaver/"
    "response-policy/1.0.0"
)

owner = "exile:palaver"

blocked_keys = frozenset({
    "diagnostic",
    "diagnostics",
    "traceback",
    "stack",
    "stacktrace",
    "exception",
    "exception_text",
    "provider_error",
    "raw_error",
    "raw_exception",
    "internal_error",
})

max_depth = 12
max_collection_items = 500
max_string_characters = 250000


def _canonical(
    value: Any,
) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(
            ",",
            ":",
        ),
        default=str,
    ).encode(
        "utf-8"
    )


def digest(
    value: Any,
) -> str:
    return (
        hashlib.sha256(
            _canonical(
                value
            )
        ).hexdigest()
    )


def _sanitize(
    value: Any,
    *,
    depth: int,
) -> Any:
    if depth > max_depth:
        return None

    if isinstance(
        value,
        dict,
    ):
        projected: dict[
            str,
            Any,
        ] = {}

        for index, (
            key,
            item,
        ) in enumerate(
            value.items()
        ):
            if (
                index
                >= max_collection_items
            ):
                break

            normalized = str(
                key
            )

            if (
                normalized
                .strip()
                .lower()
                in blocked_keys
            ):
                continue

            projected[
                normalized
            ] = _sanitize(
                item,
                depth=
                    depth + 1,
            )

        return projected

    if isinstance(
        value,
        (
            list,
            tuple,
        ),
    ):
        return [
            _sanitize(
                item,
                depth=
                    depth + 1,
            )
            for item in value[
                :max_collection_items
            ]
        ]

    if isinstance(
        value,
        str,
    ):
        return value[
            :max_string_characters
        ]

    if (
        value is None
        or isinstance(
            value,
            (
                bool,
                int,
                float,
            ),
        )
    ):
        return value

    return str(
        value
    )[
        :max_string_characters
    ]


def sanitize_public_payload(
    payload: Any,
) -> Any:
    return _sanitize(
        payload,
        depth=0,
    )


def projection(
    payload: Any,
) -> dict[str, Any]:
    sanitized = (
        sanitize_public_payload(
            payload
        )
    )

    return {
        "schema": schema,
        "owner": owner,
        "payload": sanitized,
        "semantic_digest":
            digest(
                sanitized
            ),
        "authority_effect":
            "none",
    }
