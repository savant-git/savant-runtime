#!/usr/bin/env python3
from __future__ import annotations

import datetime as dt
import hashlib
import json
import shutil
from pathlib import Path
from typing import Any


ROOT = Path("/root/savant-runtime")

LANTERN_ROOT = (
    ROOT
    / "hierarchies"
    / "identity"
    / "exiles"
    / "opus"
    / "prodigals"
    / "nocturne"
    / "quirks"
    / "lantern"
)

DEFINITION = LANTERN_ROOT / "definition.json"

RUNTIME = (
    LANTERN_ROOT
    / "runtime"
    / "lantern_runtime.py"
)

TEST = (
    LANTERN_ROOT
    / "tests"
    / "test_lantern_runtime.py"
)

CONTRACTS = (
    ROOT
    / "hierarchies"
    / "identity"
    / "exiles"
    / "opus"
    / "prodigals"
    / "nocturne"
    / "contracts"
    / "lantern_contracts.py"
)

BACKUP_ROOT = (
    ROOT
    / "backups"
    / "identity-quality"
    / "lantern-runtime-attachment"
)


def timestamp() -> str:
    return dt.datetime.now(
        dt.timezone.utc
    ).strftime("%Y%m%dT%H%M%SZ")


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as handle:
        for chunk in iter(
            lambda: handle.read(1024 * 1024),
            b"",
        ):
            digest.update(chunk)

    return digest.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(
        path.read_text(encoding="utf-8")
    )

    if not isinstance(value, dict):
        raise ValueError(
            f"Expected JSON object: {path}"
        )

    return value


def write_json(
    path: Path,
    value: Any,
) -> None:
    path.write_text(
        json.dumps(
            value,
            ensure_ascii=False,
            indent=2,
            sort_keys=False,
        )
        + "\n",
        encoding="utf-8",
    )


def append_unique(
    collection: list[Any],
    candidate: Any,
) -> None:
    if candidate not in collection:
        collection.append(candidate)


