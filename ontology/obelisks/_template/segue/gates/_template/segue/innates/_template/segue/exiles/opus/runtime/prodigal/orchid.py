from __future__ import annotations

import hashlib
import json
from typing import Any, Iterable, Mapping


SCHEMA = "savant://runtime/opus/prodigal/orchid/1.0.0"
OWNER = "exile:opus"
PRODIGAL = "prodigal:orchid"
AUTHORITY_EFFECT = "none"


def _strings(
    values: Iterable[Any] | None,
) -> tuple[str, ...]:
    if values is None:
        return ()

    return tuple(
        sorted(
            {
                str(value).strip()
                for value in values
                if str(value).strip()
            }
        )
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


def project(
    *,
    providers: Iterable[Mapping[str, Any]],
    required_capabilities: Iterable[Any] | None = None,
    required_layers: Iterable[Any] | None = None,
) -> dict[str, Any]:
    """
    Project deterministic provider branching topology.

    Historical Orchid described spectral branching and harmonic
    forking. The surviving modern kernel is provider divergence:
    expose how eligible provider paths branch across declared
    capabilities and cognitive-layer metadata without selecting
    a branch or executing it.

    Opus runtime/router.py remains authoritative for provider
    suitability, availability, selection, policy, and execution.
    """

    required_capabilities_normalized = _strings(
        required_capabilities
    )

    required_layers_normalized = _strings(
        required_layers
    )

    required_capability_set = set(
        required_capabilities_normalized
    )

    required_layer_set = set(
        required_layers_normalized
    )

    rows: list[dict[str, Any]] = []
    seen: set[str] = set()

    capability_branches: dict[
        str,
        list[str],
    ] = {}

    layer_branches: dict[
        str,
        list[str],
    ] = {}

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

        capabilities = _strings(
            provider_data.get(
                "capabilities"
            )
            or ()
        )

        layers = _strings(
            provider_data.get(
                "cognitive_layers"
            )
            or provider_data.get(
                "layers"
            )
            or ()
        )

        capability_set = set(
            capabilities
        )

        layer_set = set(
            layers
        )

        missing_capabilities = tuple(
            sorted(
                required_capability_set
                - capability_set
            )
        )

        missing_layers = tuple(
            sorted(
                required_layer_set
                - layer_set
            )
        )

        for capability in capabilities:
            capability_branches.setdefault(
                capability,
                [],
            ).append(
                provider_id
            )

        for layer in layers:
            layer_branches.setdefault(
                layer,
                [],
            ).append(
                provider_id
            )

        rows.append(
            {
                "provider_id": provider_id,
                "capabilities": list(
                    capabilities
                ),
                "layers": list(
                    layers
                ),
                "missing_capabilities": list(
                    missing_capabilities
                ),
                "missing_layers": list(
                    missing_layers
                ),
                "declared_constraint_match": (
                    not missing_capabilities
                    and not missing_layers
                ),
                "provider_digest": _digest(
                    provider_data
                ),
            }
        )

    rows.sort(
        key=lambda row: row[
            "provider_id"
        ]
    )

    capability_projection = {
        key: sorted(
            value
        )
        for key, value in sorted(
            capability_branches.items()
        )
    }

    layer_projection = {
        key: sorted(
            value
        )
        for key, value in sorted(
            layer_branches.items()
        )
    }

    matching = [
        row["provider_id"]
        for row in rows
        if row[
            "declared_constraint_match"
        ]
    ]

    projection = {
        "schema": SCHEMA,
        "owner": OWNER,
        "prodigal": PRODIGAL,
        "authority_effect": AUTHORITY_EFFECT,
        "projection_only": True,
        "deterministic": True,
        "rebuildable": True,
        "required_capabilities": list(
            required_capabilities_normalized
        ),
        "required_layers": list(
            required_layers_normalized
        ),
        "providers": rows,
        "branches": {
            "by_capability": (
                capability_projection
            ),
            "by_layer": (
                layer_projection
            ),
            "declared_constraint_matches": (
                matching
            ),
            "provider_branch_count": len(
                rows
            ),
            "capability_branch_count": len(
                capability_projection
            ),
            "layer_branch_count": len(
                layer_projection
            ),
        },
        "historical_kernel": {
            "purpose": (
                "spectral branching and "
                "harmonic forking"
            ),
            "preserved_quirks": {
                "petallo": (
                    "petal-spread semantic bloom"
                ),
                "shiftbat": (
                    "tonal pivot and polar balancing"
                ),
                "voicefork": (
                    "harmonic branching"
                ),
            },
            "quirk_execution": False,
        },
        "boundaries": {
            "selects_branch": False,
            "selects_provider": False,
            "checks_availability": False,
            "loads_provider": False,
            "executes_provider": False,
            "owns_model_suitability": False,
            "mutates_registry": False,
            "mutates_request": False,
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
