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

GRAPH_PATH = (
    ROOT
    / "authority"
    / "task-graph"
    / "masterplan.json"
)

SNAPSHOT_ROOT = (
    ROOT
    / "authority"
    / "task-graph"
    / "snapshots"
)

EVENT_ROOT = (
    ROOT
    / "authority"
    / "task-graph"
    / "events"
)

DECISION_ROOT = (
    ROOT
    / "authority"
    / "task-graph"
    / "decisions"
)

RECEIPT_ROOT = (
    ROOT
    / "authority"
    / "task-graph"
    / "receipts"
)

REPORT_ROOT = (
    ROOT
    / "reports"
    / "niche"
    / "masterplan"
    / "transitions"
)

TRANSACTION_ROOT = (
    ROOT
    / "runtime"
    / "masterplan"
    / "transactions"
)

BACKUP_ROOT = (
    ROOT
    / "backups"
    / "masterplan"
    / "task-graph"
)

LEGAL_TRANSITIONS: dict[str, frozenset[str]] = {
    "unknown": frozenset(
        {
            "proposed",
        }
    ),
    "proposed": frozenset(
        {
            "accepted",
            "rejected",
            "superseded",
        }
    ),
    "accepted": frozenset(
        {
            "ready",
            "active",
            "blocked",
            "paused",
            "rejected",
            "cancelled",
            "superseded",
        }
    ),
    "ready": frozenset(
        {
            "active",
            "blocked",
            "paused",
            "cancelled",
            "superseded",
        }
    ),
    "active": frozenset(
        {
            "blocked",
            "paused",
            "completed",
            "cancelled",
            "superseded",
        }
    ),
    "blocked": frozenset(
        {
            "ready",
            "active",
            "paused",
            "cancelled",
            "superseded",
        }
    ),
    "paused": frozenset(
        {
            "ready",
            "active",
            "blocked",
            "cancelled",
            "superseded",
        }
    ),
    "completed": frozenset(
        {
            "reopened",
            "archived",
        }
    ),
    "reopened": frozenset(
        {
            "ready",
            "active",
            "blocked",
            "paused",
            "cancelled",
            "superseded",
        }
    ),
    "rejected": frozenset(
        {
            "archived",
        }
    ),
    "cancelled": frozenset(
        {
            "reopened",
            "archived",
        }
    ),
    "superseded": frozenset(
        {
            "archived",
        }
    ),
    "archived": frozenset(),
}

ACCEPTED_AUTHORITY_STATES = {
    "accepted",
    "authoritative",
}

COMPLETION_STATES = {
    "completed",
    "archived",
    "superseded",
}

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
                "Task graph contains an invalid record."
            )

        identifier = record.get(
            "id"
        )

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


def dependency_ids(
    graph: dict[str, Any],
    task_id: str,
) -> tuple[str, ...]:
    values: set[str] = set()

    for segue in graph.get(
        "segues",
        [],
    ):
        if not isinstance(segue, dict):
            continue

        if (
            segue.get("type")
            == "depends_on"
            and segue.get("source")
            == task_id
            and isinstance(
                segue.get("target"),
                str,
            )
        ):
            values.add(
                segue["target"]
            )

    return tuple(
        sorted(values)
    )


def unresolved_dependencies(
    graph: dict[str, Any],
    task_id: str,
) -> tuple[str, ...]:
    records = task_map(
        graph
    )

    unresolved: list[str] = []

    for dependency_id in dependency_ids(
        graph,
        task_id,
    ):
        dependency = records.get(
            dependency_id
        )

        if (
            dependency is None
            or dependency.get("status")
            not in COMPLETION_STATES
        ):
            unresolved.append(
                dependency_id
            )

    return tuple(
        sorted(unresolved)
    )


def passing_attestation_exists(
    graph: dict[str, Any],
    task_id: str,
) -> bool:
    attestations = graph.get(
        "attestations",
        [],
    )

    if not isinstance(
        attestations,
        list,
    ):
        return False

    return any(
        isinstance(attestation, dict)
        and attestation.get("task_id")
        == task_id
        and attestation.get("passed")
        is True
        for attestation in attestations
    )


