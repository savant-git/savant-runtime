from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping


SCHEMA = "savant://runtime/opus/prodigal/refuze/1.0.0"
OWNER = "exile:opus"
PRODIGAL = "prodigal:refuze"
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
        _canonical(value).encode("utf-8")
    ).hexdigest()


def _require_projection(
    value: Mapping[str, Any],
    prodigal: str,
) -> None:
    if value.get(
        "prodigal"
    ) != prodigal:
        raise ValueError(
            "unexpected prodigal projection: "
            f"expected {prodigal}"
        )

    if value.get(
        "authority_effect"
    ) != "none":
        raise ValueError(
            "input projection has authority effect: "
            f"{prodigal}"
        )

    if value.get(
        "projection_only"
    ) is not True:
        raise ValueError(
            "input is not projection-only: "
            f"{prodigal}"
        )


def project(
    *,
    router_core: Mapping[str, Any],
    capex: Mapping[str, Any],
    orchid: Mapping[str, Any],
) -> dict[str, Any]:
    """
    Synthesize the three recovered Opus routing projections.

    Historical Refuze was a tri-vector synthesis kernel. Its durable
    modern kernel composes router_core, Capex, and Orchid projections
    into one deterministic diagnostic view.

    Refuze does not select or execute providers and cannot alter the
    authoritative Opus routing path.
    """

    _require_projection(
        router_core,
        "prodigal:router_core",
    )

    _require_projection(
        capex,
        "prodigal:capex",
    )

    _require_projection(
        orchid,
        "prodigal:orchid",
    )

    router_route_id = str(
        router_core.get(
            "route_id"
        )
        or ""
    ).strip()

    router_required_capabilities = (
        router_core.get(
            "required_capabilities"
        )
        or []
    )

    router_required_layers = (
        router_core.get(
            "required_layers"
        )
        or []
    )

    capex_aperture = (
        capex.get(
            "aperture"
        )
        or {}
    )

    orchid_required_capabilities = (
        orchid.get(
            "required_capabilities"
        )
        or []
    )

    orchid_required_layers = (
        orchid.get(
            "required_layers"
        )
        or []
    )

    consistency = {
        "capability_requirements": (
            router_required_capabilities
            == capex_aperture.get(
                "required_capabilities",
                [],
            )
            == orchid_required_capabilities
        ),
        "layer_requirements": (
            router_required_layers
            == capex_aperture.get(
                "required_layers",
                [],
            )
            == orchid_required_layers
        ),
    }

    router_candidates = (
        router_core.get(
            "eligible_by_declared_metadata"
        )
        or []
    )

    orchid_candidates = (
        (
            orchid.get(
                "branches"
            )
            or {}
        ).get(
            "declared_constraint_matches"
        )
        or []
    )

    consistency[
        "declared_candidate_projection"
    ] = (
        sorted(
            router_candidates
        )
        == sorted(
            orchid_candidates
        )
    )

    conflicts = [
        name
        for name, consistent
        in consistency.items()
        if not consistent
    ]

    synthesis = {
        "route_id": router_route_id,
        "dispatch_aperture": {
            "provider_count": capex.get(
                "provider_count",
                0,
            ),
            "capabilities": capex_aperture.get(
                "capabilities",
                [],
            ),
            "layers": capex_aperture.get(
                "layers",
                [],
            ),
            "missing_capabilities": (
                capex_aperture.get(
                    "missing_capabilities",
                    [],
                )
            ),
            "missing_layers": (
                capex_aperture.get(
                    "missing_layers",
                    [],
                )
            ),
        },
        "routing_candidates": list(
            router_candidates
        ),
        "branching": (
            orchid.get(
                "branches"
            )
            or {}
        ),
        "consistency": consistency,
        "conflicts": conflicts,
        "reconciliation_required": bool(
            conflicts
        ),
    }

    projection = {
        "schema": SCHEMA,
        "owner": OWNER,
        "prodigal": PRODIGAL,
        "authority_effect": AUTHORITY_EFFECT,
        "projection_only": True,
        "deterministic": True,
        "rebuildable": True,
        "inputs": {
            "router_core": {
                "digest": router_core.get(
                    "digest"
                ),
                "schema": router_core.get(
                    "schema"
                ),
            },
            "capex": {
                "digest": capex.get(
                    "digest"
                ),
                "schema": capex.get(
                    "schema"
                ),
            },
            "orchid": {
                "digest": orchid.get(
                    "digest"
                ),
                "schema": orchid.get(
                    "schema"
                ),
            },
        },
        "synthesis": synthesis,
        "historical_kernel": {
            "purpose": (
                "tri-vector synthesis kernel"
            ),
            "preserved_quirks": {
                "heatfuss": (
                    "thermal conflict pressure"
                ),
                "over_lay": (
                    "layered synthesis alignment"
                ),
                "tfold": (
                    "tri-fold recombination"
                ),
            },
            "quirk_execution": False,
        },
        "boundaries": {
            "selects_provider": False,
            "checks_availability": False,
            "loads_provider": False,
            "executes_provider": False,
            "binds_policy": False,
            "resolves_conflicts": False,
            "mutates_inputs": False,
            "mutates_registry": False,
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
