#!/usr/bin/env python3

from __future__ import annotations

import importlib
import json
import sys
import time
from pathlib import Path
from typing import Any, Dict, Mapping


RUNTIME_ROOT = Path(
    __file__
).resolve().parent

if str(RUNTIME_ROOT) not in sys.path:
    sys.path.insert(
        0,
        str(RUNTIME_ROOT),
    )

from environment import load_environment


OPUS_ROOT = RUNTIME_ROOT.parent

REGISTRY_ROOT = (
    OPUS_ROOT
    / "registry"
)

PROVIDERS_ROOT = (
    REGISTRY_ROOT
    / "providers"
)

ROUTES_ROOT = (
    REGISTRY_ROOT
    / "routes"
)

TEXT_ROUTE_ID = (
    "text_inference_route"
)


def read_json(
    path: Path,
) -> Dict[str, Any]:
    with path.open(
        "r",
        encoding="utf-8",
    ) as handle:
        value = json.load(
            handle
        )

    if not isinstance(
        value,
        dict,
    ):
        raise RuntimeError(
            f"expected JSON object: {path}"
        )

    return value


def route_data() -> Dict[str, Any]:
    return read_json(
        ROUTES_ROOT
        / f"{TEXT_ROUTE_ID}.json"
    )


def provider_data(
    provider_id: str,
) -> Dict[str, Any]:
    path = (
        PROVIDERS_ROOT
        / f"{provider_id}.json"
    )

    if not path.exists():
        return {}

    return read_json(
        path
    )


def provider_ids(
    route: Mapping[str, Any],
) -> list[str]:
    output: list[str] = []

    default_provider = str(
        route.get(
            "default_provider"
        )
        or ""
    ).strip()

    if default_provider:
        output.append(
            default_provider
        )

    for raw in (
        route.get(
            "fallback_order"
        )
        or ()
    ):
        provider_id = str(
            raw
        ).strip()

        if (
            provider_id
            and provider_id
            not in output
        ):
            output.append(
                provider_id
            )

    for path in sorted(
        PROVIDERS_ROOT.glob(
            "*.json"
        )
    ):
        provider_id = path.stem

        data = provider_data(
            provider_id
        )

        capabilities = data.get(
            "capabilities"
        ) or ()

        if isinstance(
            capabilities,
            str,
        ):
            capabilities = [
                capabilities
            ]

        normalized = {
            str(
                item
            ).strip().lower()
            for item in capabilities
        }

        if (
            "text_inference"
            in normalized
            and provider_id
            not in output
        ):
            output.append(
                provider_id
            )

    return output


def safe_error(
    exc: BaseException,
) -> str:
    return (
        f"{type(exc).__name__}: "
        f"{str(exc)}"
    )[:500]


