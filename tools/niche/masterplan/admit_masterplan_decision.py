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
    / "decisions"
)

TRANSACTION_ROOT = (
    ROOT
    / "runtime"
    / "masterplan"
    / "decision-transactions"
)

REPORT_ROOT = (
    ROOT
    / "reports"
    / "niche"
    / "masterplan"
    / "decisions"
)

ACCEPTED_AUTHORITY_STATES = {
    "accepted",
    "authoritative",
}

ALLOWED_DECISION_TYPES = {
    "accept_task",
    "reject_task",
    "override_priority",
    "pause_task",
    "resume_task",
    "cancel_task",
    "reopen_task",
    "supersede_task",
    "approve_parallel_work",
    "approve_dependency_change",
    "approve_scope_change",
    "approve_output_change",
    "approve_authority_change",
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


def decision_exists(
    graph: dict[str, Any],
    decision_id: str,
) -> bool:
    decisions = graph.get(
        "decisions",
        [],
    )

    if not isinstance(decisions, list):
        raise ValueError(
            "Task graph decisions are invalid."
        )

    return any(
        isinstance(decision, dict)
        and decision.get("id")
        == decision_id
        for decision in decisions
    )


def validate_request(
    graph: dict[str, Any],
    *,
    subject: str,
    decision_type: str,
    actor: str,
    authority_state: str,
    rationale: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    records = task_map(graph)

    if subject not in records:
        raise KeyError(
            f"Unknown task: {subject}"
        )

    if decision_type not in ALLOWED_DECISION_TYPES:
        raise ValueError(
            f"Unsupported decision type: {decision_type}"
        )

    if authority_state not in ACCEPTED_AUTHORITY_STATES:
        raise ValueError(
            "Decision authority must be accepted or authoritative."
        )

    if not actor.strip():
        raise ValueError(
            "Decision actor is required."
        )

    if not rationale.strip():
        raise ValueError(
            "Decision rationale is required."
        )

    task = records[subject]

    checks = {
        "subject_exists": True,
        "decision_type_allowed": True,
        "authority_accepted": True,
        "actor_present": True,
        "rationale_present": True,
        "payload_valid": True,
    }

    if decision_type == "override_priority":
        priority = payload.get(
            "priority"
        )

        if not isinstance(priority, dict):
            checks[
                "payload_valid"
            ] = False

        else:
            band = priority.get(
                "band"
            )

            ordinal = priority.get(
                "ordinal"
            )

            if (
                not isinstance(band, str)
                or not band.startswith("P")
                or not isinstance(
                    ordinal,
                    int,
                )
                or ordinal < 0
            ):
                checks[
                    "payload_valid"
                ] = False

    if decision_type == "approve_dependency_change":
        dependencies = payload.get(
            "dependencies"
        )

        if not isinstance(
            dependencies,
            list,
        ):
            checks[
                "payload_valid"
            ] = False

        elif any(
            dependency not in records
            for dependency in dependencies
        ):
            checks[
                "payload_valid"
            ] = False

    if decision_type == "approve_output_change":
        outputs = payload.get(
            "outputs"
        )

        if (
            not isinstance(outputs, list)
            or any(
                not isinstance(
                    output,
                    str,
                )
                for output in outputs
            )
        ):
            checks[
                "payload_valid"
            ] = False

    if decision_type == "approve_scope_change":
        scope = payload.get(
            "scope"
        )

        if not isinstance(scope, dict):
            checks[
                "payload_valid"
            ] = False

    if decision_type == "approve_authority_change":
        authority = payload.get(
            "authority"
        )

        if not isinstance(authority, dict):
            checks[
                "payload_valid"
            ] = False

    return {
        "passed": all(
            checks.values()
        ),
        "subject": subject,
        "task_status": task.get(
            "status"
        ),
        "task_authority": task.get(
            "authority"
        ),
        "decision_type": decision_type,
        "actor": actor,
        "authority_state": authority_state,
        "rationale": rationale,
        "payload": payload,
        "checks": checks,
    }


def build_decision(
    graph: dict[str, Any],
    validation: dict[str, Any],
) -> dict[str, Any]:
    occurred_at = utc_now()

    body = {
        "subject": validation[
            "subject"
        ],
        "decision_type": validation[
            "decision_type"
        ],
        "actor": validation[
            "actor"
        ],
        "authority_state": validation[
            "authority_state"
        ],
        "rationale": validation[
            "rationale"
        ],
        "payload": validation[
            "payload"
        ],
        "graph_digest": digest(
            deterministic_projection(
                graph
            )
        ),
    }

    decision_id = (
        "decision-"
        + digest(body)[:24]
    )

    if decision_exists(
        graph,
        decision_id,
    ):
        raise ValueError(
            f"Decision already exists: {decision_id}"
        )

    return {
        "id": decision_id,
        "subject": validation[
            "subject"
        ],
        "decision": validation[
            "decision_type"
        ],
        "authority": {
            "state": validation[
                "authority_state"
            ],
            "authority_class": (
                "project-owner-directed"
            ),
            "tier": 0,
            "source": (
                "masterplan-decision"
            ),
            "accepted_by": validation[
                "actor"
            ],
            "accepted_at": occurred_at,
            "confidence": 1.0,
        },
        "rationale": validation[
            "rationale"
        ],
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
                "validate_decision_request",
                "admit_project_owner_decision",
                "append_immutable_decision",
            ],
            "generated_by": (
                "prodigal.niche.masterplan."
                "admit_masterplan_decision"
            ),
            "generated_at": occurred_at,
            "contract_version": "1.0.0",
        },
        "extensions": {
            "decision_type": validation[
                "decision_type"
            ],
            "payload": validation[
                "payload"
            ],
            "validation": validation,
        },
    }


