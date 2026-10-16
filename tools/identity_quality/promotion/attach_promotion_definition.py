#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import shutil
import tempfile
from pathlib import Path
from typing import Any


ROOT = Path("/root/savant-runtime")

ADMISSION_ROOT = (
    ROOT
    / "reports"
    / "identity_quality"
    / "promotion"
    / "admissions"
)

ATTACHMENT_ROOT = (
    ROOT
    / "reports"
    / "identity_quality"
    / "promotion"
    / "definition-attachments"
)

TRANSACTION_ROOT = (
    ROOT
    / "runtime"
    / "identity-promotion"
    / "definition-attachments"
)

BACKUP_ROOT = (
    ROOT
    / "backups"
    / "identity-quality"
    / "promotion-definitions"
)

EXPECTED_ROLES = {
    "contracts",
    "runtime",
    "tests",
    "controller",
}

VOLATILE_FIELDS = {
    "generated_at",
    "started_at",
    "finished_at",
    "duration_seconds",
    "elapsed_seconds",
    "wall_clock_seconds",
    "timestamp",
}


def utc_now() -> str:
    return (
        dt.datetime.now(dt.timezone.utc)
        .replace(microsecond=0)
        .isoformat()
    )


def timestamp() -> str:
    return dt.datetime.now(
        dt.timezone.utc
    ).strftime("%Y%m%dT%H%M%SZ")


def canonical_bytes(
    value: Any,
) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def digest(
    value: Any,
) -> str:
    return hashlib.sha256(
        canonical_bytes(value)
    ).hexdigest()


def sha256_path(
    path: Path,
) -> str:
    hasher = hashlib.sha256()

    with path.open("rb") as handle:
        for chunk in iter(
            lambda: handle.read(
                1024 * 1024
            ),
            b"",
        ):
            hasher.update(chunk)

    return hasher.hexdigest()


def deterministic_projection(
    value: Any,
) -> Any:
    if isinstance(value, dict):
        return {
            key: deterministic_projection(child)
            for key, child in sorted(
                value.items(),
                key=lambda item: item[0],
            )
            if key not in VOLATILE_FIELDS
        }

    if isinstance(value, list):
        return [
            deterministic_projection(child)
            for child in value
        ]

    if isinstance(value, tuple):
        return tuple(
            deterministic_projection(child)
            for child in value
        )

    return value


def load_json(
    path: Path,
) -> dict[str, Any]:
    value = json.loads(
        path.read_text(
            encoding="utf-8",
        )
    )

    if not isinstance(value, dict):
        raise ValueError(
            f"Expected JSON object: {path}"
        )

    return value


