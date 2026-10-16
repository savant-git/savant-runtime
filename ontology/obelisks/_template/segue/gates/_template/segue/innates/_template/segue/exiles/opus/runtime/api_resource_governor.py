from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from typing import Any, Mapping


schema = (
    "savant://runtime/opus/"
    "api-resource-governor/1.0.0"
)

owner = "exile:opus"


class api_resource_error(
    ValueError
):
    pass


@dataclass(
    frozen=True
)
class resource_policy:
    max_body_bytes: int = 8_388_608
    max_messages: int = 256
    max_tools: int = 128
    max_metadata_keys: int = 128
    max_string_chars: int = 1_000_000
    max_container_items: int = 4096
    max_depth: int = 32
    max_output_tokens: int = 262_144


def _canonical_json(
    value: Any,
) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(
            ",",
            ":",
        ),
        ensure_ascii=False,
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


def _walk(
    value: Any,
    *,
    policy: resource_policy,
    depth: int = 0,
) -> dict[str, int]:
    if depth > policy.max_depth:
        raise api_resource_error(
            "request nesting exceeds limit"
        )

    metrics = {
        "nodes": 1,
        "strings": 0,
        "string_chars": 0,
        "container_items": 0,
    }

    if isinstance(
        value,
        str,
    ):
        size = len(
            value
        )

        if size > policy.max_string_chars:
            raise api_resource_error(
                "request string exceeds limit"
            )

        metrics[
            "strings"
        ] = 1

        metrics[
            "string_chars"
        ] = size

        return metrics

    if isinstance(
        value,
        Mapping,
    ):
        if len(
            value
        ) > policy.max_container_items:
            raise api_resource_error(
                "request object exceeds "
                "item limit"
            )

        metrics[
            "container_items"
        ] += len(
            value
        )

        children = value.items()

    elif isinstance(
        value,
        (
            list,
            tuple,
        ),
    ):
        if len(
            value
        ) > policy.max_container_items:
            raise api_resource_error(
                "request array exceeds "
                "item limit"
            )

        metrics[
            "container_items"
        ] += len(
            value
        )

        children = enumerate(
            value
        )

    else:
        if isinstance(
            value,
            float,
        ) and not math.isfinite(
            value
        ):
            raise api_resource_error(
                "non-finite numeric value"
            )

        return metrics

    for key, child in children:
        if isinstance(
            value,
            Mapping,
        ):
            key_metrics = _walk(
                str(
                    key
                ),
                policy=policy,
                depth=depth + 1,
            )

            for name, count in (
                key_metrics.items()
            ):
                metrics[
                    name
                ] += count

        child_metrics = _walk(
            child,
            policy=policy,
            depth=depth + 1,
        )

        for name, count in (
            child_metrics.items()
        ):
            metrics[
                name
            ] += count

    return metrics


def evaluate(
    payload: Mapping[str, Any],
    *,
    body_bytes: int | None = None,
    policy: resource_policy | None = None,
) -> dict[str, Any]:
    if not isinstance(
        payload,
        Mapping,
    ):
        raise api_resource_error(
            "request payload must "
            "be an object"
        )

    effective = (
        policy
        or resource_policy()
    )

    if body_bytes is not None:
        try:
            body_size = int(
                body_bytes
            )

        except (
            TypeError,
            ValueError,
        ) as exc:
            raise api_resource_error(
                "body_bytes must "
                "be an integer"
            ) from exc

        if body_size < 0:
            raise api_resource_error(
                "body_bytes cannot "
                "be negative"
            )

        if (
            body_size
            > effective.max_body_bytes
        ):
            raise api_resource_error(
                "request body exceeds limit"
            )

    else:
        body_size = len(
            _canonical_json(
                payload
            ).encode(
                "utf-8"
            )
        )

        if (
            body_size
            > effective.max_body_bytes
        ):
            raise api_resource_error(
                "request body exceeds limit"
            )

    messages = payload.get(
        "messages"
    )

    if (
        isinstance(
            messages,
            list,
        )
        and len(
            messages
        ) > effective.max_messages
    ):
        raise api_resource_error(
            "message count exceeds limit"
        )

    tools = payload.get(
        "tools"
    )

    if (
        isinstance(
            tools,
            list,
        )
        and len(
            tools
        ) > effective.max_tools
    ):
        raise api_resource_error(
            "tool count exceeds limit"
        )

    metadata = payload.get(
        "metadata"
    )

    if (
        isinstance(
            metadata,
            Mapping,
        )
        and len(
            metadata
        ) > effective.max_metadata_keys
    ):
        raise api_resource_error(
            "metadata key count "
            "exceeds limit"
        )

    max_tokens = payload.get(
        "max_tokens"
    )

    if max_tokens is not None:
        if isinstance(
            max_tokens,
            bool,
        ):
            raise api_resource_error(
                "max_tokens must "
                "be an integer"
            )

        try:
            max_tokens_value = int(
                max_tokens
            )

        except (
            TypeError,
            ValueError,
        ) as exc:
            raise api_resource_error(
                "max_tokens must "
                "be an integer"
            ) from exc

        if (
            max_tokens_value < 1
            or max_tokens_value
            > effective.max_output_tokens
        ):
            raise api_resource_error(
                "max_tokens outside "
                "allowed range"
            )

    metrics = _walk(
        payload,
        policy=effective,
    )

    projection = {
        "schema": schema,
        "owner": owner,
        "authority_effect": "none",
        "projection_only": True,
        "accepted": True,
        "metrics": {
            "body_bytes": body_size,
            **metrics,
        },
        "limits": {
            "max_body_bytes": (
                effective.max_body_bytes
            ),
            "max_messages": (
                effective.max_messages
            ),
            "max_tools": (
                effective.max_tools
            ),
            "max_metadata_keys": (
                effective.max_metadata_keys
            ),
            "max_string_chars": (
                effective.max_string_chars
            ),
            "max_container_items": (
                effective.max_container_items
            ),
            "max_depth": (
                effective.max_depth
            ),
            "max_output_tokens": (
                effective.max_output_tokens
            ),
        },
        "boundaries": {
            "selects_provider": False,
            "selects_model": False,
            "executes_provider": False,
            "owns_credentials": False,
            "creates_authority": False,
        },
    }

    projection[
        "digest"
    ] = _digest(
        projection
    )

    return projection
