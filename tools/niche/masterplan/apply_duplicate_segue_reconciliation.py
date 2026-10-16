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

PLAN_PATH = (
    ROOT
    / "reports"
    / "niche"
    / "masterplan"
    / "segue-reconciliation"
    / "latest.json"
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
    / "segue-reconciliation"
)

TRANSACTION_ROOT = (
    ROOT
    / "runtime"
    / "masterplan"
    / "segue-reconciliation"
)

REPORT_ROOT = (
    ROOT
    / "reports"
    / "niche"
    / "masterplan"
    / "segue-reconciliation"
    / "applications"
)

ACCEPTED_AUTHORITY_STATES = {
    "accepted",
    "authoritative",
}

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


class ReconciliationError(RuntimeError):
    pass


def utc_now() -> str:
    return (
        dt.datetime.now(
            dt.timezone.utc
        )
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


def semantic_digest(
    value: Any,
) -> str:
    return hashlib.sha256(
        canonical_bytes(
            deterministic_projection(value)
        )
    ).hexdigest()


def semantic_key(
    segue: dict[str, Any],
) -> tuple[str, str, str]:
    return (
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
    )


def canonicalize_graph(
    graph: dict[str, Any],
) -> dict[str, Any]:
    canonical_graph = json.loads(
        json.dumps(
            graph
        )
    )

    segues = canonical_graph.get(
        "segues",
        [],
    )

    if not isinstance(
        segues,
        list,
    ):
        raise ReconciliationError(
            "Graph segues are invalid."
        )

    for segue in segues:
        if not isinstance(
            segue,
            dict,
        ):
            raise ReconciliationError(
                "Graph contains an invalid segue."
            )

    canonical_graph[
        "segues"
    ] = sorted(
        segues,
        key=lambda segue: (
            semantic_key(
                segue
            ),
            str(
                segue.get(
                    "id",
                    "",
                )
            ),
        ),
    )

    return canonical_graph


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
        raise ReconciliationError(
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


def accepted_decision(
    decision_id: str,
) -> dict[str, Any]:
    path = (
        DECISION_ROOT
        / f"{decision_id}.json"
    )

    if not path.is_file():
        raise FileNotFoundError(path)

    decision = load_json(path)

    if decision.get("id") != decision_id:
        raise ReconciliationError(
            "Decision identity does not match filename."
        )

    if decision.get("decision") not in {
        "approve_duplicate_segue_reconciliation",
        "approve_scope_change",
    }:
        raise ReconciliationError(
            "Decision type does not authorize segue reconciliation."
        )

    authority = decision.get(
        "authority"
    )

    if not isinstance(
        authority,
        dict,
    ):
        raise ReconciliationError(
            "Decision authority is invalid."
        )

    if authority.get(
        "state"
    ) not in ACCEPTED_AUTHORITY_STATES:
        raise ReconciliationError(
            "Decision authority is not accepted."
        )

    return decision


def decision_payload(
    decision: dict[str, Any],
) -> dict[str, Any]:
    extensions = decision.get(
        "extensions",
        {},
    )

    if not isinstance(
        extensions,
        dict,
    ):
        raise ReconciliationError(
            "Decision extensions are invalid."
        )

    payload = extensions.get(
        "payload",
        {},
    )

    if not isinstance(
        payload,
        dict,
    ):
        raise ReconciliationError(
            "Decision payload is invalid."
        )

    return payload


def validate_authorization(
    graph: dict[str, Any],
    plan: dict[str, Any],
    decision: dict[str, Any],
) -> list[str]:
    if plan.get("passed") is not True:
        raise ReconciliationError(
            "Reconciliation plan did not pass."
        )

    current_digest = semantic_digest(
        canonicalize_graph(
            graph
        )
    )

    planned_digest = (
        plan.get(
            "graph",
            {},
        )
        or {}
    ).get(
        "semantic_digest"
    )

    if planned_digest != current_digest:
        raise ReconciliationError(
            "Authoritative graph changed after reconciliation planning."
        )

    payload = decision_payload(
        decision
    )

    authorized_plan_digest = payload.get(
        "plan_semantic_digest"
    )

    if (
        authorized_plan_digest
        != plan.get(
            "semantic_digest"
        )
    ):
        raise ReconciliationError(
            "Decision does not authorize this exact reconciliation plan."
        )

    planned_removals = plan.get(
        "proposed_removal_ids",
        [],
    )

    if (
        not isinstance(
            planned_removals,
            list,
        )
        or any(
            not isinstance(
                value,
                str,
            )
            for value in planned_removals
        )
    ):
        raise ReconciliationError(
            "Planned removal identifiers are invalid."
        )

    authorized_removals = payload.get(
        "removal_ids"
    )

    if authorized_removals is not None:
        if (
            not isinstance(
                authorized_removals,
                list,
            )
            or sorted(
                authorized_removals
            )
            != sorted(
                planned_removals
            )
        ):
            raise ReconciliationError(
                "Decision removal set differs from the plan."
            )

    return sorted(
        planned_removals
    )


def apply_reconciliation(
    graph: dict[str, Any],
    removal_ids: list[str],
) -> dict[str, Any]:
    segues = graph.get(
        "segues",
        [],
    )

    if not isinstance(
        segues,
        list,
    ):
        raise ReconciliationError(
            "Graph segues are invalid."
        )

    existing_ids = {
        segue.get("id")
        for segue in segues
        if isinstance(
            segue,
            dict,
        )
    }

    missing = sorted(
        set(removal_ids)
        - existing_ids
    )

    if missing:
        raise ReconciliationError(
            "Planned segue removals no longer exist: "
            + ", ".join(missing)
        )

    reconciled = json.loads(
        json.dumps(
            graph
        )
    )

    reconciled["segues"] = sorted(
        (
            segue
            for segue in segues
            if segue.get("id")
            not in removal_ids
        ),
        key=lambda segue: (
            semantic_key(
                segue
            ),
            str(
                segue.get(
                    "id",
                    "",
                )
            ),
        ),
    )

    return reconciled


def build_event(
    decision: dict[str, Any],
    plan: dict[str, Any],
    graph_before: dict[str, Any],
    graph_after: dict[str, Any],
    removal_ids: list[str],
) -> dict[str, Any]:
    body = {
        "decision_id": decision[
            "id"
        ],
        "plan_semantic_digest": plan[
            "semantic_digest"
        ],
        "graph_digest_before": (
            semantic_digest(
                canonicalize_graph(
                    graph_before
                )
            )
        ),
        "graph_digest_after": (
            semantic_digest(
                canonicalize_graph(
                    graph_after
                )
            )
        ),
        "removal_ids": removal_ids,
    }

    return {
        "id": (
            "event-"
            + semantic_digest(body)[
                :24
            ]
        ),
        "task_id": (
            decision.get(
                "subject"
            )
            or "SAV-P4A-003"
        ),
        "event_type": (
            "masterplan.segues."
            "duplicates.reconciled"
        ),
        "authority": decision[
            "authority"
        ],
        "occurred_at": utc_now(),
        "provenance": {
            "sources": [
                {
                    "source_id": decision[
                        "id"
                    ],
                    "source_kind": (
                        "accepted-decision"
                    ),
                    "source_path": (
                        "authority/task-graph/"
                        "decisions/"
                        f"{decision['id']}.json"
                    ),
                    "authority_state": (
                        decision[
                            "authority"
                        ][
                            "state"
                        ]
                    ),
                },
                {
                    "source_id": (
                        plan[
                            "semantic_digest"
                        ]
                    ),
                    "source_kind": (
                        "segue-reconciliation-plan"
                    ),
                    "source_path": (
                        relative_path(
                            PLAN_PATH
                        )
                    ),
                    "authority_state": (
                        "proposed"
                    ),
                },
            ],
            "transformations": [
                "validate_plan_graph_digest",
                "validate_decision_authority",
                "validate_exact_plan_authorization",
                "remove_authorized_duplicate_segues",
            ],
            "generated_by": (
                "prodigal.niche.masterplan."
                "apply_duplicate_segue_reconciliation"
            ),
            "generated_at": utc_now(),
            "contract_version": "1.0.0",
        },
        "extensions": body,
    }


def build_receipt(
    event: dict[str, Any],
    graph_before: dict[str, Any],
    graph_after: dict[str, Any],
    backup: Path,
    snapshot: Path,
) -> dict[str, Any]:
    body = {
        "event_id": event["id"],
        "graph_digest_before": (
            semantic_digest(
                canonicalize_graph(
                    graph_before
                )
            )
        ),
        "graph_digest_after": (
            semantic_digest(
                canonicalize_graph(
                    graph_after
                )
            )
        ),
        "backup": relative_path(
            backup
        ),
        "snapshot": relative_path(
            snapshot
        ),
    }

    return {
        "id": (
            "receipt-"
            + semantic_digest(body)[
                :24
            ]
        ),
        "task_id": event[
            "task_id"
        ],
        "operation": (
            "masterplan.segues."
            "duplicate-reconciliation"
        ),
        "passed": True,
        "outputs": [
            relative_path(
                GRAPH_PATH
            ),
            relative_path(
                snapshot
            ),
        ],
        "evidence": [
            event["id"],
        ],
        "occurred_at": utc_now(),
        "provenance": event[
            "provenance"
        ],
        "extensions": body,
    }


def append_unique(
    graph: dict[str, Any],
    collection: str,
    record: dict[str, Any],
) -> None:
    values = graph.setdefault(
        collection,
        [],
    )

    if not isinstance(
        values,
        list,
    ):
        raise ReconciliationError(
            f"Graph collection is invalid: {collection}"
        )

    if any(
        isinstance(
            existing,
            dict,
        )
        and existing.get(
            "id"
        )
        == record["id"]
        for existing in values
    ):
        raise ReconciliationError(
            f"Record already exists: {record['id']}"
        )

    values.append(
        record
    )

    values.sort(
        key=lambda value: str(
            value.get(
                "id",
                "",
            )
        )
    )


def apply(
    decision_id: str,
    plan_only: bool,
) -> dict[str, Any]:
    if not GRAPH_PATH.is_file():
        raise FileNotFoundError(
            GRAPH_PATH
        )

    if not PLAN_PATH.is_file():
        raise FileNotFoundError(
            PLAN_PATH
        )

    graph_before = load_json(
        GRAPH_PATH
    )

    plan = load_json(
        PLAN_PATH
    )

    decision = accepted_decision(
        decision_id
    )

    removal_ids = validate_authorization(
        graph_before,
        plan,
        decision,
    )

    graph_after = apply_reconciliation(
        graph_before,
        removal_ids,
    )

    result: dict[str, Any] = {
        "schema": (
            "savant://niche/masterplan/"
            "segue-reconciliation-application/1.0.0"
        ),
        "operation": (
            "apply_duplicate_segue_reconciliation"
        ),
        "generated_at": utc_now(),
        "passed": True,
        "applied": False,
        "decision_id": decision_id,
        "plan_semantic_digest": plan[
            "semantic_digest"
        ],
        "graph_digest_before": (
            semantic_digest(
                canonicalize_graph(
                    graph_before
                )
            )
        ),
        "graph_digest_after": (
            semantic_digest(
                canonicalize_graph(
                    graph_after
                )
            )
        ),
        "original_segue_count": len(
            graph_before.get(
                "segues",
                [],
            )
        ),
        "reconciled_segue_count": len(
            graph_after.get(
                "segues",
                [],
            )
        ),
        "removed_count": len(
            removal_ids
        ),
        "removal_ids": removal_ids,
    }

    if plan_only:
        result[
            "semantic_digest"
        ] = semantic_digest(
            result
        )

        return result

    transaction_id = (
        f"{timestamp()}__"
        f"{semantic_digest(result)[:16]}"
    )

    transaction_root = (
        TRANSACTION_ROOT
        / transaction_id
    )

    transaction_root.mkdir(
        parents=True,
        exist_ok=False,
    )

    backup = (
        BACKUP_ROOT
        / transaction_id
        / "masterplan.json"
    )

    backup.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    shutil.copy2(
        GRAPH_PATH,
        backup,
    )

    if (
        sha256_path(
            GRAPH_PATH
        )
        != sha256_path(
            backup
        )
    ):
        raise ReconciliationError(
            "Backup hash mismatch."
        )

    SNAPSHOT_ROOT.mkdir(
        parents=True,
        exist_ok=True,
    )

    snapshot = (
        SNAPSHOT_ROOT
        / (
            f"{transaction_id}__"
            "segue-reconciliation.json"
        )
    )

    event = build_event(
        decision,
        plan,
        graph_before,
        graph_after,
        removal_ids,
    )

    append_unique(
        graph_after,
        "events",
        event,
    )

    atomic_write_json(
        snapshot,
        graph_after,
    )

    receipt = build_receipt(
        event,
        graph_before,
        graph_after,
        backup,
        snapshot,
    )

    append_unique(
        graph_after,
        "receipts",
        receipt,
    )

    atomic_write_json(
        transaction_root
        / "graph-before.json",
        graph_before,
    )

    atomic_write_json(
        transaction_root
        / "plan.json",
        plan,
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

    try:
        atomic_write_json(
            GRAPH_PATH,
            graph_after,
        )

        written = load_json(
            GRAPH_PATH
        )

        if (
            semantic_digest(
                canonicalize_graph(
                    written
                )
            )
            != semantic_digest(
                canonicalize_graph(
                    graph_after
                )
            )
        ):
            raise ReconciliationError(
                "Written graph digest mismatch."
            )

    except Exception:
        shutil.copy2(
            backup,
            GRAPH_PATH,
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

    result.update(
        {
            "applied": True,
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
            "event": event,
            "receipt": receipt,
            "final_graph_sha256": (
                sha256_path(
                    GRAPH_PATH
                )
            ),
            "final_graph_semantic_digest": (
                semantic_digest(
                    canonicalize_graph(
                        load_json(
                            GRAPH_PATH
                        )
                    )
                )
            ),
        }
    )

    result[
        "semantic_digest"
    ] = semantic_digest(
        result
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
        / (
            f"{transaction_id}__"
            "segue-reconciliation.json"
        ),
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
            "Apply an explicitly accepted duplicate "
            "segue reconciliation decision."
        )
    )

    parser.add_argument(
        "decision_id"
    )

    parser.add_argument(
        "--plan",
        action="store_true",
    )

    arguments = parser.parse_args()

    try:
        result = apply(
            arguments.decision_id,
            arguments.plan,
        )

    except Exception as exc:
        print(
            json.dumps(
                {
                    "operation": (
                        "apply_duplicate_"
                        "segue_reconciliation"
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
