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

DECISION_ROOT = (
    ROOT
    / "authority"
    / "task-graph"
    / "decisions"
)

EVENT_ROOT = (
    ROOT
    / "authority"
    / "task-graph"
    / "events"
)

RECEIPT_ROOT = (
    ROOT
    / "authority"
    / "task-graph"
    / "receipts"
)

SNAPSHOT_ROOT = (
    ROOT
    / "authority"
    / "task-graph"
    / "snapshots"
)

BACKUP_ROOT = (
    ROOT
    / "backups"
    / "masterplan"
    / "decision-application"
)

TRANSACTION_ROOT = (
    ROOT
    / "runtime"
    / "masterplan"
    / "decision-application"
)

REPORT_ROOT = (
    ROOT
    / "reports"
    / "niche"
    / "masterplan"
    / "decision-application"
)

ACCEPTED_AUTHORITY_STATES = {
    "accepted",
    "authoritative",
}

DECISION_STATUS_MAP = {
    "accept_task": "accepted",
    "reject_task": "rejected",
    "pause_task": "paused",
    "resume_task": "active",
    "cancel_task": "cancelled",
    "reopen_task": "reopened",
    "supersede_task": "superseded",
    "approve_parallel_work": None,
    "override_priority": None,
    "approve_dependency_change": None,
    "approve_scope_change": None,
    "approve_output_change": None,
    "approve_authority_change": None,
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


def decision_map(
    graph: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    decisions = graph.get(
        "decisions",
        [],
    )

    if not isinstance(decisions, list):
        raise ValueError(
            "Task graph decisions are invalid."
        )

    result: dict[str, dict[str, Any]] = {}

    for decision in decisions:
        if not isinstance(decision, dict):
            raise ValueError(
                "Task graph contains an invalid decision."
            )

        identifier = decision.get(
            "id"
        )

        if not isinstance(identifier, str):
            raise ValueError(
                "Decision identifier is missing."
            )

        if identifier in result:
            raise ValueError(
                f"Duplicate decision: {identifier}"
            )

        result[identifier] = decision

    return result


def application_exists(
    graph: dict[str, Any],
    decision_id: str,
) -> bool:
    events = graph.get(
        "events",
        [],
    )

    if not isinstance(events, list):
        raise ValueError(
            "Task graph events are invalid."
        )

    return any(
        isinstance(event, dict)
        and (
            event.get(
                "extensions",
                {}
            )
            or {}
        ).get(
            "decision_id"
        )
        == decision_id
        and event.get(
            "event_type"
        )
        == "task.decision.applied"
        for event in events
    )


def accepted_decision(
    graph: dict[str, Any],
    decision_id: str,
) -> dict[str, Any]:
    decisions = decision_map(
        graph
    )

    if decision_id not in decisions:
        raise KeyError(
            f"Unknown decision: {decision_id}"
        )

    decision = decisions[
        decision_id
    ]

    authority = decision.get(
        "authority"
    )

    if (
        not isinstance(authority, dict)
        or authority.get(
            "state"
        )
        not in ACCEPTED_AUTHORITY_STATES
    ):
        raise ValueError(
            "Decision authority is not accepted."
        )

    if application_exists(
        graph,
        decision_id,
    ):
        raise ValueError(
            f"Decision is already applied: {decision_id}"
        )

    return decision


def decision_payload(
    decision: dict[str, Any],
) -> dict[str, Any]:
    extensions = decision.get(
        "extensions"
    )

    if not isinstance(extensions, dict):
        return {}

    payload = extensions.get(
        "payload",
        {},
    )

    if not isinstance(payload, dict):
        raise ValueError(
            "Decision payload is invalid."
        )

    return payload


def replace_dependencies(
    graph: dict[str, Any],
    task_id: str,
    dependencies: list[str],
    decision: dict[str, Any],
) -> None:
    records = task_map(
        graph
    )

    unknown = sorted(
        set(dependencies)
        - set(records)
    )

    if unknown:
        raise ValueError(
            "Unknown dependency tasks: "
            + ", ".join(unknown)
        )

    if task_id in dependencies:
        raise ValueError(
            "Task cannot depend on itself."
        )

    segues = graph.get(
        "segues"
    )

    if not isinstance(segues, list):
        raise ValueError(
            "Task graph segues are invalid."
        )

    retained = [
        segue
        for segue in segues
        if not (
            isinstance(segue, dict)
            and segue.get(
                "type"
            )
            == "depends_on"
            and segue.get(
                "source"
            )
            == task_id
        )
    ]

    for dependency in sorted(
        set(dependencies)
    ):
        identifier = (
            "segue-"
            + digest(
                {
                    "type": "depends_on",
                    "source": task_id,
                    "target": dependency,
                    "decision_id": decision[
                        "id"
                    ],
                }
            )[:24]
        )

        retained.append(
            {
                "id": identifier,
                "type": "depends_on",
                "source": task_id,
                "target": dependency,
                "authority": decision[
                    "authority"
                ],
                "provenance": decision[
                    "provenance"
                ],
                "validity": {
                    "active": True,
                },
                "extensions": {
                    "decision_id": decision[
                        "id"
                    ],
                },
            }
        )

    graph["segues"] = sorted(
        retained,
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


def apply_mutation(
    graph: dict[str, Any],
    decision: dict[str, Any],
) -> dict[str, Any]:
    updated = json.loads(
        json.dumps(graph)
    )

    records = task_map(
        updated
    )

    task_id = decision.get(
        "subject"
    )

    if (
        not isinstance(task_id, str)
        or task_id not in records
    ):
        raise ValueError(
            "Decision subject is not a known task."
        )

    task = records[
        task_id
    ]

    decision_type = decision.get(
        "decision"
    )

    if decision_type not in DECISION_STATUS_MAP:
        raise ValueError(
            f"Unsupported decision type: {decision_type}"
        )

    payload = decision_payload(
        decision
    )

    previous = {
        "status": task.get(
            "status"
        ),
        "priority": json.loads(
            json.dumps(
                task.get(
                    "priority"
                )
            )
        ),
        "scope": json.loads(
            json.dumps(
                task.get(
                    "scope"
                )
            )
        ),
        "outputs": json.loads(
            json.dumps(
                task.get(
                    "outputs"
                )
            )
        ),
        "authority": json.loads(
            json.dumps(
                task.get(
                    "authority"
                )
            )
        ),
        "extensions": json.loads(
            json.dumps(
                task.get(
                    "extensions"
                )
            )
        ),
    }

    next_status = DECISION_STATUS_MAP[
        decision_type
    ]

    if next_status is not None:
        task[
            "status"
        ] = next_status

    if decision_type == "accept_task":
        task[
            "authority"
        ] = {
            **decision[
                "authority"
            ],
            "source": decision[
                "id"
            ],
        }

    elif decision_type == "override_priority":
        priority = payload.get(
            "priority"
        )

        if not isinstance(priority, dict):
            raise ValueError(
                "Priority override payload is missing."
            )

        current = task.get(
            "priority"
        )

        if not isinstance(current, dict):
            raise ValueError(
                "Task priority is invalid."
            )

        band = priority.get(
            "band"
        )

        ordinal = priority.get(
            "ordinal"
        )

        if (
            not isinstance(band, str)
            or not isinstance(
                ordinal,
                int,
            )
            or ordinal < 0
        ):
            raise ValueError(
                "Priority override is invalid."
            )

        task["priority"] = {
            **current,
            "band": band,
            "ordinal": ordinal,
            "authority_locked": bool(
                priority.get(
                    "authority_locked",
                    current.get(
                        "authority_locked",
                        False,
                    ),
                )
            ),
            "rationale": str(
                priority.get(
                    "rationale",
                    decision.get(
                        "rationale",
                        "",
                    ),
                )
            ),
        }

    elif decision_type == "approve_dependency_change":
        dependencies = payload.get(
            "dependencies"
        )

        if not isinstance(
            dependencies,
            list,
        ):
            raise ValueError(
                "Dependency payload is invalid."
            )

        replace_dependencies(
            updated,
            task_id,
            [
                str(value)
                for value in dependencies
            ],
            decision,
        )

        scope = task.setdefault(
            "scope",
            {},
        )

        if not isinstance(scope, dict):
            raise ValueError(
                "Task scope is invalid."
            )

        scope[
            "depends_on"
        ] = sorted(
            set(
                str(value)
                for value in dependencies
            )
        )

    elif decision_type == "approve_scope_change":
        scope = payload.get(
            "scope"
        )

        if not isinstance(scope, dict):
            raise ValueError(
                "Scope payload is invalid."
            )

        task[
            "scope"
        ] = scope

    elif decision_type == "approve_output_change":
        outputs = payload.get(
            "outputs"
        )

        if (
            not isinstance(outputs, list)
            or any(
                not isinstance(
                    value,
                    str,
                )
                for value in outputs
            )
        ):
            raise ValueError(
                "Output payload is invalid."
            )

        task[
            "outputs"
        ] = sorted(
            set(outputs)
        )

    elif decision_type == "approve_authority_change":
        authority = payload.get(
            "authority"
        )

        if not isinstance(authority, dict):
            raise ValueError(
                "Authority payload is invalid."
            )

        state = authority.get(
            "state"
        )

        if state not in {
            "unknown",
            "observed",
            "proposed",
            "accepted",
            "authoritative",
            "rejected",
            "superseded",
        }:
            raise ValueError(
                "Authority state is invalid."
            )

        if state in ACCEPTED_AUTHORITY_STATES:
            if (
                not authority.get(
                    "accepted_by"
                )
                or not authority.get(
                    "accepted_at"
                )
            ):
                raise ValueError(
                    "Accepted authority requires acceptance metadata."
                )

        task[
            "authority"
        ] = authority

    elif decision_type == "approve_parallel_work":
        extensions = task.setdefault(
            "extensions",
            {},
        )

        if not isinstance(
            extensions,
            dict,
        ):
            raise ValueError(
                "Task extensions are invalid."
            )

        extensions[
            "parallel_work"
        ] = {
            "approved": True,
            "decision_id": decision[
                "id"
            ],
            "payload": payload,
        }

    task_extensions = task.setdefault(
        "extensions",
        {},
    )

    if not isinstance(
        task_extensions,
        dict,
    ):
        raise ValueError(
            "Task extensions are invalid."
        )

    applied_decisions = task_extensions.setdefault(
        "applied_decisions",
        [],
    )

    if not isinstance(
        applied_decisions,
        list,
    ):
        raise ValueError(
            "Applied decision history is invalid."
        )

    applied_decisions.append(
        decision[
            "id"
        ]
    )

    current = {
        "status": task.get(
            "status"
        ),
        "priority": task.get(
            "priority"
        ),
        "scope": task.get(
            "scope"
        ),
        "outputs": task.get(
            "outputs"
        ),
        "authority": task.get(
            "authority"
        ),
        "extensions": task.get(
            "extensions"
        ),
    }

    return {
        "graph": updated,
        "task_id": task_id,
        "decision_type": decision_type,
        "before": previous,
        "after": current,
    }


def build_event(
    decision: dict[str, Any],
    mutation: dict[str, Any],
    graph_before: dict[str, Any],
) -> dict[str, Any]:
    occurred_at = utc_now()

    body = {
        "decision_id": decision[
            "id"
        ],
        "task_id": mutation[
            "task_id"
        ],
        "decision_type": mutation[
            "decision_type"
        ],
        "before": mutation[
            "before"
        ],
        "after": mutation[
            "after"
        ],
        "graph_digest_before": digest(
            deterministic_projection(
                graph_before
            )
        ),
    }

    return {
        "id": (
            "event-"
            + digest(body)[:24]
        ),
        "task_id": mutation[
            "task_id"
        ],
        "event_type": (
            "task.decision.applied"
        ),
        "previous_state": mutation[
            "before"
        ].get(
            "status"
        ),
        "next_state": mutation[
            "after"
        ].get(
            "status"
        ),
        "authority": decision[
            "authority"
        ],
        "occurred_at": occurred_at,
        "provenance": {
            "sources": [
                {
                    "source_id": decision[
                        "id"
                    ],
                    "source_kind": (
                        "masterplan-decision"
                    ),
                    "source_path": (
                        "authority/task-graph/decisions/"
                        f"{decision['id']}.json"
                    ),
                    "source_sha256": None,
                    "authority_state": (
                        decision[
                            "authority"
                        ][
                            "state"
                        ]
                    ),
                    "captured_at": occurred_at,
                }
            ],
            "transformations": [
                "validate_decision_authority",
                "validate_decision_not_applied",
                "apply_decision_mutation",
                "append_decision_application_event",
            ],
            "generated_by": (
                "prodigal.niche.masterplan."
                "apply_masterplan_decision"
            ),
            "generated_at": occurred_at,
            "contract_version": "1.0.0",
        },
        "extensions": {
            "decision_id": decision[
                "id"
            ],
            "decision_type": mutation[
                "decision_type"
            ],
            "before": mutation[
                "before"
            ],
            "after": mutation[
                "after"
            ],
        },
    }


def append_event(
    graph: dict[str, Any],
    event: dict[str, Any],
) -> None:
    events = graph.setdefault(
        "events",
        [],
    )

    if not isinstance(events, list):
        raise ValueError(
            "Task graph events are invalid."
        )

    if any(
        isinstance(existing, dict)
        and existing.get(
            "id"
        )
        == event[
            "id"
        ]
        for existing in events
    ):
        raise ValueError(
            f"Event already exists: {event['id']}"
        )

    events.append(
        event
    )


def build_receipt(
    decision: dict[str, Any],
    event: dict[str, Any],
    graph_before: dict[str, Any],
    graph_after: dict[str, Any],
) -> dict[str, Any]:
    occurred_at = utc_now()

    body = {
        "decision_id": decision[
            "id"
        ],
        "event_id": event[
            "id"
        ],
        "task_id": event[
            "task_id"
        ],
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
            "task.decision.apply"
        ),
        "passed": True,
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
            decision[
                "id"
            ],
            event[
                "id"
            ],
        ],
        "occurred_at": occurred_at,
        "provenance": event[
            "provenance"
        ],
        "extensions": body,
    }


def append_receipt(
    graph: dict[str, Any],
    receipt: dict[str, Any],
) -> None:
    receipts = graph.setdefault(
        "receipts",
        [],
    )

    if not isinstance(receipts, list):
        raise ValueError(
            "Task graph receipts are invalid."
        )

    receipts.append(
        receipt
    )


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
        "expected_sha256": expected,
        "actual_sha256": actual,
        "backup": relative_path(
            backup
        ),
        "graph": relative_path(
            GRAPH_PATH
        ),
    }


