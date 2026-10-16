from __future__ import annotations

import json
import os
import ssl
import urllib.request
from typing import Any, Dict

from providers.base import ProviderError


DEFAULT_API_BASE = "https://api.anthropic.com/v1"
ANTHROPIC_VERSION = "2023-06-01"
PROVIDER_STATE_SCHEMA = (
    "savant.opus.anthropic-text-state.v1"
)


def available() -> bool:
    return bool(
        os.getenv(
            "ANTHROPIC_API_KEY"
        )
    )


def _normalize_tools(
    value: Any,
) -> list[Dict[str, Any]]:
    if value is None:
        return []

    if not isinstance(
        value,
        list,
    ):
        raise ProviderError(
            "text inference tools must "
            "be a list"
        )

    result: list[
        Dict[str, Any]
    ] = []

    for row in value:
        if not isinstance(
            row,
            dict,
        ):
            raise ProviderError(
                "text inference tool "
                "definition must be object"
            )

        name = str(
            row.get(
                "name"
            )
            or ""
        ).strip()

        if not name:
            raise ProviderError(
                "text inference tool "
                "requires name"
            )

        parameters = row.get(
            "parameters"
        )

        if parameters is None:
            parameters = {
                "type": "object",
                "properties": {},
                "additionalProperties": False,
            }

        if not isinstance(
            parameters,
            dict,
        ):
            raise ProviderError(
                "text inference tool "
                "parameters must be object"
            )

        result.append(
            {
                "name": name,
                "description": str(
                    row.get(
                        "description"
                    )
                    or ""
                ).strip(),
                "input_schema": parameters,
            }
        )

    return result


def _normalize_tool_choice(
    value: Any,
) -> Dict[str, Any] | None:
    if value is None:
        return None

    if value == "auto":
        return {
            "type": "auto"
        }

    if value == "required":
        return {
            "type": "any"
        }

    if value == "none":
        return None

    if isinstance(
        value,
        dict,
    ):
        name = str(
            value.get(
                "name"
            )
            or ""
        ).strip()

        function = value.get(
            "function"
        )

        if (
            not name
            and isinstance(
                function,
                dict,
            )
        ):
            name = str(
                function.get(
                    "name"
                )
                or ""
            ).strip()

        if name:
            return {
                "type": "tool",
                "name": name,
            }

    return None


def _initial_messages(
    *,
    message: str,
    context: str,
) -> list[Dict[str, Any]]:
    user_content = message

    if context:
        user_content = (
            "Context:\n"
            + context
            + "\n\nUser:\n"
            + message
        )

    return [
        {
            "role": "user",
            "content": user_content,
        }
    ]


def _load_provider_state(
    value: Any,
) -> list[Dict[str, Any]]:
    if value is None:
        return []

    if not isinstance(
        value,
        dict,
    ):
        raise ProviderError(
            "Anthropic provider_state "
            "must be an object"
        )

    if value.get(
        "schema"
    ) != PROVIDER_STATE_SCHEMA:
        raise ProviderError(
            "Anthropic provider_state "
            "schema mismatch"
        )

    messages = value.get(
        "messages"
    )

    if not isinstance(
        messages,
        list,
    ):
        raise ProviderError(
            "Anthropic provider_state "
            "messages must be a list"
        )

    result: list[
        Dict[str, Any]
    ] = []

    for item in messages:
        if not isinstance(
            item,
            dict,
        ):
            raise ProviderError(
                "Anthropic provider_state "
                "message must be object"
            )

        result.append(
            dict(
                item
            )
        )

    return result


def _tool_result_message(
    continuation_input: Any,
) -> Dict[str, Any]:
    if not isinstance(
        continuation_input,
        list,
    ):
        raise ProviderError(
            "continuation_input must "
            "be a list"
        )

    content: list[
        Dict[str, Any]
    ] = []

    for item in continuation_input:
        if not isinstance(
            item,
            dict,
        ):
            continue

        if (
            item.get(
                "type"
            )
            != "function_call_output"
        ):
            continue

        call_id = str(
            item.get(
                "call_id"
            )
            or ""
        ).strip()

        if not call_id:
            continue

        output = item.get(
            "output"
        )

        if not isinstance(
            output,
            str,
        ):
            output = json.dumps(
                output,
                ensure_ascii=False,
                sort_keys=True,
                default=str,
            )

        content.append(
            {
                "type": "tool_result",
                "tool_use_id": call_id,
                "content": output,
            }
        )

    if not content:
        raise ProviderError(
            "Anthropic continuation "
            "contained no tool results"
        )

    return {
        "role": "user",
        "content": content,
    }


def _response_text(
    data: Dict[str, Any],
) -> str:
    texts: list[str] = []

    for item in data.get(
        "content",
        [],
    ):
        if not isinstance(
            item,
            dict,
        ):
            continue

        if item.get(
            "type"
        ) != "text":
            continue

        text = item.get(
            "text"
        )

        if (
            isinstance(
                text,
                str,
            )
            and text
        ):
            texts.append(
                text
            )

    return "\n".join(
        texts
    ).strip()


