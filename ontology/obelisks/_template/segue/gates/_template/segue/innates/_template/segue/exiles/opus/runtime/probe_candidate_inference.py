#!/usr/bin/env python3

from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


RUNTIME_ROOT = Path(
    __file__
).resolve().parent

if str(RUNTIME_ROOT) not in sys.path:
    sys.path.insert(
        0,
        str(RUNTIME_ROOT),
    )

from environment import load_environment


PROVIDERS = {
    "cerebras": {
        "env":
            "CEREBRAS_API_KEY",
        "url":
            "https://api.cerebras.ai/v1/chat/completions",
        "models": [
            "qwen-3.8-27b",
            "gpt-oss-120b",
        ],
    },
    "deepinfra": {
        "env":
            "DEEPINFRA_API_KEY",
        "url":
            "https://api.deepinfra.com/v1/openai/chat/completions",
        "models": [
            "Qwen/Qwen3.7-Max",
            "Qwen/Qwen3-14B",
            "Qwen/Qwen2.5-72B-Instruct",
            "mistralai/Mistral-Small-3.2-24B-Instruct-2506",
        ],
    },
    "nvidia": {
        "env":
            "NVIDIA_API_KEY",
        "url":
            "https://integrate.api.nvidia.com/v1/chat/completions",
        "models": [
            "deepseek-ai/deepseek-v4.1-flash",
            "01-ai/yi-large",
            "ai21labs/jamba-1.5-large-instruct",
        ],
    },
}


def safe_body(
    exc: urllib.error.HTTPError,
) -> str:
    try:
        return exc.read(
            8192
        ).decode(
            "utf-8",
            errors="replace",
        )[:1000]

    except Exception:
        return ""


def extract_text(
    payload: Any,
) -> str:
    if not isinstance(
        payload,
        dict,
    ):
        return ""

    choices = payload.get(
        "choices"
    )

    if not isinstance(
        choices,
        list,
    ) or not choices:
        return ""

    choice = choices[0]

    if not isinstance(
        choice,
        dict,
    ):
        return ""

    message = choice.get(
        "message"
    )

    if isinstance(
        message,
        dict,
    ):
        content = message.get(
            "content"
        )

        if isinstance(
            content,
            str,
        ):
            return content.strip()

    text = choice.get(
        "text"
    )

    if isinstance(
        text,
        str,
    ):
        return text.strip()

    return ""


def probe_model(
    provider: str,
    config: dict[str, Any],
    model: str,
) -> dict[str, Any]:
    started = time.perf_counter()

    result: dict[str, Any] = {
        "provider":
            provider,
        "model":
            model,
        "attempted":
            False,
        "working":
            False,
        "http_status":
            None,
        "latency_ms":
            None,
        "response_text":
            None,
        "error":
            None,
    }

    key = os.environ.get(
        str(
            config[
                "env"
            ]
        ),
        "",
    ).strip()

    if not key:
        result[
            "error"
        ] = (
            "credential missing"
        )

        return result

    payload = {
        "model":
            model,
        "messages": [
            {
                "role":
                    "system",
                "content":
                    (
                        "This is a provider "
                        "connectivity test. "
                        "Return exactly the "
                        "lowercase word opus."
                    ),
            },
            {
                "role":
                    "user",
                "content":
                    "Return exactly: opus",
            },
        ],
        "temperature":
            0,
        "max_tokens":
            16,
    }

    encoded = json.dumps(
        payload
    ).encode(
        "utf-8"
    )

    request = urllib.request.Request(
        str(
            config[
                "url"
            ]
        ),
        data=encoded,
        headers={
            "Authorization":
                f"Bearer {key}",
            "Content-Type":
                "application/json",
            "Accept":
                "application/json",
            "User-Agent":
                "savant-opus/1",
        },
        method="POST",
    )

    result[
        "attempted"
    ] = True

    try:
        with urllib.request.urlopen(
            request,
            timeout=60,
        ) as response:
            status = int(
                response.status
            )

            body = response.read(
                2_000_000
            ).decode(
                "utf-8",
                errors="replace",
            )

        result[
            "http_status"
        ] = status

        parsed = json.loads(
            body
        )

        text = extract_text(
            parsed
        )

        result[
            "response_text"
        ] = (
            text[:200]
            if text
            else None
        )

        result[
            "working"
        ] = bool(
            200 <= status < 300
            and text
        )

        if not text:
            result[
                "error"
            ] = (
                "successful HTTP response "
                "contained no recognized text"
            )

    except urllib.error.HTTPError as exc:
        result[
            "http_status"
        ] = exc.code

        body = safe_body(
            exc
        )

        result[
            "error"
        ] = (
            f"HTTP {exc.code}"
            + (
                f": {body}"
                if body
                else ""
            )
        )

    except Exception as exc:
        result[
            "error"
        ] = (
            f"{type(exc).__name__}: "
            f"{str(exc)[:1000]}"
        )

    result[
        "latency_ms"
    ] = round(
        (
            time.perf_counter()
            - started
        )
        * 1000.0,
        2,
    )

    return result


def probe_provider(
    provider: str,
    config: dict[str, Any],
) -> dict[str, Any]:
    attempts: list[
        dict[str, Any]
    ] = []

    selected_model = None

    for model in config[
        "models"
    ]:
        attempt = probe_model(
            provider,
            config,
            model,
        )

        attempts.append(
            attempt
        )

        if attempt[
            "working"
        ]:
            selected_model = model
            break

    return {
        "provider":
            provider,
        "working":
            selected_model
            is not None,
        "selected_model":
            selected_model,
        "attempts":
            attempts,
    }


def main() -> int:
    load_environment()

    results = [
        probe_provider(
            provider,
            config,
        )
        for provider, config
        in PROVIDERS.items()
    ]

    working = [
        result[
            "provider"
        ]
        for result in results
        if result[
            "working"
        ]
    ]

    failed = [
        result[
            "provider"
        ]
        for result in results
        if not result[
            "working"
        ]
    ]

    print()
    print(
        "=" * 72
    )
    print(
        "OPUS CANDIDATE INFERENCE PROBE"
    )
    print(
        "=" * 72
    )
    print()

    for result in results:
        status = (
            "WORKING"
            if result[
                "working"
            ]
            else "FAILED"
        )

        print(
            f"{result['provider']:<20}"
            f"{status:<12}"
            f"{result['selected_model'] or '-'}"
        )

        for attempt in result[
            "attempts"
        ]:
            marker = (
                "PASS"
                if attempt[
                    "working"
                ]
                else "FAIL"
            )

            print(
                f"  {marker:<5} "
                f"{attempt['model']}"
            )

            if attempt[
                "error"
            ]:
                print(
                    "        "
                    + str(
                        attempt[
                            "error"
                        ]
                    )
                )

        print()

    output = {
        "schema":
            (
                "opus.candidate."
                "inference_probe.v1"
            ),
        "working":
            working,
        "failed":
            failed,
        "working_count":
            len(
                working
            ),
        "provider_count":
            len(
                results
            ),
        "results":
            results,
        "secret_values_exposed":
            False,
    }

    print(
        json.dumps(
            output,
            indent=2,
            sort_keys=True,
        )
    )

    return (
        0
        if working
        else 2
    )


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
