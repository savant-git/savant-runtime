from __future__ import annotations

import json
import os
import ssl
import urllib.error
import urllib.request
from typing import Any, Dict

from providers.base import ProviderError


DEFAULT_API_BASE = "https://api.deepseek.com"


def available() -> bool:
    return bool(os.getenv("DEEPSEEK_API_KEY"))


def _normalize_tools(
    value: Any,
) -> list[Dict[str, Any]]:
    if value is None:
        return []

    if not isinstance(value, list):
        raise ProviderError(
            "text inference tools must be a list"
        )

    result: list[Dict[str, Any]] = []

    for row in value:
        if not isinstance(row, dict):
            raise ProviderError(
                "text inference tool definition "
                "must be object"
            )

        name = str(
            row.get("name") or ""
        ).strip()

        if not name:
            raise ProviderError(
                "text inference tool requires name"
            )

        parameters = row.get("parameters")

        if parameters is None:
            parameters = {
                "type": "object",
                "properties": {},
                "additionalProperties": False,
            }

        if not isinstance(parameters, dict):
            raise ProviderError(
                "text inference tool parameters "
                "must be object"
            )

        result.append(
            {
                "type": "function",
                "function": {
                    "name": name,
                    "description": str(
                        row.get("description") or ""
                    ).strip(),
                    "parameters": parameters,
                },
            }
        )

    return result


def _messages(
    *,
    message: str,
    system: str,
    context: str,
) -> list[Dict[str, Any]]:
    result: list[Dict[str, Any]] = []

    if system:
        result.append(
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

    result.append(
        {
            "role": "user",
            "content": user_content,
        }
    )

    return result


def _tool_calls(
    message: Dict[str, Any],
) -> list[Dict[str, Any]]:
    raw_calls = message.get("tool_calls")

    if not isinstance(raw_calls, list):
        return []

    result: list[Dict[str, Any]] = []

    for raw in raw_calls:
        if not isinstance(raw, dict):
            continue

        function = raw.get("function")

        if not isinstance(function, dict):
            continue

        name = str(
            function.get("name") or ""
        ).strip()

        call_id = str(
            raw.get("id") or ""
        ).strip()

        if not name or not call_id:
            continue

        raw_arguments = function.get(
            "arguments"
        )

        if isinstance(raw_arguments, str):
            try:
                arguments = json.loads(
                    raw_arguments
                )
            except json.JSONDecodeError:
                arguments = {
                    "_raw": raw_arguments,
                }
        elif isinstance(raw_arguments, dict):
            arguments = dict(raw_arguments)
        else:
            arguments = {}

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
            "DEEPSEEK_API_KEY",
        )
    )

    api_key = os.getenv(env_key)

    if not api_key:
        raise ProviderError(
            f"{env_key} missing"
        )

    if request.get("continuation_input") is not None:
        raise ProviderError(
            "deepseek_text does not support "
            "Responses API continuation_input"
        )

    if request.get("previous_response_id"):
        raise ProviderError(
            "deepseek_text does not support "
            "previous_response_id"
        )

    message = str(
        request.get("message")
        or request.get("text")
        or ""
    ).strip()

    if not message:
        raise ProviderError(
            "text inference request missing message"
        )

    system = str(
        request.get("system") or ""
    ).strip()

    context = str(
        request.get("context") or ""
    ).strip()

    model_env = str(
        provider.get(
            "model_env",
            "SAVANT_DEEPSEEK_MODEL",
        )
    )

    model = str(
        request.get("model")
        or os.getenv(model_env)
        or provider.get(
            "model_default",
            "deepseek-v4-pro",
        )
    ).strip()

    api_base = str(
        os.getenv("DEEPSEEK_API_BASE")
        or provider.get("api_base")
        or DEFAULT_API_BASE
    ).rstrip("/")

    payload: Dict[str, Any] = {
        "model": model,
        "messages": _messages(
            message=message,
            system=system,
            context=context,
        ),
    }

    tools = _normalize_tools(
        request.get("tools")
    )

    if tools:
        payload["tools"] = tools

        tool_choice = request.get(
            "tool_choice"
        )

        if tool_choice is not None:
            payload["tool_choice"] = tool_choice

    http_request = urllib.request.Request(
        api_base + "/chat/completions",
        data=json.dumps(payload).encode(
            "utf-8"
        ),
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
        try:
            detail = exc.read().decode(
                "utf-8"
            )
        except Exception:
            detail = str(exc)

        raise ProviderError(
            "DeepSeek text inference failed: "
            f"HTTP {exc.code}: {detail}"
        ) from exc
    except Exception as exc:
        raise ProviderError(
            "DeepSeek text inference failed: "
            f"{exc}"
        ) from exc

    choices = data.get("choices")

    if not isinstance(choices, list) or not choices:
        raise ProviderError(
            "DeepSeek response lacks choices"
        )

    first = choices[0]

    if not isinstance(first, dict):
        raise ProviderError(
            "DeepSeek response choice is invalid"
        )

    response_message = first.get("message")

    if not isinstance(response_message, dict):
        raise ProviderError(
            "DeepSeek response lacks message"
        )

    text = str(
        response_message.get("content") or ""
    ).strip()

    tool_calls = _tool_calls(
        response_message
    )

    if not text and not tool_calls:
        raise ProviderError(
            "DeepSeek response contained neither "
            "text nor tool calls"
        )

    return {
        "ok": True,
        "provider": "deepseek_text",
        "model": model,
        "text": text,
        "tool_calls": tool_calls,
        "usage": data.get("usage", {}),
        "provider_response_id": data.get("id"),
        "provider_output": choices,
    }