def persist(
    graph_before: dict[str, Any],
    graph_after: dict[str, Any],
    decision: dict[str, Any],
    event: dict[str, Any],
    receipt: dict[str, Any],
) -> dict[str, Any]:
    transaction_seed = {
        "decision_id": decision[
            "id"
        ],
        "event_id": event[
            "id"
        ],
        "receipt_id": receipt[
            "id"
        ],
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
        / "decision.json",
        decision,
    )

    atomic_write_json(
        transaction_root
        / "event.json",
        event,
    )

    atomic_write_json(
        transaction_root
        / "receipt.json",
        receipt,
    )

    atomic_write_json(
        transaction_root
        / "graph-proposed.json",
        graph_after,
    )

    rollback = None

    try:
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
                "Written graph digest mismatch."
            )

    except Exception:
        rollback = restore_graph(
            backup
        )

        raise

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
            "decision-application/1.0.0"
        ),
        "operation": (
            "apply_masterplan_decision"
        ),
        "generated_at": utc_now(),
        "passed": True,
        "decision": decision,
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
                    "graph_digest_before"
                ]
            ),
            "digest_after": (
                transaction_seed[
                    "graph_digest_after"
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
        / f"{transaction_id}__decision-application.json",
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
            "Apply an accepted Masterplan decision "
            "to authoritative task state."
        )
    )

    parser.add_argument(
        "decision_id",
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

        decision = accepted_decision(
            graph_before,
            arguments.decision_id,
        )

        mutation = apply_mutation(
            graph_before,
            decision,
        )

        graph_after = mutation[
            "graph"
        ]

        event = build_event(
            decision,
            mutation,
            graph_before,
        )

        append_event(
            graph_after,
            event,
        )

        receipt = build_receipt(
            decision,
            event,
            graph_before,
            graph_after,
        )

        append_receipt(
            graph_after,
            receipt,
        )

        if arguments.plan:
            result = {
                "schema": (
                    "savant://niche/masterplan/"
                    "decision-application-plan/1.0.0"
                ),
                "operation": (
                    "plan_masterplan_decision_application"
                ),
                "generated_at": utc_now(),
                "passed": True,
                "decision": decision,
                "mutation": {
                    key: value
                    for key, value
                    in mutation.items()
                    if key != "graph"
                },
                "event": event,
                "receipt": receipt,
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
                decision,
                event,
                receipt,
            )

    except Exception as exc:
        print(
            json.dumps(
                {
                    "operation": (
                        "apply_masterplan_decision"
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
