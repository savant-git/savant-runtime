#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import shutil
import tempfile
from pathlib import Path
from typing import Any


ROOT = Path("/root/savant-runtime")

SUBJECT_ROOT = (
    ROOT
    / "hierarchies"
    / "identity"
    / "exiles"
    / "niche"
    / "prodigals"
    / "masterplan"
)

CURRENT_WORK = (
    SUBJECT_ROOT
    / "authority"
    / "current_work.json"
)

LEGACY_PLAN = (
    ROOT
    / "docs"
    / "SAVANT_MASTER_TASKS.md"
)

AUTHORITY_ROOT = (
    ROOT
    / "authority"
    / "task-graph"
)

GRAPH_PATH = (
    AUTHORITY_ROOT
    / "masterplan.json"
)

SEED_PATH = (
    AUTHORITY_ROOT
    / "masterplan.seed.json"
)

SNAPSHOT_ROOT = (
    AUTHORITY_ROOT
    / "snapshots"
)

BACKUP_ROOT = (
    ROOT
    / "backups"
    / "masterplan"
    / "graph-build"
)

REPORT_ROOT = (
    ROOT
    / "reports"
    / "niche"
    / "masterplan"
    / "build"
)

COLLECTION_NAMES = (
    "events",
    "decisions",
    "evidence",
    "receipts",
    "attestations",
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


def relative_path(
    path: Path,
) -> str:
    try:
        return path.relative_to(
            ROOT
        ).as_posix()

    except ValueError:
        return str(path)


def normalize_task_id(
    value: str,
) -> str:
    normalized = re.sub(
        r"[^A-Za-z0-9._-]+",
        "-",
        value.strip(),
    ).upper()

    normalized = re.sub(
        r"-+",
        "-",
        normalized,
    ).strip("-")

    if not normalized.startswith("SAV-"):
        normalized = (
            "SAV-"
            + normalized
        )

    return normalized


def infer_band(
    task_id: str,
    fallback: str,
) -> str:
    match = re.match(
        r"^SAV-(P[0-9]+[A-Z]*)-",
        task_id,
    )

    if match:
        return match.group(1)

    return fallback


def infer_ordinal(
    task_id: str,
    fallback: int,
) -> int:
    match = re.search(
        r"-([0-9]+)$",
        task_id,
    )

    if match:
        return int(
            match.group(1)
        )

    return fallback


def band_weight(
    band: str,
) -> int:
    match = re.match(
        r"^P([0-9]+)([A-Z]*)$",
        band,
    )

    if not match:
        return 0

    number = int(
        match.group(1)
    )

    suffix = match.group(2)

    value = max(
        0,
        100000
        - number * 10000,
    )

    for index, character in enumerate(
        suffix,
        start=1,
    ):
        value -= (
            index
            * (
                ord(character)
                - ord("A")
                + 1
            )
            * 100
        )

    return value


def task_map(
    graph: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    records = graph.get(
        "records",
        [],
    )

    if not isinstance(records, list):
        raise ValueError(
            "Task graph records are invalid."
        )

    result: dict[str, dict[str, Any]] = {}

    for record in records:
        if not isinstance(record, dict):
            raise ValueError(
                "Task graph contains an invalid record."
            )

        identifier = record.get("id")

        if not isinstance(identifier, str):
            raise ValueError(
                "Task record identifier is missing."
            )

        if identifier in result:
            raise ValueError(
                f"Duplicate task record: {identifier}"
            )

        result[identifier] = record

    return result


def current_work_tasks(
    document: dict[str, Any],
) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []

    for section_name in (
        "observed_parallel_work",
        "masterplan_prodigal_work",
    ):
        section = document.get(
            section_name
        )

        if not isinstance(section, dict):
            continue

        tasks = section.get(
            "tasks"
        )

        if not isinstance(tasks, list):
            continue

        result.extend(
            task
            for task in tasks
            if isinstance(task, dict)
        )

    return result


def proposed_record(
    raw: dict[str, Any],
    index: int,
) -> dict[str, Any]:
    task_id = normalize_task_id(
        str(
            raw.get(
                "id",
                f"SAV-P9-{index:03d}",
            )
        )
    )

    title = " ".join(
        str(
            raw.get(
                "title",
                task_id,
            )
        ).split()
    )

    band = infer_band(
        task_id,
        str(
            raw.get(
                "priority",
                "P9",
            )
        ),
    )

    ordinal = infer_ordinal(
        task_id,
        index,
    )

    dependencies = [
        normalize_task_id(
            str(value)
        )
        for value in raw.get(
            "depends_on",
            [],
        )
        if isinstance(
            value,
            str,
        )
    ]

    outputs = [
        str(value)
        for value in raw.get(
            "outputs",
            [],
        )
        if isinstance(
            value,
            str,
        )
    ]

    acceptance = [
        str(value)
        for value in raw.get(
            "acceptance",
            [],
        )
        if isinstance(
            value,
            str,
        )
    ]

    if not acceptance:
        acceptance = [
            (
                "Implementation satisfies the declared purpose, "
                "preserves authority boundaries, exposes lineage "
                "and provenance, and passes declared verification."
            )
        ]

    return {
        "id": task_id,
        "kind": "task",
        "title": title,
        "description": str(
            raw.get(
                "description",
                "",
            )
        ),
        "priority": {
            "band": band,
            "ordinal": ordinal,
            "authority_locked": bool(
                raw.get(
                    "authority_locked",
                    False,
                )
            ),
            "rationale": (
                "Proposed from current-work authority input."
            ),
        },
        "status": "proposed",
        "authority": {
            "state": "proposed",
            "authority_class": (
                "project-owner-directed"
            ),
            "tier": 2,
            "source": relative_path(
                CURRENT_WORK
            ),
            "accepted_by": None,
            "accepted_at": None,
            "confidence": 1.0,
        },
        "purpose": str(
            raw.get(
                "purpose",
                title,
            )
        ),
        "scope": {
            "depends_on": dependencies,
            "source_status": raw.get(
                "status",
                "proposed",
            ),
        },
        "acceptance": acceptance,
        "evidence_requirements": [],
        "outputs": outputs,
        "risks": [
            str(value)
            for value in raw.get(
                "risks",
                [],
            )
            if isinstance(
                value,
                str,
            )
        ],
        "security": {
            "authority_transfer": False,
            "requires_explicit_completion_evidence": True,
        },
        "lineage": {
            "source_task_id": task_id,
            "source": relative_path(
                CURRENT_WORK
            ),
        },
        "provenance": {
            "sources": [
                {
                    "source_id": relative_path(
                        CURRENT_WORK
                    ),
                    "source_kind": (
                        "proposed-roadmap-extension"
                    ),
                    "source_path": relative_path(
                        CURRENT_WORK
                    ),
                    "source_sha256": (
                        sha256_path(
                            CURRENT_WORK
                        )
                        if CURRENT_WORK.is_file()
                        else None
                    ),
                    "authority_state": (
                        "proposed"
                    ),
                    "captured_at": None,
                }
            ],
            "transformations": [
                "current_work_to_proposed_task_record"
            ],
            "generated_by": (
                "prodigal.niche.masterplan."
                "build_authoritative_task_graph"
            ),
            "generated_at": (
                "2026-08-01T18:43:45-04:00"
            ),
            "contract_version": "1.0.0",
        },
        "extensions": {
            "source_record": raw,
        },
    }


def segue_id(
    source: str,
    target: str,
    segue_type: str,
) -> str:
    return (
        "segue-"
        + digest(
            {
                "type": segue_type,
                "source": source,
                "target": target,
            }
        )[:24]
    )


def proposed_segues(
    records: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []

    for task_id, record in sorted(
        records.items()
    ):
        scope = record.get(
            "scope"
        )

        if not isinstance(scope, dict):
            continue

        dependencies = scope.get(
            "depends_on",
            [],
        )

        if not isinstance(
            dependencies,
            list,
        ):
            continue

        for dependency in dependencies:
            if (
                not isinstance(
                    dependency,
                    str,
                )
                or dependency not in records
            ):
                continue

            identifier = segue_id(
                task_id,
                dependency,
                "depends_on",
            )

            result.append(
                {
                    "id": identifier,
                    "type": "depends_on",
                    "source": task_id,
                    "target": dependency,
                    "authority": record[
                        "authority"
                    ],
                    "provenance": record[
                        "provenance"
                    ],
                    "validity": {
                        "active": True,
                    },
                    "extensions": {},
                }
            )

    return result


def validate_graph_shape(
    graph: dict[str, Any],
) -> None:
    required = {
        "schema_version",
        "graph_id",
        "authority",
        "records",
        "segues",
        *COLLECTION_NAMES,
    }

    missing = sorted(
        required
        - set(graph)
    )

    if missing:
        raise ValueError(
            (
                "Task graph is missing required fields: "
                + ", ".join(missing)
            )
        )

    task_map(graph)

    for field in (
        "segues",
        *COLLECTION_NAMES,
    ):
        if not isinstance(
            graph.get(field),
            list,
        ):
            raise ValueError(
                f"Task graph field is not a list: {field}"
            )


def seed_from_existing_graph() -> dict[str, Any]:
    graph = load_json(
        GRAPH_PATH
    )

    validate_graph_shape(
        graph
    )

    seed = json.loads(
        json.dumps(graph)
    )

    for collection in COLLECTION_NAMES:
        seed[collection] = []

    return seed


def create_seed_if_missing() -> None:
    if SEED_PATH.is_file():
        return

    if not GRAPH_PATH.is_file():
        raise FileNotFoundError(
            (
                "Neither authoritative graph nor seed exists. "
                f"Expected {GRAPH_PATH} or {SEED_PATH}"
            )
        )

    seed = seed_from_existing_graph()

    atomic_write_json(
        SEED_PATH,
        seed,
    )


def load_authoritative_base() -> tuple[
    dict[str, Any],
    str,
]:
    if GRAPH_PATH.is_file():
        graph = load_json(
            GRAPH_PATH
        )

        validate_graph_shape(
            graph
        )

        return graph, "existing_authoritative_graph"

    create_seed_if_missing()

    graph = load_json(
        SEED_PATH
    )

    validate_graph_shape(
        graph
    )

    return graph, "authoritative_seed"


def merge_current_work(
    graph: dict[str, Any],
) -> dict[str, Any]:
    if not CURRENT_WORK.is_file():
        return graph

    updated = json.loads(
        json.dumps(graph)
    )

    records = task_map(
        updated
    )

    current_work = load_json(
        CURRENT_WORK
    )

    for index, raw in enumerate(
        current_work_tasks(
            current_work
        ),
        start=1,
    ):
        candidate = proposed_record(
            raw,
            index,
        )

        task_id = candidate["id"]

        if task_id in records:
            existing = records[
                task_id
            ]

            extensions = existing.setdefault(
                "extensions",
                {},
            )

            if not isinstance(
                extensions,
                dict,
            ):
                raise ValueError(
                    (
                        "Task extensions are invalid: "
                        f"{task_id}"
                    )
                )

            extensions[
                "current_work_observation"
            ] = raw

            continue

        updated[
            "records"
        ].append(
            candidate
        )

        records[
            task_id
        ] = candidate

    existing_segues = {
        segue.get("id")
        for segue in updated.get(
            "segues",
            [],
        )
        if isinstance(segue, dict)
    }

    for segue in proposed_segues(
        records
    ):
        if segue["id"] in existing_segues:
            continue

        updated[
            "segues"
        ].append(
            segue
        )

        existing_segues.add(
            segue["id"]
        )

    updated[
        "records"
    ] = sorted(
        updated["records"],
        key=lambda record: (
            -band_weight(
                str(
                    (
                        record.get(
                            "priority"
                        )
                        or {}
                    ).get(
                        "band",
                        "P999",
                    )
                )
            ),
            int(
                (
                    record.get(
                        "priority"
                    )
                    or {}
                ).get(
                    "ordinal",
                    999999,
                )
            ),
            str(
                record.get(
                    "id",
                    "",
                )
            ),
        ),
    )

    updated[
        "segues"
    ] = sorted(
        updated["segues"],
        key=lambda segue: (
            str(
                segue.get(
                    "type",
                    "",
                )
            ),
            str(
                segue.get(
                    "source",
                    "",
                )
            ),
            str(
                segue.get(
                    "target",
                    "",
                )
            ),
            str(
                segue.get(
                    "id",
                    "",
                )
            ),
        ),
    )

    return updated


def assert_preserved_authority(
    before: dict[str, Any],
    after: dict[str, Any],
) -> dict[str, Any]:
    before_records = task_map(
        before
    )

    after_records = task_map(
        after
    )

    removed_tasks = sorted(
        set(before_records)
        - set(after_records)
    )

    altered_authoritative_tasks: list[
        dict[str, Any]
    ] = []

    for task_id in sorted(
        set(before_records)
        & set(after_records)
    ):
        previous = before_records[
            task_id
        ]

        current = after_records[
            task_id
        ]

        authority = previous.get(
            "authority"
        )

        previous_state = (
            authority.get(
                "state"
            )
            if isinstance(
                authority,
                dict,
            )
            else None
        )

        if previous_state not in {
            "accepted",
            "authoritative",
        }:
            continue

        protected_fields = (
            "id",
            "status",
            "authority",
            "priority",
        )

        changes = {
            field: {
                "before": previous.get(
                    field
                ),
                "after": current.get(
                    field
                ),
            }
            for field in protected_fields
            if deterministic_projection(
                previous.get(field)
            )
            != deterministic_projection(
                current.get(field)
            )
        }

        if changes:
            altered_authoritative_tasks.append(
                {
                    "task_id": task_id,
                    "changes": changes,
                }
            )

    collection_losses: dict[
        str,
        list[str],
    ] = {}

    for collection in COLLECTION_NAMES:
        before_ids = {
            record.get("id")
            for record in before.get(
                collection,
                [],
            )
            if isinstance(record, dict)
        }

        after_ids = {
            record.get("id")
            for record in after.get(
                collection,
                [],
            )
            if isinstance(record, dict)
        }

        lost = sorted(
            identifier
            for identifier in (
                before_ids
                - after_ids
            )
            if isinstance(
                identifier,
                str,
            )
        )

        if lost:
            collection_losses[
                collection
            ] = lost

    result = {
        "passed": not any(
            (
                removed_tasks,
                altered_authoritative_tasks,
                collection_losses,
            )
        ),
        "removed_tasks": removed_tasks,
        "altered_authoritative_tasks": (
            altered_authoritative_tasks
        ),
        "collection_losses": (
            collection_losses
        ),
    }

    if not result["passed"]:
        raise RuntimeError(
            json.dumps(
                result,
                ensure_ascii=False,
                sort_keys=True,
            )
        )

    return result


def backup_graph(
    run_id: str,
) -> Path | None:
    if not GRAPH_PATH.is_file():
        return None

    destination = (
        BACKUP_ROOT
        / run_id
        / "masterplan.json"
    )

    destination.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    shutil.copy2(
        GRAPH_PATH,
        destination,
    )

    if sha256_path(
        GRAPH_PATH
    ) != sha256_path(
        destination
    ):
        raise RuntimeError(
            "Graph backup hash mismatch."
        )

    return destination


def build_graph() -> tuple[
    dict[str, Any],
    dict[str, Any],
]:
    base, source_mode = (
        load_authoritative_base()
    )

    updated = merge_current_work(
        base
    )

    validate_graph_shape(
        updated
    )

    preservation = assert_preserved_authority(
        base,
        updated,
    )

    metadata = {
        "source_mode": source_mode,
        "preservation": preservation,
        "base_digest": digest(
            deterministic_projection(
                base
            )
        ),
        "updated_digest": digest(
            deterministic_projection(
                updated
            )
        ),
        "changed": (
            deterministic_projection(
                base
            )
            != deterministic_projection(
                updated
            )
        ),
    }

    return updated, metadata


def persist_graph(
    graph: dict[str, Any],
    metadata: dict[str, Any],
) -> dict[str, Any]:
    run_id = timestamp()

    backup = backup_graph(
        run_id
    )

    if not SEED_PATH.is_file():
        seed = json.loads(
            json.dumps(graph)
        )

        for collection in COLLECTION_NAMES:
            seed[collection] = []

        atomic_write_json(
            SEED_PATH,
            seed,
        )

    atomic_write_json(
        GRAPH_PATH,
        graph,
    )

    written = load_json(
        GRAPH_PATH
    )

    expected_digest = digest(
        deterministic_projection(
            graph
        )
    )

    actual_digest = digest(
        deterministic_projection(
            written
        )
    )

    if expected_digest != actual_digest:
        if backup is not None:
            shutil.copy2(
                backup,
                GRAPH_PATH,
            )

        raise RuntimeError(
            "Written graph digest mismatch."
        )

    SNAPSHOT_ROOT.mkdir(
        parents=True,
        exist_ok=True,
    )

    snapshot = (
        SNAPSHOT_ROOT
        / f"{run_id}__masterplan.json"
    )

    atomic_write_json(
        snapshot,
        graph,
    )

    records = task_map(
        graph
    )

    result: dict[str, Any] = {
        "operation": (
            "build_authoritative_task_graph"
        ),
        "passed": True,
        "generated_at": utc_now(),
        "mode": metadata[
            "source_mode"
        ],
        "changed": metadata[
            "changed"
        ],
        "preservation": metadata[
            "preservation"
        ],
        "graph": {
            "path": relative_path(
                GRAPH_PATH
            ),
            "sha256": sha256_path(
                GRAPH_PATH
            ),
            "deterministic_digest": (
                actual_digest
            ),
            "record_count": len(
                records
            ),
            "segue_count": len(
                graph.get(
                    "segues",
                    [],
                )
            ),
            "event_count": len(
                graph.get(
                    "events",
                    [],
                )
            ),
            "decision_count": len(
                graph.get(
                    "decisions",
                    [],
                )
            ),
            "evidence_count": len(
                graph.get(
                    "evidence",
                    [],
                )
            ),
            "receipt_count": len(
                graph.get(
                    "receipts",
                    [],
                )
            ),
            "attestation_count": len(
                graph.get(
                    "attestations",
                    [],
                )
            ),
            "accepted_record_count": sum(
                (
                    record.get(
                        "authority"
                    )
                    or {}
                ).get(
                    "state"
                )
                in {
                    "accepted",
                    "authoritative",
                }
                for record in records.values()
            ),
            "proposed_record_count": sum(
                (
                    record.get(
                        "authority"
                    )
                    or {}
                ).get(
                    "state"
                )
                == "proposed"
                for record in records.values()
            ),
        },
        "sources": {
            "authoritative_graph": {
                "path": relative_path(
                    GRAPH_PATH
                ),
                "exists": (
                    GRAPH_PATH.is_file()
                ),
            },
            "seed": {
                "path": relative_path(
                    SEED_PATH
                ),
                "exists": (
                    SEED_PATH.is_file()
                ),
                "sha256": (
                    sha256_path(
                        SEED_PATH
                    )
                    if SEED_PATH.is_file()
                    else None
                ),
            },
            "current_work": {
                "path": relative_path(
                    CURRENT_WORK
                ),
                "exists": (
                    CURRENT_WORK.is_file()
                ),
                "sha256": (
                    sha256_path(
                        CURRENT_WORK
                    )
                    if CURRENT_WORK.is_file()
                    else None
                ),
            },
            "legacy_projection": {
                "path": relative_path(
                    LEGACY_PLAN
                ),
                "exists": (
                    LEGACY_PLAN.is_file()
                ),
                "used_as_authority": False,
            },
        },
        "backup": (
            relative_path(backup)
            if backup is not None
            else None
        ),
        "snapshot": relative_path(
            snapshot
        ),
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
        / f"{run_id}__build.json",
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
            "Safely extend the authoritative Masterplan graph "
            "without rebuilding authority from its Markdown projection."
        )
    )

    parser.add_argument(
        "--strict",
        action="store_true",
    )

    parser.add_argument(
        "--plan",
        action="store_true",
    )

    parser.add_argument(
        "--create-seed",
        action="store_true",
    )

    arguments = parser.parse_args()

    try:
        if arguments.create_seed:
            create_seed_if_missing()

        graph, metadata = build_graph()

        if arguments.plan:
            result = {
                "operation": (
                    "plan_authoritative_task_graph_build"
                ),
                "passed": metadata[
                    "preservation"
                ][
                    "passed"
                ],
                "generated_at": utc_now(),
                "metadata": metadata,
                "statistics": {
                    "record_count": len(
                        graph.get(
                            "records",
                            [],
                        )
                    ),
                    "segue_count": len(
                        graph.get(
                            "segues",
                            [],
                        )
                    ),
                    **{
                        (
                            f"{collection[:-1]}_count"
                            if collection.endswith(
                                "s"
                            )
                            else f"{collection}_count"
                        ): len(
                            graph.get(
                                collection,
                                [],
                            )
                        )
                        for collection
                        in COLLECTION_NAMES
                    },
                },
            }

        else:
            result = persist_graph(
                graph,
                metadata,
            )

    except Exception as exc:
        print(
            json.dumps(
                {
                    "operation": (
                        "build_authoritative_task_graph"
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

    if (
        arguments.strict
        and not result[
            "passed"
        ]
    ):
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
