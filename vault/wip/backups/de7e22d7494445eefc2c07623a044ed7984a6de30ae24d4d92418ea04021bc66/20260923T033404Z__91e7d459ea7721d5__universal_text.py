#!/usr/bin/env python3

from __future__ import annotations

import json
import os
import ssl
from pathlib import Path
from typing import Any, Dict
import urllib.error
import urllib.parse
import urllib.request

from providers.base import ProviderError


OPUS_ROOT = Path(
    __file__
).resolve().parents[2]

CATALOG_PATH = (
    OPUS_ROOT
    / "registry"
    / "providers"
    / "universal_text_catalog.json"
)

DEFAULT_PROFILE = "custom"


def available() -> bool:
    return True


def _read_catalog() -> Dict[str, Any]:
    try:
        value = json.loads(
            CATALOG_PATH.read_text(
                encoding="utf-8"
            )
        )
    except FileNotFoundError as exc:
        raise ProviderError(
            "universal provider catalog missing"
        ) from exc
    except json.JSONDecodeError as exc:
        raise ProviderError(
            "invalid universal provider catalog"
        ) from exc

    if not isinstance(
        value,
        dict,
    ):
        raise ProviderError(
            "universal provider catalog must be an object"
        )

    return value


def _request_config(
    request: Dict[str, Any],
) -> Dict[str, Any]:
    profile_id = str(
        request.get(
            "provider_profile"
        )
        or os.getenv(
            "OPUS_UNIVERSAL_PROVIDER",
            DEFAULT_PROFILE,
        )
    ).strip().lower()

    catalog = _read_catalog()

    profiles = catalog.get(
        "profiles"
    )

    if not isinstance(
        profiles,
        dict,
    ):
        raise ProviderError(
            "universal provider catalog profiles missing"
        )

    base = profiles.get(
        profile_id
    )

    if not isinstance(
        base,
        dict,
    ):
        raise ProviderError(
            "unknown universal provider profile: "
            f"{profile_id}"
        )

    config = dict(
        base
    )

    override = request.get(
        "provider_config"
    )

    if override is not None:
        if not isinstance(
            override,
            dict,
        ):
            raise ProviderError(
                "provider_config must be an object"
            )

        config.update(
            override
        )

    config[
        "profile_id"
    ] = profile_id

    return config


def _env_value(
    config: Dict[str, Any],
    key: str,
    *,
    fallback_key: str | None = None,
) -> str:
    env_name = str(
        config.get(
            key
        )
        or ""
    ).strip()

    if env_name:
        value = str(
            os.getenv(
                env_name,
                "",
            )
            or ""
        ).strip()

        if value:
            return value

    if fallback_key:
        fallback_env = str(
            config.get(
                fallback_key
            )
            or ""
        ).strip()

        if fallback_env:
            return str(
                os.getenv(
                    fallback_env,
                    "",
                )
                or ""
            ).strip()

    return ""


def _api_base(
    config: Dict[str, Any],
) -> str:
    direct = str(
        config.get(
            "api_base"
        )
        or ""
    ).strip()

    env_name = str(
        config.get(
            "api_base_env"
        )
        or ""
    ).strip()

    env_value = (
        str(
            os.getenv(
                env_name,
                "",
            )
            or ""
        ).strip()
        if env_name
        else ""
    )

    value = (
        env_value
        or direct
    ).rstrip("/")

    if not value:
        raise ProviderError(
            "universal provider api base missing"
        )

    return value


def _model(
    request: Dict[str, Any],
    provider: Dict[str, Any],
    config: Dict[str, Any],
) -> str:
    model_env = str(
        config.get(
            "model_env"
        )
        or provider.get(
            "model_env"
        )
        or ""
    ).strip()

    env_model = (
        str(
            os.getenv(
                model_env,
                "",
            )
            or ""
        ).strip()
        if model_env
        else ""
    )

    model = str(
        request.get(
            "model"
        )
        or env_model
        or config.get(
            "model_default"
        )
        or provider.get(
            "model_default"
        )
        or ""
    ).strip()

    if not model:
        raise ProviderError(
            "universal provider model missing"
        )

    return model


def _message(
    request: Dict[str, Any],
) -> str:
    return str(
        request.get(
            "message"
        )
        or request.get(
            "text"
        )
        or ""
    ).strip()


def _combined_user(
    request: Dict[str, Any],
) -> str:
    message = _message(
        request
    )

    context = str(
        request.get(
            "context"
        )
        or ""
    ).strip()

    if context:
        return (
            "Context:\n"
            + context
            + "\n\nUser:\n"
            + message
        )

    return message


