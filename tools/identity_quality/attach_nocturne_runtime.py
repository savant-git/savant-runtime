#!/usr/bin/env python3
from __future__ import annotations

import datetime as dt
import hashlib
import json
import shutil
from pathlib import Path
from typing import Any


ROOT = Path("/root/savant-runtime")

NOCTURNE_ROOT = (
    ROOT
    / "hierarchies"
    / "identity"
    / "exiles"
    / "opus"
    / "prodigals"
    / "nocturne"
)

DEFINITION = (
    NOCTURNE_ROOT
    / "definition.json"
)

RUNTIME = (
    NOCTURNE_ROOT
    / "runtime"
    / "nocturne_runtime.py"
)

TEST = (
    NOCTURNE_ROOT
    / "tests"
    / "test_nocturne_runtime.py"
)

CONTRACTS = (
    NOCTURNE_ROOT
    / "contracts"
    / "nocturne_fusion_contracts.py"
)

BACKUP_ROOT = (
    ROOT
    / "backups"
    / "identity-quality"
    / "nocturne-runtime-attachment"
)

QUIRK_IDS = (
    "quirk.nocturne.veil",
    "quirk.nocturne.lantern",
    "quirk.nocturne.scribe",
    "quirk.nocturne.echo",
)


def timestamp() -> str:
    return dt.datetime.now(
        dt.timezone.utc
    ).strftime("%Y%m%dT%H%M%SZ")


def sha256_path(
    path: Path,
) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as handle:
        for chunk in iter(
            lambda: handle.read(
                1024 * 1024
            ),
            b"",
        ):
            digest.update(chunk)

    return digest.hexdigest()


def load_json(
    path: Path,
) -> dict[str, Any]:
    value = json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )

    if not isinstance(
        value,
        dict,
    ):
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


