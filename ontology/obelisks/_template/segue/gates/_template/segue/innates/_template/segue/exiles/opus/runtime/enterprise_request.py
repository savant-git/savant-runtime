from __future__ import annotations

import hashlib
import json
import math
import re
import time
import uuid
from dataclasses import dataclass
from typing import Any, Iterable, Mapping


schema = (
    "savant://runtime/opus/"
    "enterprise-request/1.0.0"
)

owner = "exile:opus"

request_id_pattern = re.compile(
    r"^[a-z0-9][a-z0-9._:-]{0,127}$"
)

idempotency_pattern = re.compile(
    r"^[A-Za-z0-9._:-]{1,255}$"
)

allowed_priorities = {
    "background",
    "low",
    "normal",
    "high",
    "critical",
}

allowed_privacy = {
    "public",
    "internal",
    "confidential",
    "restricted",
}

allowed_cache_modes = {
    "bypass",
    "read",
    "write",
    "read_write",
}

default_max_messages = 256
default_max_message_chars = 1_000_000
default_max_total_chars = 4_000_000
default_max_tools = 128
default_max_tool_schema_chars = 1_000_000
default_timeout_seconds = 120.0
maximum_timeout_seconds = 900.0
maximum_retry_attempts = 8


class enterprise_request_error(
    ValueError
):
    pass


@dataclass(
    frozen=True
)
class request_limits:
    max_messages: int = (
        default_max_messages
    )

    max_message_chars: int = (
        default_max_message_chars
    )

    max_total_chars: int = (
        default_max_total_chars
    )

    max_tools: int = (
        default_max_tools
    )

    max_tool_schema_chars: int = (
        default_max_tool_schema_chars
    )


def _string(
    value: Any,
) -> str:
    return str(
        value
        if value is not None
        else ""
    ).strip()


def _finite_number(
    value: Any,
    *,
    field: str,
) -> float:
    try:
        number = float(
            value
        )

    except (
        TypeError,
        ValueError,
    ) as exc:
        raise enterprise_request_error(
            f"{field} must be numeric"
        ) from exc

    if not math.isfinite(
        number
    ):
        raise enterprise_request_error(
            f"{field} must be finite"
        )

    return number


def _positive_int(
    value: Any,
    *,
    field: str,
    maximum: int | None = None,
) -> int:
    if isinstance(
        value,
        bool,
    ):
        raise enterprise_request_error(
            f"{field} must be an integer"
        )

    try:
        number = int(
            value
        )

    except (
        TypeError,
        ValueError,
    ) as exc:
        raise enterprise_request_error(
            f"{field} must be an integer"
        ) from exc

    if number < 1:
        raise enterprise_request_error(
            f"{field} must be positive"
        )

    if (
        maximum is not None
        and number > maximum
    ):
        raise enterprise_request_error(
            f"{field} exceeds maximum "
            f"{maximum}"
        )

    return number


def _normalized_strings(
    values: Iterable[Any] | None,
) -> list[str]:
    return sorted(
        {
            _string(
                value
            )
            for value in (
                values or ()
            )
            if _string(
                value
            )
        }
    )


