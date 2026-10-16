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

ATTESTATION_ROOT = (
    ROOT
    / "authority"
    / "task-graph"
    / "attestations"
)

SNAPSHOT_ROOT = (
    ROOT
    / "authority"
    / "task-graph"
    / "snapshots"
)

REPORT_ROOT = (
    ROOT
    / "reports"
    / "niche"
    / "masterplan"
    / "attestations"
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
            lambda: handle.read(1024 * 1024),
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
                "Task identifier is missing."
            )

        result[identifier] = record

    return result


def evidence_for_task(
    graph: dict[str, Any],
    task_id: str,
) -> list[dict[str, Any]]:
    evidence = graph.get(
        "evidence",
        [],
    )

    if not isinstance(evidence, list):
        raise ValueError(
            "Task graph evidence collection is invalid."
        )

    return sorted(
        (
            record
            for record in evidence
            if (
                isinstance(record, dict)
                and record.get("task_id")
                == task_id
            )
        ),
        key=lambda record: str(
            record.get(
                "id",
                "",
            )
        ),
    )


def required_evidence(
    task: dict[str, Any],
) -> list[dict[str, Any]]:
    requirements = task.get(
        "evidence_requirements",
        [],
    )

    if not isinstance(
        requirements,
        list,
    ):
        raise ValueError(
            "Task evidence requirements are invalid."
        )

    return [
        requirement
        for requirement in requirements
        if (
            isinstance(requirement, dict)
            and requirement.get("required")
            is True
        )
    ]


