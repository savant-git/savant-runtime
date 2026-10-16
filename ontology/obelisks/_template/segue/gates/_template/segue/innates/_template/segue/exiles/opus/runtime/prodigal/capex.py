from __future__ import annotations

import hashlib
import json
from typing import Any, Iterable, Mapping


SCHEMA = "savant://runtime/opus/prodigal/capex/1.0.0"
OWNER = "exile:opus"
PRODIGAL = "prodigal:capex"
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
    Project computational aperture metadata for Opus dispatch.

    Historical Capex described computational aperture expansion for
    model dispatch. This modern kernel exposes dispatch breadth and
    constraint coverage without selecting or executing a provider.

    Opus runtime/router.py remains authoritative for routing and
    execution.
    """

    required_capabilities_normalized = _strings(
        required_capabilities
    )

    required_layers_normalized = _strings(
        required_layers
    )

    rows: list[dict[str, Any]] = []
    seen: set[str] = set()

    capability_union: set[str] = set()
    layer_union: set[str] = set()

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

        capability_union.update(
            capabilities
        )

        layer_union.update(
            layers
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

    missing_capabilities = tuple(
        sorted(
            set(
                required_capabilities_normalized
            )
            - capability_union
        )
    )

    missing_layers = tuple(
        sorted(
            set(
                required_layers_normalized
            )
            - layer_union
        )
    )

    projection = {
        "schema": SCHEMA,
        "owner": OWNER,
        "prodigal": PRODIGAL,
        "authority_effect": AUTHORITY_EFFECT,
        "projection_only": True,
        "deterministic": True,
        "rebuildable": True,
        "provider_count": len(
            rows
        ),
        "providers": rows,
        "aperture": {
            "capabilities": sorted(
                capability_union
            ),
            "layers": sorted(
                layer_union
            ),
            "required_capabilities": list(
                required_capabilities_normalized
            ),
            "required_layers": list(
                required_layers_normalized
            ),
            "missing_capabilities": list(
                missing_capabilities
            ),
            "missing_layers": list(
                missing_layers
            ),
            "capability_coverage_complete": (
                not missing_capabilities
            ),
            "layer_coverage_complete": (
                not missing_layers
            ),
        },
        "historical_kernel": {
            "purpose": (
                "computational aperture expansion "
                "for model dispatch"
            ),
            "preserved_quirks": {
                "cadentity": (
                    "cadence and rhythmic coherence"
                ),
                "primotive": (
                    "primitive motive extraction"
                ),
                "respeaker": (
                    "acoustic semantic rebound"
                ),
                "xspan": (
                    "cross-span vector dilation"
                ),
            },
            "quirk_execution": False,
        },
        "boundaries": {
            "selects_provider": False,
            "executes_provider": False,
            "loads_provider": False,
            "owns_provider": False,
            "owns_model": False,
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