def append_decision(
    graph: dict[str, Any],
    decision: dict[str, Any],
) -> dict[str, Any]:
    updated = json.loads(
        json.dumps(graph)
    )

    decisions = updated.setdefault(
        "decisions",
        [],
    )

    if not isinstance(decisions, list):
        raise ValueError(
            "Task graph decisions are invalid."
        )

    decisions.append(
        decision
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


def persist_decision(
    graph_before: dict[str, Any],
    graph_after: dict[str, Any],
    decision: dict[str, Any],
) -> dict[str, Any]:
    transaction_seed = {
        "decision": decision,
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
        / "graph-proposed.json",
        graph_after,
    )

    rollback: dict[str, Any] | None = None

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
                "Written graph digest mismatch."
            )

    except Exception:
        rollback = restore_graph(
            backup
        )

        raise

    DECISION_ROOT.mkdir(
        parents=True,
        exist_ok=True,
    )

    decision_path = (
        DECISION_ROOT
        / f"{decision['id']}.json"
    )

    atomic_write_json(
        decision_path,
        decision,
    )

    SNAPSHOT_ROOT.mkdir(
        parents=True,
        exist_ok=True,
    )

    snapshot_path = (
        SNAPSHOT_ROOT
        / f"{transaction_id}__masterplan.json"
    )

    atomic_write_json(
        snapshot_path,
        graph_after,
    )

    result: dict[str, Any] = {
        "schema": (
            "savant://niche/masterplan/"
            "decision-admission/1.0.0"
        ),
        "operation": (
            "admit_masterplan_decision"
        ),
        "generated_at": utc_now(),
        "passed": True,
        "decision": decision,
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
                snapshot_path
            ),
            "decision": relative_path(
                decision_path
            ),
        },
        "rollback": rollback,
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

    REPORT_ROOT.mkdir(
        parents=True,
        exist_ok=True,
    )

    atomic_write_json(
        REPORT_ROOT
        / f"{transaction_id}__decision.json",
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
            "Admit an explicit authoritative decision "
            "into the Masterplan task graph."
        )
    )

    parser.add_argument(
        "subject",
    )

    parser.add_argument(
        "decision_type",
        choices=sorted(
            ALLOWED_DECISION_TYPES
        ),
    )

    parser.add_argument(
        "--actor",
        required=True,
    )

    parser.add_argument(
        "--authority-state",
        choices=sorted(
            ACCEPTED_AUTHORITY_STATES
        ),
        default="accepted",
    )

    parser.add_argument(
        "--rationale",
        required=True,
    )

    parser.add_argument(
        "--payload",
        default="{}",
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

        payload = json.loads(
            arguments.payload
        )

        if not isinstance(payload, dict):
            raise ValueError(
                "Decision payload must be a JSON object."
            )

        graph_before = load_json(
            GRAPH_PATH
        )

        validation = validate_request(
            graph_before,
            subject=arguments.subject,
            decision_type=(
                arguments.decision_type
            ),
            actor=arguments.actor,
            authority_state=(
                arguments.authority_state
            ),
            rationale=arguments.rationale,
            payload=payload,
        )

        decision = build_decision(
            graph_before,
            validation,
        )

        graph_after = append_decision(
            graph_before,
            decision,
        )

        if arguments.plan:
            result = {
                "schema": (
                    "savant://niche/masterplan/"
                    "decision-admission-plan/1.0.0"
                ),
                "operation": (
                    "plan_masterplan_decision"
                ),
                "generated_at": utc_now(),
                "passed": validation[
                    "passed"
                ],
                "validation": validation,
                "decision": decision,
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

            result = persist_decision(
                graph_before,
                graph_after,
                decision,
            )

    except Exception as exc:
        print(
            json.dumps(
                {
                    "operation": (
                        "admit_masterplan_decision"
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
