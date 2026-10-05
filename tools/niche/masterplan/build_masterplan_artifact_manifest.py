#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import tempfile
from pathlib import Path
from typing import Any


ROOT = Path("/root/savant-runtime")

GRAPH_PATH = (
    ROOT
    / "authority"
    / "task-graph"
    / "masterplan.json"
)

MANIFEST_ROOT = (
    ROOT
    / "authority"
    / "task-graph"
    / "manifests"
)

REPORT_ROOT = (
    ROOT
    / "reports"
    / "niche"
    / "masterplan"
    / "manifests"
)

RUNTIME_ROOT = (
    ROOT
    / "runtime"
    / "masterplan"
    / "manifests"
)

VOLATILE_FIELDS = {
    "generated_at",
    "created_at",
    "captured_at",
    "accepted_at",
    "occurred_at",
    "issued_at",
    "expires_at",
    "timestamp",
    "started_at",
    "finished_at",
    "duration_seconds",
    "elapsed_seconds",
    "wall_clock_seconds",
}


class ManifestError(RuntimeError):
    pass


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


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def deterministic_projection(value: Any) -> Any:
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


def semantic_digest(value: Any) -> str:
    return hashlib.sha256(
        canonical_bytes(
            deterministic_projection(value)
        )
    ).hexdigest()


def sha256_path(path: Path) -> str:
    hasher = hashlib.sha256()

    with path.open("rb") as handle:
        for chunk in iter(
            lambda: handle.read(1024 * 1024),
            b"",
        ):
            hasher.update(chunk)

    return hasher.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )

    if not isinstance(value, dict):
        raise ManifestError(
            f"Expected JSON object: {path}"
        )

    return value


def atomic_write_text(
    path: Path,
    value: str,
    mode: int = 0o644,
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=str(path.parent),
    )

    temporary_path = Path(temporary_name)

    try:
        with os.fdopen(
            descriptor,
            "w",
            encoding="utf-8",
        ) as handle:
            handle.write(value)
            handle.flush()
            os.fsync(handle.fileno())

        os.chmod(
            temporary_path,
            mode,
        )

        os.replace(
            temporary_path,
            path,
        )

    finally:
        if temporary_path.exists():
            temporary_path.unlink()


