#!/usr/bin/env python3

from __future__ import annotations

import json
import os
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict

from providers.base import ProviderError


OWNER = "opus"


def _env(
    profile: Dict[str, Any],
    field: str,
    *,
    fallback: str | None = None,
) -> str:
    name = str(
        profile.get(field)
        or ""
    ).strip()

    if name:
        value = str(
            os.getenv(
                name,
                "",
            )
            or ""
        ).strip()

        if value:
            return value

    if fallback:
        name = str(
            profile.get(fallback)
            or ""
        ).strip()

        if name:
            return str(
                os.getenv(
                    name,
                    "",
                )
                or ""
            ).strip()

    return ""


def _model(
    request: Dict[str, Any],
    profile: Dict[str, Any],
) -> str:
    model = str(
        request.get("model")
        or _env(
            profile,
            "model_env",
        )
        or profile.get(
            "model_default"
        )
        or ""
    ).strip()

    if not model:
        raise ProviderError(
            "native provider model missing"
        )

    return model


def _message(
    request: Dict[str, Any],
) -> str:
    message = str(
        request.get("message")
        or request.get("text")
        or ""
    ).strip()

    if not message:
        raise ProviderError(
            "text inference request missing message"
        )

    context = str(
        request.get("context")
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


def _system(
    request: Dict[str, Any],
) -> str:
    return str(
        request.get("system")
        or ""
    ).strip()


def _timeout(
    request: Dict[str, Any],
    provider: Dict[str, Any],
) -> int:
    return int(
        request.get(
            "timeout_seconds"
        )
        or provider.get(
            "timeout_seconds",
            120,
        )
    )


def _json_request(
    *,
    url: str,
    payload: Dict[str, Any] | None,
    headers: Dict[str, str],
    timeout: int,
    method: str = "POST",
) -> Dict[str, Any]:
    data = None

    if payload is not None:
        data = json.dumps(
            payload
        ).encode(
            "utf-8"
        )

    request = urllib.request.Request(
        url,
        data=data,
        headers=headers,
        method=method,
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
        detail = ""

        try:
            detail = exc.read().decode(
                "utf-8",
                errors="replace",
            )
        except Exception:
            pass

        raise ProviderError(
            f"native provider http failure "
            f"{exc.code}: {detail[:2000]}"
        ) from exc

    except Exception as exc:
        raise ProviderError(
            f"native provider request failed: {exc}"
        ) from exc

    try:
        value = json.loads(
            raw
        )

    except json.JSONDecodeError as exc:
        raise ProviderError(
            "native provider returned invalid json"
        ) from exc

    if not isinstance(
        value,
        dict,
    ):
        raise ProviderError(
            "native provider response must be object"
        )

    return value


def _bedrock_available(
    profile: Dict[str, Any],
) -> bool:
    try:
        import boto3
    except ImportError:
        return False

    if not _env(
        profile,
        "model_env",
    ) and not profile.get(
        "model_default"
    ):
        return False

    try:
        session = boto3.Session()

        return (
            session.get_credentials()
            is not None
        )

    except Exception:
        return False


def _bedrock(
    request: Dict[str, Any],
    provider: Dict[str, Any],
    profile: Dict[str, Any],
) -> Dict[str, Any]:
    try:
        import boto3
    except ImportError as exc:
        raise ProviderError(
            "aws bedrock requires boto3"
        ) from exc

    model = _model(
        request,
        profile,
    )

    region = str(
        request.get(
            "region"
        )
        or _env(
            profile,
            "region_env",
        )
        or profile.get(
            "region_default"
        )
        or os.getenv(
            "AWS_REGION"
        )
        or os.getenv(
            "AWS_DEFAULT_REGION"
        )
        or ""
    ).strip()

    if not region:
        raise ProviderError(
            "aws bedrock region missing"
        )

    client = boto3.client(
        "bedrock-runtime",
        region_name=region,
    )

    kwargs: Dict[str, Any] = {
        "modelId":
            model,
        "messages": [
            {
                "role":
                    "user",
                "content": [
                    {
                        "text":
                            _message(
                                request
                            )
                    }
                ],
            }
        ],
    }

    system = _system(
        request
    )

    if system:
        kwargs[
            "system"
        ] = [
            {
                "text":
                    system,
            }
        ]

    inference_config: Dict[
        str,
        Any,
    ] = {}

    if request.get(
        "max_tokens"
    ) is not None:
        inference_config[
            "maxTokens"
        ] = int(
            request[
                "max_tokens"
            ]
        )

    if request.get(
        "temperature"
    ) is not None:
        inference_config[
            "temperature"
        ] = float(
            request[
                "temperature"
            ]
        )

    if request.get(
        "top_p"
    ) is not None:
        inference_config[
            "topP"
        ] = float(
            request[
                "top_p"
            ]
        )

    if inference_config:
        kwargs[
            "inferenceConfig"
        ] = inference_config

    try:
        data = client.converse(
            **kwargs
        )

    except Exception as exc:
        raise ProviderError(
            f"aws bedrock converse failed: {exc}"
        ) from exc

    output = data.get(
        "output"
    ) or {}

    message = output.get(
        "message"
    ) or {}

    parts = []

    for row in message.get(
        "content",
        [],
    ):
        if (
            isinstance(
                row,
                dict,
            )
            and isinstance(
                row.get("text"),
                str,
            )
        ):
            parts.append(
                row["text"]
            )

    text = "\n".join(
        parts
    ).strip()

    if not text:
        raise ProviderError(
            "aws bedrock response contained no text"
        )

    return {
        "ok":
            True,
        "provider":
            "catalog_text",
        "provider_profile":
            profile.get(
                "profile_id",
                "aws_bedrock",
            ),
        "protocol":
            "bedrock_converse",
        "model":
            model,
        "text":
            text,
        "usage":
            data.get(
                "usage",
                {},
            ),
        "
