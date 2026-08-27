#!/usr/bin/env python3
from __future__ import annotations

import datetime as dt
import hashlib
import json
import shutil
from pathlib import Path
from typing import Any


ROOT = Path("/root/savant-runtime")

SCRIBE_ROOT = (
    ROOT
    / "hierarchies"
    / "identity"
    / "exiles"
    / "opus"
    / "prodigals"
    / "nocturne"
    / "quirks"
    / "scribe"
)

DEFINITION = SCRIBE_ROOT / "definition.json"

RUNTIME = (
    SCRIBE_ROOT
    / "runtime"
    / "scribe_runtime.py"
)

TEST = (
    SCRIBE_ROOT
    / "tests"
    / "test_scribe_runtime.py"
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
    / "scribe_contracts.py"
)

BACKUP_ROOT = (
    ROOT
    / "backups"
    / "identity-quality"
    / "scribe-runtime-attachment"
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
        "bin/scribectl",
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
            "name": "extraction_request",
            "schema": "scribe_contracts.ExtractionRequest",
            "required": True,
        },
        {
            "name": "extraction_policy",
            "schema": "scribe_contracts.ExtractionPolicy",
            "required": True,
        },
        {
            "name": "source_document",
            "schema": "scribe_contracts.SourceDocument",
            "required": True,
        },
    ):
        append_unique(
            contracts["inputs"],
            item,
        )

    for item in (
        {
            "name": "extracted_observation",
            "schema": "scribe_contracts.ExtractedObservation",
            "required": False,
        },
        {
            "name": "extraction_index",
            "schema": "scribe_contracts.ExtractionIndex",
            "required": True,
        },
        {
            "name": "scribe_result",
            "schema": "scribe_contracts.ScribeResult",
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
            "code": "scribe.runtime.failure",
            "condition": (
                "Source parsing or extraction cannot "
                "complete under the declared policy."
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
            "id": "quirk.nocturne.scribe.format_detection",
            "description": (
                "Detect text, Markdown, JSON, and HTML "
                "source formats without external access."
            ),
            "status": "active",
        },
        {
            "id": "quirk.nocturne.scribe.structured_extraction",
            "description": (
                "Extract headings, paragraphs, links, text, "
                "and JSON scalar observations."
            ),
            "status": "active",
        },
        {
            "id": "quirk.nocturne.scribe.source_span_preservation",
            "description": (
                "Preserve character and line spans for every "
                "extracted observation."
            ),
            "status": "active",
        },
        {
            "id": "quirk.nocturne.scribe.provenance_preservation",
            "description": (
                "Preserve source references and transformation "
                "lineage through deterministic extraction."
            ),
            "status": "active",
        },
        {
            "id": "quirk.nocturne.scribe.extractor_adapter",
            "description": (
                "Attach optional specialized parsers through "
                "explicit contracts and apertures."
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
            "id": "nocturne.scribe.contracts",
            "kind": "contract_module",
            "required": True,
        },
    )

    append_unique(
        dependencies["optional"],
        {
            "id": "scribe.extractor_adapter",
            "kind": "aperture",
            "required": False,
        },
    )

    security = document.setdefault(
        "security",
        {},
    )

    security["boundary"] = (
        "Read supplied content only. Perform no network, "
        "filesystem-write, subprocess, secret, or provider access."
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
        "input_bytes",
        "observation_count",
        "source_format",
    ]

    observability["events"] = [
        "scribe.request.accepted",
        "scribe.format.detected",
        "scribe.observation.extracted",
        "scribe.index.generated",
        "scribe.execution.failed",
    ]

    observability["health"] = [
        "definition_valid",
        "contracts_available",
        "runtime_importable",
        "tests_passing",
        "source_spans_bounded",
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
        "source_spans_are_bounded",
        "heading_extraction_preserves_value",
    ]

    validation["security_tests"] = [
        "disallowed_format_fails_closed",
        "runtime_performs_no_external_access",
    ]

    validation["acceptance"] = [
        "Equal source material and policies produce equal extraction digests.",
        "Every observation preserves exact bounded source spans.",
        "Every observation preserves source provenance.",
        "Unsupported formats fail closed.",
        "Runtime performs no external access.",
        "Specialized parsers remain optional attachments.",
    ]

    apertures = document.setdefault(
        "apertures",
        [],
    )

    append_unique(
        apertures,
        {
            "id": "quirk.nocturne.scribe.extractor",
            "purpose": (
                "Admit compatible specialized extractors "
                "without replacing Scribe."
            ),
            "admission": (
                "Requires deterministic behavior, versioned "
                "contracts, exact source-span provenance, "
                "security review, and complete tests."
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
        "savant.identity-quality.scribe-runtime-attachment",
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
