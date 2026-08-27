from __future__ import annotations

import importlib
import json
from pathlib import Path
from typing import Any, Dict, Iterable

from environment import load_environment
from model_projection import (
    model_supports_layers,
    provider_model,
)


OPUS_ROOT = Path(
    __file__
).resolve().parents[1]

ROUTES = (
    OPUS_ROOT
    / "registry"
    / "routes"
)

PROVIDERS = (
    OPUS_ROOT
    / "registry"
    / "providers"
)

POLICIES = (
    OPUS_ROOT
    / "registry"
    / "policies"
)


def read_json(
    path: Path,
) -> Dict[str, Any]:
    return json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )


def route(
    route_id: str,
) -> Dict[str, Any]:
    return read_json(
        ROUTES
        / f"{route_id}.json"
    )


def provider(
    provider_id: str,
) -> Dict[str, Any]:
    return read_json(
        PROVIDERS
        / f"{provider_id}.json"
    )


def policy(
    policy_id: str,
) -> Dict[str, Any]:
    return read_json(
        POLICIES
        / f"{policy_id}.json"
    )


def load_provider_module(
    provider_id: str,
):
    return importlib.import_module(
        f"providers.{provider_id}"
    )


def _normalized(
    values: Iterable[Any] | None,
) -> set[str]:
    if values is None:
        return set()

    return {
        str(value).strip().lower()
        for value in values
        if str(value).strip()
    }


def _provider_supports_capabilities(
    provider_data: Dict[str, Any],
    required_capabilities: Iterable[Any] | None,
) -> bool:
    required = _normalized(
        required_capabilities
    )

    if not required:
        return True

    available = _normalized(
        provider_data.get(
            "capabilities"
        )
        or []
    )

    return required.issubset(
        available
    )


def _provider_supports_layers(
    provider_data: Dict[str, Any],
    required_layers: Iterable[Any] | None,
) -> bool:
    required = _normalized(
        required_layers
    )

    if not required:
        return True

    model_id = provider_model(
        provider_data
    )

    if not model_id:
        return False

    return model_supports_layers(
        model_id,
        required,
    )


def select_provider(
    route_id: str = "voice_tts_route",
    *,
    required_capabilities: Iterable[Any] | None = None,
    required_layers: Iterable[Any] | None = None,
) -> Dict[str, Any]:
    load_environment()

    route_data = route(
        route_id
    )

    fallback = (
        route_data.get(
            "fallback_order"
        )
        or [
            route_data.get(
                "default_provider"
            )
        ]
    )

    for provider_id in fallback:
        if not provider_id:
            continue

        provider_data = provider(
            provider_id
        )

        if not _provider_supports_capabilities(
            provider_data,
            required_capabilities,
        ):
            continue

        if not _provider_supports_layers(
            provider_data,
            required_layers,
        ):
            continue

        module = load_provider_module(
            provider_id
        )

        available = getattr(
            module,
            "available",
            None,
        )

        if (
            not callable(
                available
            )
            or available()
        ):
            selected = dict(
                provider_data
            )

            selected[
                "selected"
            ] = True

            selected[
                "route_id"
            ] = route_id

            selected[
                "selected_model"
            ] = provider_model(
                provider_data
            )

            selected[
                "required_capabilities"
            ] = sorted(
                _normalized(
                    required_capabilities
                )
            )

            selected[
                "required_layers"
            ] = sorted(
                _normalized(
                    required_layers
                )
            )

            return selected

    constraints = {
        "required_capabilities": sorted(
            _normalized(
                required_capabilities
            )
        ),
        "required_layers": sorted(
            _normalized(
                required_layers
            )
        ),
    }

    raise RuntimeError(
        "No available provider for route "
        f"{route_id} satisfying constraints: "
        f"{constraints}"
    )


def orchestration_context(
    route_id: str,
    *,
    required_capabilities: Iterable[Any] | None = None,
    required_layers: Iterable[Any] | None = None,
) -> tuple[
    Dict[str, Any],
    Dict[str, Any],
    Dict[str, Any],
]:
    route_data = route(
        route_id
    )

    provider_data = select_provider(
        route_id,
        required_capabilities=(
            required_capabilities
        ),
        required_layers=(
            required_layers
        ),
    )

    policy_id = route_data.get(
        "policy_ref"
    )

    if not policy_id:
        raise RuntimeError(
            "Route has no policy_ref: "
            f"{route_id}"
        )

    policy_data = policy(
        str(
            policy_id
        )
    )

    provider_data[
        "timeout_seconds"
    ] = policy_data.get(
        "timeout_seconds",
        60,
    )

    return (
        route_data,
        provider_data,
        policy_data,
    )


def execute_voice_request(
    request: Dict[str, Any],
) -> Dict[str, Any]:
    (
        route_data,
        provider_data,
        policy_data,
    ) = orchestration_context(
        "voice_tts_route"
    )

    module = load_provider_module(
        provider_data["id"]
    )

    result = module.synthesize(
        request,
        provider_data,
    )

    result["lineage"] = {
        "owner": "opus",
        "route": "voice_tts_route",
        "provider": provider_data[
            "id"
        ],
        "policy": policy_data.get(
            "id"
        ),
        "fallback_order": route_data.get(
            "fallback_order",
            [],
        ),
        "request_owner": request.get(
            "owner",
            "envoy",
        ),
    }

    return result


def execute_text_request(
    request: Dict[str, Any],
) -> Dict[str, Any]:
    required_capabilities = (
        request.get(
            "required_capabilities"
        )
    )

    required_layers = request.get(
        "required_layers"
    )

    (
        route_data,
        provider_data,
        policy_data,
    ) = orchestration_context(
        "text_inference_route",
        required_capabilities=(
            required_capabilities
        ),
        required_layers=(
            required_layers
        ),
    )

    module = load_provider_module(
        provider_data["id"]
    )

    infer = getattr(
        module,
        "infer",
        None,
    )

    if not callable(
        infer
    ):
        raise RuntimeError(
            "Selected text provider has no "
            f"infer(): {provider_data['id']}"
        )

    result = infer(
        request,
        provider_data,
    )

    result["lineage"] = {
        "owner": "opus",
        "route": "text_inference_route",
        "provider": provider_data[
            "id"
        ],
        "model": provider_data.get(
            "selected_model"
        ),
        "policy": policy_data.get(
            "id"
        ),
        "fallback_order": route_data.get(
            "fallback_order",
            [],
        ),
        "required_capabilities": sorted(
            _normalized(
                required_capabilities
            )
        ),
        "required_layers": sorted(
            _normalized(
                required_layers
            )
        ),
        "request_owner": request.get(
            "owner",
            "palaver",
        ),
    }

    return result