def accepted_decision_exists(
    graph: dict[str, Any],
    decision_id: str,
) -> bool:
    decisions = graph.get(
        "decisions",
        [],
    )

    if not isinstance(
        decisions,
        list,
    ):
        return False

    for decision in decisions:
        if not isinstance(
            decision,
            dict,
        ):
            continue

        if decision.get("id") != decision_id:
            continue

        authority = decision.get(
            "authority"
        )

        return (
            isinstance(authority, dict)
            and authority.get("state")
            in ACCEPTED_AUTHORITY_STATES
        )

    return False


def validate_transition(
    graph: dict[str, Any],
    task_id: str,
    next_state: str,
    *,
    decision_id: str | None,
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

    previous_state = str(
        task.get(
            "status",
            "unknown",
        )
    )

    if next_state not in LEGAL_TRANSITIONS:
        raise ValueError(
            f"Unknown task state: {next_state}"
        )

    if next_state not in LEGAL_TRANSITIONS.get(
        previous_state,
        frozenset(),
    ):
        raise ValueError(
            (
                "Illegal task transition: "
                f"{previous_state}->{next_state}"
            )
        )

    authority = task.get(
        "authority"
    )

    authority_state = (
        authority.get(
            "state"
        )
        if isinstance(
            authority,
            dict,
        )
        else None
    )

    checks = {
        "legal_transition": True,
        "accepted_authority": (
            authority_state
            in ACCEPTED_AUTHORITY_STATES
        ),
        "dependencies_satisfied": True,
        "completion_attested": True,
        "decision_admitted": True,
    }

    unresolved = ()

    if next_state in {
        "ready",
        "active",
        "completed",
    }:
        unresolved = unresolved_dependencies(
            graph,
            task_id,
        )

        checks[
            "dependencies_satisfied"
        ] = not unresolved

    if next_state == "completed":
        checks[
            "completion_attested"
        ] = passing_attestation_exists(
            graph,
            task_id,
        )

    if decision_id is not None:
        checks[
            "decision_admitted"
        ] = accepted_decision_exists(
            graph,
            decision_id,
        )

    return {
        "passed": all(
            checks.values()
        ),
        "task_id": task_id,
        "previous_state": previous_state,
        "next_state": next_state,
        "authority_state": authority_state,
        "unresolved_dependencies": unresolved,
        "decision_id": decision_id,
        "checks": checks,
    }


def build_event(
    graph: dict[str, Any],
    validation: dict[str, Any],
    *,
    actor: str,
    rationale: str,
    decision_id: str | None,
) -> dict[str, Any]:
    occurred_at = utc_now()

    body = {
        "task_id": validation[
            "task_id"
        ],
        "event_type": (
            "task.status.transition"
        ),
        "previous_state": validation[
            "previous_state"
        ],
        "next_state": validation[
            "next_state"
        ],
        "actor": actor,
        "rationale": rationale,
        "decision_id": decision_id,
        "graph_digest_before": digest(
            deterministic_projection(
                graph
            )
        ),
    }

    event_id = (
        "event-"
        + digest(body)[:24]
    )

    return {
        "id": event_id,
        "task_id": validation[
            "task_id"
        ],
        "event_type": (
            "task.status.transition"
        ),
        "previous_state": validation[
            "previous_state"
        ],
        "next_state": validation[
            "next_state"
        ],
        "authority": {
            "state": "accepted",
            "authority_class": (
                "project-owner-directed"
            ),
            "tier": 1,
            "source": (
                decision_id
                or "masterplan-transition"
            ),
            "accepted_by": actor,
            "accepted_at": occurred_at,
            "confidence": 1.0,
        },
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
                }
            ],
            "transformations": [
                (
                    "validate_legal_transition"
                ),
                (
                    "validate_dependency_state"
                ),
                (
                    "validate_completion_attestation"
                ),
                (
                    "append_immutable_task_event"
                ),
            ],
            "generated_by": (
                "prodigal.niche.masterplan."
                "apply_masterplan_transition"
            ),
            "generated_at": occurred_at,
            "contract_version": "1.0.0",
        },
        "extensions": {
            "actor": actor,
            "rationale": rationale,
            "decision_id": decision_id,
            "validation": validation,
        },
    }


