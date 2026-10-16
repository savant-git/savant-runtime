#!/usr/bin/env python3

from __future__ import annotations

from typing import Any, Callable, Dict, Iterable, Mapping

from cognitive_context import (
    context_from_request,
    inject_context,
)
from cognitive_execution import (
    ProviderExecutor,
    execute_cognitive_request,
)
from cognitive_provider_health import (
    capability_healthy_providers,
)
from cognitive_synthesis import synthesize


def orchestrate(
    request: Mapping[str, Any],
    providers: Iterable[
        Mapping[str, Any]
    ],
    *,
    executor: ProviderExecutor | None = None,
) -> Dict[str, Any]:
    request_value = dict(request)

    context = context_from_request(
        request_value
    )

    request_value = inject_context(
        request_value,
        context,
    )

    required = request_value.get(
        "required_capabilities"
    ) or ("text",)

    if isinstance(required, str):
        required = (required,)

    provider_values = [
        dict(provider)
        for provider in providers
        if isinstance(provider, Mapping)
    ]

    healthy = capability_healthy_providers(
        provider_values,
        tuple(required),
    )

    if not healthy:
        return {
            "ok": False,
            "error":
                "no healthy capability-compatible provider available",
            "context":
                context.as_dict(),
            "providers_considered":
                len(provider_values),
            "providers_usable":
                0,
        }

    result = execute_cognitive_request(
        request_value,
        healthy,
        executor=executor,
    )

    if not result.get("ok"):
        result["context"] = (
            context.as_dict()
        )

        return result

    candidates = result.get(
        "candidates"
    ) or ()

    synthesis = synthesize(
        candidates
    )

    result["text"] = synthesis.text

    result["provider"] = (
        synthesis.source_provider_id
        or result.get("provider")
    )

    result["synthesis"] = (
        synthesis.as_dict()
    )

    result["context"] = (
        context.as_dict()
    )

    result[
        "providers_considered"
    ] = len(provider_values)

    result[
        "providers_usable"
    ] = len(healthy)

    result[
        "cognitive_orchestration"
    ] = True

    return result


def orchestrate_text(
    text: str,
    providers: Iterable[
        Mapping[str, Any]
    ],
    *,
    executor: ProviderExecutor | None = None,
    request_id: str | None = None,
    cognitive_context: Mapping[
        str,
        Any,
    ] | None = None,
    required_capabilities: tuple[
        str,
        ...,
    ] = ("text",),
    strategy: str | None = None,
    authority_sensitive: bool = False,
    requires_verification: bool = False,
) -> Dict[str, Any]:
    request: Dict[str, Any] = {
        "text": str(text),
        "required_capabilities":
            list(required_capabilities),
        "authority_sensitive":
            bool(authority_sensitive),
        "requires_verification":
            bool(requires_verification),
    }

    if request_id:
        request[
            "request_id"
        ] = request_id

    if cognitive_context:
        request[
            "cognitive_context"
        ] = dict(
            cognitive_context
        )

    if strategy:
        request[
            "cognitive_strategy"
        ] = strategy

    return orchestrate(
        request,
        providers,
        executor=executor,
    )