def _response_tool_calls(
    data: Dict[str, Any],
) -> list[Dict[str, Any]]:
    result: list[
        Dict[str, Any]
    ] = []

    for item in data.get(
        "content",
        [],
    ):
        if not isinstance(
            item,
            dict,
        ):
            continue

        if item.get(
            "type"
        ) != "tool_use":
            continue

        call_id = str(
            item.get(
                "id"
            )
            or ""
        ).strip()

        name = str(
            item.get(
                "name"
            )
            or ""
        ).strip()

        arguments = item.get(
            "input"
        )

        if not isinstance(
            arguments,
            dict,
        ):
            arguments = {}

        if not call_id or not name:
            continue

        result.append(
            {
                "call_id": call_id,
                "name": name,
                "arguments": arguments,
            }
        )

    return result


def infer(
    request: Dict[str, Any],
    provider: Dict[str, Any],
) -> Dict[str, Any]:
    env_key = str(
        provider.get(
            "env_key",
            "ANTHROPIC_API_KEY",
        )
    )

    api_key = os.getenv(
        env_key
    )

    if not api_key:
        raise ProviderError(
            f"{env_key} missing"
        )

    message = str(
        request.get(
            "message"
        )
        or request.get(
            "text"
        )
        or ""
    ).strip()

    continuation_input = (
        request.get(
            "continuation_input"
        )
    )

    if (
        not message
        and continuation_input is None
    ):
        raise ProviderError(
            "text inference request "
            "missing message"
        )

    system = str(
        request.get(
            "system"
        )
        or ""
    ).strip()

    context = str(
        request.get(
            "context"
        )
        or ""
    ).strip()

    model_env = str(
        provider.get(
            "model_env",
            "SAVANT_ANTHROPIC_MODEL",
        )
    )

    model = str(
        request.get(
            "model"
        )
        or os.getenv(
            model_env
        )
        or provider.get(
            "model_default",
            "claude-sonnet-4-20250514",
        )
    ).strip()

    api_base = str(
        os.getenv(
            "ANTHROPIC_API_BASE"
        )
        or provider.get(
            "api_base"
        )
        or DEFAULT_API_BASE
    ).rstrip("/")

    provider_state = request.get(
        "provider_state"
    )

    if continuation_input is None:
        messages = _initial_messages(
            message=message,
            context=context,
        )
    else:
        messages = _load_provider_state(
            provider_state
        )

        if not messages:
            raise ProviderError(
                "Anthropic continuation "
                "requires provider_state"
            )

        messages.append(
            _tool_result_message(
                continuation_input
            )
        )

    payload: Dict[
        str,
        Any,
    ] = {
        "model": model,
        "max_tokens": int(
            request.get(
                "max_tokens"
            )
            or provider.get(
                "max_tokens",
                4096,
            )
        ),
        "messages": messages,
    }

    if system:
        payload[
            "system"
        ] = system

    tools = _normalize_tools(
        request.get(
            "tools"
        )
    )

    if tools:
        payload[
            "tools"
        ] = tools

        choice = (
            _normalize_tool_choice(
                request.get(
                    "tool_choice"
                )
            )
        )

        if choice is not None:
            payload[
                "tool_choice"
            ] = choice

    http_request = (
        urllib.request.Request(
            api_base
            + "/messages",
            data=json.dumps(
                payload
            ).encode(
                "utf-8"
            ),
            headers={
                "Content-Type": (
                    "application/json"
                ),
                "x-api-key": api_key,
                "anthropic-version": (
                    ANTHROPIC_VERSION
                ),
            },
            method="POST",
        )
    )

    timeout = int(
        provider.get(
            "timeout_seconds",
            120,
        )
    )

    try:
        with urllib.request.urlopen(
            http_request,
            timeout=timeout,
            context=(
                ssl.create_default_context()
            ),
        ) as response:
            data = json.loads(
                response.read().decode(
                    "utf-8"
                )
            )
    except Exception as exc:
        raise ProviderError(
            "Anthropic text inference "
            f"failed: {exc}"
        ) from exc

    text = _response_text(
        data
    )

    tool_calls = (
        _response_tool_calls(
            data
        )
    )

    if (
        not text
        and not tool_calls
    ):
        raise ProviderError(
            "Anthropic response contained "
            "neither text nor tool calls"
        )

    response_content = data.get(
        "content",
        [],
    )

    if not isinstance(
        response_content,
        list,
    ):
        response_content = []

    next_messages = [
        dict(
            item
        )
        for item in messages
    ]

    next_messages.append(
        {
            "role": "assistant",
            "content": response_content,
        }
    )

    return {
        "ok": True,
        "provider": "anthropic_text",
        "model": model,
        "text": text,
        "tool_calls": tool_calls,
        "usage": data.get(
            "usage",
            {},
        ),
        "provider_response_id": (
            data.get(
                "id"
            )
        ),
        "provider_output": (
            response_content
        ),
        "provider_state": {
            "schema": (
                PROVIDER_STATE_SCHEMA
            ),
            "messages": next_messages,
        },
    }