def _headers(
    config: Dict[str, Any],
    *,
    protocol: str,
) -> Dict[str, str]:
    result = {
        "Content-Type":
            "application/json",
    }

    static_headers = config.get(
        "headers"
    )

    if isinstance(
        static_headers,
        dict,
    ):
        for key, value in static_headers.items():
            result[
                str(key)
            ] = str(
                value
            )

    header_env = config.get(
        "header_env"
    )

    if isinstance(
        header_env,
        dict,
    ):
        for header, env_name in header_env.items():
            value = os.getenv(
                str(
                    env_name
                ),
                "",
            )

            if value:
                result[
                    str(
                        header
                    )
                ] = value

    api_key = _env_value(
        config,
        "api_key_env",
        fallback_key=(
            "api_key_env_fallback"
        ),
    )

    optional = bool(
        config.get(
            "api_key_optional",
            False,
        )
    )

    if (
        not api_key
        and not optional
    ):
        raise ProviderError(
            "universal provider credential missing"
        )

    if api_key:
        if protocol == "anthropic_messages":
            result[
                "x-api-key"
            ] = api_key

            result[
                "anthropic-version"
            ] = str(
                config.get(
                    "anthropic_version",
                    "2023-06-01",
                )
            )

        elif protocol != "gemini_generate_content":
            result[
                "Authorization"
            ] = (
                f"Bearer {api_key}"
            )

    return result


def _openai_responses_payload(
    request: Dict[str, Any],
    model: str,
) -> Dict[str, Any]:
    message = _combined_user(
        request
    )

    continuation = request.get(
        "continuation_input"
    )

    if continuation is not None:
        if not isinstance(
            continuation,
            list,
        ):
            raise ProviderError(
                "continuation_input must be a list"
            )

        inputs = [
            dict(
                row
            )
            for row in continuation
            if isinstance(
                row,
                dict,
            )
        ]

    else:
        if not message:
            raise ProviderError(
                "text inference request missing message"
            )

        inputs = []

        system = str(
            request.get(
                "system"
            )
            or ""
        ).strip()

        if system:
            inputs.append(
                {
                    "role":
                        "system",
                    "content":
                        system,
                }
            )

        inputs.append(
            {
                "role":
                    "user",
                "content":
                    message,
            }
        )

    payload: Dict[str, Any] = {
        "model":
            model,
        "input":
            inputs,
    }

    previous = str(
        request.get(
            "previous_response_id"
        )
        or ""
    ).strip()

    if previous:
        payload[
            "previous_response_id"
        ] = previous

    tools = request.get(
        "tools"
    )

    if isinstance(
        tools,
        list,
    ) and tools:
        payload[
            "tools"
        ] = tools

        if request.get(
            "tool_choice"
        ) is not None:
            payload[
                "tool_choice"
            ] = request[
                "tool_choice"
            ]

    return payload


def _openai_chat_payload(
    request: Dict[str, Any],
    model: str,
) -> Dict[str, Any]:
    message = _combined_user(
        request
    )

    if not message:
        raise ProviderError(
            "text inference request missing message"
        )

    messages = []

    system = str(
        request.get(
            "system"
        )
        or ""
    ).strip()

    if system:
        messages.append(
            {
                "role":
                    "system",
                "content":
                    system,
            }
        )

    messages.append(
        {
            "role":
                "user",
            "content":
                message,
        }
    )

    payload: Dict[str, Any] = {
        "model":
            model,
        "messages":
            messages,
    }

    tools = request.get(
        "tools"
    )

    if isinstance(
        tools,
        list,
    ) and tools:
        normalized = []

        for tool in tools:
            if not isinstance(
                tool,
                dict,
            ):
                continue

            if tool.get(
                "type"
            ) == "function":
                normalized.append(
                    tool
                )

            else:
                normalized.append(
                    {
                        "type":
                            "function",
                        "function": {
                            "name":
                                str(
                                    tool.get(
                                        "name",
                                        "",
                                    )
                                ),
                            "description":
                                str(
                                    tool.get(
                                        "description",
                                        "",
                                    )
                                ),
                            "parameters":
                                tool.get(
                                    "parameters"
                                )
                                or {
                                    "type":
                                        "object",
                                    "properties":
                                        {},
                                },
                        },
                    }
                )

        if normalized:
            payload[
                "tools"
            ] = normalized

        if request.get(
            "tool_choice"
        ) is not None:
            payload[
                "tool_choice"
            ] = request[
                "tool_choice"
            ]

    return payload


def _anthropic_payload(
    request: Dict[str, Any],
    model: str,
) -> Dict[str, Any]:
    message = _combined_user(
        request
    )

    if not message:
        raise ProviderError(
            "text inference request missing message"
        )

    payload: Dict[str, Any] = {
        "model":
            model,
        "max_tokens":
            int(
                request.get(
                    "max_tokens",
                    4096,
                )
            ),
        "messages": [
            {
                "role":
                    "user",
                "content":
                    message,
            }
        ],
    }

    system = str(
        request.get(
            "system"
        )
        or ""
    ).strip()

    if system:
        payload[
            "system"
        ] = system

    return payload


