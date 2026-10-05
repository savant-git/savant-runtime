#!/usr/bin/env python3
"""
Savant Kindred / Kinship compatibility auditor.

Canonical implementation:
    /root/savant-runtime/vault/dimensions/sys/kindred_migration.py

Current authority:

Kindred
    Canonical relationship methodology and universal typed relationship
    substrate/system.

Kinship
    Active functional relationship-plane service/runtime which consumes
    Kindred authority.

Therefore:

- Kinship is NOT a historical alias of Kindred.
- Kindred does NOT supersede Kinship.
- Kinship does NOT supersede Kindred.
- Global Kinship -> Kindred replacement is forbidden.
- Existing Kinship references must be classified by semantic role.
- Only uses demonstrably intending the Kindred methodology are conflicts.

This module preserves the historical command surface:
    plan
    apply
    verify

`apply` is intentionally non-mutating. The former blind lexical migration is
no longer authorized.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import sys
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Final, Iterator, Sequence


SAVANT_ROOT: Final[Path] = Path(
    "/root/savant-runtime"
)

DIMENSIONS_ROOT: Final[Path] = (
    SAVANT_ROOT
    / "vault"
    / "dimensions"
)

SYS_ROOT: Final[Path] = (
    DIMENSIONS_ROOT
    / "sys"
)

REPORT_ROOT: Final[Path] = (
    SYS_ROOT
    / "reports"
    / "kindred-kinship-audit"
)

MAX_FILE_BYTES: Final[int] = (
    4 * 1024 * 1024
)

SEARCHABLE_SUFFIXES: Final[frozenset[str]] = frozenset(
    {
        ".c",
        ".cc",
        ".conf",
        ".cpp",
        ".css",
        ".go",
        ".h",
        ".hpp",
        ".html",
        ".ini",
        ".java",
        ".js",
        ".json",
        ".jsx",
        ".md",
        ".markdown",
        ".mjs",
        ".php",
        ".py",
        ".rb",
        ".rs",
        ".sh",
        ".sql",
        ".toml",
        ".ts",
        ".tsx",
        ".txt",
        ".xml",
        ".yaml",
        ".yml",
    }
)

EXCLUDED_DIRECTORY_NAMES: Final[frozenset[str]] = frozenset(
    {
        ".cache",
        ".git",
        ".hg",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        ".svn",
        ".tox",
        ".venv",
        "__pycache__",
        "backups",
        "cache",
        "coverage",
        "dist",
        "node_modules",
        "quarantine",
        "reports",
        "vendor",
        "venv",
    }
)

GENERATED_DIMENSION_NAMES: Final[frozenset[str]] = frozenset(
    {
        "affinity",
        "context",
        "motive",
        "proof",
        "seed",
        "sense",
        "signal",
        "trajectory",
    }
)

KINSHIP_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"\bkinship\b",
    flags=re.IGNORECASE,
)

KINDRED_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"\bkindred\b",
    flags=re.IGNORECASE,
)

ACTIVE_KINSHIP_MARKERS: Final[tuple[str, ...]] = (
    "service:kinship",
    "runtime/kinship",
    "runtime.kinship",
    "kinship service",
    "kinshipregistry",
    "kinshipgraph",
    "kinshipalgebra",
    "kinshipnode",
    "kinshipvalidationerror",
    "kinshiplookuperror",
    "kinshipdetermination",
    "kinship_registry",
    "kinship_graph",
    "kinship_algebra",
    "kinship_node",
    "kinship service lexeme",
    "functional relationship-plane service",
)

KINDRED_INTENT_MARKERS: Final[tuple[str, ...]] = (
    "relationship methodology",
    "relationship substrate",
    "typed relationship substrate",
    "universal typed relationship",
    "system:kindred",
    "kindred methodology",
    "kindred substrate",
)

OBSOLETE_MIGRATION_MARKERS: Final[tuple[str, ...]] = (
    "kinship is historical",
    "kinship is historical vocabulary",
    "kinship -> kindred",
    "kinship → kindred",
    "source_lexeme",
    "destination_lexeme",
    "replace kinship",
    "replacement_for",
    "kindred-migration-report",
)


@dataclass(frozen=True, slots=True)
class Match:
    path: str
    line: int
    column: int
    text: str
    classification: str
    reason: str


@dataclass(frozen=True, slots=True)
class AuditSummary:
    total_occurrences: int
    active_kinship_occurrences: int
    historical_or_governance_occurrences: int
    suspicious_kindred_intent_occurrences: int
    obsolete_migration_occurrences: int
    unclassified_occurrences: int


def utc_now() -> str:
    return (
        dt.datetime.now(
            dt.timezone.utc
        )
        .replace(
            microsecond=0
        )
        .isoformat()
        .replace(
            "+00:00",
            "Z",
        )
    )


def timestamp_slug() -> str:
    return (
        dt.datetime.now(
            dt.timezone.utc
        )
        .strftime(
            "%Y%m%dT%H%M%SZ"
        )
    )


def sha256_file(
    path: Path,
) -> str:
    digest = hashlib.sha256()

    with path.open(
        "rb"
    ) as handle:
        for chunk in iter(
            lambda: handle.read(
                1024 * 1024
            ),
            b"",
        ):
            digest.update(
                chunk
            )

    return digest.hexdigest()


def atomic_write(
    path: Path,
    content: str,
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    destination_mode = (
        path.stat().st_mode
        & 0o777
        if path.exists()
        else 0o644
    )

    descriptor, temporary_name = (
        tempfile.mkstemp(
            prefix=(
                f".{path.name}."
            ),
            suffix=".tmp",
            dir=str(
                path.parent
            ),
            text=True,
        )
    )

    temporary_path = Path(
        temporary_name
    )

    try:
        with os.fdopen(
            descriptor,
            "w",
            encoding="utf-8",
            newline="\n",
        ) as handle:
            handle.write(
                content
            )
            handle.flush()
            os.fsync(
                handle.fileno()
            )

        os.chmod(
            temporary_path,
            destination_mode,
        )

        os.replace(
            temporary_path,
            path,
        )

    finally:
        if temporary_path.exists():
            temporary_path.unlink()


def atomic_json_write(
    path: Path,
    value: object,
) -> None:
    atomic_write(
        path,
        json.dumps(
            value,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n",
    )


def is_generated_dimension_path(
    path: Path,
) -> bool:
    try:
        relative = path.relative_to(
            DIMENSIONS_ROOT
        )

    except ValueError:
        return False

    if not relative.parts:
        return False

    return (
        relative.parts[0]
        in GENERATED_DIMENSION_NAMES
    )


def should_prune_directory(
    path: Path,
) -> bool:
    if (
        path.name
        in EXCLUDED_DIRECTORY_NAMES
    ):
        return True

    if is_generated_dimension_path(
        path
    ):
        return True

    return False


def iter_candidate_files(
    root: Path = SAVANT_ROOT,
) -> Iterator[Path]:
    if not root.is_dir():
        raise RuntimeError(
            "Savant root does not exist: "
            f"{root}"
        )

    for (
        current_root,
        directory_names,
        file_names,
    ) in os.walk(
        root,
        topdown=True,
        followlinks=False,
    ):
        current = Path(
            current_root
        )

        directory_names[:] = sorted(
            name
            for name
            in directory_names
            if not should_prune_directory(
                current / name
            )
        )

        for file_name in sorted(
            file_names
        ):
            path = (
                current
                / file_name
            )

            if path.is_symlink():
                continue

            if (
                path.suffix.lower()
                not in SEARCHABLE_SUFFIXES
            ):
                continue

            try:
                stat = path.stat()

            except OSError:
                continue

            if (
                stat.st_size
                > MAX_FILE_BYTES
            ):
                continue

            yield path


def is_binary(
    path: Path,
) -> bool:
    try:
        with path.open(
            "rb"
        ) as handle:
            return (
                b"\x00"
                in handle.read(
                    8192
                )
            )

    except OSError:
        return True


def read_text(
    path: Path,
) -> str | None:
    if is_binary(
        path
    ):
        return None

    try:
        return path.read_text(
            encoding="utf-8"
        )

    except (
        OSError,
        UnicodeDecodeError,
    ):
        return None


def normalized(
    value: str,
) -> str:
    return " ".join(
        value
        .casefold()
        .split()
    )


def is_governance_or_history_path(
    path: Path,
) -> bool:
    try:
        relative = path.relative_to(
            SAVANT_ROOT
        )

    except ValueError:
        return False

    parts = {
        part.casefold()
        for part
        in relative.parts
    }

    if (
        "lexicon"
        in parts
    ):
        if path.name in {
            "registry.yaml",
            "TERMINOLOGY_EVOLUTION.yaml",
            "registry.schema.yaml",
            "lexeme.schema.yaml",
            "LEXICON_CONSTITUTION.md",
        }:
            return True

    return False


def classify_occurrence(
    *,
    path: Path,
    line: str,
    surrounding_text: str,
) -> tuple[str, str]:
    lowered_line = normalized(
        line
    )

    lowered_context = normalized(
        surrounding_text
    )

    if is_governance_or_history_path(
        path
    ):
        return (
            "historical_or_governance",
            (
                "Occurrence is inside "
                "lexical authority/history."
            ),
        )

    if any(
        marker
        in lowered_context
        for marker
        in ACTIVE_KINSHIP_MARKERS
    ):
        return (
            "active_kinship",
            (
                "Context identifies the "
                "active Kinship service/runtime."
            ),
        )

    if any(
        marker
        in lowered_context
        for marker
        in OBSOLETE_MIGRATION_MARKERS
    ):
        return (
            "obsolete_migration",
            (
                "Context encodes the obsolete "
                "global Kinship-to-Kindred "
                "migration assumption."
            ),
        )

    if any(
        marker
        in lowered_context
        for marker
        in KINDRED_INTENT_MARKERS
    ):
        return (
            "suspicious_kindred_intent",
            (
                "Kinship appears in context "
                "describing the Kindred "
                "methodology/substrate."
            ),
        )

    if (
        "historical"
        in lowered_line
        or "compatibility"
        in lowered_line
        or "migration"
        in lowered_line
        or "supersed"
        in lowered_line
    ):
        return (
            "historical_or_governance",
            (
                "Line explicitly describes "
                "history, compatibility, "
                "migration, or supersession."
            ),
        )

    return (
        "unclassified",
        (
            "Occurrence requires semantic "
            "classification; no mutation "
            "is authorized."
        ),
    )


def discover_matches() -> list[Match]:
    matches: list[Match] = []

    for path in iter_candidate_files():
        content = read_text(
            path
        )

        if content is None:
            continue

        lines = content.splitlines()

        for line_index, line in enumerate(
            lines
        ):
            if not KINSHIP_PATTERN.search(
                line
            ):
                continue

            context_start = max(
                0,
                line_index - 3,
            )

            context_end = min(
                len(lines),
                line_index + 4,
            )

            context = "\n".join(
                lines[
                    context_start:
                    context_end
                ]
            )

            classification, reason = (
                classify_occurrence(
                    path=path,
                    line=line,
                    surrounding_text=context,
                )
            )

            for match in (
                KINSHIP_PATTERN.finditer(
                    line
                )
            ):
                matches.append(
                    Match(
                        path=str(
                            path
                        ),
                        line=(
                            line_index
                            + 1
                        ),
                        column=(
                            match.start()
                            + 1
                        ),
                        text=(
                            match.group(
                                0
                            )
                        ),
                        classification=(
                            classification
                        ),
                        reason=reason,
                    )
                )

    return matches


def summarize(
    matches: Sequence[Match],
) -> AuditSummary:
    counts = {
        "active_kinship": 0,
        "historical_or_governance": 0,
        "suspicious_kindred_intent": 0,
        "obsolete_migration": 0,
        "unclassified": 0,
    }

    for match in matches:
        counts[
            match.classification
        ] += 1

    return AuditSummary(
        total_occurrences=len(
            matches
        ),
        active_kinship_occurrences=(
            counts[
                "active_kinship"
            ]
        ),
        historical_or_governance_occurrences=(
            counts[
                "historical_or_governance"
            ]
        ),
        suspicious_kindred_intent_occurrences=(
            counts[
                "suspicious_kindred_intent"
            ]
        ),
        obsolete_migration_occurrences=(
            counts[
                "obsolete_migration"
            ]
        ),
        unclassified_occurrences=(
            counts[
                "unclassified"
            ]
        ),
    )


def grouped_paths(
    matches: Sequence[Match],
) -> list[str]:
    return sorted(
        {
            match.path
            for match
            in matches
        }
    )


def report_path(
    stamp: str,
    operation: str,
) -> Path:
    return (
        REPORT_ROOT
        / (
            f"{stamp}__"
            f"{operation}.json"
        )
    )


def write_report(
    *,
    stamp: str,
    operation: str,
    matches: Sequence[Match],
) -> Path:
    summary = summarize(
        matches
    )

    historical = report_path(
        stamp,
        operation,
    )

    latest = (
        REPORT_ROOT
        / "latest.json"
    )

    unresolved = [
        match
        for match
        in matches
        if match.classification
        in {
            "suspicious_kindred_intent",
            "obsolete_migration",
            "unclassified",
        }
    ]

    report = {
        "schema": (
            "savant://vault/dimensions/"
            "kindred-kinship-audit/"
            "2.0.0"
        ),
        "operation": operation,
        "generated_at": utc_now(),
        "authority": {
            "kindred": (
                "relationship methodology "
                "and typed relationship system"
            ),
            "kinship": (
                "active functional "
                "relationship-plane service"
            ),
            "kinship_depends_on_kindred": True,
            "global_replacement_authorized": False,
        },
        "summary": asdict(
            summary
        ),
        "file_count": len(
            grouped_paths(
                matches
            )
        ),
        "passed": (
            len(
                unresolved
            )
            == 0
        ),
        "matches": [
            asdict(
                match
            )
            for match
            in matches
        ],
        "unresolved": [
            asdict(
                match
            )
            for match
            in unresolved
        ],
    }

    atomic_json_write(
        historical,
        report,
    )

    atomic_json_write(
        latest,
        report,
    )

    return historical


def run_plan() -> int:
    stamp = timestamp_slug()

    matches = (
        discover_matches()
    )

    report = write_report(
        stamp=stamp,
        operation="plan",
        matches=matches,
    )

    summary = summarize(
        matches
    )

    print(
        json.dumps(
            {
                "operation": "plan",
                "report": str(
                    report
                ),
                "summary": asdict(
                    summary
                ),
                "mutation_authorized": False,
            },
            indent=2,
            sort_keys=True,
        )
    )

    return 0


def run_apply() -> int:
    stamp = timestamp_slug()

    matches = (
        discover_matches()
    )

    report = write_report(
        stamp=stamp,
        operation="apply",
        matches=matches,
    )

    summary = summarize(
        matches
    )

    print(
        json.dumps(
            {
                "operation": "apply",
                "report": str(
                    report
                ),
                "summary": asdict(
                    summary
                ),
                "mutation_count": 0,
                "mutation_authorized": False,
                "message": (
                    "Global Kinship-to-Kindred "
                    "mutation is not authorized. "
                    "Apply now performs a governed "
                    "classification audit only."
                ),
            },
            indent=2,
            sort_keys=True,
        )
    )

    return 0


def run_verify() -> int:
    stamp = timestamp_slug()

    matches = (
        discover_matches()
    )

    report = write_report(
        stamp=stamp,
        operation="verify",
        matches=matches,
    )

    summary = summarize(
        matches
    )

    unresolved_count = (
        summary
        .suspicious_kindred_intent_occurrences
        + summary
        .obsolete_migration_occurrences
        + summary
        .unclassified_occurrences
    )

    payload = {
        "operation": "verify",
        "report": str(
            report
        ),
        "summary": asdict(
            summary
        ),
        "global_replacement_authorized": False,
        "passed": (
            unresolved_count
            == 0
        ),
    }

    print(
        json.dumps(
            payload,
            indent=2,
            sort_keys=True,
        )
    )

    return (
        0
        if unresolved_count
        == 0
        else 1
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Audit Kindred and Kinship "
            "terminology without conflating "
            "the two active concepts."
        )
    )

    parser.add_argument(
        "operation",
        choices=(
            "plan",
            "apply",
            "verify",
        ),
    )

    return parser


def main(
    argv: Sequence[str] | None = None,
) -> int:
    args = build_parser().parse_args(
        argv
    )

    if args.operation == "plan":
        return run_plan()

    if args.operation == "apply":
        return run_apply()

    if args.operation == "verify":
        return run_verify()

    raise AssertionError(
        args.operation
    )


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
