from __future__ import annotations

import json
import os
import ssl
import urllib.request
from typing import Any, Dict

from providers.base import ProviderError
from .response_text import response_text


OPENAI_RESPONSES_URL = "https://api.openai.com/v1/responses"


def available() -> bool:
    return bool(
        os.getenv(
            "OPENAI_API_KEY"
        )
    )


def response_tool_calls(
    data: Dict[str, Any],
) -> list[Dict[str, Any]]:
    result: list[
        Dict[str, Any]
    ] = []

    for item in data.get(
        "output",
        [],
    ):
        if not isinstance(
            item,
            dict,
        ):
            continue

        item_type = str(
            item.get(
                "type"
            )
            or ""
        ).strip()

        if item_type not in {
            "function_call",
            "tool_call",
        }:
            continue

        name = str(
            item.get(
                "name"
            )
            or ""
        ).strip()

        call_id = str(
            item.get(
                "call_id"
            )
            or item.get(
                "id"
            )
            or ""
        ).strip()

        arguments_raw = item.get(
            "arguments"
        )

        if isinstance(
            arguments_raw,
            str,
        ):
            try:
                arguments = json.loads(
                    arguments_raw
                )
            except json.JSONDecodeError:
                arguments = {
                    "_raw": arguments_raw,
                }
        elif isinstance(
            arguments_raw,
            dict,
        ):
            arguments = dict(
                arguments_raw
            )
        else:
            arguments = {}

        if not name:
            continue

        result.append(
            {
                "call_id": call_id,
                "name": name,
                "arguments": arguments,
            }
        )

    return result


def normalize_tools(
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

        description = str(
            row.get(
                "description"
            )
            or ""
        ).strip()

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
                "type": "function",
                "name": name,
                "description": description,
                "parameters": parameters,
            }
        )

    return result


def normalize_input_images(
    value: Any,
) -> list[Dict[str, Any]]:
    if value is None:
        return []

    if not isinstance(
        value,
        list,
    ):
        raise ProviderError(
            "input_images must be a list"
        )

    result: list[
        Dict[str, Any]
    ] = []

    for index, row in enumerate(
        value,
        start=1,
    ):
        if isinstance(
            row,
            str,
        ):
            source = row.strip()
            detail = "auto"
            label = (
                f"image-{index}"
            )
        elif isinstance(
            row,
            dict,
        ):
            source = str(
                row.get(
                    "source"
                )
                or row.get(
                    "url"
                )
                or row.get(
                    "image_url"
                )
                or ""
            ).strip()

            detail = str(
                row.get(
                    "detail"
                )
                or "auto"
            ).strip().lower()

            label = str(
                row.get(
                    "label"
                )
                or f"image-{index}"
            ).strip()
        else:
            raise ProviderError(
                "each input image must "
                "be a string or object"
            )

        if not source:
            raise ProviderError(
                "input image source "
                "is required"
            )

        if not (
            source.startswith(
                "https://"
            )
            or source.startswith(
                "http://"
            )
            or source.startswith(
                "data:image/"
            )
        ):
            raise ProviderError(
                "input image source must "
                "be an http(s) URL or "
                "image data URL"
            )

        if detail not in {
            "auto",
            "low",
            "high",
        }:
            raise ProviderError(
                "input image detail must "
                "be auto, low, or high"
            )

        result.append(
            {
                "source": source,
                "detail": detail,
                "label": label,
            }
        )

    return result


def build_input_items(
    *,
    message: str,
    system: str,
    context: str,
    continuation_input: Any,
    input_images: Any = None,
) -> list[Dict[str, Any]]:
    images = normalize_input_images(
        input_images
    )

    if continuation_input is not None:
        if images:
            raise ProviderError(
                "input_images cannot be "
                "combined with "
                "continuation_input"
            )

        if not isinstance(
            continuation_input,
            list,
        ):
            raise ProviderError(
                "continuation_input must "
                "be a list"
            )

        return [
            dict(
                item
            )
            for item in continuation_input
            if isinstance(
                item,
                dict,
            )
        ]

    user_text = message

    if context:
        user_text = (
            "Context:\n"
            + context
            + "\n\nUser:\n"
            + message
        )

    input_items: list[
        Dict[str, Any]
    ] = []

    if system:
        input_items.append(
            {
                "role": "system",
                "content": system,
            }
        )

    if images:
        content: list[
            Dict[str, Any]
        ] = []

        if user_text:
            content.append(
                {
                    "type": "input_text",
                    "text": user_text,
                }
            )

        for image in images:
            content.append(
                {
                    "type": "input_text",
                    "text": (
                        "Reference label: "
                        + image[
                            "label"
                        ]
                    ),
                }
            )

            content.append(
                {
                    "type": "input_image",
                    "image_url": image[
                        "source"
                    ],
                    "detail": image[
                        "detail"
                    ],
                }
            )

        input_items.append(
            {
                "role": "user",
                "content": content,
            }
        )
    else:
        input_items.append(
            {
                "role": "user",
                "content": user_text,
            }
        )

    return input_items


def infer(
    request: Dict[str, Any],
    provider: Dict[str, Any],
) -> Dict[str, Any]:
    api_key = os.getenv(
        str(
            provider.get(
                "env_key",
                "OPENAI_API_KEY",
            )
        )
    )

    if not api_key:
        raise ProviderError(
            "OPENAI_API_KEY missing"
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

    input_images = request.get(
        "input_images"
    )

    if (
        not message
        and continuation_input is None
        and not input_images
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

    model = str(
        request.get(
            "model"
        )
        or os.getenv(
            str(
                provider.get(
                    "model_env",
                    "SAVANT_MODEL",
                )
            )
        )
        or provider.get(
            "model_default",
            "gpt-5",
        )
    )

    input_items = (
        build_input_items(
            message=message,
            system=system,
            context=context,
            continuation_input=(
                continuation_input
            ),
            input_images=input_images,
        )
    )

    payload: Dict[
        str,
        Any,
    ] = {
        "model": model,
        "input": input_items,
    }

    tools = normalize_tools(
        request.get(
            "tools"
        )
    )

    if tools:
        payload[
            "tools"
        ] = tools

        tool_choice = request.get(
            "tool_choice"
        )

        if tool_choice is not None:
            payload[
                "tool_choice"
            ] = tool_choice

    previous_response_id = str(
        request.get(
            "previous_response_id"
        )
        or ""
    ).strip()

    if previous_response_id:
        payload[
            "previous_response_id"
        ] = previous_response_id

    http_request = (
        urllib.request.Request(
            OPENAI_RESPONSES_URL,
            data=json.dumps(
                payload
            ).encode(
                "utf-8"
            ),
            headers={
                "Content-Type": (
                    "application/json"
                ),
                "Authorization": (
                    f"Bearer {api_key}"
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
            "OpenAI text inference "
            f"failed: {exc}"
        ) from exc

    text = response_text(
        data
    )

    tool_calls = (
        response_tool_calls(
            data
        )
    )

    if (
        not text
        and not tool_calls
    ):
        raise ProviderError(
            "OpenAI response contained "
            "neither text nor tool calls"
        )

    return {
        "ok": True,
        "provider": "openai_text",
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
        "provider_output": data.get(
            "output",
            [],
        ),
    }