def ensure_list(
    value: Any,
) -> list[Any]:
    if isinstance(
        value,
        list,
    ):
        return value

    return []


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
                    "operation": (
                        "attach_nocturne_runtime"
                    ),
                    "passed": False,
                    "missing": missing,
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 2

    document = load_json(
        DEFINITION
    )

    backup = (
        BACKUP_ROOT
        / timestamp()
        / DEFINITION.relative_to(
            ROOT
        )
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
        RUNTIME.relative_to(
            ROOT
        ).as_posix(),
    )

    commands = runtime.setdefault(
        "commands",
        [],
    )

    append_unique(
        commands,
        "bin/nocturnectl",
    )

    hooks = runtime.setdefault(
        "hooks",
        [],
    )

    for hook in (
        "admission",
        "authority_resolution",
        "policy_resolution",
        "quirk_selection",
        "dependency_resolution",
        "execution_planning",
        "quirk_execution",
        "result_normalization",
        "cross_quirk_correlation",
        "validation",
        "provenance_propagation",
        "output_projection",
        "attestation",
    ):
        append_unique(
            hooks,
            hook,
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
            "name": "nocturne_request",
            "schema": (
                "nocturne_fusion_contracts."
                "NocturneRequest"
            ),
            "required": True,
        },
        {
            "name": "fusion_policy",
            "schema": (
                "nocturne_fusion_contracts."
                "FusionPolicy"
            ),
            "required": True,
        },
    ):
        append_unique(
            contracts["inputs"],
            item,
        )

    for item in (
        {
            "name": "stage_result",
            "schema": (
                "nocturne_fusion_contracts."
                "StageResult"
            ),
            "required": False,
        },
        {
            "name": "nocturne_result",
            "schema": (
                "nocturne_fusion_contracts."
                "NocturneResult"
            ),
            "required": True,
        },
    ):
        append_unique(
            contracts["outputs"],
            item,
        )

    for item in (
        {
            "code": "nocturne.input.missing",
            "condition": (
                "A required enabled quirk has no "
                "request payload."
            ),
            "recoverable": True,
        },
        {
            "code": "nocturne.stage.failure",
            "condition": (
                "A quirk request, import, validation, "
                "or execution stage fails."
            ),
            "recoverable": True,
        },
        {
            "code": "nocturne.stage.halted",
            "condition": (
                "Composition halts under fail-closed "
                "policy before a later stage executes."
            ),
            "recoverable": True,
        },
    ):
        append_unique(
            contracts["errors"],
            item,
        )

    composition = document.setdefault(
        "composition",
        {},
    )

    children = composition.setdefault(
        "children",
        [],
    )

    for quirk_id in QUIRK_IDS:
        append_unique(
            children,
            quirk_id,
        )

    composition.setdefault(
        "shared_children",
        [],
    )

    composition[
        "composition_policy"
    ] = (
        "Select and execute enabled quirks through "
        "versioned contracts; preserve each quirk's "
        "authority, lineage, provenance, failures, "
        "and independent runtime identity."
    )

    composition[
        "execution_order"
    ] = [
        "veil",
        "lantern",
        "scribe",
        "echo",
    ]

    composition[
        "fusion_stages"
    ] = [
        "admission",
        "authority_resolution",
        "policy_resolution",
        "quirk_selection",
        "dependency_resolution",
        "execution_planning",
        "quirk_execution",
        "result_normalization",
        "cross_quirk_correlation",
        "validation",
        "provenance_propagation",
        "output_projection",
        "attestation",
    ]

    capabilities = document.setdefault(
        "capabilities",
        [],
    )

    for capability in (
        {
            "id": (
                "prodigal.nocturne."
                "contract_governed_composition"
            ),
            "description": (
                "Compose enabled quirks through "
                "validated versioned contracts."
            ),
            "status": "active",
        },
        {
            "id": (
                "prodigal.nocturne."
                "partial_result_preservation"
            ),
            "description": (
                "Preserve attributable partial results "
                "when policy permits incomplete execution."
            ),
            "status": "active",
        },
        {
            "id": (
                "prodigal.nocturne."
                "failure_isolation"
            ),
            "description": (
                "Isolate quirk failures without silently "
                "substituting unavailable behavior."
            ),
            "status": "active",
        },
        {
            "id": (
                "prodigal.nocturne."
                "provenance_propagation"
            ),
            "description": (
                "Propagate source and transformation "
                "provenance through every composition stage."
            ),
            "status": "active",
        },
        {
            "id": (
                "prodigal.nocturne."
                "deterministic_projection"
            ),
            "description": (
                "Exclude volatile telemetry from "
                "authoritative composition digests."
            ),
            "status": "active",
        },
        {
            "id": (
                "prodigal.nocturne."
                "opus_attachment"
            ),
            "description": (
                "Attach Nocturne to Opus through a "
                "separately governed reversible adapter."
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
            "id": (
                "nocturne.fusion.contracts"
            ),
            "kind": "contract_module",
            "required": True,
        },
    )

    for quirk_id in QUIRK_IDS:
        append_unique(
            dependencies["runtime"],
            {
                "id": quirk_id,
                "kind": "quirk_runtime",
                "required": False,
            },
        )

    append_unique(
        dependencies["optional"],
        {
            "id": (
                "opus.nocturne.adapter"
            ),
            "kind": "aperture",
            "required": False,
        },
    )

    relationships = ensure_list(
        document.get(
            "relationships"
        )
    )

    document[
        "relationships"
    ] = relationships

    for quirk_id in QUIRK_IDS:
        append_unique(
            relationships,
            {
                "type": "composes",
                "target": quirk_id,
                "direction": "outbound",
            },
        )

    append_unique(
        relationships,
        {
            "type": "attaches_to",
            "target": "exile.opus",
            "direction": "outbound",
        },
    )

    security = document.setdefault(
        "security",
        {},
    )

    security["boundary"] = (
        "Nocturne may invoke only explicitly enabled "
        "local quirk runtimes. It inherits no network, "
        "filesystem-write, subprocess, provider, secret, "
        "or orchestration authority from Opus."
    )

    security["permissions"] = [
        "import_declared_local_quirk_runtime",
        "validate_declared_quirk_contract",
        "execute_declared_local_quirk_runtime",
        "project_declared_stage_result",
    ]

    security[
        "data_classification"
    ] = "sensitive"

    security[
        "network_policy"
    ] = "deny_by_default"

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
        "enabled_count",
        "completed_count",
        "failed_count",
        "skipped_count",
        "partial",
    ]

    observability["events"] = [
        "nocturne.request.accepted",
        "nocturne.policy.resolved",
        "nocturne.stage.started",
        "nocturne.stage.completed",
        "nocturne.stage.failed",
        "nocturne.stage.skipped",
        "nocturne.composition.completed",
        "nocturne.composition.failed",
    ]

    observability["health"] = [
        "definition_valid",
        "contracts_available",
        "runtime_importable",
        "quirk_runtimes_discoverable",
        "tests_passing",
        "composition_deterministic",
        "authority_boundaries_preserved",
    ]

    observability["audit"] = True

    validation = document.setdefault(
        "validation",
        {},
    )

    validation["unit_tests"] = [
        TEST.relative_to(
            ROOT
        ).as_posix(),
    ]

    validation[
        "integration_tests"
    ] = [
        (
            "hierarchies/identity/exiles/opus/"
            "prodigals/nocturne/quirks/veil/"
            "tests/test_veil_runtime.py"
        ),
        (
            "hierarchies/identity/exiles/opus/"
            "prodigals/nocturne/quirks/lantern/"
            "tests/test_lantern_runtime.py"
        ),
        (
            "hierarchies/identity/exiles/opus/"
            "prodigals/nocturne/quirks/scribe/"
            "tests/test_scribe_runtime.py"
        ),
        (
            "hierarchies/identity/exiles/opus/"
            "prodigals/nocturne/quirks/echo/"
            "tests/test_echo_runtime.py"
        ),
    ]

    validation[
        "property_tests"
    ] = [
        (
            "equal_requests_produce_equal_"
            "composition_digests"
        ),
        (
            "canonical_serialization_is_stable"
        ),
        (
            "stage_results_preserve_provenance"
        ),
        (
            "required_quirks_must_be_enabled"
        ),
    ]

    validation[
        "security_tests"
    ] = [
        (
            "missing_required_payload_fails_closed"
        ),
        (
            "missing_optional_payload_is_skipped"
        ),
        (
            "nocturne_inherits_no_opus_"
            "orchestration_authority"
        ),
    ]

    validation["acceptance"] = [
        (
            "Every quirk remains independently executable."
        ),
        (
            "Nocturne invokes quirks only through "
            "declared contracts."
        ),
        (
            "Equal requests, policies, versions, and "
            "inputs produce equal composition digests."
        ),
        (
            "Volatile telemetry never alters "
            "authoritative composition identity."
        ),
        (
            "Partial results preserve exact stage "
            "status, failure, lineage, and provenance."
        ),
        (
            "Unavailable behavior is never silently "
            "substituted or fabricated."
        ),
        (
            "Nocturne does not acquire Opus API "
            "orchestration authority."
        ),
    ]

    apertures = document.setdefault(
        "apertures",
        [],
    )

    for aperture in (
        {
            "id": (
                "prodigal.nocturne.quirk"
            ),
            "purpose": (
                "Admit compatible future quirks."
            ),
            "admission": (
                "Requires an independent bounded runtime, "
                "versioned contracts, authority, lineage, "
                "provenance, security review, tests, and "
                "deterministic composition behavior."
            ),
        },
        {
            "id": (
                "prodigal.nocturne.opus"
            ),
            "purpose": (
                "Attach Nocturne to Opus without "
                "transferring orchestration authority."
            ),
            "admission": (
                "Requires a reversible adapter, explicit "
                "request and result contracts, authority "
                "isolation, auditability, and passing "
                "integration tests."
            ),
        },
        {
            "id": (
                "prodigal.nocturne.observatory"
            ),
            "purpose": (
                "Admit read-only projections of runtime "
                "state, lineage, provenance, failures, "
                "metrics, and composition graphs."
            ),
            "admission": (
                "Projection must remain deterministic, "
                "disposable, and non-authoritative."
            ),
        },
    ):
        append_unique(
            apertures,
            aperture,
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
        (
            "savant.identity-quality."
            "nocturne-runtime-attachment"
        ),
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
            provenance[
                "created_from"
            ],
            relative,
        )

        provenance[
            "source_hashes"
        ][relative] = sha256_path(
            path
        )

    write_json(
        DEFINITION,
        document,
    )

    print(
        json.dumps(
            {
                "operation": (
                    "attach_nocturne_runtime"
                ),
                "passed": True,
                "definition": str(
                    DEFINITION
                ),
                "definition_sha256": (
                    sha256_path(
                        DEFINITION
                    )
                ),
                "backup": str(
                    backup
                ),
                "runtime": str(
                    RUNTIME
                ),
                "test": str(
                    TEST
                ),
                "contracts": str(
                    CONTRACTS
                ),
                "quirks": list(
                    QUIRK_IDS
                ),
            },
            indent=2,
            sort_keys=True,
        )
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
