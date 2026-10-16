#!/usr/bin/env python3

from __future__ import annotations

import importlib
from typing import Any, Dict, Iterable, Mapping

from cognitive_orchestrator import orchestrate


def _provider_id(
    provider_data: Mapping[str, Any],
) -> str:
    return str(
        provider_data.get("id")
        or provider_data.get("provider_id")
        or ""
    ).strip()


def _load_provider_module(
    provider_id: str,
):
    module_name = str(
        provider_id
    ).strip()

    if not module_name:
        raise RuntimeError(
            "provider id is required"
        )

    if not module_name.startswith(
        "providers."
    ):
        module_name = (
            f"providers.{module_name}"
        )

    return importlib.import_module(
        module_name
    )


def provider_executor(
    request: Mapping[str, Any],
    provider_data: Mapping[str, Any],
) -> Mapping[str, Any]:
    provider_id = _provider_id(
        provider_data
    )

    module = _load_provider_module(
        provider_id
    )

    infer = getattr(
        module,
        "infer",
        None,
    )

    if not callable(infer):
        raise RuntimeError(
            "Selected text provider has no "
            f"infer(): {provider_id}"
        )

    result = infer(
        dict(request),
        dict(provider_data),
    )

    if not isinstance(
        result,
        Mapping,
    ):
        raise RuntimeError(
            f"Invalid provider result: {provider_id}"
        )

    return dict(result)


def provider_descriptors(
    *,
    route_data: Mapping[str, Any],
    primary_provider: Mapping[str, Any],
    provider_lookup,
) -> list[Dict[str, Any]]:
    ordered_ids: list[str] = []

    primary_id = _provider_id(
        primary_provider
    )

    if primary_id:
        ordered_ids.append(
            primary_id
        )

    for provider_id in (
        route_data.get(
            "fallback_order"
        )
        or ()
    ):
        value = str(
            provider_id
        ).strip()

        if (
            value
            and value not in ordered_ids
        ):
            ordered_ids.append(
                value
            )

    providers: list[
        Dict[str, Any]
    ] = []

    for provider_id in ordered_ids:
        try:
            data = provider_lookup(
                provider_id
            )
        except Exception:
            continue

        if not isinstance(
            data,
            Mapping,
        ):
            continue

        value = dict(data)

        value.setdefault(
            "id",
            provider_id,
        )

        value.setdefault(
            "available",
            True,
        )

        capabilities = value.get(
            "capabilities"
        )

        if not capabilities:
            value[
                "capabilities"
            ] = [
                "text",
            ]

        providers.append(
            value
        )

    return providers


def execute(
    request: Mapping[str, Any],
    *,
    route_data: Mapping[str, Any],
    primary_provider: Mapping[str, Any],
    policy_data: Mapping[str, Any],
    provider_lookup,
) -> Dict[str, Any]:
    providers = provider_descriptors(
        route_data=route_data,
        primary_provider=primary_provider,
        provider_lookup=provider_lookup,
    )

    if not providers:
        raise RuntimeError(
            "No Opus text providers available"
        )

    cognitive_request = dict(
        request
    )

    cognitive_request.setdefault(
        "required_capabilities",
        [
            "text",
        ],
    )

    result = orchestrate(
        cognitive_request,
        providers,
        executor=provider_executor,
    )

    if not result.get("ok"):
        raise RuntimeError(
            str(
                result.get("error")
                or "Opus cognitive orchestration failed"
            )
        )

    lineage = result.get(
        "lineage"
    )

    if not isinstance(
        lineage,
        Mapping,
    ):
        lineage = {}

    lineage = dict(lineage)

    lineage.update(
        {
            "owner":
                "opus",
            "route":
                "text_inference_route",
            "provider":
                result.get(
                    "provider"
                ),
            "policy":
                policy_data.get(
                    "id"
                ),
            "fallback_order":
                list(
                    route_data.get(
                        "fallback_order"
                    )
                    or ()
                ),
            "request_owner":
                request.get(
                    "owner",
                    "palaver",
                ),
            "cognitive_orchestration":
                True,
        }
    )

    result[
        "lineage"
    ] = lineage

    return result
