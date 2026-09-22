from __future__ import annotations

from hashlib import sha256
import json
from typing import Any, Mapping

from runtime.oid.completion import (
    REQUIREMENTS,
    requirement_statuses,
)


SCHEMA = "savant://oid/manifest/1"

MODULES = (
    "runtime.oid.core",
    "runtime.oid.frame",
    "runtime.oid.clock",
    "runtime.oid.constraint",
    "runtime.oid.store",
    "runtime.oid.recovery",
    "runtime.oid.runtime",
    "runtime.oid.projection",
    "runtime.oid.bridge",
    "runtime.oid.conversion",
    "runtime.oid.integrity",
    "runtime.oid.completion",
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


def oid_manifest() -> Mapping[str, Any]:
    statuses = requirement_statuses()

    implemented = tuple(
        status.requirement
        for status in statuses
        if status.implemented
    )

    missing = tuple(
        requirement
        for requirement in REQUIREMENTS
        if requirement not in implemented
    )

    body: dict[str, Any] = {
        "schema": SCHEMA,
        "name": "oid",
        "semantic_scope": "temporal_coherence",
        "modules": list(MODULES),
        "requirements": list(REQUIREMENTS),
        "implemented_requirements": list(
            implemented
        ),
        "missing_requirements": list(missing),
        "requirement_count": len(
            REQUIREMENTS
        ),
        "implemented_count": len(
            implemented
        ),
        "complete": not missing,
        "universal_single_present_claimed": False,
        "external_truth_authority": False,
        "external_chronology_authority": False,
        "automatic_reconciliation": False,
        "authority_transferred": False,
        "model_independent": True,
        "provider_independent": True,
        "dependency_sovereign": True,
        "stdlib_capable": True,
        "historical_halo_required": False,
        "authoritative": False,
        "authority_effect": "none",
    }

    body["digest"] = _digest(body)
    return body


def validate_manifest() -> bool:
    manifest = oid_manifest()

    if manifest["requirement_count"] != 35:
        return False

    if manifest["implemented_count"] != 35:
        return False

    if manifest["missing_requirements"]:
        return False

    if manifest["complete"] is not True:
        return False

    if (
        manifest[
            "universal_single_present_claimed"
        ]
        is not False
    ):
        return False

    if (
        manifest[
            "external_truth_authority"
        ]
        is not False
    ):
        return False

    if (
        manifest[
            "external_chronology_authority"
        ]
        is not False
    ):
        return False

    if (
        manifest[
            "automatic_reconciliation"
        ]
        is not False
    ):
        return False

    if (
        manifest["authority_transferred"]
        is not False
    ):
        return False

    if (
        manifest["historical_halo_required"]
        is not False
    ):
        return False

    if manifest["authoritative"] is not False:
        return False

    if manifest["authority_effect"] != "none":
        return False

    return True
