#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import os
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path("/root/savant-runtime")
OUTPUT_ROOT = ROOT / "exports" / "final-migration"
MASTERPLAN = ROOT / "authority" / "task-graph" / "masterplan.json"

SCHEMA = "savant://migration/final-packet/1.0.0"
OWNER = "savant"


class MigrationPacketError(RuntimeError):
    pass


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def digest(value: Any) -> str:
    return hashlib.sha256(
        canonical_json(value).encode("utf-8")
    ).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()

    with path.open("rb") as handle:
        for chunk in iter(
            lambda: handle.read(1024 * 1024),
            b"",
        ):
            h.update(chunk)

    return h.hexdigest()


def relative(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def load_json(path: Path) -> Any:
    try:
        return json.loads(
            path.read_text(
                encoding="utf-8"
            )
        )
    except Exception as exc:
        raise MigrationPacketError(
            f"unable to load {path}: {exc}"
        ) from exc


def task_summary(graph: dict[str, Any]) -> dict[str, Any]:
    records = graph.get("records", [])

    tasks = [
        record
        for record in records
        if isinstance(record, dict)
        and record.get("kind") == "task"
    ]

    statuses: dict[str, int] = {}

    for task in tasks:
        status = str(
            task.get(
                "status",
                "unknown",
            )
        ).lower()

        statuses[status] = (
            statuses.get(status, 0) + 1
        )

    active = [
        {
            "id": task.get("id"),
            "title": task.get("title"),
            "status": task.get("status"),
            "priority": task.get("priority"),
            "depends_on": (
                task.get("scope", {})
                .get("depends_on", [])
            ),
        }
        for task in tasks
        if str(
            task.get(
                "status",
                "",
            )
        ).lower()
        == "active"
    ]

    return {
        "count": len(tasks),
        "statuses": dict(
            sorted(statuses.items())
        ),
        "active": active,
    }


def authority_summary(
    graph: dict[str, Any],
) -> dict[str, Any]:
    return {
        "graph_id": graph.get("graph_id"),
        "schema_version": graph.get(
            "schema_version"
        ),
        "authority": graph.get("authority"),
        "record_count": len(
            graph.get("records", [])
        ),
        "segue_count": len(
            graph.get("segues", [])
        ),
        "decision_count": len(
            graph.get("decisions", [])
        ),
        "evidence_count": len(
            graph.get("evidence", [])
        ),
        "attestation_count": len(
            graph.get("attestations", [])
        ),
        "event_count": len(
            graph.get("events", [])
        ),
        "receipt_count": len(
            graph.get("receipts", [])
        ),
    }


def important_paths() -> list[Path]:
    candidates = [
        ROOT
        / "authority"
        / "task-graph"
        / "masterplan.json",

        ROOT
        / "docs"
        / "SAVANT_MASTER_TASKS.md",

        ROOT
        / "canon-system"
        / "runtime"
        / "authority_reconciliation.py",

        ROOT
        / "canon-system"
        / "runtime"
        / "authority_reconciliation_commit.py",

        ROOT
        / "canon-system"
        / "runtime"
        / "reconcile_authority",

        ROOT
        / "bin"
        / "masterplan-verify",

        ROOT
        / "canon"
        / "structure"
        / "canonical_runtime_structure.json",

        ROOT
        / "canon"
        / "structure"
        / "canonical_runtime_structure.yaml",
    ]

    accepted = (
        ROOT
        / "authority"
        / "accepted-decisions"
    )

    if accepted.is_dir():
        candidates.extend(
            sorted(
                path
                for path in accepted.iterdir()
                if path.is_file()
            )
        )

    return [
        path
        for path in candidates
        if path.is_file()
    ]


def build_manifest(
    paths: list[Path],
) -> list[dict[str, Any]]:
    manifest = []

    for path in paths:
        stat = path.stat()

        manifest.append(
            {
                "path": relative(path),
                "bytes": stat.st_size,
                "sha256": sha256_file(path),
            }
        )

    return manifest


def latest_reconciliation_receipt() -> (
    dict[str, Any] | None
):
    root = (
        ROOT
        / "canon-system"
        / "history"
        / "authority-reconciliation"
    )

    if not root.is_dir():
        return None

    paths = sorted(
        root.glob("*__receipt.json"),
        key=lambda path: path.stat().st_mtime,
    )

    if not paths:
        return None

    path = paths[-1]

    return {
        "path": relative(path),
        "sha256": sha256_file(path),
        "content": load_json(path),
    }


def render_markdown(
    packet: dict[str, Any],
) -> str:
    tasks = packet["masterplan"]["tasks"]
    authority = packet["masterplan"][
        "authority"
    ]

    lines = [
        "# savant final migration packet",
        "",
        "## identity",
        "",
        "- system: savant",
        "- runtime root: `/root/savant-runtime`",
        f"- packet schema: `{SCHEMA}`",
        "",
        "## authoritative state",
        "",
        (
            "- authoritative graph: "
            "`authority/task-graph/masterplan.json`"
        ),
        (
            "- graph id: "
            f"`{authority.get('graph_id')}`"
        ),
        (
            "- schema version: "
            f"`{authority.get('schema_version')}`"
        ),
        (
            "- task records: "
            f"{tasks['count']}"
        ),
        (
            "- task statuses: "
            f"`{canonical_json(tasks['statuses'])}`"
        ),
        (
            "- active tasks: "
            f"{len(tasks['active'])}"
        ),
        "",
        "## migration law",
        "",
        (
            "The authoritative graph and accepted "
            "decisions govern continuation. Historical "
            "documents and implementation evidence do "
            "not supersede higher authority."
        ),
        "",
        (
            "Derived structures must be projected "
            "deterministically from authoritative "
            "primitives wherever possible."
        ),
        "",
        (
            "Accepted decisions remain immutable. "
            "Future changes supersede rather than "
            "silently rewrite accepted history."
        ),
        "",
        "## current task state",
        "",
    ]

    if tasks["active"]:
        for task in tasks["active"]:
            lines.extend(
                [
                    (
                        f"- `{task['id']}` — "
                        f"{task['title']}"
                    ),
                ]
            )
    else:
        lines.extend(
            [
                (
                    "No task is currently marked "
                    "`active` in the authoritative "
                    "masterplan."
                ),
                "",
                (
                    "This is a terminal/no-executable-"
                    "task state, not evidence that "
                    "Savant itself is finished."
                ),
            ]
        )

    lines.extend(
        [
            "",
            "## continuation rule",
            "",
            (
                "Do not invent a new executable task "
                "from historical roadmap material. "
                "Continuation requires accepted "
                "authority for the next task."
            ),
            "",
            "## preserved files",
            "",
        ]
    )

    for entry in packet["manifest"]:
        lines.append(
            f"- `{entry['path']}` — "
            f"{entry['bytes']} bytes — "
            f"`sha256:{entry['sha256']}`"
        )

    lines.extend(
        [
            "",
            "## provenance",
            "",
            (
                "This packet is a deterministic "
                "projection of the current Savant "
                "runtime state. It does not create "
                "new project authority."
            ),
            "",
        ]
    )

    return "\n".join(lines)


def main() -> int:
    if not ROOT.is_dir():
        raise MigrationPacketError(
            f"runtime root missing: {ROOT}"
        )

    if not MASTERPLAN.is_file():
        raise MigrationPacketError(
            f"masterplan missing: {MASTERPLAN}"
        )

    graph = load_json(MASTERPLAN)

    if not isinstance(graph, dict):
        raise MigrationPacketError(
            "masterplan root must be an object"
        )

    paths = important_paths()
    manifest = build_manifest(paths)

    packet: dict[str, Any] = {
        "schema": SCHEMA,
        "owner": OWNER,
        "authority_effect": "none",
        "generated_at": now_iso(),
        "runtime": {
            "root": str(ROOT),
            "python": sys.version.split()[0],
            "platform": platform.platform(),
            "hostname": platform.node(),
        },
        "masterplan": {
            "path": relative(MASTERPLAN),
            "sha256": sha256_file(
                MASTERPLAN
            ),
            "authority": authority_summary(
                graph
            ),
            "tasks": task_summary(graph),
        },
        "authority_reconciliation": (
            latest_reconciliation_receipt()
        ),
        "manifest": manifest,
        "migration": {
            "chatgpt_full_export_required": False,
            "source_runtime_authoritative": True,
            "safe_assumptions": [
                (
                    "filesystem presence alone does "
                    "not establish authority"
                ),
                (
                    "accepted authority outranks "
                    "historical implementation"
                ),
                (
                    "derived structures should be "
                    "deterministically projected"
                ),
            ],
        },
    }

    semantic = dict(packet)
    semantic.pop("generated_at", None)
    semantic["runtime"] = dict(
        semantic["runtime"]
    )
    semantic["runtime"].pop(
        "hostname",
        None,
    )
    semantic["runtime"].pop(
        "platform",
        None,
    )

    packet["semantic_digest"] = digest(
        semantic
    )

    OUTPUT_ROOT.mkdir(
        parents=True,
        exist_ok=True,
    )

    json_path = (
        OUTPUT_ROOT
        / "savant-final-migration.json"
    )

    md_path = (
        OUTPUT_ROOT
        / "savant-final-migration.md"
    )

    json_path.write_text(
        json.dumps(
            packet,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    md_path.write_text(
        render_markdown(packet),
        encoding="utf-8",
    )

    result = {
        "passed": True,
        "authority_effect": "none",
        "schema": SCHEMA,
        "semantic_digest": packet[
            "semantic_digest"
        ],
        "outputs": {
            "json": relative(json_path),
            "markdown": relative(md_path),
        },
        "masterplan": {
            "active_tasks": len(
                packet["masterplan"][
                    "tasks"
                ]["active"]
            ),
            "task_statuses": packet[
                "masterplan"
            ]["tasks"]["statuses"],
        },
        "manifest_count": len(manifest),
    }

    print(
        json.dumps(
            result,
            indent=2,
            sort_keys=True,
        )
    )

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except MigrationPacketError as exc:
        print(
            json.dumps(
                {
                    "passed": False,
                    "error": str(exc),
                },
                indent=2,
                sort_keys=True,
            ),
            file=sys.stderr,
        )
        raise SystemExit(1)
