from __future__ import annotations

from typing import Any, Iterable

from .json_io import read_json
from .prodigal import project as project_prodigals
from .router import OPUS_ROOT
from .router import provider
from .router import route


SCHEMA = (
    "savant://runtime/opus/"
    "routing_projection/1.0.0"
)

OWNER = "exile:opus"
AUTHORITY_EFFECT = "none"


def project_route(
    route_id: str,
    *,
    required_capabilities: Iterable[Any] | None = None,
    required_layers: Iterable[Any] | None = None,
) -> dict[str, Any]:
    """
    Project the non-authoritative analytical view of an Opus route.

    This function deliberately does not call select_provider(),
    orchestration_context(), provider availability functions, or
    provider execution.

    The canonical Opus router remains the sole routing authority.
    """

    route_data = route(
        route_id
    )

    fallback_order = (
        route_data.get(
            "fallback_order"
        )
        or [
            route_data.get(
                "default_provider"
            )
        ]
    )

    provider_material = []

    for provider_id in fallback_order:
        if not provider_id:
            continue

        provider_material.append(
            provider(
                str(
                    provider_id
                )
            )
        )

    prodigal_projection = (
        project_prodigals(
            route=route_data,
            providers=provider_material,
            required_capabilities=(
                required_capabilities
            ),
            required_layers=(
                required_layers
            ),
        )
    )

    return {
        "schema": SCHEMA,
        "owner": OWNER,
        "authority_effect": (
            AUTHORITY_EFFECT
        ),
        "projection_only": True,
        "deterministic": True,
        "rebuildable": True,
        "route_id": route_id,
        "route": {
            "id": route_data.get(
                "id"
            ),
            "domain": route_data.get(
                "domain"
            ),
            "default_provider": (
                route_data.get(
                    "default_provider"
                )
            ),
            "fallback_order": list(
                fallback_order
            ),
            "policy_ref": route_data.get(
                "policy_ref"
            ),
        },
        "requirements": {
            "capabilities": sorted(
                {
                    str(value).strip()
                    for value
                    in (
                        required_capabilities
                        or ()
                    )
                    if str(value).strip()
                }
            ),
            "layers": sorted(
                {
                    str(value).strip()
                    for value
                    in (
                        required_layers
                        or ()
                    )
                    if str(value).strip()
                }
            ),
        },
        "prodigal_projection": (
            prodigal_projection
        ),
        "lineage": {
            "owner": OWNER,
            "route": route_id,
            "projection": (
                prodigal_projection.get(
                    "digest"
                )
            ),
        },
        "boundaries": {
            "selects_provider": False,
            "checks_availability": False,
            "loads_provider": False,
            "executes_provider": False,
            "binds_policy": False,
            "owns_model_suitability": False,
            "mutates_registry": False,
            "mutates_route": False,
            "creates_authority": False,
            "authoritative_router": (
                "opus.runtime.router"
            ),
        },
    }


def project_text_inference(
    *,
    required_capabilities: Iterable[Any] | None = None,
    required_layers: Iterable[Any] | None = None,
) -> dict[str, Any]:
    return project_route(
        "text_inference_route",
        required_capabilities=(
            required_capabilities
        ),
        required_layers=(
            required_layers
        ),
    )
