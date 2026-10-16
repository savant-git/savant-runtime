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
        or profile.get("model_default")
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
        request.get("timeout_seconds")
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
    body = (
        None
        if payload is None
        else json.dumps(
            payload
        ).encode(
            "utf-8"
        )
    )

    request = urllib.request.Request(
        url,
        data=body,
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
            "native provider http failure "
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

    if not (
        _env(
            profile,
            "model_env",
        )
        or profile.get(
            "model_default"
        )
    ):
        return False

    try:
        return (
            boto3.Session().get_credentials()
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
        request.get("region")
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
        "modelId": model,
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "text": _message(
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
        kwargs["system"] = [
            {
                "text": system,
            }
        ]

    inference_config: Dict[str, Any] = {}

    if request.get("max_tokens") is not None:
        inference_config["maxTokens"] = int(
            request["max_tokens"]
        )

    if request.get("temperature") is not None:
        inference_config["temperature"] = float(
            request["temperature"]
        )

    if request.get("top_p") is not None:
        inference_config["topP"] = float(
            request["top_p"]
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

    message = (
        data.get("output")
        or {}
    ).get(
        "message"
    ) or {}

    parts = [
        row["text"]
        for row in message.get(
            "content",
            [],
        )
        if isinstance(
            row,
            dict,
        )
        and isinstance(
            row.get("text"),
            str,
        )
    ]

    text = "\n".join(
        parts
    ).strip()

    if not text:
        raise ProviderError(
            "aws bedrock response contained no text"
        )

    return {
        "ok": True,
        "provider": "catalog_text",
        "provider_profile": profile.get(
            "profile_id",
            "aws_bedrock",
        ),
        "protocol": "bedrock_converse",
        "model": model,
        "text": text,
        "usage": data.get(
            "usage",
            {},
        ),
        "stop_reason": data.get(
            "stopReason"
        ),
        "authority_effect": "none",
    }


def _cohere_available(
    profile: Dict[str, Any],
) -> bool:
    return bool(
        _env(
            profile,
            "api_key_env",
        )
        and (
            _env(
                profile,
                "model_env",
            )
            or profile.get(
                "model_default"
            )
        )
    )


def _cohere(
    request: Dict[str, Any],
    provider: Dict[str, Any],
    profile: Dict[str, Any],
) -> Dict[str, Any]:
    key = _env(
        profile,
        "api_key_env",
    )

    if not key:
        raise ProviderError(
            "cohere credential missing"
        )

    model = _model(
        request,
        profile,
    )

    base = str(
        profile.get("api_base")
        or "https://api.cohere.com"
    ).rstrip("/")

    messages = []

    system = _system(
        request
    )

    if system:
        messages.append(
            {
                "role": "system",
                "content": system,
            }
        )

    messages.append(
        {
            "role": "user",
            "content": _message(
                request
            ),
        }
    )

    payload: Dict[str, Any] = {
        "model": model,
        "messages": messages,
    }

    if request.get("temperature") is not None:
        payload[
            "temperature"
        ] = request[
            "temperature"
        ]

    if request.get("max_tokens") is not None:
        payload[
            "max_tokens"
        ] = request[
            "max_tokens"
        ]

    data = _json_request(
        url=base + "/v2/chat",
        payload=payload,
        headers={
            "Content-Type":
                "application/json",
            "Authorization":
                f"Bearer {key}",
        },
        timeout=_timeout(
            request,
            provider,
        ),
    )

    result_message = (
        data.get("message")
        or {}
    )

    parts = [
        row["text"]
        for row in result_message.get(
            "content",
            [],
        )
        if isinstance(
            row,
            dict,
        )
        and row.get(
            "type"
        )
        == "text"
        and isinstance(
            row.get("text"),
            str,
        )
    ]

    text = "\n".join(
        parts
    ).strip()

    if not text:
        raise ProviderError(
            "cohere response contained no text"
        )

    return {
        "ok": True,
        "provider": "catalog_text",
        "provider_profile": profile.get(
            "profile_id",
            "cohere",
        ),
        "protocol": "cohere_chat",
        "model": model,
        "text": text,
        "usage": data.get(
            "usage",
            {},
        ),
        "provider_response_id": data.get(
            "id"
        ),
        "authority_effect": "none",
    }


def _ollama_available(
    profile: Dict[str, Any],
) -> bool:
    return bool(
        _env(
            profile,
            "model_env",
        )
        or profile.get(
            "model_default"
        )
    )


def _ollama(
    request: Dict[str, Any],
    provider: Dict[str, Any],
    profile: Dict[str, Any],
) -> Dict[str, Any]:
    model = _model(
        request,
        profile,
    )

    base = str(
        _env(
            profile,
            "api_base_env",
        )
        or profile.get("api_base")
        or "http://127.0.0.1:11434"
    ).rstrip("/")

    messages = []

    system = _system(
        request
    )

    if system:
        messages.append(
            {
                "role": "system",
                "content": system,
            }
        )

    messages.append(
        {
            "role": "user",
            "content": _message(
                request
            ),
        }
    )

    payload: Dict[str, Any] = {
        "model": model,
        "messages": messages,
        "stream": False,
    }

    options: Dict[str, Any] = {}

    if request.get("temperature") is not None:
        options[
            "temperature"
        ] = request[
            "temperature"
        ]

    if request.get("top_p") is not None:
        options[
            "top_p"
        ] = request[
            "top_p"
        ]

    if options:
        payload[
            "options"
        ] = options

    data = _json_request(
        url=base + "/api/chat",
        payload=payload,
        headers={
            "Content-Type":
                "application/json",
        },
        timeout=_timeout(
            request,
            provider,
        ),
    )

    text = str(
        (
            data.get("message")
            or {}
        ).get(
            "content"
        )
        or ""
    ).strip()

    if not text:
        raise ProviderError(
            "ollama response contained no text"
        )

    return {
        "ok": True,
        "provider": "catalog_text",
        "provider_profile": profile.get(
            "profile_id",
            "ollama_native",
        ),
        "protocol": "ollama_chat",
        "model": model,
        "text": text,
        "usage": {
            "prompt_tokens":
                data.get(
                    "prompt_eval_count"
                ),
            "completion_tokens":
                data.get(
                    "eval_count"
                ),
        },
        "authority_effect": "none",
    }


def _replicate_available(
    profile: Dict[str, Any],
) -> bool:
    return bool(
        _env(
            profile,
            "api_key_env",
        )
        and (
            _env(
                profile,
                "model_env",
            )
            or profile.get(
                "model_default"
            )
        )
    )


def _replicate_output_text(
    value: Any,
) -> str:
    if isinstance(
        value,
        str,
    ):
        return value.strip()

    if isinstance(
        value,
        list,
    ):
        return "".join(
            str(row)
            for row in value
        ).strip()

    if isinstance(
        value,
        dict,
    ):
        for key in (
            "text",
            "output",
            "response",
            "answer",
        ):
            candidate = value.get(
                key
            )

            if (
                isinstance(
                    candidate,
                    str,
                )
                and candidate.strip()
            ):
                return candidate.strip()

    return ""


def _replicate(
    request: Dict[str, Any],
    provider: Dict[str, Any],
    profile: Dict[str, Any],
) -> Dict[str, Any]:
    token = _env(
        profile,
        "api_key_env",
    )

    if not token:
        raise ProviderError(
            "replicate credential missing"
        )

    model = _model(
        request,
        profile,
    )

    base = str(
        profile.get("api_base")
        or "https://api.replicate.com/v1"
    ).rstrip("/")

    model_parts = model.split("/")

    if len(model_parts) != 2:
        raise ProviderError(
            "replicate model must be owner/name"
        )

    owner = urllib.parse.quote(
        model_parts[0],
        safe="",
    )

    name = urllib.parse.quote(
        model_parts[1],
        safe="",
    )

    url = (
        base
        + "/models/"
        + owner
        + "/"
        + name
        + "/predictions"
    )

    provider_input = request.get(
        "provider_input"
    )

    if provider_input is None:
        provider_input = {
            "prompt": _message(
                request
            )
        }

    if not isinstance(
        provider_input,
        dict,
    ):
        raise ProviderError(
            "replicate provider_input must be object"
        )

    timeout = _timeout(
        request,
        provider,
    )

    wait_seconds = max(
        1,
        min(
            timeout,
            60,
        ),
    )

    headers = {
        "Content-Type":
            "application/json",
        "Authorization":
            f"Bearer {token}",
        "Prefer":
            f"wait={wait_seconds}",
    }

    data = _json_request(
        url=url,
        payload={
            "input":
                provider_input,
        },
        headers=headers,
        timeout=wait_seconds + 10,
    )

    started = time.monotonic()

    while str(
        data.get("status")
        or ""
    ).lower() in {
        "starting",
        "processing",
    }:
        if (
            time.monotonic()
            - started
            >= timeout
        ):
            raise ProviderError(
                "replicate prediction timed out"
            )

        get_url = str(
            (
                data.get("urls")
                or {}
            ).get(
                "get"
            )
            or ""
        ).strip()

        if not get_url:
            raise ProviderError(
                "replicate prediction polling url missing"
            )

        time.sleep(1)

        data = _json_request(
            url=get_url,
            payload=None,
            headers={
                "Authorization":
                    f"Bearer {token}",
            },
            timeout=timeout,
            method="GET",
        )

    status = str(
        data.get("status")
        or ""
    ).lower()

    if status != "succeeded":
        raise ProviderError(
            "replicate prediction failed: "
            + str(
                data.get("error")
                or status
            )
        )

    text = _replicate_output_text(
        data.get("output")
    )

    if not text:
        raise ProviderError(
            "replicate prediction contained no text"
        )

    return {
        "ok": True,
        "provider": "catalog_text",
        "provider_profile": profile.get(
            "profile_id",
            "replicate",
        ),
        "protocol": "replicate_prediction",
        "model": model,
        "text": text,
        "provider_response_id": data.get(
            "id"
        ),
        "metrics": data.get(
            "metrics",
            {},
        ),
        "authority_effect": "none",
    }


def profile_available(
    profile: Dict[str, Any],
) -> bool:
    protocol = str(
        profile.get("protocol")
        or ""
    ).strip().lower()

    if protocol == "bedrock_converse":
        return _bedrock_available(
            profile
        )

    if protocol == "cohere_chat":
        return _cohere_available(
            profile
        )

    if protocol == "ollama_chat":
        return _ollama_available(
            profile
        )

    if protocol == "replicate_prediction":
        return _replicate_available(
            profile
        )

    return False


def infer(
    request: Dict[str, Any],
    provider: Dict[str, Any],
    profile: Dict[str, Any],
) -> Dict[str, Any]:
    protocol = str(
        profile.get("protocol")
        or ""
    ).strip().lower()

    if protocol == "bedrock_converse":
        return _bedrock(
            request,
            provider,
            profile,
        )

    if protocol == "cohere_chat":
        return _cohere(
            request,
            provider,
            profile,
        )

    if protocol == "ollama_chat":
        return _ollama(
            request,
            provider,
            profile,
        )

    if protocol == "replicate_prediction":
        return _replicate(
            request,
            provider,
            profile,
        )

    raise ProviderError(
        f"unsupported native protocol: {protocol}"
    )