def atomic_write_json(
    path: Path,
    value: Any,
) -> None:
    atomic_write_text(
        path,
        json.dumps(
            value,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n",
    )


def relative_path(path: Path) -> str:
    try:
        return path.relative_to(
            ROOT
        ).as_posix()

    except ValueError:
        return str(path)


def resolve_output_path(
    declared: str,
) -> Path:
    path = Path(declared).expanduser()

    if not path.is_absolute():
        path = ROOT / path

    path = path.resolve()

    try:
        path.relative_to(ROOT)

    except ValueError as exc:
        raise ManifestError(
            f"Output escapes Savant root: {path}"
        ) from exc

    return path


def task_map(
    graph: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    records = graph.get(
        "records"
    )

    if not isinstance(records, list):
        raise ManifestError(
            "Task graph records are invalid."
        )

    result: dict[str, dict[str, Any]] = {}

    for record in records:
        if not isinstance(record, dict):
            raise ManifestError(
                "Task graph contains an invalid task."
            )

        identifier = record.get(
            "id"
        )

        if not isinstance(identifier, str):
            raise ManifestError(
                "Task identifier is missing."
            )

        if identifier in result:
            raise ManifestError(
                f"Duplicate task identifier: {identifier}"
            )

        result[identifier] = record

    return result


def collection_for_task(
    graph: dict[str, Any],
    collection: str,
    task_id: str,
) -> list[dict[str, Any]]:
    values = graph.get(
        collection,
        [],
    )

    if not isinstance(values, list):
        raise ManifestError(
            f"Graph collection is invalid: {collection}"
        )

    return sorted(
        (
            value
            for value in values
            if (
                isinstance(value, dict)
                and value.get("task_id")
                == task_id
            )
        ),
        key=lambda value: str(
            value.get("id", "")
        ),
    )


def decisions_for_task(
    graph: dict[str, Any],
    task_id: str,
) -> list[dict[str, Any]]:
    values = graph.get(
        "decisions",
        [],
    )

    if not isinstance(values, list):
        raise ManifestError(
            "Task graph decisions are invalid."
        )

    return sorted(
        (
            value
            for value in values
            if (
                isinstance(value, dict)
                and value.get("subject")
                == task_id
            )
        ),
        key=lambda value: str(
            value.get("id", "")
        ),
    )


def segues_for_task(
    graph: dict[str, Any],
    task_id: str,
) -> list[dict[str, Any]]:
    values = graph.get(
        "segues",
        [],
    )

    if not isinstance(values, list):
        raise ManifestError(
            "Task graph segues are invalid."
        )

    return sorted(
        (
            value
            for value in values
            if (
                isinstance(value, dict)
                and (
                    value.get("source")
                    == task_id
                    or value.get("target")
                    == task_id
                )
            )
        ),
        key=lambda value: (
            str(value.get("type", "")),
            str(value.get("source", "")),
            str(value.get("target", "")),
            str(value.get("id", "")),
        ),
    )


def artifact_record(
    declared: str,
) -> dict[str, Any]:
    path = resolve_output_path(
        declared
    )

    record: dict[str, Any] = {
        "declared": declared,
        "path": relative_path(path),
        "exists": path.exists(),
        "kind": (
            "directory"
            if path.is_dir()
            else "file"
            if path.is_file()
            else "missing"
        ),
        "sha256": None,
        "byte_count": None,
    }

    if path.is_file():
        record["sha256"] = sha256_path(
            path
        )

        record["byte_count"] = (
            path.stat().st_size
        )

    elif path.is_dir():
        children = sorted(
            (
                child
                for child in path.rglob("*")
                if child.is_file()
            ),
            key=lambda child: (
                child.relative_to(path).as_posix()
            ),
        )

        child_records = [
            {
                "path": child.relative_to(
                    path
                ).as_posix(),
                "sha256": sha256_path(
                    child
                ),
                "byte_count": (
                    child.stat().st_size
                ),
            }
            for child in children
        ]

        record["children"] = child_records

        record["sha256"] = semantic_digest(
            child_records
        )

        record["byte_count"] = sum(
            child["byte_count"]
            for child in child_records
        )

    return record


def build_manifest(
    graph: dict[str, Any],
    task_id: str,
) -> dict[str, Any]:
    records = task_map(
        graph
    )

    if task_id not in records:
        raise KeyError(
            f"Unknown task: {task_id}"
        )

    task = records[
        task_id
    ]

    declared_outputs = task.get(
        "outputs",
        [],
    )

    if not isinstance(
        declared_outputs,
        list,
    ):
        raise ManifestError(
            "Task outputs are invalid."
        )

    artifacts = [
        artifact_record(
            declared
        )
        for declared in declared_outputs
        if isinstance(declared, str)
    ]

    events = collection_for_task(
        graph,
        "events",
        task_id,
    )

    evidence = collection_for_task(
        graph,
        "evidence",
        task_id,
    )

    receipts = collection_for_task(
        graph,
        "receipts",
        task_id,
    )

    attestations = collection_for_task(
        graph,
        "attestations",
        task_id,
    )

    decisions = decisions_for_task(
        graph,
        task_id,
    )

    segues = segues_for_task(
        graph,
        task_id,
    )

    manifest: dict[str, Any] = {
        "schema": (
            "savant://niche/masterplan/"
            "artifact-manifest/1.0.0"
        ),
        "task_id": task_id,
        "task": {
            "title": task.get("title"),
            "status": task.get("status"),
            "authority": task.get("authority"),
            "priority": task.get("priority"),
            "purpose": task.get("purpose"),
            "acceptance": task.get(
                "acceptance",
                [],
            ),
        },
        "graph": {
            "path": relative_path(
                GRAPH_PATH
            ),
            "sha256": sha256_path(
                GRAPH_PATH
            ),
            "semantic_digest": (
                semantic_digest(graph)
            ),
            "schema_version": graph.get(
                "schema_version"
            ),
        },
        "artifacts": artifacts,
        "segues": segues,
        "decisions": decisions,
        "events": events,
        "evidence": evidence,
        "receipts": receipts,
        "attestations": attestations,
        "statistics": {
            "declared_output_count": len(
                declared_outputs
            ),
            "existing_output_count": sum(
                artifact["exists"]
                for artifact in artifacts
            ),
            "missing_output_count": sum(
                not artifact["exists"]
                for artifact in artifacts
            ),
            "segue_count": len(segues),
            "decision_count": len(decisions),
            "event_count": len(events),
            "evidence_count": len(evidence),
            "receipt_count": len(receipts),
            "attestation_count": len(
                attestations
            ),
        },
        "generated_at": utc_now(),
    }

    manifest["content_digest"] = (
        semantic_digest(
            {
                key: value
                for key, value
                in manifest.items()
                if key not in {
                    "generated_at",
                    "content_digest",
                }
            }
        )
    )

    manifest["manifest_id"] = (
        "manifest-"
        + manifest["content_digest"][:24]
    )

    return manifest


def verify_manifest(
    manifest: dict[str, Any],
    graph: dict[str, Any],
) -> dict[str, Any]:
    task_id = manifest.get(
        "task_id"
    )

    if not isinstance(task_id, str):
        raise ManifestError(
            "Manifest task identifier is invalid."
        )

    rebuilt = build_manifest(
        graph,
        task_id,
    )

    checks = {
        "task_matches": (
            rebuilt["task_id"]
            == manifest.get("task_id")
        ),
        "graph_digest_matches": (
            rebuilt["graph"][
                "semantic_digest"
            ]
            == manifest.get(
                "graph",
                {},
            ).get(
                "semantic_digest"
            )
        ),
        "artifact_digest_matches": (
            semantic_digest(
                rebuilt["artifacts"]
            )
            == semantic_digest(
                manifest.get(
                    "artifacts",
                    [],
                )
            )
        ),
        "content_digest_matches": (
            rebuilt["content_digest"]
            == manifest.get(
                "content_digest"
            )
        ),
        "manifest_id_matches": (
            rebuilt["manifest_id"]
            == manifest.get(
                "manifest_id"
            )
        ),
    }

    return {
        "passed": all(
            checks.values()
        ),
        "checks": checks,
        "expected_manifest_id": (
            rebuilt["manifest_id"]
        ),
        "actual_manifest_id": (
            manifest.get(
                "manifest_id"
            )
        ),
        "expected_content_digest": (
            rebuilt["content_digest"]
        ),
        "actual_content_digest": (
            manifest.get(
                "content_digest"
            )
        ),
    }


def persist_manifest(
    manifest: dict[str, Any],
) -> dict[str, Any]:
    task_id = manifest[
        "task_id"
    ]

    task_root = (
        MANIFEST_ROOT
        / task_id
    )

    task_root.mkdir(
        parents=True,
        exist_ok=True,
    )

    historical = (
        task_root
        / (
            f"{manifest['manifest_id']}"
            ".json"
        )
    )

    latest = (
        task_root
        / "latest.json"
    )

    if historical.exists():
        existing = load_json(
            historical
        )

        if (
            semantic_digest(existing)
            != semantic_digest(manifest)
        ):
            raise ManifestError(
                "Manifest ID collision."
            )

    else:
        atomic_write_json(
            historical,
            manifest,
        )

    atomic_write_json(
        latest,
        manifest,
    )

    return {
        "historical": relative_path(
            historical
        ),
        "latest": relative_path(
            latest
        ),
    }


def persist_report(
    operation: str,
    result: dict[str, Any],
) -> dict[str, str]:
    REPORT_ROOT.mkdir(
        parents=True,
        exist_ok=True,
    )

    run_id = timestamp()

    historical = (
        REPORT_ROOT
        / f"{run_id}__{operation}.json"
    )

    latest = (
        REPORT_ROOT
        / "latest.json"
    )

    atomic_write_json(
        historical,
        result,
    )

    atomic_write_json(
        latest,
        result,
    )

    return {
        "historical": relative_path(
            historical
        ),
        "latest": relative_path(
            latest
        ),
    }


def command_build(
    task_id: str,
    persist: bool,
) -> dict[str, Any]:
    graph = load_json(
        GRAPH_PATH
    )

    manifest = build_manifest(
        graph,
        task_id,
    )

    files = (
        persist_manifest(manifest)
        if persist
        else None
    )

    result: dict[str, Any] = {
        "operation": (
            "build_masterplan_artifact_manifest"
        ),
        "passed": True,
        "persisted": persist,
        "manifest": manifest,
        "files": files,
    }

    result["semantic_digest"] = (
        semantic_digest(result)
    )

    return result


def command_verify(
    manifest_path: Path,
) -> dict[str, Any]:
    path = manifest_path.expanduser()

    if not path.is_absolute():
        path = ROOT / path

    path = path.resolve()

    if not path.is_file():
        raise FileNotFoundError(path)

    manifest = load_json(
        path
    )

    graph = load_json(
        GRAPH_PATH
    )

    verification = verify_manifest(
        manifest,
        graph,
    )

    result: dict[str, Any] = {
        "operation": (
            "verify_masterplan_artifact_manifest"
        ),
        "passed": verification[
            "passed"
        ],
        "manifest_path": relative_path(
            path
        ),
        "manifest_sha256": sha256_path(
            path
        ),
        "verification": verification,
    }

    result["semantic_digest"] = (
        semantic_digest(result)
    )

    return result


def command_all(
    persist: bool,
) -> dict[str, Any]:
    graph = load_json(
        GRAPH_PATH
    )

    records = task_map(
        graph
    )

    manifests = [
        build_manifest(
            graph,
            task_id,
        )
        for task_id in sorted(
            records
        )
    ]

    files = []

    if persist:
        files = [
            persist_manifest(
                manifest
            )
            for manifest in manifests
        ]

    result: dict[str, Any] = {
        "operation": (
            "build_all_masterplan_artifact_manifests"
        ),
        "passed": True,
        "persisted": persist,
        "manifest_count": len(
            manifests
        ),
        "manifest_ids": [
            manifest[
                "manifest_id"
            ]
            for manifest in manifests
        ],
        "collection_digest": (
            semantic_digest(
                [
                    {
                        "task_id": manifest[
                            "task_id"
                        ],
                        "manifest_id": manifest[
                            "manifest_id"
                        ],
                        "content_digest": manifest[
                            "content_digest"
                        ],
                    }
                    for manifest in manifests
                ]
            )
        ),
        "files": files,
    }

    result["semantic_digest"] = (
        semantic_digest(result)
    )

    return result


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Build and verify content-addressed "
            "Masterplan task artifact manifests."
        )
    )

    subparsers = parser.add_subparsers(
        dest="command",
        required=True,
    )

    build_parser = subparsers.add_parser(
        "build"
    )

    build_parser.add_argument(
        "task_id"
    )

    build_parser.add_argument(
        "--persist",
        action="store_true",
    )

    verify_parser = subparsers.add_parser(
        "verify"
    )

    verify_parser.add_argument(
        "manifest_path",
        type=Path,
    )

    all_parser = subparsers.add_parser(
        "all"
    )

    all_parser.add_argument(
        "--persist",
        action="store_true",
    )

    arguments = parser.parse_args()

    try:
        if arguments.command == "build":
            result = command_build(
                arguments.task_id,
                arguments.persist,
            )

        elif arguments.command == "verify":
            result = command_verify(
                arguments.manifest_path
            )

        elif arguments.command == "all":
            result = command_all(
                arguments.persist
            )

        else:
            return 2

        result["reports"] = persist_report(
            arguments.command,
            result,
        )

    except Exception as exc:
        print(
            json.dumps(
                {
                    "operation": (
                        "build_masterplan_artifact_manifest"
                    ),
                    "passed": False,
                    "error": {
                        "type": type(
                            exc
                        ).__name__,
                        "message": str(
                            exc
                        ),
                    },
                },
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
        )

        return 1

    print(
        json.dumps(
            result,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )

    return (
        0
        if result.get("passed")
        is True
        else 1
    )


if __name__ == "__main__":
    raise SystemExit(main())
