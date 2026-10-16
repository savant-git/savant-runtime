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

EVIDENCE_ROOT = (
    ROOT
    / "authority"
    / "task-graph"
    / "evidence"
)

REPORT_ROOT = (
    ROOT
    / "reports"
    / "niche"
    / "masterplan"
    / "evidence"
)

SNAPSHOT_ROOT = (
    ROOT
    / "authority"
    / "task-graph"
    / "snapshots"
)

VOLATILE_FIELDS = {
    "generated_at",
    "created_at",
    "captured_at",
    "accepted_at",
    "occurred_at",
    "timestamp",
    "started_at",
    "finished_at",
    "duration_seconds",
    "elapsed_seconds",
    "wall_clock_seconds",
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


def atomic_write_text(
    path: Path,
    value: str,
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

    temporary_path = Path(
        temporary_name
    )

    try:
        with os.fdopen(
            descriptor,
            "w",
            encoding="utf-8",
        ) as handle:
            handle.write(value)
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


def relative_path(
    path: Path,
) -> str:
    try:
        return path.relative_to(
            ROOT
        ).as_posix()

    except ValueError:
        return str(path)


def resolve_path(
    declared: str | None,
) -> Path | None:
    if declared is None:
        return None

    path = Path(
        declared
    ).expanduser()

    if not path.is_absolute():
        path = ROOT / path

    path = path.resolve()

    try:
        path.relative_to(ROOT)

    except ValueError as exc:
        raise ValueError(
            f"Evidence path escapes runtime root: {path}"
        ) from exc

    return path


def task_map(
    graph: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    records = graph.get(
        "records"
    )

    if not isinstance(records, list):
        raise ValueError(
            "Task graph records are invalid."
        )

    result: dict[str, dict[str, Any]] = {}

    for record in records:
        if not isinstance(record, dict):
            raise ValueError(
                "Task graph contains an invalid task record."
            )

        identifier = record.get(
            "id"
        )

        if not isinstance(identifier, str):
            raise ValueError(
                "Task record identifier is missing."
            )

        result[identifier] = record

    return result


def evidence_exists(
    graph: dict[str, Any],
    evidence_id: str,
) -> bool:
    evidence = graph.get(
        "evidence",
        [],
    )

    if not isinstance(evidence, list):
        raise ValueError(
            "Task graph evidence collection is invalid."
        )

    return any(
        isinstance(record, dict)
        and record.get("id") == evidence_id
        for record in evidence
    )


def build_evidence(
    graph: dict[str, Any],
    *,
    task_id: str,
    kind: str,
    declared_path: str | None,
    passed: bool | None,
    actor: str,
    authority_state: str,
    notes: str,
) -> dict[str, Any]:
    records = task_map(
        graph
    )

    if task_id not in records:
        raise KeyError(
            f"Unknown task: {task_id}"
        )

    if authority_state not in {
        "accepted",
        "authoritative",
    }:
        raise ValueError(
            "Evidence authority must be accepted or authoritative."
        )

    if not kind.strip():
        raise ValueError(
            "Evidence kind is required."
        )

    path = resolve_path(
        declared_path
    )

    if (
        path is not None
        and not path.exists()
    ):
        raise FileNotFoundError(
            path
        )

    occurred_at = utc_now()

    path_sha256 = (
        sha256_path(path)
        if (
            path is not None
            and path.is_file()
        )
        else None
    )

    body = {
        "task_id": task_id,
        "kind": kind,
        "path": (
            relative_path(path)
            if path is not None
            else None
        ),
        "sha256": path_sha256,
        "passed": passed,
        "actor": actor,
        "authority_state": authority_state,
        "notes": notes,
        "graph_digest": digest(
            deterministic_projection(
                graph
            )
        ),
    }

    evidence_id = (
        "evidence-"
        + digest(body)[:24]
    )

    if evidence_exists(
        graph,
        evidence_id,
    ):
        raise ValueError(
            f"Evidence already exists: {evidence_id}"
        )

    return {
        "id": evidence_id,
        "task_id": task_id,
        "kind": kind,
        "path": body["path"],
        "sha256": path_sha256,
        "passed": passed,
        "authority": {
            "state": authority_state,
            "authority_class": (
                "project-owner-directed"
            ),
            "tier": 1,
            "source": (
                body["path"]
                or "masterplan-evidence"
            ),
            "accepted_by": actor,
            "accepted_at": occurred_at,
            "confidence": 1.0,
        },
        "provenance": {
            "sources": [
                {
                    "source_id": (
                        body["path"]
                        or evidence_id
                    ),
                    "source_kind": kind,
                    "source_path": body["path"],
                    "source_sha256": path_sha256,
                    "authority_state": (
                        authority_state
                    ),
                    "captured_at": occurred_at,
                }
            ],
            "transformations": [
                "validate_evidence_subject",
                "validate_evidence_authority",
                "capture_evidence_digest",
                "append_authoritative_evidence",
            ],
            "generated_by": (
                "prodigal.niche.masterplan."
                "admit_masterplan_evidence"
            ),
            "generated_at": occurred_at,
            "contract_version": "1.0.0",
        },
        "extensions": {
            "actor": actor,
            "notes": notes,
            "captured_at": occurred_at,
        },
    }


def append_evidence(
    graph: dict[str, Any],
    evidence: dict[str, Any],
) -> dict[str, Any]:
    updated = json.loads(
        json.dumps(graph)
    )

    collection = updated.setdefault(
        "evidence",
        [],
    )

    if not isinstance(collection, list):
        raise ValueError(
            "Task graph evidence collection is invalid."
        )

    collection.append(
        evidence
    )

    return updated


def persist(
    graph_before: dict[str, Any],
    graph_after: dict[str, Any],
    evidence: dict[str, Any],
) -> dict[str, Any]:
    atomic_write_json(
        GRAPH_PATH,
        graph_after,
    )

    written = load_json(
        GRAPH_PATH
    )

    if digest(
        deterministic_projection(
            written
        )
    ) != digest(
        deterministic_projection(
            graph_after
        )
    ):
        raise RuntimeError(
            "Written task graph digest mismatch."
        )

    EVIDENCE_ROOT.mkdir(
        parents=True,
        exist_ok=True,
    )

    evidence_path = (
        EVIDENCE_ROOT
        / f"{evidence['id']}.json"
    )

    atomic_write_json(
        evidence_path,
        evidence,
    )

    SNAPSHOT_ROOT.mkdir(
        parents=True,
        exist_ok=True,
    )

    run_id = (
        f"{timestamp()}__"
        f"{evidence['id']}"
    )

    snapshot = (
        SNAPSHOT_ROOT
        / f"{run_id}__masterplan.json"
    )

    atomic_write_json(
        snapshot,
        graph_after,
    )

    result: dict[str, Any] = {
        "schema": (
            "savant://niche/masterplan/"
            "evidence-admission/1.0.0"
        ),
        "operation": (
            "admit_masterplan_evidence"
        ),
        "generated_at": utc_now(),
        "passed": True,
        "evidence": evidence,
        "graph": {
            "path": relative_path(
                GRAPH_PATH
            ),
            "sha256": sha256_path(
                GRAPH_PATH
            ),
            "digest_before": digest(
                deterministic_projection(
                    graph_before
                )
            ),
            "digest_after": digest(
                deterministic_projection(
                    graph_after
                )
            ),
        },
        "files": {
            "evidence": relative_path(
                evidence_path
            ),
            "snapshot": relative_path(
                snapshot
            ),
        },
    }

    result["digest"] = digest(
        deterministic_projection(
            result
        )
    )

    REPORT_ROOT.mkdir(
        parents=True,
        exist_ok=True,
    )

    atomic_write_json(
        REPORT_ROOT
        / f"{run_id}__evidence.json",
        result,
    )

    atomic_write_json(
        REPORT_ROOT
        / "latest.json",
        result,
    )

    return result


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Admit authoritative task evidence into "
            "the Masterplan graph."
        )
    )

    parser.add_argument(
        "task_id",
    )

    parser.add_argument(
        "kind",
    )

    parser.add_argument(
        "--path",
    )

    parser.add_argument(
        "--passed",
        choices=[
            "true",
            "false",
            "unknown",
        ],
        default="unknown",
    )

    parser.add_argument(
        "--actor",
        required=True,
    )

    parser.add_argument(
        "--authority-state",
        choices=[
            "accepted",
            "authoritative",
        ],
        default="accepted",
    )

    parser.add_argument(
        "--notes",
        default="",
    )

    parser.add_argument(
        "--plan",
        action="store_true",
    )

    arguments = parser.parse_args()

    try:
        graph_before = load_json(
            GRAPH_PATH
        )

        passed_value = {
            "true": True,
            "false": False,
            "unknown": None,
        }[
            arguments.passed
        ]

        evidence = build_evidence(
            graph_before,
            task_id=arguments.task_id,
            kind=arguments.kind,
            declared_path=arguments.path,
            passed=passed_value,
            actor=arguments.actor,
            authority_state=(
                arguments.authority_state
            ),
            notes=arguments.notes,
        )

        graph_after = append_evidence(
            graph_before,
            evidence,
        )

        if arguments.plan:
            result = {
                "schema": (
                    "savant://niche/masterplan/"
                    "evidence-admission-plan/1.0.0"
                ),
                "operation": (
                    "plan_masterplan_evidence"
                ),
                "generated_at": utc_now(),
                "passed": True,
                "evidence": evidence,
                "graph": {
                    "digest_before": digest(
                        deterministic_projection(
                            graph_before
                        )
                    ),
                    "digest_after": digest(
                        deterministic_projection(
                            graph_after
                        )
                    ),
                },
            }

        else:
            result = persist(
                graph_before,
                graph_after,
                evidence,
            )

    except Exception as exc:
        print(
            json.dumps(
                {
                    "operation": (
                        "admit_masterplan_evidence"
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

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
