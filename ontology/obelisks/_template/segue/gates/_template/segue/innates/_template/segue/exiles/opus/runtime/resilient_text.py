#!/usr/bin/env python3

from __future__ import annotations

import json

from typing import Any, Dict, Iterable

from .environment import load_environment
from .model_projection import (
    model_supports_layers,
    provider_model,
)
from .router import (
    load_provider_module,
    policy,
    provider,
    route,
)
from .normalization import normalized_strings as _normalized


SCHEMA = "savant.opus.resilient-text.v1"
OWNER = "opus"
ROUTE_ID = "text_inference_route"


class ResilientTextError(
    RuntimeError
):
    pass


def _supports_capabilities(
    provider_data: Dict[str, Any],
    required: Iterable[Any] | None,
) -> bool:
    required_set = _normalized(
        required
    )

    if not required_set:
        return True

    available = _normalized(
        provider_data.get(
            "capabilities"
        )
        or []
    )

    return required_set.issubset(
        available
    )


def _supports_layers(
    provider_data: Dict[str, Any],
    required: Iterable[Any] | None,
) -> bool:
    required_set = _normalized(
        required
    )

    if not required_set:
        return True

    model_id = provider_model(
        provider_data
    )

    if not model_id:
        return False

    return model_supports_layers(
        model_id,
        required_set,
    )


def _diagnostic(
    exc: Exception,
) -> str:
    return (
        f"{type(exc).__name__}: "
        f"{str(exc or '').strip()}"
    )


def _retryable(
    exc: Exception,
) -> bool:
    text = _diagnostic(
        exc
    ).lower()

    markers = (
        "429",
        "too many requests",
        "rate limit",
        "rate_limit",
        "401",
        "unauthorized",
        "authentication",
        "invalid api key",
        "incorrect api key",
        "403",
        "forbidden",
        "permission denied",
        "404",
        "model unavailable",
        "model not found",
        "timeout",
        "timed out",
        "connection refused",
        "connection reset",
        "network is unreachable",
        "temporary failure",
        "name or service not known",
        "500",
        "502",
        "503",
        "504",
        "internal server error",
        "bad gateway",
        "service unavailable",
        "overloaded",
        "capacity",
        "all admitted opus catalog provider profiles failed",
        "no admitted opus catalog provider could be executed",
        "no admitted opus catalog provider projection available",
    )

    return any(
        marker in text
        for marker in markers
    )


def _provider_available(
    module: Any,
) -> bool:
    available = getattr(
        module,
        "available",
        None,
    )

    if not callable(
        available
    ):
        return True

    try:
        return bool(
            available()
        )

    except Exception:
        return False


def _result_model(
    result: Dict[str, Any],
    selected: Dict[str, Any],
) -> str:
    return str(
        result.get(
            "model"
        )
        or selected.get(
            "selected_model"
        )
        or ""
    ).strip()


def _result_provider_profile(
    result: Dict[str, Any],
) -> str | None:
    value = str(
        result.get(
            "provider_profile"
        )
        or ""
    ).strip()

    return value or None


def _catalog_attempts(
    result: Dict[str, Any],
) -> list[Dict[str, Any]]:
    value = result.get(
        "catalog_attempts"
    )

    if not isinstance(
        value,
        list,
    ):
        return []

    return [
        dict(item)
        for item in value
        if isinstance(
            item,
            dict,
        )
    ]