def canonical_json(
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


def digest(
    value: Any,
) -> str:
    return hashlib.sha256(
        canonical_json(
            value
        ).encode(
            "utf-8"
        )
    ).hexdigest()


def _request_id(
    supplied: Any = None,
) -> str:
    value = _string(
        supplied
    )

    if not value:
        return (
            "opusreq_"
            + uuid.uuid4().hex
        )

    if not request_id_pattern.fullmatch(
        value
    ):
        raise enterprise_request_error(
            "invalid request_id"
        )

    return value


def _idempotency_key(
    supplied: Any = None,
) -> str | None:
    value = _string(
        supplied
    )

    if not value:
        return None

    if not idempotency_pattern.fullmatch(
        value
    ):
        raise enterprise_request_error(
            "invalid idempotency_key"
        )

    return value


def _messages(
    value: Any,
    *,
    limits: request_limits,
) -> list[dict[str, Any]]:
    if not isinstance(
        value,
        list,
    ):
        raise enterprise_request_error(
            "messages must be a list"
        )

    if not value:
        raise enterprise_request_error(
            "at least one message "
            "is required"
        )

    if len(
        value
    ) > limits.max_messages:
        raise enterprise_request_error(
            "message count exceeds limit"
        )

    normalized = []
    total_chars = 0

    for index, message in enumerate(
        value
    ):
        if not isinstance(
            message,
            Mapping,
        ):
            raise enterprise_request_error(
                "message "
                f"{index} must be an object"
            )

        role = _string(
            message.get(
                "role"
            )
        )

        if not role:
            raise enterprise_request_error(
                "message "
                f"{index} role is required"
            )

        content = message.get(
            "content"
        )

        if content is None:
            raise enterprise_request_error(
                "message "
                f"{index} content is required"
            )

        if isinstance(
            content,
            str,
        ):
            content_chars = len(
                content
            )

        else:
            try:
                serialized = canonical_json(
                    content
                )

            except (
                TypeError,
                ValueError,
            ) as exc:
                raise enterprise_request_error(
                    "message "
                    f"{index} content is not "
                    "json serializable"
                ) from exc

            content_chars = len(
                serialized
            )

        if (
            content_chars
            > limits.max_message_chars
        ):
            raise enterprise_request_error(
                "message "
                f"{index} exceeds size limit"
            )

        total_chars += (
            content_chars
        )

        if (
            total_chars
            > limits.max_total_chars
        ):
            raise enterprise_request_error(
                "request message content "
                "exceeds total size limit"
            )

        normalized_message = {
            "role": role,
            "content": content,
        }

        name = _string(
            message.get(
                "name"
            )
        )

        if name:
            normalized_message[
                "name"
            ] = name

        tool_call_id = _string(
            message.get(
                "tool_call_id"
            )
        )

        if tool_call_id:
            normalized_message[
                "tool_call_id"
            ] = tool_call_id

        if "tool_calls" in message:
            normalized_message[
                "tool_calls"
            ] = message[
                "tool_calls"
            ]

        normalized.append(
            normalized_message
        )

    return normalized


def _tools(
    value: Any,
    *,
    limits: request_limits,
) -> list[Any]:
    if value is None:
        return []

    if not isinstance(
        value,
        list,
    ):
        raise enterprise_request_error(
            "tools must be a list"
        )

    if len(
        value
    ) > limits.max_tools:
        raise enterprise_request_error(
            "tool count exceeds limit"
        )

    try:
        serialized = canonical_json(
            value
        )

    except (
        TypeError,
        ValueError,
    ) as exc:
        raise enterprise_request_error(
            "tools must be json "
            "serializable"
        ) from exc

    if (
        len(
            serialized
        )
        > limits.max_tool_schema_chars
    ):
        raise enterprise_request_error(
            "tool schemas exceed size limit"
        )

    return list(
        value
    )


def _timeout(
    value: Any,
) -> float:
    if value is None:
        return (
            default_timeout_seconds
        )

    timeout = _finite_number(
        value,
        field="timeout_seconds",
    )

    if timeout <= 0:
        raise enterprise_request_error(
            "timeout_seconds must "
            "be positive"
        )

    if timeout > maximum_timeout_seconds:
        raise enterprise_request_error(
            "timeout_seconds exceeds "
            "maximum"
        )

    return timeout


def _retry_policy(
    value: Any,
) -> dict[str, Any]:
    if value is None:
        return {
            "max_attempts": 1,
            "retry_on_provider_error": (
                False
            ),
            "retry_on_timeout": False,
        }

    if not isinstance(
        value,
        Mapping,
    ):
        raise enterprise_request_error(
            "retry_policy must "
            "be an object"
        )

    attempts = _positive_int(
        value.get(
            "max_attempts",
            1,
        ),
        field="retry_policy.max_attempts",
        maximum=maximum_retry_attempts,
    )

    return {
        "max_attempts": attempts,
        "retry_on_provider_error": bool(
            value.get(
                "retry_on_provider_error",
                False,
            )
        ),
        "retry_on_timeout": bool(
            value.get(
                "retry_on_timeout",
                False,
            )
        ),
    }


def _budget(
    value: Any,
) -> dict[str, Any]:
    if value is None:
        return {}

    if not isinstance(
        value,
        Mapping,
    ):
        raise enterprise_request_error(
            "budget must be an object"
        )

    result = {}

    if "max_input_tokens" in value:
        result[
            "max_input_tokens"
        ] = _positive_int(
            value[
                "max_input_tokens"
            ],
            field=(
                "budget.max_input_tokens"
            ),
        )

    if "max_output_tokens" in value:
        result[
            "max_output_tokens"
        ] = _positive_int(
            value[
                "max_output_tokens"
            ],
            field=(
                "budget.max_output_tokens"
            ),
        )

    if "max_cost" in value:
        maximum_cost = _finite_number(
            value[
                "max_cost"
            ],
            field="budget.max_cost",
        )

        if maximum_cost < 0:
            raise enterprise_request_error(
                "budget.max_cost cannot "
                "be negative"
            )

        result[
            "max_cost"
        ] = maximum_cost

    return result


def _priority(
    value: Any,
) -> str:
    priority = (
        _string(
            value
        ).lower()
        or "normal"
    )

    if priority not in allowed_priorities:
        raise enterprise_request_error(
            "invalid priority"
        )

    return priority


def _privacy(
    value: Any,
) -> str:
    privacy = (
        _string(
            value
        ).lower()
        or "internal"
    )

    if privacy not in allowed_privacy:
        raise enterprise_request_error(
            "invalid privacy classification"
        )

    return privacy


def _cache_mode(
    value: Any,
) -> str:
    mode = (
        _string(
            value
        ).lower()
        or "bypass"
    )

    if mode not in allowed_cache_modes:
        raise enterprise_request_error(
            "invalid cache_mode"
        )

    return mode


def _metadata(
    value: Any,
) -> dict[str, Any]:
    if value is None:
        return {}

    if not isinstance(
        value,
        Mapping,
    ):
        raise enterprise_request_error(
            "metadata must be an object"
        )

    try:
        canonical_json(
            value
        )

    except (
        TypeError,
        ValueError,
    ) as exc:
        raise enterprise_request_error(
            "metadata must be json "
            "serializable"
        ) from exc

    return {
        str(key): item
        for key, item in value.items()
    }


def project(
    request: Mapping[str, Any],
    *,
    limits: request_limits | None = None,
    now_monotonic: float | None = None,
) -> dict[str, Any]:
    if not isinstance(
        request,
        Mapping,
    ):
        raise enterprise_request_error(
            "request must be an object"
        )

    effective_limits = (
        limits
        or request_limits()
    )

    request_id = _request_id(
        request.get(
            "request_id"
        )
    )

    idempotency_key = (
        _idempotency_key(
            request.get(
                "idempotency_key"
            )
        )
    )

    messages = _messages(
        request.get(
            "messages"
        ),
        limits=effective_limits,
    )

    tools = _tools(
        request.get(
            "tools"
        ),
        limits=effective_limits,
    )

    timeout_seconds = _timeout(
        request.get(
            "timeout_seconds"
        )
    )

    monotonic_origin = (
        time.monotonic()
        if now_monotonic is None
        else float(
            now_monotonic
        )
    )

    required_capabilities = (
        _normalized_strings(
            request.get(
                "required_capabilities"
            )
        )
    )

    required_layers = (
        _normalized_strings(
            request.get(
                "required_layers"
            )
        )
    )

    tenant_id = (
        _string(
            request.get(
                "tenant_id"
            )
        )
        or "default"
    )

    trace_id = (
        _string(
            request.get(
                "trace_id"
            )
        )
        or (
            "opustrace_"
            + uuid.uuid4().hex
        )
    )

    payload = {
        "schema": schema,
        "owner": owner,
        "type": (
            "opus_enterprise_request"
        ),
        "request_id": request_id,
        "idempotency_key": (
            idempotency_key
        ),
        "tenant_id": tenant_id,
        "trace_id": trace_id,
        "priority": _priority(
            request.get(
                "priority"
            )
        ),
        "privacy": _privacy(
            request.get(
                "privacy"
            )
        ),
        "cache_mode": _cache_mode(
            request.get(
                "cache_mode"
            )
        ),
        "stream": bool(
            request.get(
                "stream",
                False,
            )
        ),
        "messages": messages,
        "tools": tools,
        "tool_choice": request.get(
            "tool_choice"
        ),
        "required_capabilities": (
            required_capabilities
        ),
        "required_layers": (
            required_layers
        ),
        "requested_model": (
            _string(
                request.get(
                    "requested_model"
                )
            )
            or None
        ),
        "timeout_seconds": (
            timeout_seconds
        ),
        "deadline_monotonic": (
            monotonic_origin
            + timeout_seconds
        ),
        "retry_policy": _retry_policy(
            request.get(
                "retry_policy"
            )
        ),
        "budget": _budget(
            request.get(
                "budget"
            )
        ),
        "metadata": _metadata(
            request.get(
                "metadata"
            )
        ),
        "provenance": {
            "request_owner": (
                _string(
                    request.get(
                        "owner"
                    )
                )
                or "unknown"
            ),
            "request_origin": (
                _string(
                    request.get(
                        "request_origin"
                    )
                )
                or "internal"
            ),
            "client_key_id": (
                _string(
                    request.get(
                        "client_key_id"
                    )
                )
                or None
            ),
            "client_owner": (
                _string(
                    request.get(
                        "client_owner"
                    )
                )
                or None
            ),
        },
        "authority_effect": "none",
        "boundaries": {
            "selects_provider": False,
            "selects_model": False,
            "executes_provider": False,
            "owns_credentials": False,
            "mutates_registry": False,
            "creates_authority": False,
            "authoritative_router": (
                "opus.runtime.router"
            ),
        },
    }

    identity_material = dict(
        payload
    )

    identity_material.pop(
        "deadline_monotonic",
        None,
    )

    payload[
        "canonical_digest"
    ] = digest(
        identity_material
    )

    return payload


def expired(
    envelope: Mapping[str, Any],
    *,
    now_monotonic: float | None = None,
) -> bool:
    deadline = _finite_number(
        envelope.get(
            "deadline_monotonic"
        ),
        field="deadline_monotonic",
    )

    current = (
        time.monotonic()
        if now_monotonic is None
        else float(
            now_monotonic
        )
    )

    return current >= deadline


def replay_projection(
    envelope: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "schema": schema,
        "owner": owner,
        "request_id": envelope.get(
            "request_id"
        ),
        "idempotency_key": (
            envelope.get(
                "idempotency_key"
            )
        ),
        "tenant_id": envelope.get(
            "tenant_id"
        ),
        "trace_id": envelope.get(
            "trace_id"
        ),
        "canonical_digest": (
            envelope.get(
                "canonical_digest"
            )
        ),
        "authority_effect": "none",
        "rebuildable": True,
    }