def main() -> int:
    required = (
        DEFINITION,
        RUNTIME,
        TEST,
        CONTRACTS,
    )

    missing = [
        str(path)
        for path in required
        if not path.is_file()
    ]

    if missing:
        print(
            json.dumps(
                {
                    "passed": False,
                    "missing": missing,
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 2

    document = load_json(DEFINITION)

    backup = (
        BACKUP_ROOT
        / timestamp()
        / DEFINITION.relative_to(ROOT)
    )

    backup.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    shutil.copy2(
        DEFINITION,
        backup,
    )

    runtime = document.setdefault(
        "runtime",
        {},
    )

    runtime["implementation"] = "partial"
    runtime["deterministic"] = True
    runtime["side_effects"] = []

    entrypoints = runtime.setdefault(
        "entrypoints",
        [],
    )

    append_unique(
        entrypoints,
        RUNTIME.relative_to(ROOT).as_posix(),
    )

    commands = runtime.setdefault(
        "commands",
        [],
    )

    append_unique(
        commands,
        "bin/lanternctl",
    )

    runtime.setdefault(
        "hooks",
        [],
    )

    contracts = document.setdefault(
        "contracts",
        {},
    )

    for field in (
        "inputs",
        "outputs",
        "errors",
    ):
        contracts.setdefault(
            field,
            [],
        )

    for item in (
        {
            "name": "discovery_request",
            "schema": "lantern_contracts.DiscoveryRequest",
            "required": True,
        },
        {
            "name": "discovery_policy",
            "schema": "lantern_contracts.DiscoveryPolicy",
            "required": True,
        },
        {
            "name": "discovery_record",
            "schema": "lantern_contracts.DiscoveryRecord",
            "required": True,
        },
    ):
        append_unique(
            contracts["inputs"],
            item,
        )

    for item in (
        {
            "name": "normalized_location",
            "schema": "lantern_contracts.NormalizedLocation",
            "required": False,
        },
        {
            "name": "location_index",
            "schema": "lantern_contracts.LocationIndex",
            "required": True,
        },
        {
            "name": "lantern_result",
            "schema": "lantern_contracts.LanternResult",
            "required": True,
        },
    ):
        append_unique(
            contracts["outputs"],
            item,
        )

    append_unique(
        contracts["errors"],
        {
            "code": "lantern.runtime.failure",
            "condition": (
                "Supplied observations cannot be normalized "
                "or indexed under the declared policy."
            ),
            "recoverable": True,
        },
    )

    capabilities = document.setdefault(
        "capabilities",
        [],
    )

    for capability in (
        {
            "id": "quirk.nocturne.lantern.location_normalization",
            "description": (
                "Normalize explicitly supplied network-location "
                "observations without external access."
            ),
            "status": "active",
        },
        {
            "id": "quirk.nocturne.lantern.location_validation",
            "description": (
                "Validate onion-v3 hosts, ports, credentials, "
                "queries, fragments, and policy boundaries."
            ),
            "status": "active",
        },
        {
            "id": "quirk.nocturne.lantern.duplicate_detection",
            "description": (
                "Detect equivalent normalized observations while "
                "preserving every contributing source."
            ),
            "status": "active",
        },
        {
            "id": "quirk.nocturne.lantern.location_indexing",
            "description": (
                "Build deterministic provenance-preserving indexes "
                "from authorized supplied observations."
            ),
            "status": "active",
        },
        {
            "id": "quirk.nocturne.lantern.live_discovery",
            "description": (
                "Perform separately authorized live discovery through "
                "a future governed adapter."
            ),
            "status": "proposed",
        },
    ):
        append_unique(
            capabilities,
            capability,
        )

    dependencies = document.setdefault(
        "dependencies",
        {},
    )

    for field in (
        "required",
        "optional",
        "runtime",
        "external",
    ):
        dependencies.setdefault(
            field,
            [],
        )

    append_unique(
        dependencies["required"],
        {
            "id": "python.pydantic",
            "kind": "library",
            "required": True,
        },
    )

    append_unique(
        dependencies["runtime"],
        {
            "id": "nocturne.lantern.contracts",
            "kind": "contract_module",
            "required": True,
        },
    )

    append_unique(
        dependencies["optional"],
        {
            "id": "lantern.discovery_adapter",
            "kind": "aperture",
            "required": False,
        },
    )

    security = document.setdefault(
        "security",
        {},
    )

    security["boundary"] = (
        "Accept supplied observations only. Perform no crawling, "
        "probing, network access, filesystem writes, subprocess "
        "execution, provider access, or secret access."
    )
    security["permissions"] = []
    security["data_classification"] = "sensitive"
    security["network_policy"] = "offline_only"
    security["sandbox"] = True

    observability = document.setdefault(
        "observability",
        {},
    )

    observability["metrics"] = [
        "execution_count",
        "success_count",
        "failure_count",
        "duration_seconds",
        "input_count",
        "accepted_count",
        "rejected_count",
        "duplicate_count",
    ]

    observability["events"] = [
        "lantern.request.accepted",
        "lantern.location.normalized",
        "lantern.location.rejected",
        "lantern.duplicate.detected",
        "lantern.index.generated",
        "lantern.execution.failed",
    ]

    observability["health"] = [
        "definition_valid",
        "contracts_available",
        "runtime_importable",
        "tests_passing",
        "network_access_disabled",
    ]

    observability["audit"] = True

    validation = document.setdefault(
        "validation",
        {},
    )

    validation["unit_tests"] = [
        TEST.relative_to(ROOT).as_posix(),
    ]

    validation["integration_tests"] = []

    validation["property_tests"] = [
        "equal_requests_produce_equal_indexes",
        "canonical_serialization_is_stable",
        "duplicate_count_is_deterministic",
    ]

    validation["security_tests"] = [
        "network_access_cannot_be_enabled",
        "embedded_credentials_are_rejected",
        "non_onion_location_is_rejected",
    ]

    validation["acceptance"] = [
        "Runtime performs no external network access.",
        "Equal observations and policies produce equal index digests.",
        "Accepted and rejected locations preserve source provenance.",
        "Duplicate aggregation never discards contributing sources.",
        "Malformed or unauthorized locations are rejected.",
        "Live discovery remains unavailable until an authorized adapter exists.",
    ]

    apertures = document.setdefault(
        "apertures",
        [],
    )

    append_unique(
        apertures,
        {
            "id": "quirk.nocturne.lantern.discovery",
            "purpose": (
                "Admit compatible authorized discovery providers "
                "without replacing Lantern."
            ),
            "admission": (
                "Requires explicit authority, versioned contracts, "
                "security review, deterministic normalization, "
                "complete provenance, and passing tests."
            ),
        },
    )

    provenance = document.setdefault(
        "provenance",
        {},
    )

    provenance.setdefault(
        "created_from",
        [],
    )

    provenance.setdefault(
        "captured_by",
        "savant.identity-quality.lantern-runtime-attachment",
    )

    provenance.setdefault(
        "source_hashes",
        {},
    )

    for path in (
        RUNTIME,
        TEST,
        CONTRACTS,
    ):
        relative = path.relative_to(
            ROOT
        ).as_posix()

        append_unique(
            provenance["created_from"],
            relative,
        )

        provenance["source_hashes"][
            relative
        ] = sha256_path(path)

    write_json(
        DEFINITION,
        document,
    )

    print(
        json.dumps(
            {
                "passed": True,
                "definition": str(DEFINITION),
                "definition_sha256": sha256_path(
                    DEFINITION
                ),
                "backup": str(backup),
                "runtime": str(RUNTIME),
                "test": str(TEST),
                "contracts": str(CONTRACTS),
            },
            indent=2,
            sort_keys=True,
        )
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