def _gemini_payload(
    request: Dict[str, Any],
) -> Dict[str, Any]:
    message = _combined_user(
        request
    )

    if not message:
        raise ProviderError(
            "text inference request missing message"
        )

    payload: Dict[str, Any] = {
        "contents": [
            {
                "role":
                    "user",
                "parts": [
                    {
                        "text":
                            message,
                    }
                ],
            }
        ]
    }

    system = str(
        request.get(
            "system"
        )
        or ""
    ).strip()

    if system:
        payload[
            "systemInstruction"
        ] = {
            "parts": [
                {
                    "text":
                        system,
                }
            ]
        }

    return payload


def _request_url(
    config: Dict[str, Any],
    protocol: str,
    model: str,
) -> str:
    base = _api_base(
        config
    )

    endpoint = str(
        config.get(
            "endpoint"
        )
        or ""
    ).strip()

    if endpoint:
        return (
            base
            + "/"
            + endpoint.lstrip("/")
        )

    if protocol == "openai_responses":
        return (
            base
            + "/responses"
        )

    if protocol == "openai_chat":
        return (
            base
            + "/chat/completions"
        )

    if protocol == "anthropic_messages":
        return (
            base
            + "/messages"
        )

    if protocol == "gemini_generate_content":
        api_key = _env_value(
            config,
            "api_key_env",
            fallback_key=(
                "api_key_env_fallback"
            ),
        )

        if not api_key:
            raise ProviderError(
                "gemini credential missing"
            )

        encoded_model = (
            urllib.parse.quote(
                model,
                safe="-._/",
            )
        )

        encoded_key = (
            urllib.parse.quote(
                api_key,
                safe="",
            )
        )

        return (
            base
            + "/models/"
            + encoded_model
            + ":generateContent?key="
            + encoded_key
        )

    if protocol == "generic_json":
        if not endpoint:
            raise ProviderError(
                "generic_json endpoint missing"
            )

        return (
            base
            + "/"
            + endpoint.lstrip("/")
        )

    raise ProviderError(
        "unsupported universal protocol: "
        f"{protocol}"
    )


def _post_json(
    url: str,
    payload: Dict[str, Any],
    headers: Dict[str, str],
    timeout: int,
) -> Dict[str, Any]:
    request = urllib.request.Request(
        url,
        data=json.dumps(
            payload
        ).encode(
            "utf-8"
        ),
        headers=headers,
        method="POST",
    )

    try:
        with urllib.request.urlopen(
            request,
            timeout=timeout,
            context=ssl.create_default_context(),
        ) as response:
            raw = response.read().decode(
                "utf-8"
            )

    except urllib.error.HTTPError as exc:
        raise ProviderError(
            "universal provider http failure: "
            f"{exc.code}"
        ) from exc

    except urllib.error.URLError as exc:
        reason = type(
            exc.reason
        ).__name__

        raise ProviderError(
            "universal provider network failure: "
            f"{reason}"
        ) from exc

    except TimeoutError as exc:
        raise ProviderError(
            "universal provider timeout"
        ) from exc

    except Exception as exc:
        raise ProviderError(
            "universal provider request failed: "
            f"{type(exc).__name__}"
        ) from exc

    try:
        value = json.loads(
            raw
        )
    except json.JSONDecodeError as exc:
        raise ProviderError(
            "universal provider returned invalid json"
        ) from exc

    if not isinstance(
        value,
        dict,
    ):
        raise ProviderError(
            "universal provider response must be object"
        )

    return value


def _openai_responses_text(
    data: Dict[str, Any],
) -> str:
    direct = data.get(
        "output_text"
    )

    if isinstance(
        direct,
        str,
    ) and direct.strip():
        return direct.strip()

    result = []

    for item in data.get(
        "output",
        [],
    ):
        if not isinstance(
            item,
            dict,
        ):
            continue

        for content in item.get(
            "content",
            [],
        ):
            if not isinstance(
                content,
                dict,
            ):
                continue

            text = content.get(
                "text"
            )

            if isinstance(
                text,
                str,
            ) and text:
                result.append(
                    text
                )

    return "\n".join(
        result
    ).strip()


def _openai_chat_text(
    data: Dict[str, Any],
) -> str:
    choices = data.get(
        "choices"
    )

    if not isinstance(
        choices,
        list,
    ):
        return ""

    parts = []

    for choice in choices:
        if not isinstance(
            choice,
            dict,
        ):
            continue

        message = choice.get(
            "message"
        )

        if not isinstance(
            message,
            dict,
        ):
            continue

        content = message.get(
            "content"
        )

        if isinstance(
            content,
            str,
        ) and content:
            parts.append(
                content
            )

    return "\n".join(
        parts
    ).strip()