def test_provider(
    provider_id: str,
) -> Dict[str, Any]:
    started = time.perf_counter()

    result: Dict[str, Any] = {
        "provider":
            provider_id,
        "configured":
            False,
        "available":
            False,
        "api_call_attempted":
            False,
        "api_call_worked":
            False,
        "model":
            None,
        "latency_ms":
            None,
        "error":
            None,
    }

    registry = provider_data(
        provider_id
    )

    if not registry:
        result[
            "error"
        ] = (
            "provider registry missing"
        )

        return result

    try:
        module = importlib.import_module(
            f"providers.{provider_id}"
        )

    except Exception as exc:
        result[
            "error"
        ] = safe_error(
            exc
        )

        return result

    available = getattr(
        module,
        "available",
        None,
    )

    infer = getattr(
        module,
        "infer",
        None,
    )

    if not callable(
        infer
    ):
        result[
            "error"
        ] = (
            "provider has no infer()"
        )

        return result

    if callable(
        available
    ):
        try:
            configured = bool(
                available()
            )

        except Exception as exc:
            result[
                "error"
            ] = safe_error(
                exc
            )

            return result

    else:
        configured = True

    result[
        "configured"
    ] = configured

    result[
        "available"
    ] = configured

    if not configured:
        result[
            "error"
        ] = (
            "provider reports unavailable; "
            "credential or required configuration "
            "was not resolved"
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

    request = {
        "owner":
            "opus_provider_key_check",
        "text":
            "Return exactly the word opus.",
        "prompt":
            "Return exactly the word opus.",
        "system":
            (
                "This is an Opus provider "
                "connectivity test. Return exactly "
                "the lowercase word opus."
            ),
        "required_capabilities": [
            "text_inference",
        ],
        "capabilities": [
            "text_inference",
        ],
        "cognitive_orchestration":
            False,
        "diagnostic":
            True,
        "provider":
            provider_id,
    }

    result[
        "api_call_attempted"
    ] = True

    try:
        response = infer(
            request,
            registry,
        )

        if not isinstance(
            response,
            Mapping,
        ):
            raise RuntimeError(
                "infer() returned a non-mapping result"
            )

        text = str(
            response.get(
                "text"
            )
            or response.get(
                "output"
            )
            or response.get(
                "response"
            )
            or response.get(
                "content"
            )
            or ""
        ).strip()

        response_ok = bool(
            response.get(
                "ok",
                bool(
                    text
                ),
            )
        )

        result[
            "model"
        ] = response.get(
            "model"
        )

        if (
            response_ok
            and text
        ):
            result[
                "api_call_worked"
            ] = True

        else:
            result[
                "error"
            ] = str(
                response.get(
                    "error"
                )
                or (
                    "provider returned no "
                    "successful text result"
                )
            )[:500]

    except Exception as exc:
        result[
            "error"
        ] = safe_error(
            exc
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


def status_label(
    result: Mapping[str, Any],
) -> str:
    if result.get(
        "api_call_worked"
    ):
        return "WORKING"

    if not result.get(
        "configured"
    ):
        return "NOT CONFIGURED"

    if result.get(
        "api_call_attempted"
    ):
        return "FAILED"

    return "UNAVAILABLE"


def main() -> int:
    load_environment()

    route = route_data()

    ids = provider_ids(
        route
    )

    results = [
        test_provider(
            provider_id
        )
        for provider_id in ids
    ]

    print()
    print(
        "=" * 72
    )
    print(
        "OPUS PROVIDER API KEY / CONNECTIVITY CHECK"
    )
    print(
        "=" * 72
    )
    print()

    working: list[str] = []
    failed: list[str] = []
    unavailable: list[str] = []

    for result in results:
        label = status_label(
            result
        )

        provider_id = str(
            result[
                "provider"
            ]
        )

        print(
            f"{provider_id:<28} "
            f"{label:<16} "
            f"{result['latency_ms'] or 0:>9.2f} ms"
        )

        if result.get(
            "model"
        ):
            print(
                "  model: "
                f"{result['model']}"
            )

        if result.get(
            "error"
        ):
            print(
                "  error: "
                f"{result['error']}"
            )

        if label == "WORKING":
            working.append(
                provider_id
            )

        elif label == "FAILED":
            failed.append(
                provider_id
            )

        else:
            unavailable.append(
                provider_id
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

    print(
        "not configured/unavailable: "
        + (
            ", ".join(
                unavailable
            )
            if unavailable
            else "none"
        )
    )

    print()
    print(
        f"working providers: "
        f"{len(working)}/{len(results)}"
    )

    print(
        "multi-provider opus ready: "
        + (
            "YES"
            if len(
                working
            ) >= 2
            else "NO"
        )
    )

    print()

    machine_output = {
        "working":
            working,
        "failed":
            failed,
        "unavailable":
            unavailable,
        "working_count":
            len(
                working
            ),
        "provider_count":
            len(
                results
            ),
        "multi_provider_ready":
            len(
                working
            ) >= 2,
        "results":
            results,
    }

    print(
        json.dumps(
            machine_output,
            indent=2,
            sort_keys=True,
        )
    )

    if not working:
        return 2

    if len(
        working
    ) < 2:
        return 3

    return 0


if __name__ == "__main__":
    sys.exit(
        main()
    )
