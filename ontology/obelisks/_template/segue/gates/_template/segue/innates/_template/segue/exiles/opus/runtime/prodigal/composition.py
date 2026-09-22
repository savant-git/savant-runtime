from __future__ import annotations

import hashlib
import json
from typing import Any, Iterable, Mapping

from . import capex
from . import orchid
from . import refuze
from . import router_core


SCHEMA = (
    "savant://runtime/opus/"
    "prodigal/composition/1.0.0"
)

OWNER = "exile:opus"
AUTHORITY_EFFECT = "none"


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
        _canonical(value).encode(
            "utf-8"
        )
    ).hexdigest()


def project(
    *,
    route: Mapping[str, Any],
    providers: Iterable[Mapping[str, Any]],
    required_capabilities: Iterable[Any] | None = None,
    required_layers: Iterable[Any] | None = None,
) -> dict[str, Any]:
    """
    Compose recovered Opus Prodigal projections.

    This is a deterministic diagnostic aperture only.

    The authoritative Opus router retains provider availability
    checks, model suitability, provider selection, policy binding,
    provider loading, and execution.
    """

    provider_material = tuple(
        dict(provider)
        for provider in providers
    )

    router_projection = (
        router_core.project(
            route=route,
            providers=provider_material,
            required_capabilities=(
                required_capabilities
            ),
            required_layers=(
                required_layers
            ),
        )
    )

    capex_projection = capex.project(
        providers=provider_material,
        required_capabilities=(
            required_capabilities
        ),
        required_layers=(
            required_layers
        ),
    )

    orchid_projection = (
        orchid.project(
            providers=provider_material,
            required_capabilities=(
                required_capabilities
            ),
            required_layers=(
                required_layers
            ),
        )
    )

    refuze_projection = (
        refuze.project(
            router_core=router_projection,
            capex=capex_projection,
            orchid=orchid_projection,
        )
    )

    projection = {
        "schema": SCHEMA,
        "owner": OWNER,
        "authority_effect": (
            AUTHORITY_EFFECT
        ),
        "projection_only": True,
        "deterministic": True,
        "rebuildable": True,
        "route_id": str(
            route.get("id") or ""
        ).strip(),
        "prodigals": {
            "router_core": (
                router_projection
            ),
            "capex": capex_projection,
            "orchid": (
                orchid_projection
            ),
            "refuze": (
                refuze_projection
            ),
        },
        "summary": {
            "provider_count": (
                capex_projection.get(
                    "provider_count",
                    0,
                )
            ),
            "declared_candidates": (
                router_projection.get(
                    "eligible_by_declared_metadata",
                    [],
                )
            ),
            "reconciliation_required": (
                refuze_projection.get(
                    "synthesis",
                    {},
                ).get(
                    "reconciliation_required",
                    False,
                )
            ),
        },
        "lineage": {
            "router_core_digest": (
                router_projection.get(
                    "digest"
                )
            ),
            "capex_digest": (
                capex_projection.get(
                    "digest"
                )
            ),
            "orchid_digest": (
                orchid_projection.get(
                    "digest"
                )
            ),
            "refuze_digest": (
                refuze_projection.get(
                    "digest"
                )
            ),
        },
        "boundaries": {
            "selects_provider": False,
            "checks_runtime_availability": False,
            "loads_provider": False,
            "executes_provider": False,
            "binds_policy": False,
            "owns_model_suitability": False,
            "mutates_route": False,
            "mutates_provider": False,
            "mutates_registry": False,
            "creates_authority": False,
            "authoritative_router": (
                "opus.runtime.router"
            ),
        },
    }

    projection[
        "digest"
    ] = _digest(
        projection
    )

    return projection
