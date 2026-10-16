#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys

from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


runtime_root = Path(
    "/root/savant-runtime/"
    "ontology/obelisks/_template/"
    "segue/gates/_template/segue/"
    "innates/_template/segue/"
    "exiles/niche/runtime"
)

savant_root = Path(
    "/root/savant-runtime"
)

default_db = Path(
    "/root/savant-runtime/runtime/niche/tasks.sqlite3"
)

projection_path = Path(
    "/root/savant-runtime/"
    "runtime/niche/projections/"
    "completion-candidates.json"
)

schema = (
    "savant://runtime/niche/"
    "completion-reconciler/1.0.0"
)

owner = "exile:niche"

allowed_suffixes = {
    ".py",
    ".sh",
    ".js",
    ".jsx",
    ".ts",
    ".tsx",
    ".json",
    ".yaml",
    ".yml",
    ".md",
}

excluded_parts = {
    ".git",
    ".venv",
    "__pycache__",
    ".pytest_cache",
    "node_modules",
    "backups",
    "backup",
    "snapshots",
    "snapshot",
    "archives",
    "archive",
    "relics",
}

marker_re = re.compile(
    r"\b("
    r"TODO"
    r"|FIXME"
    r"|XXX"
    r"|NOT\s+IMPLEMENTED"
    r"|NOT\s+YET\s+IMPLEMENTED"
    r"|UNIMPLEMENTED"
    r")\b",
    re.IGNORECASE,
)

historical_re = re.compile(
    r"\b("
    r"historical"
    r"|deprecated"
    r"|superseded"
    r"|relic"
    r"|legacy\s+reference"
    r"|example"
    r"|fixture"
    r"|test\s+fixture"
    r")\b",
    re.IGNORECASE,
)

negative_re = re.compile(
    r"\b("
    r"no\s+todo"
    r"|without\s+todo"
    r"|todo\s+marker"
    r"|fixme\s+marker"
    r"|marker\s+discovery"
    r"|scan\s+for\s+todo"
    r")\b",
    re.IGNORECASE,
)

if str(runtime_root) not in sys.path:
    sys.path.insert(
        0,
        str(runtime_root),
    )

from living_task import LivingTaskEngine  # noqa: E402


@dataclass(frozen=True)
class Candidate:
    candidate_id: str
    source_path: str
    line: int
    marker: str
    excerpt: str
    system: str
    workstream: str
    confidence: str
    disposition: str
    reasons: tuple[str, ...]
    duplicate_task_ids: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "candidate_id":
                self.candidate_id,

            "source_path":
                self.source_path,

            "line":
                self.line,

            "marker":
                self.marker,

            "excerpt":
                self.excerpt,

            "system":
                self.system,

            "workstream":
                self.workstream,

            "confidence":
                self.confidence,

            "disposition":
                self.disposition,

            "reasons":
                list(self.reasons),

            "duplicate_task_ids":
                list(
                    self.duplicate_task_ids
                ),
        }


def utc_now() -> str:
    return (
        datetime.now(timezone.utc)
        .isoformat()
    )