def apply_event(
    graph: dict[str, Any],
    event: dict[str, Any],
) -> dict[str, Any]:
    updated = json.loads(
        json.dumps(graph)
    )

    records = task_map(
        updated
    )

    task = records[
        event["task_id"]
    ]

    task[
        "status"
    ] = event[
        "next_state"
    ]

    events = updated.setdefault(
        "events",
        [],
    )

    if not isinstance(events, list):
        raise ValueError(
            "Task graph event collection is invalid."
        )

    existing_ids = {
        value.get("id")
        for value in events
        if isinstance(value, dict)
    }

    if event["id"] in existing_ids:
        raise ValueError(
            f"Duplicate event: {event['id']}"
        )

    events.append(
        event
    )

    return updated


def backup_graph(
    transaction_id: str,
) -> Path:
    destination = (
        BACKUP_ROOT
        / transaction_id
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
            "Task graph backup hash mismatch."
        )

    return destination


def restore_graph(
    backup: Path,
) -> dict[str, Any]:
    if not backup.is_file():
        return {
            "passed": False,
            "reason": (
                "backup is missing"
            ),
        }

    shutil.copy2(
        backup,
        GRAPH_PATH,
    )

    expected = sha256_path(
        backup
    )

    actual = sha256_path(
        GRAPH_PATH
    )

    return {
        "passed": (
            expected == actual
        ),
        "backup": relative_path(
            backup
        ),
        "graph": relative_path(
            GRAPH_PATH
        ),
        "expected_sha256": expected,
        "actual_sha256": actual,
    }


def build_receipt(
    event: dict[str, Any],
    graph_before: dict[str, Any],
    graph_after: dict[str, Any],
    *,
    passed: bool,
) -> dict[str, Any]:
    occurred_at = utc_now()

    body = {
        "task_id": event[
            "task_id"
        ],
        "event_id": event[
            "id"
        ],
        "previous_state": event[
            "previous_state"
        ],
        "next_state": event[
            "next_state"
        ],
        "passed": passed,
        "graph_digest_before": digest(
            deterministic_projection(
                graph_before
            )
        ),
        "graph_digest_after": digest(
            deterministic_projection(
                graph_after
            )
        ),
    }

    return {
        "id": (
            "receipt-"
            + digest(body)[:24]
        ),
        "task_id": event[
            "task_id"
        ],
        "operation": (
            "task.status.transition"
        ),
        "passed": passed,
        "outputs": [
            relative_path(
                GRAPH_PATH
            ),
            (
                "authority/task-graph/events/"
                f"{event['id']}.json"
            ),
        ],
        "evidence": [
            event[
                "id"
            ]
        ],
        "occurred_at": occurred_at,
        "provenance": event[
            "provenance"
        ],
        "extensions": body,
    }


