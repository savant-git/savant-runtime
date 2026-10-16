from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path
from typing import Any, Dict, Iterable

from environment import load_environment


OPUS_ROOT = Path(__file__).resolve().parents[1]
PROVIDERS = OPUS_ROOT / "registry" / "providers"
ROUTES = OPUS_ROOT / "registry" / "routes"


def read_json(path: Path) -> Dict[str, Any]:
    return json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )


def route(route_id: str) -> Dict[str, Any]:
    return read_json(
        ROUTES / f"{route_id}.json"
    )


def provider(provider_id: str) -> Dict[str, Any]:
    return read_json(
        PROVIDERS / f"{provider_id}.json"
    )


def route_provider_ids(
    route_data: Dict[str, Any],
) -> list[str]:
    raw = route_data.get(
        "fallback_order"
    )

    if not isinstance(raw, list):
        raw = []

    default_provider = str(
        route_data.get(
            "default_provider"
        )
        or ""
    ).strip()

    values: list[str] = []

    if default_provider:
        values.append(
            default_provider
        )

    for item in raw:
        provider_id = str(
            item or ""
        ).strip()

        if (
            provider_id
            and provider_id not in values
        ):
            values.append(
                provider_id
            )

    return values


def normalized_capabilities(
    provider_data: Dict[str, Any],
) -> list[str]:
    raw = provider_data.get(
        "capabilities"
    )

    if not isinstance(raw, list):
        return []

    return sorted(
        {
            str(value).strip()
            for value in raw
            if str(value).strip()
        }
    )


def diagnose_provider(
    provider_id: str,
) -> Dict[str, Any]:
    result: Dict[str, Any] = {
        "provider": provider_id,
        "registry_exists": False,
        "module_importable": False,
        "available_callable": False,
        "available": False,
        "capabilities": [],
        "supports_text": False,
        "infer_callable": False,
        "error": None,
    }

    registry_path = (
        PROVIDERS
        / f"{provider_id}.json"
    )

    if not registry_path.exists():
        result["error"] = (
            "provider registry missing"
        )
        return result

    result["registry_exists"] = True

    try:
        provider_data = provider(
            provider_id
        )
    except Exception as exc:
        result["error"] = (
            f"registry load failed: "
            f"{type(exc).__name__}: {exc}"
        )
        return result

    capabilities = (
        normalized_capabilities(
            provider_data
        )
    )

    result["capabilities"] = (
        capabilities
    )

    result["supports_text"] = (
        "text" in capabilities
    )

    try:
        module = importlib.import_module(
            f"providers.{provider_id}"
        )
    except Exception as exc:
        result["error"] = (
            f"provider import failed: "
            f"{type(exc).__name__}: {exc}"
        )
        return result

    result[
        "module_importable"
    ] = True

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

    if callable(available):
        try:
            result["available"] = bool(
                available()
            )
        except Exception as exc:
            result["error"] = (
                f"available() failed: "
                f"{type(exc).__name__}: "
                f"{exc}"
            )
            return result
    else:
        result["available"] = True

    return result


def main() -> int:
    load_environment()

    try:
        route_data = route(
            "text_inference_route"
        )
    except Exception as exc:
        print(
            json.dumps(
                {
                    "ok": False,
                    "route":
                        "text_inference_route",
                    "error":
                        f"{type(exc).__name__}: "
                        f"{exc}",
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 2

    provider_ids = (
        route_provider_ids(
            route_data
        )
    )

    results = [
        diagnose_provider(
            provider_id
        )
        for provider_id
        in provider_ids
    ]

    usable = [
        item["provider"]
        for item in results
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
                "supports_text"
            ]
            and item[
                "infer_callable"
            ]
        )
    ]

    output = {
        "ok": bool(usable),
        "route":
            "text_inference_route",
        "default_provider":
            route_data.get(
                "default_provider"
            ),
        "fallback_order":
            route_data.get(
                "fallback_order",
                [],
            ),
        "usable_text_providers":
            usable,
        "providers":
            results,
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
        if usable
        else 1
    )


if __name__ == "__main__":
    sys.exit(
        main()
    )