def execute_text_request_resilient(
    request: Dict[str, Any],
) -> Dict[str, Any]:
    if not isinstance(
        request,
        dict,
    ):
        raise ResilientTextError(
            "request must be an object"
        )

    load_environment()

    route_data = route(
        ROUTE_ID
    )

    policy_id = str(
        route_data.get(
            "policy_ref"
        )
        or ""
    ).strip()

    if not policy_id:
        raise ResilientTextError(
            "text inference route "
            "has no policy_ref"
        )

    policy_data = policy(
        policy_id
    )

    fallback_order = [
        str(value).strip()
        for value
        in (
            route_data.get(
                "fallback_order"
            )
            or [
                route_data.get(
                    "default_provider"
                )
            ]
        )
        if str(value).strip()
    ]

    if not fallback_order:
        raise ResilientTextError(
            "text inference route "
            "has no providers"
        )

    required_capabilities = (
        request.get(
            "required_capabilities"
        )
    )

    required_layers = (
        request.get(
            "required_layers"
        )
    )

    attempts: list[
        dict[str, Any]
    ] = []

    eligible_count = 0

    for provider_id in fallback_order:
        provider_data = provider(
            provider_id
        )

        if not _supports_capabilities(
            provider_data,
            required_capabilities,
        ):
            attempts.append(
                {
                    "provider": provider_id,
                    "state": "skipped",
                    "reason": (
                        "required_capabilities"
                    ),
                }
            )

            continue

        if not _supports_layers(
            provider_data,
            required_layers,
        ):
            attempts.append(
                {
                    "provider": provider_id,
                    "state": "skipped",
                    "reason": (
                        "required_layers"
                    ),
                }
            )

            continue

        module = load_provider_module(
            provider_id
        )

        if not _provider_available(
            module
        ):
            attempts.append(
                {
                    "provider": provider_id,
                    "state": "skipped",
                    "reason": "unavailable",
                }
            )

            continue

        infer = getattr(
            module,
            "infer",
            None,
        )

        if not callable(
            infer
        ):
            attempts.append(
                {
                    "provider": provider_id,
                    "state": "skipped",
                    "reason": (
                        "infer_missing"
                    ),
                }
            )

            continue

        eligible_count += 1

        selected = dict(
            provider_data
        )

        selected[
            "selected"
        ] = True

        selected[
            "route_id"
        ] = ROUTE_ID

        selected[
            "selected_model"
        ] = provider_model(
            selected
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

        selected[
            "timeout_seconds"
        ] = policy_data.get(
            "timeout_seconds",
            60,
        )

        try:
            result = infer(
                request,
                selected,
            )

        except Exception as exc:
            retryable = _retryable(
                exc
            )

            attempts.append(
                {
                    "provider": (
                        provider_id
                    ),
                    "model": (
                        selected.get(
                            "selected_model"
                        )
                    ),
                    "state": "failed",
                    "retryable": (
                        retryable
                    ),
                    "diagnostic": (
                        _diagnostic(
                            exc
                        )
                    ),
                }
            )

            if retryable:
                continue

            raise

        if not isinstance(
            result,
            dict,
        ):
            attempts.append(
                {
                    "provider": provider_id,
                    "model": (
                        selected.get(
                            "selected_model"
                        )
                    ),
                    "state": "failed",
                    "retryable": False,
                    "diagnostic": (
                        "provider result "
                        "was not an object"
                    ),
                }
            )

            raise ResilientTextError(
                "provider result "
                "must be an object"
            )

        resolved_model = _result_model(
            result,
            selected,
        )

        resolved_profile = (
            _result_provider_profile(
                result
            )
        )

        catalog_attempts = (
            _catalog_attempts(
                result
            )
        )

        successful_attempt: Dict[
            str,
            Any,
        ] = {
            "provider": provider_id,
            "model": resolved_model,
            "state": "succeeded",
        }

        if resolved_profile:
            successful_attempt[
                "provider_profile"
            ] = resolved_profile

        if catalog_attempts:
            successful_attempt[
                "catalog_attempts"
            ] = catalog_attempts

        attempts.append(
            successful_attempt
        )

        lineage: Dict[
            str,
            Any,
        ] = {
            "owner": OWNER,
            "route": ROUTE_ID,
            "provider": provider_id,
            "provider_profile": (
                resolved_profile
            ),
            "model": resolved_model,
            "policy": policy_data.get(
                "id"
            ),
            "fallback_order": (
                fallback_order
            ),
            "required_capabilities": (
                sorted(
                    _normalized(
                        required_capabilities
                    )
                )
            ),
            "required_layers": (
                sorted(
                    _normalized(
                        required_layers
                    )
                )
            ),
            "request_owner": (
                request.get(
                    "owner",
                    "palaver",
                )
            ),
            "fallback_triggered": (
                len(
                    [
                        attempt
                        for attempt
                        in attempts[
                            :-1
                        ]
                        if attempt.get(
                            "state"
                        )
                        == "failed"
                    ]
                )
                > 0
            ),
            "attempts": attempts,
            "executor": (
                "resilient_text"
            ),
            "schema": SCHEMA,
        }

        if catalog_attempts:
            lineage[
                "catalog_attempts"
            ] = catalog_attempts

        admission_digest = str(
            result.get(
                "admission_projection_digest"
            )
            or ""
        ).strip()

        if admission_digest:
            lineage[
                "admission_projection_digest"
            ] = admission_digest

        lineage[
            "admission_selected"
        ] = bool(
            result.get(
                "admission_selected",
                False,
            )
        )

        result[
            "lineage"
        ] = lineage

        return result

    if eligible_count == 0:
        raise ResilientTextError(
            "no eligible text provider "
            "was available"
        )

    diagnostics = "; ".join(
        (
            f"{attempt.get('provider')}: "
            f"{attempt.get('diagnostic')}"
        )
        for attempt in attempts
        if attempt.get(
            "state"
        )
        == "failed"
    )

    raise ResilientTextError(
        "all eligible text providers "
        "failed"
        + (
            f": {diagnostics}"
            if diagnostics
            else ""
        )
    )


def projection() -> Dict[str, Any]:
    load_environment()

    route_data = route(
        ROUTE_ID
    )

    fallback_order = [
        str(value).strip()
        for value
        in (
            route_data.get(
                "fallback_order"
            )
            or []
        )
        if str(value).strip()
    ]

    providers = []

    for provider_id in fallback_order:
        try:
            provider_data = provider(
                provider_id
            )

            module = (
                load_provider_module(
                    provider_id
                )
            )

            providers.append(
                {
                    "id": provider_id,
                    "model": (
                        provider_model(
                            provider_data
                        )
                    ),
                    "available": (
                        _provider_available(
                            module
                        )
                    ),
                }
            )

        except Exception as exc:
            providers.append(
                {
                    "id": provider_id,
                    "available": False,
                    "diagnostic": (
                        _diagnostic(
                            exc
                        )
                    ),
                }
            )

    return {
        "schema": SCHEMA,
        "owner": OWNER,
        "route": ROUTE_ID,
        "fallback_order": (
            fallback_order
        ),
        "providers": providers,
        "execution_time_fallback": True,
        "catalog_lineage_preserved": True,
        "model_lineage_preserved": True,
        "migration_portable": True,
        "authority_effect": "none",
    }


if __name__ == "__main__":
    print(
        json.dumps(
            projection(),
            indent=2,
            sort_keys=True,
        )
    )