def persist_transition(
    graph_before: dict[str, Any],
    graph_after: dict[str, Any],
    event: dict[str, Any],
) -> dict[str, Any]:
    transaction_seed = {
        "event": event,
        "graph_before": digest(
            deterministic_projection(
                graph_before
            )
        ),
        "graph_after": digest(
            deterministic_projection(
                graph_after
            )
        ),
    }

    transaction_id = (
        f"{timestamp()}__"
        f"{digest(transaction_seed)[:16]}"
    )

    transaction_root = (
        TRANSACTION_ROOT
        / transaction_id
    )

    transaction_root.mkdir(
        parents=True,
        exist_ok=False,
    )

    backup = backup_graph(
        transaction_id
    )

    atomic_write_json(
        transaction_root
        / "graph-before.json",
        graph_before,
    )

    atomic_write_json(
        transaction_root
        / "event.json",
        event,
    )

    atomic_write_json(
        transaction_root
        / "graph-proposed.json",
        graph_after,
    )

    rollback: dict[str, Any] | None = None
    passed = False

    try:
        atomic_write_json(
            GRAPH_PATH,
            graph_after,
        )

        written = load_json(
            GRAPH_PATH
        )

        passed = (
            digest(
                deterministic_projection(
                    written
                )
            )
            == digest(
                deterministic_projection(
                    graph_after
                )
            )
        )

        if not passed:
            raise RuntimeError(
                "Written task graph digest mismatch."
            )

    except Exception:
        rollback = restore_graph(
            backup
        )

        raise

    receipt = build_receipt(
        event,
        graph_before,
        graph_after,
        passed=passed,
    )

    EVENT_ROOT.mkdir(
        parents=True,
        exist_ok=True,
    )

    RECEIPT_ROOT.mkdir(
        parents=True,
        exist_ok=True,
    )

    atomic_write_json(
        EVENT_ROOT
        / f"{event['id']}.json",
        event,
    )

    atomic_write_json(
        RECEIPT_ROOT
        / f"{receipt['id']}.json",
        receipt,
    )

    SNAPSHOT_ROOT.mkdir(
        parents=True,
        exist_ok=True,
    )

    snapshot = (
        SNAPSHOT_ROOT
        / f"{transaction_id}__masterplan.json"
    )

    atomic_write_json(
        snapshot,
        graph_after,
    )

    result: dict[str, Any] = {
        "schema": (
            "savant://niche/masterplan/"
            "task-transition/1.0.0"
        ),
        "operation": (
            "apply_masterplan_transition"
        ),
        "generated_at": utc_now(),
        "passed": passed,
        "event": event,
        "receipt": receipt,
        "graph": {
            "path": relative_path(
                GRAPH_PATH
            ),
            "sha256": sha256_path(
                GRAPH_PATH
            ),
            "digest_before": (
                transaction_seed[
                    "graph_before"
                ]
            ),
            "digest_after": (
                transaction_seed[
                    "graph_after"
                ]
            ),
        },
        "transaction": {
            "id": transaction_id,
            "root": relative_path(
                transaction_root
            ),
            "backup": relative_path(
                backup
            ),
            "snapshot": relative_path(
                snapshot
            ),
        },
        "rollback": rollback,
    }

    result[
        "digest"
    ] = digest(
        deterministic_projection(
            result
        )
    )

    atomic_write_json(
        transaction_root
        / "result.json",
        result,
    )

    REPORT_ROOT.mkdir(
        parents=True,
        exist_ok=True,
    )

    atomic_write_json(
        REPORT_ROOT
        / f"{transaction_id}__transition.json",
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
            "Apply an admitted, validated, immutable "
            "Masterplan task-state transition."
        )
    )

    parser.add_argument(
        "task_id",
    )

    parser.add_argument(
        "next_state",
    )

    parser.add_argument(
        "--actor",
        required=True,
    )

    parser.add_argument(
        "--rationale",
        required=True,
    )

    parser.add_argument(
        "--decision-id",
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
        if not GRAPH_PATH.is_file():
            raise FileNotFoundError(
                GRAPH_PATH
            )

        graph_before = load_json(
            GRAPH_PATH
        )

        validation = validate_transition(
            graph_before,
            arguments.task_id,
            arguments.next_state,
            decision_id=(
                arguments.decision_id
            ),
        )

        event = build_event(
            graph_before,
            validation,
            actor=arguments.actor,
            rationale=arguments.rationale,
            decision_id=(
                arguments.decision_id
            ),
        )

        graph_after = apply_event(
            graph_before,
            event,
        )

        if arguments.plan:
            result = {
                "schema": (
                    "savant://niche/masterplan/"
                    "task-transition-plan/1.0.0"
                ),
                "operation": (
                    "plan_masterplan_transition"
                ),
                "generated_at": utc_now(),
                "passed": validation[
                    "passed"
                ],
                "validation": validation,
                "event": event,
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
            if not validation[
                "passed"
            ]:
                raise RuntimeError(
                    json.dumps(
                        validation,
                        ensure_ascii=False,
                        sort_keys=True,
                    )
                )

            result = persist_transition(
                graph_before,
                graph_after,
                event,
            )

    except Exception as exc:
        print(
            json.dumps(
                {
                    "operation": (
                        "apply_masterplan_transition"
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
