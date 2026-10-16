from __future__ import annotations

from hashlib import sha256
import json
from typing import Any, Mapping

from runtime.catax.completion import (
    REQUIREMENTS,
    requirement_statuses,
)


SCHEMA = "savant://catax/manifest/1"

MODULES = (
    "runtime.catax.core",
    "runtime.catax.transform",
    "runtime.catax.composition",
    "runtime.catax.interaction",
    "runtime.catax.integrity",
    "runtime.catax.completion",
)


def _canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def _digest(value: Any) -> str:
    return sha256(
        _canonical_json(value).encode("utf-8")
    ).hexdigest()


def catax_manifest() -> Mapping[str, Any]:
    statuses = requirement_statuses()

    implemented = tuple(
        status["requirement"]
        for status in statuses
        if status["implemented"]
    )

    missing = tuple(
        status["requirement"]
        for status in statuses
        if not status["implemented"]
    )

    body: dict[str, Any] = {
        "schema": SCHEMA,
        "name": "catax",
        "semantic_scope": (
            "temporal_geometry"
        ),
        "historical_kernel": (
            "catax_applies_temporal_geometry"
        ),
        "modules": list(MODULES),
        "requirements": list(
            REQUIREMENTS
        ),
        "implemented_requirements": list(
            implemented
        ),
        "missing_requirements": list(
            missing
        ),
        "module_count": len(MODULES),
        "requirement_count": len(
            REQUIREMENTS
        ),
        "implemented_count": len(
            implemented
        ),
        "complete": not missing,
        "historical_halo_required": False,
        "historical_catena_required": False,
        "metaphysical_rotation_required": False,
        "fixed_catax_taxonomy_required": False,
        "external_truth_authority": False,
        "external_chronology_authority": False,
        "automatic_reconciliation": False,
        "authority_transferred": False,
        "model_independent": True,
        "provider_independent": True,
        "dependency_sovereign": True,
        "stdlib_capable": True,
        "derived": True,
        "authoritative": False,
        "authority_effect": "none",
    }

    body["digest"] = _digest(body)
    return body


def validate_manifest() -> bool:
    manifest = catax_manifest()

    return all(
        (
            manifest[
                "requirement_count"
            ]
            == 35,
            manifest[
                "implemented_count"
            ]
            == 35,
            manifest[
                "missing_requirements"
            ]
            == [],
            manifest["complete"] is True,
            manifest[
                "historical_halo_required"
            ]
            is False,
            manifest[
                "historical_catena_required"
            ]
            is False,
            manifest[
                "metaphysical_rotation_required"
            ]
            is False,
            manifest[
                "fixed_catax_taxonomy_required"
            ]
            is False,
            manifest[
                "external_truth_authority"
            ]
            is False,
            manifest[
                "external_chronology_authority"
            ]
            is False,
            manifest[
                "automatic_reconciliation"
            ]
            is False,
            manifest[
                "authority_transferred"
            ]
            is False,
            manifest[
                "model_independent"
            ]
            is True,
            manifest[
                "provider_independent"
            ]
            is True,
            manifest[
                "dependency_sovereign"
            ]
            is True,
            manifest[
                "stdlib_capable"
            ]
            is True,
            manifest[
                "authoritative"
            ]
            is False,
            manifest[
                "authority_effect"
            ]
            == "none",
        )
    )
