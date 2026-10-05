from __future__ import annotations

import hashlib
import json
from typing import Any, Iterable, Mapping


SCHEMA = "savant://runtime/opus/prodigal/router_core/1.0.0"
OWNER = "exile:opus"
PRODIGAL = "prodigal:router_core"

AUTHORITY_EFFECT = "none"


def _strings(
    values: Iterable[Any] | None,
) -> tuple[str, ...]:
    if values is None:
        return ()

    normalized = {
        str(value).strip()
        for value in values
        if str(value).strip()
    }

    return tuple(
        sorted(normalized)
    )


def _canonical(
    value: Any,
) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )


def _digest(
    value: Any,
) -> str:
    return hashlib.sha256(
        _canonical(value).encode("utf-8")
    ).hexdigest()


def _provider_id(
    provider: Mapping[str, Any],
) -> str:
    return str(
        provider.get("id") or ""
    ).strip()


def _capabilities(
    provider: Mapping[str, Any],
) -> tuple[str, ...]:
    return _strings(
        provider.get("capabilities") or ()
    )


def _layers(
    provider: Mapping[str, Any],
) -> tuple[str, ...]:
    return _strings(
        provider.get("cognitive_layers")
        or provider.get("layers")
        or ()
    )


def _fallback_rank(
    provider_id: str,
    fallback_order: tuple[str, ...],
) -> int | None:
    try:
        return fallback_order.index(
            provider_id
        )
    except ValueError:
        return None


def _constraint_projection(
    provider: Mapping[str, Any],
    *,
    required_capabilities: tuple[str, ...],
    required_layers: tuple[str, ...],
) -> dict[str, Any]:
    available_capabilities = set(
        _capabilities(provider)
    )

    available_layers = set(
        _layers(provider)
    )

    required_capability_set = set(
        required_capabilities
    )

    required_layer_set = set(
        required_layers
    )

    missing_capabilities = tuple(
        sorted(
            required_capability_set
            - available_capabilities
        )
    )

    missing_layers = tuple(
        sorted(
            required_layer_set
            - available_layers
        )
    )

    return {
        "required_capabilities": list(
            required_capabilities
        ),
        "required_layers": list(
            required_layers
        ),
        "missing_capabilities": list(
            missing_capabilities
        ),
        "missing_layers": list(
            missing_layers
        ),
        "capability_match": (
            not missing_capabilities
        ),
        "layer_metadata_match": (
            not missing_layers
        ),
    }


def project(
    *,
    route: Mapping[str, Any],
    providers: Iterable[Mapping[str, Any]],
    required_capabilities: Iterable[Any] | None = None,
    required_layers: Iterable[Any] | None = None,
) -> dict[str, Any]:
    """
    Project deterministic routing refinement metadata.

    router_core does not select, load, invoke, rank by hidden
    preference, or execute providers. The authoritative Opus router
    remains responsible for availability checks, model-layer
    suitability, fallback traversal, policy binding, and execution.

    This projection preserves the durable historical router_core
    kernel without creating parallel routing authority.
    """

    route_id = str(
        route.get("id") or ""
    ).strip()

    fallback_order = _strings(
        route.get("fallback_order") or ()
    )

    required_capabilities_normalized = _strings(
        required_capabilities
    )

    required_layers_normalized = _strings(
        required_layers
    )

    provider_rows: list[dict[str, Any]] = []

    seen: set[str] = set()

    for provider_data in providers:
        provider_id = _provider_id(
            provider_data
        )

        if not provider_id:
            continue

        if provider_id in seen:
            raise ValueError(
                "duplicate provider id: "
                f"{provider_id}"
            )

        seen.add(
            provider_id
        )

        constraints = _constraint_projection(
            provider_data,
            required_capabilities=(
                required_capabilities_normalized
            ),
            required_layers=(
                required_layers_normalized
            ),
        )

        fallback_rank = _fallback_rank(
            provider_id,
            fallback_order,
        )

        provider_rows.append(
            {
                "provider_id": provider_id,
                "fallback_rank": fallback_rank,
                "in_fallback_order": (
                    fallback_rank is not None
                ),
                "constraints": constraints,
                "provider_digest": _digest(
                    provider_data
                ),
            }
        )

    provider_rows.sort(
        key=lambda row: (
            row["fallback_rank"] is None,
            (
                row["fallback_rank"]
                if row["fallback_rank"] is not None
                else 0
            ),
            row["provider_id"],
        )
    )

    eligible_by_declared_metadata = [
        row["provider_id"]
        for row in provider_rows
        if (
            row["in_fallback_order"]
            and row["constraints"][
                "capability_match"
            ]
            and row["constraints"][
                "layer_metadata_match"
            ]
        )
    ]

    projection = {
        "schema": SCHEMA,
        "owner": OWNER,
        "prodigal": PRODIGAL,
        "authority_effect": AUTHORITY_EFFECT,
        "projection_only": True,
        "deterministic": True,
        "rebuildable": True,
        "route_id": route_id,
        "route_digest": _digest(
            route
        ),
        "required_capabilities": list(
            required_capabilities_normalized
        ),
        "required_layers": list(
            required_layers_normalized
        ),
        "fallback_order": list(
            fallback_order
        ),
        "providers": provider_rows,
        "eligible_by_declared_metadata": (
            eligible_by_declared_metadata
        ),
        "boundaries": {
            "selects_provider": False,
            "checks_runtime_availability": False,
            "loads_provider_module": False,
            "executes_provider": False,
            "binds_policy": False,
            "owns_model_suitability": False,
            "mutates_route": False,
            "mutates_provider": False,
            "creates_authority": False,
            "authoritative_router": (
                "opus.runtime.router"
            ),
        },
    }

    projection["digest"] = _digest(
        projection
    )

    return projection
