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

ROUTES_ROOT = (
    REGISTRY_ROOT
    / "routes"
)

PROVIDERS_ROOT = (
    REGISTRY_ROOT
    / "providers"
)

TEXT_ROUTE_ID = (
    "text_inference_route"
)


def _read_json(
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
            f"expected object in {path}"
        )

    return value


def _route() -> Dict[str, Any]:
    return _read_json(
        ROUTES_ROOT
        / f"{TEXT_ROUTE_ID}.json"
    )


def _provider_registry(
    provider_id: str,
) -> Dict[str, Any]:
    path = (
        PROVIDERS_ROOT
        / f"{provider_id}.json"
    )

    if not path.exists():
        return {}

    return _read_json(
        path
    )


def _provider_ids(
    route_data: Mapping[str, Any],
) -> list[str]:
    values: list[str] = []

    default_provider = str(
        route_data.get(
            "default_provider"
        )
        or ""
    ).strip()

    if default_provider:
        values.append(
            default_provider
        )

    for raw in (
        route_data.get(
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
            not in values
        ):
            values.append(
                provider_id
            )

    return values


def _capabilities(
    provider_data: Mapping[str, Any],
) -> list[str]:
    raw = (
        provider_data.get(
            "capabilities"
        )
        or ()
    )

    if isinstance(
        raw,
        str,
    ):
        raw = [
            raw
        ]

    values: list[str] = []

    for item in raw:
        value = str(
            item
        ).strip().lower()

        if (
            value
            and value not in values
        ):
            values.append(
                value
            )

    return sorted(
        values
    )


def _import_provider(
    provider_id: str,
):
    return importlib.import_module(
        f"providers.{provider_id}"
    )


def _runtime_available(
    module: Any,
) -> tuple[bool, str | None]:
    available = getattr(
        module,
        "available",
        None,
    )

    if not callable(
        available
    ):
        return (
            True,
            None,
        )

    try:
        return (
            bool(
                available()
            ),
            None,
        )
    except Exception as exc:
        return (
            False,
            (
                f"{type(exc).__name__}: "
                f"{exc}"
            ),
        )


def _probe_request(
    provider_id: str,
) -> Dict[str, Any]:
    return {
        "owner":
            "opus_provider_diagnostics",
        "text":
            "Return exactly: opus",
        "prompt":
            "Return exactly: opus",
        "system":
            (
                "Provider transport diagnostic. "
                "Return exactly the lowercase "
                "word opus and nothing else."
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


def _response_text(
    response: Mapping[str, Any],
) -> str:
    for key in (
        "text",
        "output",
        "response",
        "content",
    ):
        value = response.get(
            key
        )

        if isinstance(
            value,
            str,
        ) and value.strip():
            return value.strip()

    return ""


def _probe_provider(
    provider_id: str,
    provider_data: Mapping[str, Any],
) -> Dict[str, Any]:
    started = time.perf_counter()

    capabilities = (
        _capabilities(
            provider_data
        )
    )

    result: Dict[str, Any] = {
        "provider":
            provider_id,
        "registry_exists":
            bool(
                provider_data
            ),
        "capabilities":
            capabilities,
        "supports_text":
            (
                "text_inference"
                in capabilities
            ),
        "module_importable":
            False,
        "available_callable":
            False,
        "available":
            False,
        "infer_callable":
            False,
        "probe_attempted":
            False,
        "probe_ok":
            False,
        "probe_model":
            None,
        "probe_text":
            None,
        "latency_ms":
            None,
        "error":
            None,
    }

    try:
        module = _import_provider(
            provider_id
        )

        result[
            "module_importable"
        ] = True

    except Exception as exc:
        result[
            "error"
        ] = (
            f"{type(exc).__name__}: "
            f"{exc}"
        )

        result[
            "latency_ms"
        ] = round(
            (
                time.perf_counter()
                - started
            )
            * 1000.0,
            3,
        )

        return result

    available = getattr(
        module,
        "available",
        None,
    )

    result[
        "available_callable"
    ] = callable(
        available
    )

    runtime_available, error = (
        _runtime_available(
            module
        )
    )

    result[
        "available"
    ] = runtime_available

    if error:
        result[
            "error"
        ] = error

    infer = getattr(
        module,
        "infer",
        None,
    )

    result[
        "infer_callable"
    ] = callable(
        infer
    )

    if not (
        result[
            "supports_text"
        ]
        and runtime_available
        and callable(
            infer
        )
    ):
        result[
            "latency_ms"
        ] = round(
            (
                time.perf_counter()
                - started
            )
            * 1000.0,
            3,
        )

        return result

    result[
        "probe_attempted"
    ] = True

    try:
        response = infer(
            _probe_request(
                provider_id
            ),
            dict(
                provider_data
            ),
        )

        if not isinstance(
            response,
            Mapping,
        ):
            raise RuntimeError(
                "provider infer returned "
                "non-mapping result"
            )

        text = _response_text(
            response
        )

        response_ok = bool(
            response.get(
                "ok",
                bool(
                    text
                ),
            )
        )

        result[
            "probe_ok"
        ] = bool(
            response_ok
            and text
        )

        result[
            "probe_model"
        ] = response.get(
            "model"
        )

        result[
            "probe_text"
        ] = (
            text[:160]
            if text
            else None
        )

        if not result[
            "probe_ok"
        ]:
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
            )

    except Exception as exc:
        result[
            "error"
        ] = (
            f"{type(exc).__name__}: "
            f"{exc}"
        )

    result[
        "latency_ms"
    ] = round(
        (
            time.perf_counter()
            - started
        )
        * 1000.0,
        3,
    )

    return result


def main() -> int:
    load_environment()

    try:
        route_data = _route()
    except Exception as exc:
        print(
            json.dumps(
                {
                    "ok":
                        False,
                    "route":
                        TEXT_ROUTE_ID,
                    "error":
                        (
                            f"{type(exc).__name__}: "
                            f"{exc}"
                        ),
                },
                indent=2,
                sort_keys=True,
            )
        )

        return 2

    provider_ids = (
        _provider_ids(
            route_data
        )
    )

    providers: list[
        Dict[str, Any]
    ] = []

    for provider_id in provider_ids:
        provider_data = (
            _provider_registry(
                provider_id
            )
        )

        providers.append(
            _probe_provider(
                provider_id,
                provider_data,
            )
        )

    declared_usable = [
        item[
            "provider"
        ]
        for item in providers
        if (
            item[
                "registry_exists"
            ]
            and item[
                "module_importable"
            ]
            and item[
                "available"
            ]
            and item[
                "infer_callable"
            ]
            and item[
                "supports_text"
            ]
        )
    ]

    proven_usable = [
        item[
            "provider"
        ]
        for item in providers
        if item[
            "probe_ok"
        ]
    ]

    failed_runtime = [
        {
            "provider":
                item[
                    "provider"
                ],
            "error":
                item[
                    "error"
                ],
        }
        for item in providers
        if (
            item[
                "probe_attempted"
            ]
            and not item[
                "probe_ok"
            ]
        )
    ]

    output = {
        "ok":
            bool(
                proven_usable
            ),
        "multi_provider_ready":
            (
                len(
                    proven_usable
                )
                >= 2
            ),
        "route":
            TEXT_ROUTE_ID,
        "default_provider":
            route_data.get(
                "default_provider"
            ),
        "fallback_order":
            list(
                route_data.get(
                    "fallback_order"
                )
                or ()
            ),
        "declared_usable_text_providers":
            declared_usable,
        "proven_usable_text_providers":
            proven_usable,
        "proven_usable_count":
            len(
                proven_usable
            ),
        "failed_runtime_providers":
            failed_runtime,
        "providers":
            providers,
    }

    print(
        json.dumps(
            output,
            indent=2,
            sort_keys=True,
        )
    )

    if not proven_usable:
        return 3

    if len(
        proven_usable
    ) < 2:
        return 4

    return 0


if __name__ == "__main__":
    sys.exit(
        main()
    )
