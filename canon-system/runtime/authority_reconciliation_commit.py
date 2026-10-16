#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

RUNTIME = Path(
    "/root/savant-runtime/canon-system/runtime"
)

if str(RUNTIME) not in sys.path:
    sys.path.insert(0, str(RUNTIME))

from authority_reconciliation import (
    SCHEMA as RECONCILIATION_SCHEMA,
    reconcile,
)

ROOT = Path("/root/savant-runtime")

PROJECTION_ROOT = (
    ROOT
    / "canon-system"
    / "projections"
    / "authority-reconciliation"
)

HISTORY_ROOT = (
    ROOT
    / "canon-system"
    / "history"
    / "authority-reconciliation"
)

SCHEMA = (
    "savant://canon/"
    "authority-reconciliation-receipt/1.0.0"
)


class ReconciliationCommitError(RuntimeError):
    pass


def canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )


def digest(value: Any) -> str:
    return hashlib.sha256(
        canonical_json(value).encode("utf-8")
    ).hexdigest()


def atomic_write(
    path: Path,
    content: str,
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    temporary = path.with_name(
        f".{path.name}.{os.getpid()}.tmp"
    )

    temporary.write_text(
        content,
        encoding="utf-8",
    )

    temporary.replace(path)


def relative(path: Path) -> str:
    return str(
        path.relative_to(ROOT)
    )


def main() -> int:
    projection = reconcile()

    if projection.unresolved_conflicts:
        raise ReconciliationCommitError(
            "authority reconciliation contains "
            "unresolved conflicts; projection refused"
        )

    semantic = projection.to_dict()

    semantic.pop(
        "generated_at",
        None,
    )

    semantic_digest = (
        semantic.get("semantic_digest")
        or digest(semantic)
    )

    stamp = datetime.now(
        UTC
    ).strftime("%Y%m%dT%H%M%SZ")

    projection_name = (
        f"{stamp}__"
        f"{semantic_digest[:16]}"
        "__authority-reconciliation.json"
    )

    projection_path = (
        PROJECTION_ROOT
        / projection_name
    )

    latest_path = (
        PROJECTION_ROOT
        / "latest.json"
    )

    projection_payload = {
        **semantic,
        "generated_at": (
            datetime.now(UTC).isoformat()
        ),
    }

    projection_text = (
        json.dumps(
            projection_payload,
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
            default=str,
        )
        + "\n"
    )

    atomic_write(
        projection_path,
        projection_text,
    )

    atomic_write(
        latest_path,
        projection_text,
    )

    receipt = {
        "schema": SCHEMA,
        "operation": (
            "canon.authority.reconciliation"
        ),
        "task_id": "SAV-P0-001",
        "passed": True,
        "authority_effect": "none",
        "occurred_at": (
            datetime.now(UTC).isoformat()
        ),
        "reconciliation_schema": (
            RECONCILIATION_SCHEMA
        ),
        "semantic_digest": (
            semantic_digest
        ),
        "outputs": [
            relative(projection_path),
            relative(latest_path),
        ],
        "evidence": {
            "source_count": len(
                projection.sources
            ),
            "conflict_count": len(
                projection.conflicts
            ),
            "unresolved_conflict_count": len(
                projection.unresolved_conflicts
            ),
            "safe_to_project": True,
        },
        "provenance": {
            "generated_by": (
                "canon-system.runtime."
                "authority_reconciliation_commit"
            ),
            "transformations": [
                "collect_declared_authority",
                "preserve_source_authority_state",
                "deterministically_order_precedence",
                "detect_metadata_conflicts",
                "refuse_unresolved_equal_precedence",
                "project_without_authority_transfer",
            ],
            "sources": [
                {
                    "source_id": source.source_id,
                    "source_kind": source.source_kind,
                    "source_path": source.source_path,
                    "authority_class": (
                        source.authority_class
                    ),
                    "authority_state": (
                        source.authority_state
                    ),
                    "digest": source.digest,
                }
                for source in projection.sources
            ],
        },
    }

    receipt["receipt_digest"] = digest(
        receipt
    )

    receipt_path = (
        HISTORY_ROOT
        / (
            f"{stamp}__"
            f"{receipt['receipt_digest'][:16]}"
            "__receipt.json"
        )
    )

    atomic_write(
        receipt_path,
        json.dumps(
            receipt,
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
            default=str,
        )
        + "\n",
    )

    print(
        json.dumps(
            {
                "passed": True,
                "task_id": "SAV-P0-001",
                "semantic_digest": (
                    semantic_digest
                ),
                "projection": (
                    relative(projection_path)
                ),
                "receipt": (
                    relative(receipt_path)
                ),
                "unresolved_conflicts": 0,
            },
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
        )
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