def atomic_json(
    path: Path,
    payload: Any,
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    body = json.dumps(
        payload,
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    ) + "\n"

    temporary = path.with_name(
        path.name + ".tmp"
    )

    temporary.write_text(
        body,
        encoding="utf-8",
    )

    temporary.replace(path)


def normalize(value: str) -> str:
    return " ".join(
        re.findall(
            r"[a-z0-9]+",
            value.lower(),
        )
    )


def tokens(value: str) -> set[str]:
    ignored = {
        "a",
        "an",
        "and",
        "as",
        "at",
        "be",
        "by",
        "for",
        "from",
        "in",
        "is",
        "it",
        "of",
        "on",
        "or",
        "the",
        "this",
        "to",
        "with",
    }

    return {
        token
        for token in normalize(value).split()
        if (
            len(token) > 2
            and token not in ignored
        )
    }


def similarity(
    left: str,
    right: str,
) -> float:
    a = tokens(left)
    b = tokens(right)

    if not a or not b:
        return 0.0

    return (
        len(a & b)
        / len(a | b)
    )


def excluded(path: Path) -> bool:
    try:
        relative = path.relative_to(
            savant_root
        )
    except ValueError:
        return True

    return any(
        part.lower() in excluded_parts
        for part in relative.parts
    )


def infer_system(
    relative: Path,
) -> str:
    parts = [
        part.lower()
        for part in relative.parts
    ]

    if "niche" in parts:
        return "niche"

    if "palaver" in parts:
        return "palaver"

    if "carbon" in parts:
        return "carbon"

    if "kindred" in parts:
        return "kindred"

    if "coda" in parts:
        return "coda"

    if "opus" in parts:
        return "opus"

    if "assurance" in parts:
        return "assurance"

    if "canon" in parts:
        return "canon"

    if "runtime" in parts:
        return "runtime"

    if "ontology" in parts:
        return "ontology"

    if "tools" in parts:
        return "tools"

    return (
        parts[0]
        if parts
        else "savant"
    )


def infer_workstream(
    relative: Path,
    system: str,
) -> str:
    parts = [
        part.lower()
        for part in relative.parts
    ]

    if system in parts:
        index = parts.index(system)

        for part in parts[index + 1:]:
            if part not in {
                "runtime",
                "apps",
                "app",
                "commands",
                "command",
                "assets",
                "static",
                "src",
                "lib",
                "tests",
                "test",
                "_template",
                "segue",
                "gates",
                "innates",
                "exiles",
            }:
                if "." not in part:
                    return part

    if len(parts) > 1:
        parent = parts[-2]

        if parent not in {
            "runtime",
            "src",
            "lib",
            "tests",
            "test",
        }:
            return parent

    return system


def candidate_identity(
    source_path: str,
    line: int,
    excerpt: str,
) -> str:
    material = (
        f"{source_path}\n"
        f"{line}\n"
        f"{normalize(excerpt)}"
    ).encode("utf-8")

    digest = hashlib.sha256(
        material
    ).hexdigest()[:20]

    return (
        "completion-candidate:"
        + digest
    )


def task_text(task: Any) -> str:
    slots = (
        task.extension_slots
        if isinstance(
            task.extension_slots,
            dict,
        )
        else {}
    )

    board = slots.get(
        "niche.taskboard",
        {},
    )

    values = [
        task.task_id,
        task.purpose,
        task.completion_condition,
        str(board.get("title", "")),
        str(board.get("system", "")),
        str(board.get("workstream", "")),
        *task.implementation_references,
        *task.affected_instances,
    ]

    return " ".join(
        str(value)
        for value in values
    )


def duplicate_tasks(
    excerpt: str,
    source_path: str,
    tasks: Iterable[Any],
) -> tuple[str, ...]:
    matches: list[
        tuple[float, str]
    ] = []

    source_name = (
        Path(source_path).name.lower()
    )

    for task in tasks:
        text = task_text(task)

        score = similarity(
            excerpt,
            text,
        )

        references = [
            str(value).lower()
            for value
            in task.implementation_references
        ]

        if any(
            source_path.lower()
            in reference
            or source_name
            in reference
            for reference
            in references
        ):
            score = max(
                score,
                0.8,
            )

        if score >= 0.48:
            matches.append(
                (
                    score,
                    task.task_id,
                )
            )

    matches.sort(
        key=lambda item: (
            -item[0],
            item[1],
        )
    )

    return tuple(
        task_id
        for _score, task_id
        in matches[:8]
    )


def disposition(
    *,
    path: Path,
    excerpt: str,
    duplicate_ids: tuple[str, ...],
) -> tuple[
    str,
    str,
    tuple[str, ...],
]:
    reasons: list[str] = []

    lower_path = str(
        path
    ).lower()

    if historical_re.search(
        excerpt
    ):
        reasons.append(
            "historical-or-example-language"
        )

        return (
            "rejected",
            "low",
            tuple(reasons),
        )

    if negative_re.search(
        excerpt
    ):
        reasons.append(
            "marker-discussion-not-work"
        )

        return (
            "rejected",
            "low",
            tuple(reasons),
        )

    if (
        "/test/" in lower_path
        or "/tests/" in lower_path
        or path.name.lower().startswith(
            "test_"
        )
    ):
        reasons.append(
            "test-surface"
        )

        return (
            "review",
            "low",
            tuple(reasons),
        )

    if duplicate_ids:
        reasons.append(
            "possible-existing-task"
        )

        return (
            "review",
            "medium",
            tuple(reasons),
        )

    reasons.append(
        "explicit-unfinished-marker"
    )

    return (
        "proposed",
        "high",
        tuple(reasons),
    )


def scan_file(
    path: Path,
    tasks: list[Any],
) -> list[Candidate]:
    if excluded(path):
        return []

    if (
        path.suffix.lower()
        not in allowed_suffixes
    ):
        return []

    try:
        if path.stat().st_size > (
            4 * 1024 * 1024
        ):
            return []
    except OSError:
        return []

    try:
        text = path.read_text(
            encoding="utf-8",
            errors="replace",
        )
    except OSError:
        return []

    try:
        relative = path.relative_to(
            savant_root
        )
    except ValueError:
        return []

    system = infer_system(
        relative
    )

    workstream = infer_workstream(
        relative,
        system,
    )

    found: list[Candidate] = []

    for line_number, line in enumerate(
        text.splitlines(),
        start=1,
    ):
        match = marker_re.search(
            line
        )

        if not match:
            continue

        excerpt = line.strip()

        if not excerpt:
            continue

        duplicate_ids = duplicate_tasks(
            excerpt,
            str(relative),
            tasks,
        )

        (
            candidate_disposition,
            confidence,
            reasons,
        ) = disposition(
            path=relative,
            excerpt=excerpt,
            duplicate_ids=duplicate_ids,
        )

        found.append(
            Candidate(
                candidate_id=
                    candidate_identity(
                        str(relative),
                        line_number,
                        excerpt,
                    ),

                source_path=
                    str(relative),

                line=
                    line_number,

                marker=
                    match.group(1).lower(),

                excerpt=
                    excerpt[:1000],

                system=
                    system,

                workstream=
                    workstream,

                confidence=
                    confidence,

                disposition=
                    candidate_disposition,

                reasons=
                    reasons,

                duplicate_task_ids=
                    duplicate_ids,
            )
        )

    return found


def scan(
    tasks: list[Any],
) -> list[Candidate]:
    candidates: list[Candidate] = []

    for path in savant_root.rglob("*"):
        if not path.is_file():
            continue

        candidates.extend(
            scan_file(
                path,
                tasks,
            )
        )

    candidates.sort(
        key=lambda item: (
            item.disposition,
            item.system,
            item.workstream,
            item.source_path,
            item.line,
            item.candidate_id,
        )
    )

    return candidates


def projection(
    engine: LivingTaskEngine,
) -> dict[str, Any]:
    tasks = list(
        engine.tasks()
    )

    candidates = scan(
        tasks
    )

    disposition_counts = Counter(
        item.disposition
        for item in candidates
    )

    confidence_counts = Counter(
        item.confidence
        for item in candidates
    )

    system_counts = Counter(
        item.system
        for item in candidates
        if item.disposition
        != "rejected"
    )

    return {
        "schema":
            schema,

        "owner":
            owner,

        "authority_effect":
            "none",

        "generated_at":
            utc_now(),

        "source_root":
            str(savant_root),

        "task_store":
            str(engine.db_path),

        "task_count":
            len(tasks),

        "candidate_count":
            len(candidates),

        "disposition_counts":
            dict(
                sorted(
                    disposition_counts.items()
                )
            ),

        "confidence_counts":
            dict(
                sorted(
                    confidence_counts.items()
                )
            ),

        "system_counts":
            dict(
                sorted(
                    system_counts.items()
                )
            ),

        "admission_rule":
            (
                "No candidate is authoritative. "
                "Only explicit later acceptance "
                "may create or transition a Niche task."
            ),

        "candidates":
            [
                item.as_dict()
                for item in candidates
            ],
    }


def health(
    engine: LivingTaskEngine,
) -> dict[str, Any]:
    niche = engine.health()

    return {
        "schema":
            schema,

        "owner":
            owner,

        "authority_effect":
            "none",

        "database":
            str(engine.db_path),

        "healthy":
            bool(
                niche.get(
                    "healthy",
                    False,
                )
            ),

        "niche":
            niche,

        "projection":
            str(
                projection_path
            ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="completion_reconciler"
    )

    parser.add_argument(
        "--db",
        type=Path,
        default=default_db,
    )

    subparsers = (
        parser.add_subparsers(
            dest="command",
            required=True,
        )
    )

    subparsers.add_parser(
        "preview"
    )

    subparsers.add_parser(
        "project"
    )

    subparsers.add_parser(
        "health"
    )

    args = parser.parse_args()

    engine = LivingTaskEngine(
        args.db
    )

    if args.command == "health":
        payload = health(
            engine
        )

    else:
        payload = projection(
            engine
        )

        if args.command == "project":
            atomic_json(
                projection_path,
                payload,
            )

            payload = {
                "schema":
                    schema,

                "owner":
                    owner,

                "authority_effect":
                    "none",

                "projection":
                    str(
                        projection_path
                    ),

                "candidate_count":
                    payload[
                        "candidate_count"
                    ],

                "disposition_counts":
                    payload[
                        "disposition_counts"
                    ],

                "confidence_counts":
                    payload[
                        "confidence_counts"
                    ],

                "system_counts":
                    payload[
                        "system_counts"
                    ],
            }

    print(
        json.dumps(
            payload,
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