def criterion_results(
    task: dict[str, Any],
    evidence: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    results: list[
        dict[str, Any]
    ] = []

    evidence_by_kind: dict[
        str,
        list[dict[str, Any]],
    ] = {}

    for record in evidence:
        kind = str(
            record.get(
                "kind",
                "",
            )
        )

        evidence_by_kind.setdefault(
            kind,
            [],
        ).append(record)

    for requirement in required_evidence(
        task
    ):
        kind = str(
            requirement.get(
                "kind",
                "",
            )
        )

        matches = evidence_by_kind.get(
            kind,
            [],
        )

        accepted_matches = [
            record
            for record in matches
            if (
                isinstance(
                    record.get(
                        "authority"
                    ),
                    dict,
                )
                and record[
                    "authority"
                ].get(
                    "state"
                )
                in {
                    "accepted",
                    "authoritative",
                }
                and record.get(
                    "passed"
                )
                is not False
            )
        ]

        results.append(
            {
                "criterion": (
                    requirement.get(
                        "acceptance",
                        kind,
                    )
                ),
                "passed": bool(
                    accepted_matches
                ),
                "evidence": [
                    record[
                        "id"
                    ]
                    for record in accepted_matches
                    if isinstance(
                        record.get(
                            "id"
                        ),
                        str,
                    )
                ],
                "reason": (
                    ""
                    if accepted_matches
                    else (
                        "No accepted passing evidence "
                        f"exists for kind: {kind}"
                    )
                ),
            }
        )

    acceptance = task.get(
        "acceptance",
        [],
    )

    if not isinstance(
        acceptance,
        list,
    ):
        acceptance = []

    accepted_general_evidence = [
        record
        for record in evidence
        if (
            isinstance(
                record.get(
                    "authority"
                ),
                dict,
            )
            and record[
                "authority"
            ].get(
                "state"
            )
            in {
                "accepted",
                "authoritative",
            }
            and record.get(
                "passed"
            )
            is not False
        )
    ]

    for criterion in acceptance:
        results.append(
            {
                "criterion": str(
                    criterion
                ),
                "passed": bool(
                    accepted_general_evidence
                ),
                "evidence": [
                    record[
                        "id"
                    ]
                    for record
                    in accepted_general_evidence
                    if isinstance(
                        record.get(
                            "id"
                        ),
                        str,
                    )
                ],
                "reason": (
                    ""
                    if accepted_general_evidence
                    else (
                        "No accepted passing evidence "
                        "is attached to the task."
                    )
                ),
            }
        )

    return results


def build_attestation(
    graph: dict[str, Any],
    *,
    task_id: str,
    actor: str,
    notes: str,
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

    authority = task.get(
        "authority"
    )

    if (
        not isinstance(
            authority,
            dict,
        )
        or authority.get(
            "state"
        )
        not in {
            "accepted",
            "authoritative",
        }
    ):
        raise ValueError(
            "Task authority is not accepted."
        )

    evidence = evidence_for_task(
        graph,
        task_id,
    )

    criteria = criterion_results(
        task,
        evidence,
    )

    passed = (
        bool(criteria)
        and all(
            criterion[
                "passed"
            ]
            for criterion in criteria
        )
    )

    occurred_at = utc_now()

    evidence_ids = sorted(
        {
            record[
                "id"
            ]
            for record in evidence
            if isinstance(
                record.get(
                    "id"
                ),
                str,
            )
        }
    )

    attestation_body = {
        "task_id": task_id,
        "passed": passed,
        "criteria": criteria,
        "evidence": evidence_ids,
        "actor": actor,
        "notes": notes,
        "graph_digest": digest(
            deterministic_projection(
                graph
            )
        ),
    }

    attestation_digest = digest(
        attestation_body
    )

    return {
        "id": (
            "attestation-"
            + attestation_digest[:24]
        ),
        "task_id": task_id,
        "passed": passed,
        "criteria": criteria,
        "evidence": evidence_ids,
        "digest": attestation_digest,
        "occurred_at": occurred_at,
        "provenance": {
            "sources": [
                {
                    "source_id": relative_path(
                        GRAPH_PATH
                    ),
                    "source_kind": (
                        "authoritative-task-graph"
                    ),
                    "source_path": relative_path(
                        GRAPH_PATH
                    ),
                    "source_sha256": sha256_path(
                        GRAPH_PATH
                    ),
                    "authority_state": (
                        "authoritative"
                    ),
                    "captured_at": occurred_at,
                },
                *[
                    {
                        "source_id": record[
                            "id"
                        ],
                        "source_kind": (
                            record.get(
                                "kind",
                                "task-evidence",
                            )
                        ),
                        "source_path": record.get(
                            "path"
                        ),
                        "source_sha256": record.get(
                            "sha256"
                        ),
                        "authority_state": (
                            (
                                record.get(
                                    "authority"
                                )
                                or {}
                            ).get(
                                "state",
                                "unknown",
                            )
                        ),
                        "captured_at": occurred_at,
                    }
                    for record in evidence
                ],
            ],
            "transformations": [
                "resolve_task_acceptance",
                "resolve_required_evidence",
                "validate_evidence_authority",
                "evaluate_completion_criteria",
                "emit_deterministic_attestation",
            ],
            "generated_by": (
                "prodigal.niche.masterplan."
                "build_masterplan_attestation"
            ),
            "generated_at": occurred_at,
            "contract_version": "1.0.0",
        },
        "extensions": {
            "actor": actor,
            "notes": notes,
            "task_status": task.get(
                "status"
            ),
            "task_authority": authority,
        },
    }


def attestation_exists(
    graph: dict[str, Any],
    attestation_id: str,
) -> bool:
    attestations = graph.get(
        "attestations",
        [],
    )

    if not isinstance(
        attestations,
        list,
    ):
        raise ValueError(
            "Task graph attestation collection is invalid."
        )

    return any(
        isinstance(record, dict)
        and record.get("id")
        == attestation_id
        for record in attestations
    )


def append_attestation(
    graph: dict[str, Any],
    attestation: dict[str, Any],
) -> dict[str, Any]:
    if attestation_exists(
        graph,
        attestation[
            "id"
        ],
    ):
        raise ValueError(
            (
                "Attestation already exists: "
                f"{attestation['id']}"
            )
        )

    updated = json.loads(
        json.dumps(graph)
    )

    collection = updated.setdefault(
        "attestations",
        [],
    )

    if not isinstance(
        collection,
        list,
    ):
        raise ValueError(
            "Task graph attestation collection is invalid."
        )

    collection.append(
        attestation
    )

    return updated


def persist(
    graph_before: dict[str, Any],
    graph_after: dict[str, Any],
    attestation: dict[str, Any],
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

    ATTESTATION_ROOT.mkdir(
        parents=True,
        exist_ok=True,
    )

    attestation_path = (
        ATTESTATION_ROOT
        / f"{attestation['id']}.json"
    )

    atomic_write_json(
        attestation_path,
        attestation,
    )

    SNAPSHOT_ROOT.mkdir(
        parents=True,
        exist_ok=True,
    )

    run_id = (
        f"{timestamp()}__"
        f"{attestation['id']}"
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
            "task-attestation/1.0.0"
        ),
        "operation": (
            "build_masterplan_attestation"
        ),
        "generated_at": utc_now(),
        "passed": attestation[
            "passed"
        ],
        "attestation": attestation,
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
            "attestation": relative_path(
                attestation_path
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
        / f"{run_id}__attestation.json",
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
            "Build and admit a deterministic task "
            "completion attestation."
        )
    )

    parser.add_argument(
        "task_id",
    )

    parser.add_argument(
        "--actor",
        required=True,
    )

    parser.add_argument(
        "--notes",
        default="",
    )

    parser.add_argument(
        "--plan",
        action="store_true",
    )

    parser.add_argument(
        "--strict",
        action="store_true",
    )

    arguments = parser.parse_args()

    try:
        graph_before = load_json(
            GRAPH_PATH
        )

        attestation = build_attestation(
            graph_before,
            task_id=arguments.task_id,
            actor=arguments.actor,
            notes=arguments.notes,
        )

        graph_after = append_attestation(
            graph_before,
            attestation,
        )

        if arguments.plan:
            result = {
                "schema": (
                    "savant://niche/masterplan/"
                    "task-attestation-plan/1.0.0"
                ),
                "operation": (
                    "plan_masterplan_attestation"
                ),
                "generated_at": utc_now(),
                "passed": attestation[
                    "passed"
                ],
                "attestation": attestation,
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
            if (
                arguments.strict
                and not attestation[
                    "passed"
                ]
            ):
                raise RuntimeError(
                    json.dumps(
                        attestation,
                        ensure_ascii=False,
                        sort_keys=True,
                    )
                )

            result = persist(
                graph_before,
                graph_after,
                attestation,
            )

    except Exception as exc:
        print(
            json.dumps(
                {
                    "operation": (
                        "build_masterplan_attestation"
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
    raise SystemExit(
        main()
    )
