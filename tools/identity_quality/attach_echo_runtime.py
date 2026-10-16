#!/usr/bin/env python3
from __future__ import annotations

import datetime as dt
import hashlib
import json
import shutil
from pathlib import Path
from typing import Any


ROOT = Path("/root/savant-runtime")

ECHO_ROOT = (
    ROOT
    / "edifices"
    / "identity"
    / "exiles"
    / "opus"
    / "prodigals"
    / "nocturne"
    / "quirks"
    / "echo"
)

DEFINITION = ECHO_ROOT / "definition.json"

RUNTIME = (
    ECHO_ROOT
    / "runtime"
    / "echo_runtime.py"
)

TEST = (
    ECHO_ROOT
    / "tests"
    / "test_echo_runtime.py"
)

CONTRACTS = (
    ROOT
    / "edifices"
    / "identity"
    / "exiles"
    / "opus"
    / "prodigals"
    / "nocturne"
    / "contracts"
    / "echo_contracts.py"
)

BACKUP_ROOT = (
    ROOT
    / "backups"
    / "identity-quality"
    / "echo-runtime-attachment"
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

    document = load_json(
        DEFINITION
    )

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
        "bin/echoctl",
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
            "name": "correlation_request",
            "schema": "echo_contracts.CorrelationRequest",
            "required": True,
        },
        {
            "name": "correlation_policy",
            "schema": "echo_contracts.CorrelationPolicy",
            "required": True,
        },
    ):
        append_unique(
            contracts["inputs"],
            item,
        )

    for item in (
        {
            "name": "correlation_pair",
            "schema": "echo_contracts.CorrelationPair",
            "required": False,
        },
        {
            "name": "correlation_cluster",
            "schema": "echo_contracts.CorrelationCluster",
            "required": False,
        },
        {
            "name": "threat_hypothesis",
            "schema": "echo_contracts.ThreatHypothesis",
            "required": False,
        },
        {
            "name": "correlation_index",
            "schema": "echo_contracts.CorrelationIndex",
            "required": True,
        },
        {
            "name": "echo_result",
            "schema": "echo_contracts.EchoResult",
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
            "code": "echo.runtime.failure",
            "condition": (
                "Correlation input, policy, or runtime "
                "execution cannot be completed."
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
            "id": "quirk.nocturne.echo.cross_source_correlation",
            "description": (
                "Correlate supplied observations across "
                "distinct sources using bounded declared evidence."
            ),
            "status": "active",
        },
        {
            "id": "quirk.nocturne.echo.pattern_detection",
            "description": (
                "Detect exact, token, label, source, and "
                "temporal relationships under explicit policy."
            ),
            "status": "active",
        },
        {
            "id": "quirk.nocturne.echo.cluster_projection",
            "description": (
                "Project deterministic connected correlation "
                "clusters without duplicating observation authority."
            ),
            "status": "active",
        },
        {
            "id": "quirk.nocturne.echo.hypothesis_generation",
            "description": (
                "Emit bounded proposed hypotheses that preserve "
                "limitations and never claim causation."
            ),
            "status": "active",
        },
        {
            "id": "quirk.nocturne.echo.external_analysis_adapter",
            "description": (
                "Attach optional separately governed analytical "
                "providers through explicit contracts."
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
            "id": "nocturne.echo.contracts",
            "kind": "contract_module",
            "required": True,
        },
    )

    append_unique(
        dependencies["optional"],
        {
            "id": "echo.analysis_adapter",
            "kind": "aperture",
            "required": False,
        },
    )

    security = document.setdefault(
        "security",
        {},
    )

    security["boundary"] = (
        "Analyze supplied observations only. Perform no "
        "network, filesystem-write, subprocess, secret, "
        "or external-provider access."
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
        "observation_count",
        "pair_count",
        "cluster_count",
        "hypothesis_count",
        "unmatched_count",
    ]

    observability["events"] = [
        "echo.request.accepted",
        "echo.pair.proposed",
        "echo.cluster.generated",
        "echo.hypothesis.proposed",
        "echo.execution.failed",
    ]

    observability["health"] = [
        "definition_valid",
        "contracts_available",
        "runtime_importable",
        "tests_passing",
        "authority_isolation_preserved",
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
        "shared_tokens_produce_bounded_scores",
        "unmatched_observations_are_preserved",
    ]

    validation["security_tests"] = [
        "hypotheses_remain_proposed",
        "correlation_does_not_claim_causation",
        "runtime_performs_no_external_access",
    ]

    validation["acceptance"] = [
        "Equal observations and policies produce equal correlation digests.",
        "Every correlation remains supported by explicit evidence.",
        "No hypothesis is promoted beyond proposed authority.",
        "Correlation never claims causation.",
        "Unmatched observations remain visible and attributable.",
        "Every output preserves source provenance.",
    ]

    apertures = document.setdefault(
        "apertures",
        [],
    )

    append_unique(
        apertures,
        {
            "id": "quirk.nocturne.echo.analysis",
            "purpose": (
                "Admit compatible bounded analytical providers "
                "without replacing Echo."
            ),
            "admission": (
                "Requires explicit contracts, authority isolation, "
                "deterministic fallback, provenance, security review, "
                "and complete validation."
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
        "savant.identity-quality.echo-runtime-attachment",
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
    raise SystemExit(
        main()
    )
