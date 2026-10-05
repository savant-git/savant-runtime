#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import tempfile
from collections import defaultdict
from pathlib import Path
from typing import Any


ROOT = Path("/root/savant-runtime")

GRAPH_PATH = (
    ROOT
    / "authority"
    / "task-graph"
    / "masterplan.json"
)

CANONICAL_MARKDOWN = (
    ROOT
    / "docs"
    / "SAVANT_MASTER_TASKS.md"
)

PROJECTION_ROOT = (
    ROOT
    / "reports"
    / "niche"
    / "masterplan"
    / "roadmap"
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

    temporary_path = Path(temporary_name)

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


def band_weight(
    band: str,
) -> int:
    if not band.startswith("P"):
        return 0

    body = band[1:]
    digits = ""

    for character in body:
        if character.isdigit():
            digits += character

        else:
            break

    if not digits:
        return 0

    number = int(digits)

    suffix = body[
        len(digits):
    ]

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
                ord(character.upper())
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

    return {
        record["id"]: record
        for record in records
        if (
            isinstance(record, dict)
            and isinstance(
                record.get("id"),
                str,
            )
        )
    }


def dependency_map(
    graph: dict[str, Any],
) -> dict[str, list[str]]:
    dependencies: dict[
        str,
        list[str],
    ] = defaultdict(list)

    for segue in graph.get(
        "segues",
        [],
    ):
        if not isinstance(
            segue,
            dict,
        ):
            continue

        if segue.get("type") != "depends_on":
            continue

        source = segue.get("source")
        target = segue.get("target")

        if (
            isinstance(source, str)
            and isinstance(target, str)
        ):
            dependencies[source].append(
                target
            )

    return {
        key: sorted(set(values))
        for key, values in sorted(
            dependencies.items()
        )
    }


def status_counts(
    graph: dict[str, Any],
) -> dict[str, int]:
    counts: dict[str, int] = defaultdict(int)

    for record in graph.get(
        "records",
        [],
    ):
        if not isinstance(
            record,
            dict,
        ):
            continue

        status = str(
            record.get(
                "status",
                "unknown",
            )
        )

        counts[status] += 1

    return dict(
        sorted(
            counts.items()
        )
    )


def authority_counts(
    graph: dict[str, Any],
) -> dict[str, int]:
    counts: dict[str, int] = defaultdict(int)

    for record in graph.get(
        "records",
        [],
    ):
        if not isinstance(
            record,
            dict,
        ):
            continue

        authority = record.get(
            "authority"
        )

        state = (
            authority.get(
                "state",
                "unknown",
            )
            if isinstance(
                authority,
                dict,
            )
            else "unknown"
        )

        counts[str(state)] += 1

    return dict(
        sorted(
            counts.items()
        )
    )


def grouped_records(
    graph: dict[str, Any],
) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[
        str,
        list[dict[str, Any]],
    ] = defaultdict(list)

    for record in graph.get(
        "records",
        [],
    ):
        if not isinstance(
            record,
            dict,
        ):
            continue

        priority = record.get(
            "priority"
        )

        band = (
            priority.get(
                "band",
                "P999",
            )
            if isinstance(
                priority,
                dict,
            )
            else "P999"
        )

        grouped[str(band)].append(
            record
        )

    return {
        band: sorted(
            records,
            key=lambda record: (
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
        for band, records in sorted(
            grouped.items(),
            key=lambda item: (
                -band_weight(
                    item[0]
                ),
                item[0],
            ),
        )
    }


def render_list(
    heading: str,
    values: list[str] | tuple[str, ...],
) -> list[str]:
    lines = [
        heading,
        "",
    ]

    if not values:
        lines.extend(
            [
                "- None declared.",
                "",
            ]
        )

        return lines

    for value in values:
        lines.append(
            f"- {value}"
        )

    lines.append("")

    return lines


def render_record(
    record: dict[str, Any],
    dependencies: dict[str, list[str]],
) -> list[str]:
    identifier = str(
        record.get(
            "id",
            "UNKNOWN",
        )
    )

    title = str(
        record.get(
            "title",
            identifier,
        )
    )

    priority = record.get(
        "priority"
    )

    authority = record.get(
        "authority"
    )

    lines = [
        f"### {identifier} — {title}",
        "",
        (
            f"- Kind: `"
            f"{record.get('kind', 'task')}`"
        ),
        (
            f"- Status: `"
            f"{record.get('status', 'unknown')}`"
        ),
        (
            f"- Authority: `"
            f"{authority.get('state', 'unknown') if isinstance(authority, dict) else 'unknown'}`"
        ),
        (
            f"- Priority locked: `"
            f"{priority.get('authority_locked', False) if isinstance(priority, dict) else False}`"
        ),
        "",
    ]

    purpose = str(
        record.get(
            "purpose",
            "",
        )
    ).strip()

    if purpose:
        lines.extend(
            [
                "Purpose:",
                "",
                purpose,
                "",
            ]
        )

    task_dependencies = dependencies.get(
        identifier,
        [],
    )

    lines.extend(
        render_list(
            "Depends on:",
            task_dependencies,
        )
    )

    outputs = record.get(
        "outputs",
        [],
    )

    lines.extend(
        render_list(
            "Outputs:",
            [
                str(value)
                for value in outputs
            ],
        )
    )

    acceptance = record.get(
        "acceptance",
        [],
    )

    lines.extend(
        render_list(
            "Acceptance:",
            [
                str(value)
                for value in acceptance
            ],
        )
    )

    risks = record.get(
        "risks",
        [],
    )

    if risks:
        lines.extend(
            render_list(
                "Risks:",
                [
                    str(value)
                    for value in risks
                ],
            )
        )

    return lines


def render_markdown(
    graph: dict[str, Any],
) -> str:
    graph_value_digest = digest(
        deterministic_projection(
            graph
        )
    )

    dependencies = dependency_map(
        graph
    )

    grouped = grouped_records(
        graph
    )

    counts = status_counts(
        graph
    )

    authority = authority_counts(
        graph
    )

    records = task_map(
        graph
    )

    active = [
        record
        for record in records.values()
        if record.get("status")
        == "active"
    ]

    locked = [
        record
        for record in records.values()
        if (
            isinstance(
                record.get(
                    "priority"
                ),
                dict,
            )
            and record[
                "priority"
            ].get(
                "authority_locked"
            )
            is True
        )
    ]

    lines = [
        "# SAVANT MASTER TASKS",
        "",
        "> GENERATED PROJECTION — DO NOT EDIT DIRECTLY",
        ">",
        (
            "> Authority: "
            "`/root/savant-runtime/authority/task-graph/masterplan.json`"
        ),
        (
            "> Generator: "
            "`tools/niche/masterplan/project_masterplan_markdown.py`"
        ),
        "",
        "## Governing Status",
        "",
        "- State: `ACTIVE GOVERNING ROADMAP`",
        (
            f"- Graph ID: "
            f"`{graph.get('graph_id', 'savant.masterplan')}`"
        ),
        (
            f"- Schema version: "
            f"`{graph.get('schema_version', 'unknown')}`"
        ),
        (
            f"- Deterministic graph digest: "
            f"`{graph_value_digest}`"
        ),
        (
            f"- Record count: "
            f"**{len(records)}**"
        ),
        (
            f"- Segue count: "
            f"**{len(graph.get('segues', []))}**"
        ),
        "",
        "## Governing Laws",
        "",
        (
            "1. The authoritative task graph governs project order. "
            "This Markdown file is only a deterministic projection."
        ),
        (
            "2. Accepted authority precedes inference, projection, "
            "observation, convenience, and implementation momentum."
        ),
        (
            "3. The highest-priority executable accepted task governs "
            "unless an accepted override decision explicitly changes it."
        ),
        (
            "4. No task becomes complete without accepted evidence "
            "and a passing attestation."
        ),
        (
            "5. Dependencies, blockers, outputs, relationships, lineage, "
            "provenance, receipts, and attestations remain graph-addressable."
        ),
        (
            "6. Existing working implementation is extended rather than "
            "replaced unless replacement is explicitly authorized."
        ),
        (
            "7. Proposed and observed work may be represented without "
            "silently becoming accepted project authority."
        ),
        "",
        "## Current Authority",
        "",
    ]

    if active:
        for record in sorted(
            active,
            key=lambda value: (
                -band_weight(
                    (
                        value.get(
                            "priority"
                        )
                        or {}
                    ).get(
                        "band",
                        "P999",
                    )
                ),
                (
                    value.get(
                        "priority"
                    )
                    or {}
                ).get(
                    "ordinal",
                    999999,
                ),
                value.get(
                    "id",
                    "",
                ),
            ),
        ):
            lines.append(
                (
                    f"- Active: `{record['id']}` — "
                    f"{record.get('title', '')}"
                )
            )

    else:
        lines.append(
            "- No task is marked active."
        )

    if locked:
        for record in sorted(
            locked,
            key=lambda value: (
                value.get(
                    "id",
                    "",
                ),
            ),
        ):
            lines.append(
                (
                    f"- Authority locked: `{record['id']}` — "
                    f"{record.get('title', '')}"
                )
            )

    lines.extend(
        [
            "",
            "## Statistics",
            "",
            "### Status",
            "",
        ]
    )

    for key, value in counts.items():
        lines.append(
            f"- `{key}`: **{value}**"
        )

    lines.extend(
        [
            "",
            "### Authority",
            "",
        ]
    )

    for key, value in authority.items():
        lines.append(
            f"- `{key}`: **{value}**"
        )

    lines.append("")

    for band, band_records in grouped.items():
        lines.extend(
            [
                f"## {band}",
                "",
            ]
        )

        for record in band_records:
            lines.extend(
                render_record(
                    record,
                    dependencies,
                )
            )

    lines.extend(
        [
            "## Projection Contract",
            "",
            (
                "This document may be deleted and regenerated without "
                "losing authoritative task state."
            ),
            (
                "Changes must be made through the authoritative task graph, "
                "accepted decisions, events, receipts, or attestations."
            ),
            "",
        ]
    )

    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Project the authoritative Masterplan task graph "
            "into the canonical human-readable roadmap."
        )
    )

    parser.add_argument(
        "--graph",
        type=Path,
        default=GRAPH_PATH,
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=CANONICAL_MARKDOWN,
    )

    parser.add_argument(
        "--strict",
        action="store_true",
    )

    arguments = parser.parse_args()

    graph_path = arguments.graph.expanduser()

    if not graph_path.is_absolute():
        graph_path = ROOT / graph_path

    output = arguments.output.expanduser()

    if not output.is_absolute():
        output = ROOT / output

    try:
        if not graph_path.is_file():
            raise FileNotFoundError(
                graph_path
            )

        graph = load_json(
            graph_path
        )

        rendered = render_markdown(
            graph
        )

        atomic_write_text(
            output,
            rendered,
        )

        PROJECTION_ROOT.mkdir(
            parents=True,
            exist_ok=True,
        )

        run_id = timestamp()

        historical = (
            PROJECTION_ROOT
            / f"{run_id}__SAVANT_MASTER_TASKS.md"
        )

        latest_markdown = (
            PROJECTION_ROOT
            / "latest.md"
        )

        atomic_write_text(
            historical,
            rendered,
        )

        atomic_write_text(
            latest_markdown,
            rendered,
        )

        graph_value_digest = digest(
            deterministic_projection(
                graph
            )
        )

        report = {
            "operation": (
                "project_masterplan_markdown"
            ),
            "passed": True,
            "generated_at": utc_now(),
            "graph": {
                "path": relative_path(
                    graph_path
                ),
                "sha256": sha256_path(
                    graph_path
                ),
                "deterministic_digest": (
                    graph_value_digest
                ),
            },
            "projection": {
                "path": relative_path(
                    output
                ),
                "sha256": sha256_path(
                    output
                ),
                "historical": relative_path(
                    historical
                ),
                "latest": relative_path(
                    latest_markdown
                ),
            },
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
            },
        }

        report_path = (
            PROJECTION_ROOT
            / f"{run_id}__projection.json"
        )

        latest_json = (
            PROJECTION_ROOT
            / "latest.json"
        )

        atomic_write_json(
            report_path,
            report,
        )

        atomic_write_json(
            latest_json,
            report,
        )

        print(
            json.dumps(
                report,
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
        )

        return 0

    except Exception as exc:
        print(
            json.dumps(
                {
                    "operation": (
                        "project_masterplan_markdown"
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


if __name__ == "__main__":
    raise SystemExit(main())
