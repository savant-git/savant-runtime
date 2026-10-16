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
        "env": "CEREBRAS_API_KEY",
        "base_url":
            "https://api.cerebras.ai/v1",
        "models_path":
            "/models",
    },
    "deepinfra": {
        "env": "DEEPINFRA_API_KEY",
        "base_url":
            "https://api.deepinfra.com/v1/openai",
        "models_path":
            "/models",
    },
    "nvidia": {
        "env": "NVIDIA_API_KEY",
        "base_url":
            "https://integrate.api.nvidia.com/v1",
        "models_path":
            "/models",
    },
    "perplexity": {
        "env": "PERPLEXITY_API_KEY",
        "base_url":
            "https://api.perplexity.ai",
        "models_path":
            "/models",
    },
    "together": {
        "env": "TOGETHER_API_KEY",
        "base_url":
            "https://api.together.xyz/v1",
        "models_path":
            "/models",
    },
    "xai": {
        "env": "XAI_API_KEY",
        "base_url":
            "https://api.x.ai/v1",
        "models_path":
            "/models",
    },
}


def request_models(
    provider: str,
    config: dict[str, str],
) -> dict[str, Any]:
    started = time.perf_counter()

    key = os.environ.get(
        config["env"],
        "",
    ).strip()

    result: dict[str, Any] = {
        "provider":
            provider,
        "credential_variable":
            config["env"],
        "configured":
            bool(
                key
            ),
        "request_attempted":
            False,
        "working":
            False,
        "http_status":
            None,
        "latency_ms":
            None,
        "model_count":
            0,
        "sample_models":
            [],
        "error":
            None,
    }

    if not key:
        result[
            "error"
        ] = (
            "credential not configured"
        )

        return result

    url = (
        config[
            "base_url"
        ].rstrip("/")
        + config[
            "models_path"
        ]
    )

    request = urllib.request.Request(
        url,
        headers={
            "Authorization":
                f"Bearer {key}",
            "Accept":
                "application/json",
            "User-Agent":
                "savant-opus/1",
        },
        method="GET",
    )

    result[
        "request_attempted"
    ] = True

    try:
        with urllib.request.urlopen(
            request,
            timeout=20,
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

        payload = json.loads(
            body
        )

        data = (
            payload.get(
                "data"
            )
            if isinstance(
                payload,
                dict,
            )
            else None
        )

        if isinstance(
            data,
            list,
        ):
            model_ids: list[str] = []

            for item in data:
                if isinstance(
                    item,
                    dict,
                ):
                    model_id = str(
                        item.get(
                            "id"
                        )
                        or item.get(
                            "name"
                        )
                        or ""
                    ).strip()

                    if model_id:
                        model_ids.append(
                            model_id
                        )

            result[
                "model_count"
            ] = len(
                model_ids
            )

            result[
                "sample_models"
            ] = model_ids[:10]

        result[
            "working"
        ] = (
            200
            <= status
            < 300
        )

    except urllib.error.HTTPError as exc:
        result[
            "http_status"
        ] = exc.code

        try:
            body = exc.read(
                4096
            ).decode(
                "utf-8",
                errors="replace",
            )

        except Exception:
            body = ""

        result[
            "error"
        ] = (
            f"HTTP {exc.code}"
            + (
                f": {body[:500]}"
                if body
                else ""
            )
        )

    except Exception as exc:
        result[
            "error"
        ] = (
            f"{type(exc).__name__}: "
            f"{str(exc)[:500]}"
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


def main() -> int:
    load_environment()

    results = [
        request_models(
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
        "UNINTEGRATED OPUS AI PROVIDER CHECK"
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
            f"HTTP "
            f"{str(result['http_status']):<5}"
            f"{result['latency_ms']:>10.2f} ms"
        )

        if result[
            "sample_models"
        ]:
            print(
                "  models: "
                + ", ".join(
                    result[
                        "sample_models"
                    ][:5]
                )
            )

        if result[
            "error"
        ]:
            print(
                "  error: "
                + str(
                    result[
                        "error"
                    ]
                )
            )

        print()

    print(
        "=" * 72
    )
    print(
        "SUMMARY"
    )
    print(
        "=" * 72
    )

    print(
        "working: "
        + (
            ", ".join(
                working
            )
            if working
            else "none"
        )
    )

    print(
        "failed: "
        + (
            ", ".join(
                failed
            )
            if failed
            else "none"
        )
    )

    print()

    print(
        json.dumps(
            {
                "schema":
                    (
                        "opus.unintegrated."
                        "ai_provider_check.v1"
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
            },
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