def atomic_write_json(
    path: Path,
    value: Any,
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    rendered = (
        json.dumps(
            value,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )

    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=str(path.parent),
    )

    temporary_path = Path(
        temporary_name
    )

    try:
        with os.fdopen(
            descriptor,
            "w",
            encoding="utf-8",
        ) as handle:
            handle.write(rendered)
            handle.flush()
            os.fsync(
                handle.fileno()
            )

        os.replace(
            temporary_path,
            path,
        )

    finally:
        if temporary_path.exists():
            temporary_path.unlink()


def write_text(
    path: Path,
    value: str,
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    path.write_text(
        value,
        encoding="utf-8",
    )


def relative_path(
    path: Path,
) -> str:
    try:
        return path.relative_to(
            ROOT
        ).as_posix()

    except ValueError:
        return str(path)


def safe_key(
    value: str,
) -> str:
    return "".join(
        character
        if (
            character.isalnum()
            or character in {
                ".",
                "_",
                "-",
            }
        )
        else "_"
        for character in value
    ).strip("_")


def latest_admission_paths() -> list[Path]:
    if not ADMISSION_ROOT.is_dir():
        return []

    return sorted(
        (
            path
            for path in ADMISSION_ROOT.glob(
                "*/latest.json"
            )
            if path.is_file()
        ),
        key=lambda path: (
            path.stat().st_mtime_ns,
            path.as_posix(),
        ),
        reverse=True,
    )


def latest_admission_path() -> Path:
    paths = latest_admission_paths()

    if not paths:
        raise FileNotFoundError(
            "No promotion admission exists."
        )

    return paths[0]


def resolve_admission_path(
    declared: Path | None,
) -> Path:
    if declared is None:
        return latest_admission_path()

    path = declared.expanduser()

    if not path.is_absolute():
        path = ROOT / path

    path = path.resolve()

    if not path.is_file():
        raise FileNotFoundError(path)

    return path


def append_unique(
    collection: list[Any],
    candidate: Any,
) -> None:
    if candidate not in collection:
        collection.append(candidate)


def ensure_mapping(
    document: dict[str, Any],
    field: str,
) -> dict[str, Any]:
    value = document.get(field)

    if isinstance(value, dict):
        return value

    value = {}
    document[field] = value

    return value


def ensure_list(
    document: dict[str, Any],
    field: str,
) -> list[Any]:
    value = document.get(field)

    if isinstance(value, list):
        return value

    value = []
    document[field] = value

    return value


def validate_admission(
    admission: dict[str, Any],
) -> None:
    if admission.get("mode") != "apply":
        raise ValueError(
            "Admission was not applied."
        )

    if admission.get("passed") is not True:
        raise ValueError(
            "Admission did not pass."
        )

    subject = admission.get("subject")

    if not isinstance(subject, dict):
        raise ValueError(
            "Admission has no subject."
        )

    definition = subject.get("definition")

    if (
        not isinstance(definition, str)
        or not definition.strip()
    ):
        raise ValueError(
            "Admission subject has no definition path."
        )

    files = admission.get("files")

    if (
        not isinstance(files, list)
        or not files
    ):
        raise ValueError(
            "Admission has no files."
        )

    roles = {
        record.get("role")
        for record in files
        if isinstance(record, dict)
    }

    missing = EXPECTED_ROLES - roles

    if missing:
        raise ValueError(
            "Admission is missing roles: "
            + ", ".join(sorted(missing))
        )

    for record in files:
        if not isinstance(record, dict):
            continue

        if record.get("role") not in EXPECTED_ROLES:
            continue

        if record.get("state") != "written":
            raise ValueError(
                f"Role was not written: {record.get('role')}"
            )

        if record.get("passed") is not True:
            raise ValueError(
                f"Role failed admission: {record.get('role')}"
            )


def admission_files(
    admission: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    records: dict[str, dict[str, Any]] = {}

    for record in admission["files"]:
        if not isinstance(record, dict):
            continue

        role = record.get("role")

        if role in EXPECTED_ROLES:
            records[role] = record

    return records


def admitted_path(
    record: dict[str, Any],
) -> Path:
    declared = record.get("path")

    if not isinstance(declared, str):
        raise ValueError(
            "Admitted file has no path."
        )

    path = (ROOT / declared).resolve()

    try:
        path.relative_to(ROOT)

    except ValueError as exc:
        raise ValueError(
            f"Admitted path escapes root: {path}"
        ) from exc

    if not path.is_file():
        raise FileNotFoundError(path)

    return path


def admitted_hash(
    record: dict[str, Any],
    path: Path,
) -> str:
    details = record.get("details")

    expected = None

    if isinstance(details, dict):
        expected = (
            details.get("expected_sha256")
            or details.get("after_sha256")
        )

    actual = sha256_path(path)

    if (
        isinstance(expected, str)
        and expected != actual
    ):
        raise ValueError(
            f"Admitted file hash changed: {path}"
        )

    return actual


def backup_definition(
    definition: Path,
    subject_id: str,
    run_id: str,
) -> Path:
    destination = (
        BACKUP_ROOT
        / safe_key(subject_id)
        / run_id
        / definition.relative_to(ROOT)
    )

    destination.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    shutil.copy2(
        definition,
        destination,
    )

    if sha256_path(definition) != sha256_path(destination):
        raise RuntimeError(
            "Definition backup hash mismatch."
        )

    return destination


def resolve_parent(
    document: dict[str, Any],
) -> str | None:
    lineage = document.get("lineage")

    if isinstance(lineage, dict):
        parents = lineage.get("parents")

        if (
            isinstance(parents, list)
            and parents
            and isinstance(parents[0], str)
        ):
            return parents[0]

    return None


def extend_definition(
    document: dict[str, Any],
    admission: dict[str, Any],
    records: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    subject = admission["subject"]
    subject_id = subject["id"]

    paths: dict[str, str] = {}
    hashes: dict[str, str] = {}

    for role, record in records.items():
        path = admitted_path(record)
        paths[role] = relative_path(path)
        hashes[role] = admitted_hash(
            record,
            path,
        )

    runtime = ensure_mapping(
        document,
        "runtime",
    )

    runtime["implementation"] = "complete"
    runtime["deterministic"] = True
    runtime.setdefault(
        "side_effects",
        [],
    )

    entrypoints = runtime.setdefault(
        "entrypoints",
        [],
    )

    if not isinstance(entrypoints, list):
        entrypoints = []
        runtime["entrypoints"] = entrypoints

    append_unique(
        entrypoints,
        paths["runtime"],
    )

    commands = runtime.setdefault(
        "commands",
        [],
    )

    if not isinstance(commands, list):
        commands = []
        runtime["commands"] = commands

    append_unique(
        commands,
        paths["controller"],
    )

    hooks = runtime.setdefault(
        "hooks",
        [],
    )

    if not isinstance(hooks, list):
        hooks = []
        runtime["hooks"] = hooks

    for hook in (
        "admission",
        "authority_resolution",
        "contract_validation",
        "execution",
        "projection",
        "provenance_propagation",
        "attestation",
    ):
        append_unique(
            hooks,
            hook,
        )

    contracts = ensure_mapping(
        document,
        "contracts",
    )

    modules = contracts.setdefault(
        "modules",
        [],
    )

    if not isinstance(modules, list):
        modules = []
        contracts["modules"] = modules

    append_unique(
        modules,
        {
            "path": paths["contracts"],
            "version": "1.0.0",
            "sha256": hashes["contracts"],
        },
    )

    dependencies = ensure_mapping(
        document,
        "dependencies",
    )

    for field in (
        "required",
        "optional",
        "runtime",
        "external",
    ):
        value = dependencies.setdefault(
            field,
            [],
        )

        if not isinstance(value, list):
            dependencies[field] = []

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
            "id": f"{subject_id}.contracts",
            "kind": "contract_module",
            "path": paths["contracts"],
            "sha256": hashes["contracts"],
            "required": True,
        },
    )

    validation = ensure_mapping(
        document,
        "validation",
    )

    unit_tests = validation.setdefault(
        "unit_tests",
        [],
    )

    if not isinstance(unit_tests, list):
        unit_tests = []
        validation["unit_tests"] = unit_tests

    append_unique(
        unit_tests,
        paths["tests"],
    )

    property_tests = validation.setdefault(
        "property_tests",
        [],
    )

    if not isinstance(property_tests, list):
        property_tests = []
        validation["property_tests"] = property_tests

    for test_name in (
        "equal_requests_produce_equal_result_digests",
        "canonical_serialization_is_stable",
        "volatile_telemetry_does_not_change_identity",
    ):
        append_unique(
            property_tests,
            test_name,
        )

    security_tests = validation.setdefault(
        "security_tests",
        [],
    )

    if not isinstance(security_tests, list):
        security_tests = []
        validation["security_tests"] = security_tests

    for test_name in (
        "runtime_rejects_undeclared_capability",
        "runtime_rejects_external_authority",
        "projection_remains_proposed",
    ):
        append_unique(
            security_tests,
            test_name,
        )

    acceptance = validation.setdefault(
        "acceptance",
        [],
    )

    if not isinstance(acceptance, list):
        acceptance = []
        validation["acceptance"] = acceptance

    for criterion in (
        "Runtime remains independently executable.",
        "Equal requests produce equal authoritative result digests.",
        "Volatile telemetry does not alter deterministic identity.",
        "No undeclared external authority is admitted.",
        "All results preserve provenance.",
        "Existing authoritative primitives remain preserved.",
    ):
        append_unique(
            acceptance,
            criterion,
        )

    provenance = ensure_mapping(
        document,
        "provenance",
    )

    created_from = provenance.setdefault(
        "created_from",
        [],
    )

    if not isinstance(created_from, list):
        created_from = []
        provenance["created_from"] = created_from

    source_hashes = provenance.setdefault(
        "source_hashes",
        {},
    )

    if not isinstance(source_hashes, dict):
        source_hashes = {}
        provenance["source_hashes"] = source_hashes

    for role in sorted(paths):
        append_unique(
            created_from,
            paths[role],
        )

        source_hashes[
            paths[role]
        ] = hashes[role]

    provenance[
        "captured_by"
    ] = (
        "savant.identity-quality."
        "promotion-definition-attachment"
    )

    relationships = ensure_list(
        document,
        "relationships",
    )

    parent = resolve_parent(document)

    if parent:
        append_unique(
            relationships,
            {
                "type": "attaches_to",
                "target": parent,
                "direction": "outbound",
                "authority_transfer": False,
                "reversible": True,
            },
        )

    append_unique(
        relationships,
        {
            "type": "implemented_by",
            "target": paths["runtime"],
            "direction": "outbound",
            "sha256": hashes["runtime"],
        },
    )

    append_unique(
        relationships,
        {
            "type": "validated_by",
            "target": paths["tests"],
            "direction": "outbound",
            "sha256": hashes["tests"],
        },
    )

    apertures = ensure_list(
        document,
        "apertures",
    )

    append_unique(
        apertures,
        {
            "id": f"{subject_id}.attachment",
            "purpose": (
                "Admit compatible future attachments "
                "without replacing the identity."
            ),
            "admission": (
                "Requires explicit authority, versioned "
                "contracts, provenance, deterministic behavior, "
                "security review, and passing tests."
            ),
        },
    )

    observability = ensure_mapping(
        document,
        "observability",
    )

    observability["audit"] = True

    metrics = observability.setdefault(
        "metrics",
        [],
    )

    if not isinstance(metrics, list):
        metrics = []
        observability["metrics"] = metrics

    for metric in (
        "execution_count",
        "success_count",
        "failure_count",
        "duration_seconds",
        "admitted_capability_count",
    ):
        append_unique(
            metrics,
            metric,
        )

    events = observability.setdefault(
        "events",
        [],
    )

    if not isinstance(events, list):
        events = []
        observability["events"] = events

    for event in (
        f"{subject_id}.request.accepted",
        f"{subject_id}.request.rejected",
        f"{subject_id}.execution.completed",
        f"{subject_id}.execution.failed",
    ):
        append_unique(
            events,
            event,
        )

    security = ensure_mapping(
        document,
        "security",
    )

    security.setdefault(
        "boundary",
        (
            "No undeclared network, filesystem, subprocess, "
            "provider, registry, policy, or secret authority."
        ),
    )

    security.setdefault(
        "permissions",
        [],
    )

    security.setdefault(
        "data_classification",
        "sensitive",
    )

    security.setdefault(
        "network_policy",
        "deny_by_default",
    )

    security.setdefault(
        "sandbox",
        True,
    )

    lifecycle = ensure_mapping(
        document,
        "lifecycle",
    )

    lifecycle["implementation_state"] = "complete"
    lifecycle["verification_required"] = True
    lifecycle["attestation_required"] = True

    document[
        "implementation_evidence"
    ] = {
        role: {
            "path": paths[role],
            "sha256": hashes[role],
        }
        for role in sorted(paths)
    }

    return document


def restore_definition(
    backup: Path,
    definition: Path,
) -> dict[str, Any]:
    if not backup.is_file():
        return {
            "passed": False,
            "code": "rollback.backup_missing",
        }

    definition.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    shutil.copy2(
        backup,
        definition,
    )

    backup_hash = sha256_path(backup)
    restored_hash = sha256_path(definition)

    return {
        "passed": (
            backup_hash == restored_hash
        ),
        "backup": relative_path(backup),
        "definition": relative_path(definition),
        "backup_sha256": backup_hash,
        "restored_sha256": restored_hash,
    }


def attach_definition(
    admission_path: Path,
    *,
    apply: bool,
    rollback_on_failure: bool,
) -> dict[str, Any]:
    admission = load_json(
        admission_path
    )

    validate_admission(admission)

    subject = admission["subject"]
    subject_id = subject["id"]

    definition = (
        ROOT
        / subject["definition"]
    ).resolve()

    try:
        definition.relative_to(ROOT)

    except ValueError as exc:
        raise ValueError(
            "Definition path escapes runtime root."
        ) from exc

    if not definition.is_file():
        raise FileNotFoundError(definition)

    records = admission_files(
        admission
    )

    before_document = load_json(
        definition
    )

    before_hash = sha256_path(
        definition
    )

    proposed_document = extend_definition(
        json.loads(
            json.dumps(before_document)
        ),
        admission,
        records,
    )

    proposed_hash = digest(
        deterministic_projection(
            proposed_document
        )
    )

    run_id = (
        f"definition-{timestamp()}-"
        f"{proposed_hash[:16]}"
    )

    transaction_root = (
        TRANSACTION_ROOT
        / safe_key(subject_id)
        / run_id
    )

    transaction_root.mkdir(
        parents=True,
        exist_ok=False,
    )

    admission_snapshot = (
        transaction_root
        / "admission.json"
    )

    proposed_snapshot = (
        transaction_root
        / "proposed_definition.json"
    )

    atomic_write_json(
        admission_snapshot,
        admission,
    )

    atomic_write_json(
        proposed_snapshot,
        proposed_document,
    )

    backup: Path | None = None
    rollback: dict[str, Any] | None = None

    passed = True
    applied = False
    after_hash: str | None = None

    if apply:
        backup = backup_definition(
            definition,
            subject_id,
            run_id,
        )

        try:
            atomic_write_json(
                definition,
                proposed_document,
            )

            after_hash = sha256_path(
                definition
            )

            written_document = load_json(
                definition
            )

            written_digest = digest(
                deterministic_projection(
                    written_document
                )
            )

            passed = (
                written_digest
                == proposed_hash
            )

            applied = passed

            if not passed:
                raise RuntimeError(
                    "Written definition digest mismatch."
                )

        except Exception:
            passed = False

            if (
                rollback_on_failure
                and backup is not None
            ):
                rollback = restore_definition(
                    backup,
                    definition,
                )

    result: dict[str, Any] = {
        "schema": (
            "savant://identity-quality/"
            "promotion-definition-attachment/1.0.0"
        ),
        "operation": (
            "attach_promotion_definition"
        ),
        "generated_at": utc_now(),
        "mode": (
            "apply"
            if apply
            else "plan"
        ),
        "admission": {
            "path": relative_path(
                admission_path
            ),
            "sha256": sha256_path(
                admission_path
            ),
            "digest": admission.get(
                "digest"
            ),
        },
        "subject": subject,
        "definition": {
            "path": relative_path(
                definition
            ),
            "before_sha256": before_hash,
            "proposed_digest": proposed_hash,
            "after_sha256": after_hash,
            "backup": (
                relative_path(backup)
                if backup
                else None
            ),
            "applied": applied,
        },
        "transaction": {
            "id": run_id,
            "root": relative_path(
                transaction_root
            ),
            "admission_snapshot": relative_path(
                admission_snapshot
            ),
            "proposed_definition": relative_path(
                proposed_snapshot
            ),
        },
        "rollback": rollback,
        "passed": passed,
    }

    result["digest"] = digest(
        deterministic_projection(
            result
        )
    )

    atomic_write_json(
        transaction_root
        / "result.json",
        result,
    )

    return result


def markdown(
    result: dict[str, Any],
) -> str:
    return "\n".join(
        [
            "# Promotion Definition Attachment",
            "",
            (
                f"- Generated: "
                f"`{result['generated_at']}`"
            ),
            (
                f"- Subject: "
                f"`{result['subject']['id']}`"
            ),
            (
                f"- Mode: "
                f"`{result['mode']}`"
            ),
            (
                f"- Applied: "
                f"**{result['definition']['applied']}**"
            ),
            (
                f"- Passed: "
                f"**{result['passed']}**"
            ),
            (
                f"- Definition: "
                f"`{result['definition']['path']}`"
            ),
            (
                f"- Digest: "
                f"`{result['digest']}`"
            ),
            "",
        ]
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Attach admitted promotion runtime evidence "
            "to the authoritative identity definition."
        )
    )

    parser.add_argument(
        "--admission",
        type=Path,
    )

    parser.add_argument(
        "--apply",
        action="store_true",
    )

    parser.add_argument(
        "--no-rollback",
        action="store_true",
    )

    parser.add_argument(
        "--strict",
        action="store_true",
    )

    parser.add_argument(
        "--output-root",
        type=Path,
        default=ATTACHMENT_ROOT,
    )

    arguments = parser.parse_args()

    try:
        admission_path = resolve_admission_path(
            arguments.admission
        )

        result = attach_definition(
            admission_path,
            apply=arguments.apply,
            rollback_on_failure=(
                not arguments.no_rollback
            ),
        )

    except Exception as exc:
        print(
            json.dumps(
                {
                    "operation": (
                        "attach_promotion_definition"
                    ),
                    "passed": False,
                    "error": {
                        "type": type(exc).__name__,
                        "message": str(exc),
                    },
                },
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
        )

        return 1

    subject_key = safe_key(
        result["subject"]["id"]
    )

    output_root = (
        arguments.output_root
        .expanduser()
        .resolve()
        / subject_key
    )

    output_root.mkdir(
        parents=True,
        exist_ok=True,
    )

    run_id = timestamp()

    json_path = (
        output_root
        / f"{run_id}__definition-attachment.json"
    )

    markdown_path = (
        output_root
        / f"{run_id}__definition-attachment.md"
    )

    latest_json = (
        output_root
        / "latest.json"
    )

    latest_markdown = (
        output_root
        / "latest.md"
    )

    atomic_write_json(
        json_path,
        result,
    )

    atomic_write_json(
        latest_json,
        result,
    )

    rendered = markdown(result)

    write_text(
        markdown_path,
        rendered,
    )

    write_text(
        latest_markdown,
        rendered,
    )

    manifest = {
        "generated_at": result["generated_at"],
        "subject": result["subject"]["id"],
        "mode": result["mode"],
        "passed": result["passed"],
        "attachment_digest": result["digest"],
        "files": {
            json_path.name: sha256_path(
                json_path
            ),
            markdown_path.name: sha256_path(
                markdown_path
            ),
            latest_json.name: sha256_path(
                latest_json
            ),
            latest_markdown.name: sha256_path(
                latest_markdown
            ),
        },
    }

    manifest_path = (
        output_root
        / f"{run_id}__manifest.json"
    )

    atomic_write_json(
        manifest_path,
        manifest,
    )

    print(
        json.dumps(
            {
                "operation": (
                    "attach_promotion_definition"
                ),
                "passed": result["passed"],
                "mode": result["mode"],
                "subject": result["subject"],
                "definition": result["definition"],
                "digest": result["digest"],
                "transaction": result["transaction"],
                "rollback": result["rollback"],
                "reports": {
                    "json": str(json_path),
                    "markdown": str(markdown_path),
                    "latest_json": str(latest_json),
                    "latest_markdown": str(
                        latest_markdown
                    ),
                    "manifest": str(
                        manifest_path
                    ),
                },
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )

    if (
        arguments.strict
        and not result["passed"]
    ):
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
