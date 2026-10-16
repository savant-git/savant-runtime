from __future__ import annotations

import importlib
import json
from pathlib import Path
from typing import Any, Dict, Iterable

from environment import load_environment


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


def _route_provider_ids(
    route_data: Dict[str, Any],
) -> list[str]:
    raw = (
        route_data.get(
            "fallback_order"
        )
        or [
            route_data.get(
                "default_provider"
            )
        ]
    )

    result: list[str] = []

    for value in raw:
        provider_id = str(
            value or ""
        ).strip()

        if (
            provider_id
            and provider_id
            not in result
        ):
            result.append(
                provider_id
            )

    return result


def _normalized_capabilities(
    values: Iterable[Any] | None,
) -> set[str]:
    if values is None:
        return set()

    return {
        str(value).strip()
        for value in values
        if str(value).strip()
    }


def provider_capabilities(
    provider_data: Dict[str, Any],
) -> set[str]:
    raw = provider_data.get(
        "capabilities"
    )

    if not isinstance(
        raw,
        list,
    ):
        return set()

    return _normalized_capabilities(
        raw
    )


def provider_supports(
    provider_data: Dict[str, Any],
    required_capabilities: Iterable[Any] | None = None,
) -> bool:
    required = _normalized_capabilities(
        required_capabilities
    )

    if not required:
        return True

    available = provider_capabilities(
        provider_data
    )

    return required.issubset(
        available
    )


def provider_available(
    provider_id: str,
) -> bool:
    module = load_provider_module(
        provider_id
    )

    available = getattr(
        module,
        "available",
        None,
    )

    return (
        not callable(
            available
        )
        or bool(
            available()
        )
    )


def select_provider(
    route_id: str = "voice_tts_route",
    *,
    required_capabilities: Iterable[Any] | None = None,
    preferred_providers: Iterable[Any] | None = None,
) -> Dict[str, Any]:
    load_environment()

    route_data = route(
        route_id
    )

    route_provider_ids = (
        _route_provider_ids(
            route_data
        )
    )

    preferred = [
        str(value).strip()
        for value in (
            preferred_providers
            or []
        )
        if str(value).strip()
    ]

    candidates: list[str] = []

    for provider_id in preferred:
        if (
            provider_id
            in route_provider_ids
            and provider_id
            not in candidates
        ):
            candidates.append(
                provider_id
            )

    for provider_id in route_provider_ids:
        if provider_id not in candidates:
            candidates.append(
                provider_id
            )

    required = _normalized_capabilities(
        required_capabilities
    )

    for provider_id in candidates:
        provider_data = provider(
            provider_id
        )

        if not provider_supports(
            provider_data,
            required,
        ):
            continue

        if not provider_available(
            provider_id
        ):
            continue

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
            "required_capabilities"
        ] = sorted(
            required
        )

        selected[
            "selection_mode"
        ] = (
            "capability"
            if required
            else "fallback"
        )

        return selected

    detail = ""

    if required:
        detail = (
            "; required_capabilities="
            + ",".join(
                sorted(
                    required
                )
            )
        )

    raise RuntimeError(
        "No available provider for route: "
        f"{route_id}"
        + detail
    )


def orchestration_context(
    route_id: str,
    *,
    required_capabilities: Iterable[Any] | None = None,
    preferred_providers: Iterable[Any] | None = None,
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
        preferred_providers=(
            preferred_providers
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
        "selection_mode": provider_data.get(
            "selection_mode",
            "fallback",
        ),
        "required_capabilities": (
            provider_data.get(
                "required_capabilities",
                [],
            )
        ),
    }

    return result


def _request_capabilities(
    request: Dict[str, Any],
) -> list[Any] | None:
    raw = request.get(
        "required_capabilities"
    )

    if raw is None:
        return None

    if not isinstance(
        raw,
        list,
    ):
        raise RuntimeError(
            "required_capabilities must be a list"
        )

    return raw


def _request_preferred_providers(
    request: Dict[str, Any],
) -> list[Any] | None:
    raw = request.get(
        "preferred_providers"
    )

    if raw is None:
        return None

    if not isinstance(
        raw,
        list,
    ):
        raise RuntimeError(
            "preferred_providers must be a list"
        )

    return raw


def _legacy_text_execution(
    request: Dict[str, Any],
    *,
    route_data: Dict[str, Any],
    provider_data: Dict[str, Any],
    policy_data: Dict[str, Any],
) -> Dict[str, Any]:
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
        "policy": policy_data.get(
            "id"
        ),
        "fallback_order": route_data.get(
            "fallback_order",
            [],
        ),
        "request_owner": request.get(
            "owner",
            "palaver",
        ),
        "selection_mode": provider_data.get(
            "selection_mode",
            "fallback",
        ),
        "required_capabilities": (
            provider_data.get(
                "required_capabilities",
                [],
            )
        ),
        "cognitive_orchestration": False,
    }

    return result


def execute_text_request(
    request: Dict[str, Any],
) -> Dict[str, Any]:
    required_capabilities = (
        _request_capabilities(
            request
        )
    )

    preferred_providers = (
        _request_preferred_providers(
            request
        )
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
        preferred_providers=(
            preferred_providers
        ),
    )

    cognitive_enabled = request.get(
        "cognitive_orchestration",
        True,
    )

    if not bool(
        cognitive_enabled
    ):
        return _legacy_text_execution(
            request,
            route_data=route_data,
            provider_data=provider_data,
            policy_data=policy_data,
        )

    from cognitive_api import (
        execute_text,
    )

    return execute_text(
        request,
        route_data=route_data,
        provider_data=provider_data,
        policy_data=policy_data,
        provider_lookup=provider,
    )