def _anthropic_text(
    data: Dict[str, Any],
) -> str:
    parts = []

    for row in data.get(
        "content",
        [],
    ):
        if not isinstance(
            row,
            dict,
        ):
            continue

        if row.get(
            "type"
        ) != "text":
            continue

        text = row.get(
            "text"
        )

        if isinstance(
            text,
            str,
        ) and text:
            parts.append(
                text
            )

    return "\n".join(
        parts
    ).strip()


def _gemini_text(
    data: Dict[str, Any],
) -> str:
    parts = []

    for candidate in data.get(
        "candidates",
        [],
    ):
        if not isinstance(
            candidate,
            dict,
        ):
            continue

        content = candidate.get(
            "content"
        )

        if not isinstance(
            content,
            dict,
        ):
            continue

        for row in content.get(
            "parts",
            [],
        ):
            if not isinstance(
                row,
                dict,
            ):
                continue

            text = row.get(
                "text"
            )

            if isinstance(
                text,
                str,
            ) and text:
                parts.append(
                    text
                )

    return "\n".join(
        parts
    ).strip()


def _extract_generic_path(
    value: Any,
    path: str,
) -> Any:
    current = value

    for part in path.split(
        "."
    ):
        if isinstance(
            current,
            dict,
        ):
            current = current.get(
                part
            )

        elif (
            isinstance(
                current,
                list,
            )
            and part.isdigit()
        ):
            index = int(
                part
            )

            if index >= len(
                current
            ):
                return None

            current = current[
                index
            ]

        else:
            return None

    return current


def _generic_text(
    data: Dict[str, Any],
    config: Dict[str, Any],
) -> str:
    paths = config.get(
        "text_paths"
    ) or [
        "text",
        "output_text",
        "response",
        "answer",
        "result.text",
        "choices.0.message.content",
    ]

    for path in paths:
        value = _extract_generic_path(
            data,
            str(
                path
            ),
        )

        if (
            isinstance(
                value,
                str,
            )
            and value.strip()
        ):
            return value.strip()

    return ""


def infer(
    request: Dict[str, Any],
    provider: Dict[str, Any],
) -> Dict[str, Any]:
    if not isinstance(
        request,
        dict,
    ):
        raise ProviderError(
            "request must be an object"
        )

    config = _request_config(
        request
    )

    protocol = str(
        config.get(
            "protocol"
        )
        or "openai_chat"
    ).strip().lower()

    model = _model(
        request,
        provider,
        config,
    )

    if protocol == "openai_responses":
        payload = (
            _openai_responses_payload(
                request,
                model,
            )
        )

    elif protocol == "openai_chat":
        payload = (
            _openai_chat_payload(
                request,
                model,
            )
        )

    elif protocol == "anthropic_messages":
        payload = (
            _anthropic_payload(
                request,
                model,
            )
        )

    elif protocol == "gemini_generate_content":
        payload = (
            _gemini_payload(
                request
            )
        )

    elif protocol == "generic_json":
        body = request.get(
            "provider_body"
        )

        if not isinstance(
            body,
            dict,
        ):
            raise ProviderError(
                "generic_json requires provider_body object"
            )

        payload = dict(
            body
        )

    else:
        raise ProviderError(
            "unsupported universal protocol: "
            f"{protocol}"
        )

    headers = _headers(
        config,
        protocol=protocol,
    )

    url = _request_url(
        config,
        protocol,
        model,
    )

    timeout = int(
        request.get(
            "timeout_seconds"
        )
        or provider.get(
            "timeout_seconds",
            120,
        )
    )

    data = _post_json(
        url,
        payload,
        headers,
        timeout,
    )

    if protocol == "openai_responses":
        text = (
            _openai_responses_text(
                data
            )
        )

    elif protocol == "openai_chat":
        text = (
            _openai_chat_text(
                data
            )
        )

    elif protocol == "anthropic_messages":
        text = (
            _anthropic_text(
                data
            )
        )

    elif protocol == "gemini_generate_content":
        text = (
            _gemini_text(
                data
            )
        )

    else:
        text = _generic_text(
            data,
            config,
        )

    if not text:
        raise ProviderError(
            "universal provider response contained no text"
        )

    return {
        "ok":
            True,
        "provider":
            "universal_text",
        "provider_profile":
            config.get(
                "profile_id"
            ),
        "protocol":
            protocol,
        "model":
            model,
        "text":
            text,
        "usage":
            data.get(
                "usage"
            )
            or data.get(
                "usageMetadata"
            )
            or {},
        "provider_response_id":
            data.get(
                "id"
            ),
        "authority_effect":
            "none",
    }
