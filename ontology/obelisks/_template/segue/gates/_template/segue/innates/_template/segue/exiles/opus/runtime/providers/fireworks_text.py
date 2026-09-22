from __future__ import annotations

import json
import os
import ssl
import urllib.error
import urllib.request
from typing import Any, Dict

from providers.base import ProviderError
from .tool_normalization import make_tool_normalizer


DEFAULT_API_BASE = "https://api.fireworks.ai/inference/v1"


def available() -> bool:
    return bool(
        os.getenv("FIREWORKS_API_KEY")
    )


_normalize_tools = make_tool_normalizer(ProviderError)

def _messages(
    *,
    message: str,
    system: str,
    context: str,
    provider_state: Any,
) -> list[Dict[str, Any]]:
    if provider_state is not None:
        if not isinstance(provider_state, list):
            raise ProviderError(
                "fireworks provider_state must "
                "be a list"
            )

        messages = [
            dict(item)
            for item in provider_state
            if isinstance(item, dict)
        ]
    else:
        messages = []

        if system:
            messages.append(
                {
                    "role": "system",
                    "content": system,
                }
            )

        user_content = message

        if context:
            user_content = (
                "Context:\n"
                + context
                + "\n\nUser:\n"
                + message
            )

        if user_content:
            messages.append(
                {
                    "role": "user",
                    "content": user_content,
                }
            )

    return messages


def _tool_calls(
    message: Dict[str, Any],
) -> list[Dict[str, Any]]:
    result: list[Dict[str, Any]] = []

    raw_calls = message.get(
        "tool_calls"
    )

    if not isinstance(raw_calls, list):
        return result

    for raw_call in raw_calls:
        if not isinstance(raw_call, dict):
            continue

        function = raw_call.get(
            "function"
        )

        if not isinstance(function, dict):
            continue

        name = str(
            function.get("name") or ""
        ).strip()

        call_id = str(
            raw_call.get("id") or ""
        ).strip()

        arguments_raw = function.get(
            "arguments"
        )

        if isinstance(arguments_raw, str):
            try:
                arguments = json.loads(
                    arguments_raw
                )
            except json.JSONDecodeError:
                arguments = {
                    "_raw": arguments_raw
                }
        elif isinstance(arguments_raw, dict):
            arguments = dict(
                arguments_raw
            )
        else:
            arguments = {}

        if name:
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
            "FIREWORKS_API_KEY",
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
        request.get("message")
        or request.get("text")
        or ""
    ).strip()

    provider_state = request.get(
        "provider_state"
    )

    if not message and provider_state is None:
        raise ProviderError(
            "text inference request "
            "missing message"
        )

    system = str(
        request.get("system")
        or ""
    ).strip()

    context = str(
        request.get("context")
        or ""
    ).strip()

    model_env = str(
        provider.get(
            "model_env",
            "SAVANT_FIREWORKS_MODEL",
        )
    )

    model = str(
        request.get("model")
        or os.getenv(model_env)
        or provider.get(
            "model_default",
            (
                "accounts/fireworks/models/"
                "deepseek-v4-pro"
            ),
        )
    ).strip()

    api_base = str(
        os.getenv("FIREWORKS_API_BASE")
        or provider.get("api_base")
        or DEFAULT_API_BASE
    ).rstrip("/")

    messages = _messages(
        message=message,
        system=system,
        context=context,
        provider_state=provider_state,
    )

    payload: Dict[str, Any] = {
        "model": model,
        "messages": messages,
    }

    max_tokens = request.get(
        "max_tokens"
    )

    if max_tokens is not None:
        payload["max_tokens"] = int(
            max_tokens
        )

    tools = _normalize_tools(
        request.get("tools")
    )

    if tools:
        payload["tools"] = tools

        tool_choice = request.get(
            "tool_choice"
        )

        if tool_choice is not None:
            payload[
                "tool_choice"
            ] = tool_choice

    http_request = urllib.request.Request(
        api_base + "/chat/completions",
        data=json.dumps(
            payload
        ).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": (
                f"Bearer {api_key}"
            ),
        },
        method="POST",
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
            context=ssl.create_default_context(),
        ) as response:
            data = json.loads(
                response.read().decode(
                    "utf-8"
                )
            )

    except urllib.error.HTTPError as exc:
        detail = exc.read().decode(
            "utf-8",
            errors="replace",
        )

        raise ProviderError(
            "Fireworks text inference "
            f"failed: HTTP {exc.code}: "
            f"{detail}"
        ) from exc

    except Exception as exc:
        raise ProviderError(
            "Fireworks text inference "
            f"failed: {exc}"
        ) from exc

    choices = data.get(
        "choices"
    )

    if not isinstance(choices, list) or not choices:
        raise ProviderError(
            "Fireworks response lacks choices"
        )

    first = choices[0]

    if not isinstance(first, dict):
        raise ProviderError(
            "Fireworks response choice "
            "must be object"
        )

    assistant = first.get(
        "message"
    )

    if not isinstance(assistant, dict):
        raise ProviderError(
            "Fireworks response lacks "
            "assistant message"
        )

    text = str(
        assistant.get("content")
        or ""
    ).strip()

    tool_calls = _tool_calls(
        assistant
    )

    if not text and not tool_calls:
        raise ProviderError(
            "Fireworks response contained "
            "neither text nor tool calls"
        )

    next_state = list(
        messages
    )

    next_state.append(
        assistant
    )

    return {
        "ok": True,
        "provider": "fireworks_text",
        "model": str(
            data.get("model")
            or model
        ),
        "text": text,
        "tool_calls": tool_calls,
        "usage": data.get(
            "usage",
            {},
        ),
        "provider_response_id": (
            data.get("id")
        ),
        "provider_output": (
            data.get("choices", [])
        ),
        "provider_state": next_state,
    }
