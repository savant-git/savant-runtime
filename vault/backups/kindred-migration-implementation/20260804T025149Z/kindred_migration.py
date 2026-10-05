#!/usr/bin/env python3
"""
Governed Savant lexical migration from `kinship` to `kindred`.

Canonical implementation:
    /root/savant-runtime/vault/dimensions/sys/kindred_migration.py

The migration:

- scans eligible Savant source and data files
- excludes backups, reports, caches, dependencies, generated dimensional data,
  binary files, and oversized files
- performs whole-word, case-preserving replacement
- creates immutable backups before mutation
- binds every mutation to the source file's pre-mutation SHA-256
- writes a complete JSON receipt
- verifies that no eligible occurrence remains
- supports plan, apply, and verify modes
- never mutates filenames or directory names silently
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import shutil
import sys
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Final, Iterator, Sequence


SAVANT_ROOT: Final[Path] = Path("/root/savant-runtime")
DIMENSIONS_ROOT: Final[Path] = (
    SAVANT_ROOT / "vault" / "dimensions"
)
SYS_ROOT: Final[Path] = DIMENSIONS_ROOT / "sys"

BACKUP_ROOT: Final[Path] = (
    SAVANT_ROOT
    / "vault"
    / "backups"
    / "kindred-migration"
)
REPORT_ROOT: Final[Path] = (
    SYS_ROOT
    / "reports"
    / "kindred-migration"
)

MAX_FILE_BYTES: Final[int] = 4 * 1024 * 1024

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


@dataclass(frozen=True)
class Match:
    path: str
    line: int
    column: int
    text: str


@dataclass(frozen=True)
class Mutation:
    path: str
    backup: str
    before_sha256: str
    after_sha256: str
    replacement_count: int


def utc_now() -> str:
    return (
        dt.datetime.now(dt.timezone.utc)
        .replace(microsecond=0)
        .isoformat()
    )


def timestamp_slug() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime(
        "%Y%m%dT%H%M%SZ"
    )


def sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as handle:
        for block in iter(
            lambda: handle.read(1024 * 1024),
            b"",
        ):
            digest.update(block)

    return digest.hexdigest()


def atomic_write(path: Path, content: str) -> None:
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=str(path.parent),
        text=True,
    )
    temporary_path = Path(temporary_name)

    try:
        with os.fdopen(
            descriptor,
            "w",
            encoding="utf-8",
            newline="\n",
        ) as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())

        os.chmod(
            temporary_path,
            path.stat().st_mode & 0o777,
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
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

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


def is_generated_dimension_path(path: Path) -> bool:
    try:
        relative = path.relative_to(
            DIMENSIONS_ROOT
        )
    except ValueError:
        return False

    if not relative.parts:
        return False

    return relative.parts[0] in GENERATED_DIMENSION_NAMES


def should_prune_directory(path: Path) -> bool:
    if path.name in EXCLUDED_DIRECTORY_NAMES:
        return True

    if is_generated_dimension_path(path):
        return True

    return False


def iter_candidate_files(
    root: Path = SAVANT_ROOT,
) -> Iterator[Path]:
    if not root.is_dir():
        raise RuntimeError(
            f"Savant root does not exist: {root}"
        )

    for current_root, directory_names, file_names in os.walk(
        root,
        topdown=True,
        followlinks=False,
    ):
        current = Path(current_root)

        directory_names[:] = sorted(
            name
            for name in directory_names
            if not should_prune_directory(
                current / name
            )
        )

        for file_name in sorted(file_names):
            path = current / file_name

            if path.is_symlink():
                continue

            if path.suffix.lower() not in SEARCHABLE_SUFFIXES:
                continue

            try:
                stat = path.stat()
            except OSError:
                continue

            if stat.st_size > MAX_FILE_BYTES:
                continue

            yield path


def is_binary(path: Path) -> bool:
    try:
        with path.open("rb") as handle:
            return b"\x00" in handle.read(8192)
    except OSError:
        return True


def read_text(path: Path) -> str | None:
    if is_binary(path):
        return None

    try:
        return path.read_text(
            encoding="utf-8",
        )
    except (
        OSError,
        UnicodeDecodeError,
    ):
        return None


def replacement_for(value: str) -> str:
    if value.isupper():
        return "KINDRED"

    if value[:1].isupper():
        return "Kindred"

    return "kindred"


def replace_content(
    content: str,
) -> tuple[str, int]:
    return KINSHIP_PATTERN.subn(
        lambda match: replacement_for(
            match.group(0)
        ),
        content,
    )


def discover_matches() -> list[Match]:
    matches: list[Match] = []

    for path in iter_candidate_files():
        content = read_text(path)

        if content is None:
            continue

        for line_number, line in enumerate(
            content.splitlines(),
            start=1,
        ):
            for match in KINSHIP_PATTERN.finditer(
                line
            ):
                matches.append(
                    Match(
                        path=str(path),
                        line=line_number,
                        column=match.start() + 1,
                        text=match.group(0),
                    )
                )

    return matches


def grouped_paths(
    matches: Sequence[Match],
) -> list[Path]:
    return sorted(
        {
            Path(match.path)
            for match in matches
        }
    )


def backup_file(
    path: Path,
    stamp: str,
) -> Path:
    relative = path.relative_to(
        SAVANT_ROOT
    )
    destination = (
        BACKUP_ROOT
        / stamp
        / relative
    )

    destination.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    shutil.copy2(
        path,
        destination,
    )

    return destination


def mutate_file(
    path: Path,
    stamp: str,
) -> Mutation:
    content = read_text(path)

    if content is None:
        raise RuntimeError(
            f"Unable to read eligible file: {path}"
        )

    replacement, count = replace_content(
        content
    )

    if count == 0:
        raise RuntimeError(
            f"Mutation target no longer contains kinship: {path}"
        )

    before_digest = sha256_file(path)
    backup = backup_file(
        path,
        stamp,
    )

    atomic_write(
        path,
        replacement,
    )

    after_digest = sha256_file(path)

    if before_digest == after_digest:
        raise RuntimeError(
            f"Mutation did not change digest: {path}"
        )

    if KINSHIP_PATTERN.search(
        replacement
    ):
        raise RuntimeError(
            f"Mutation left eligible occurrences in file: {path}"
        )

    return Mutation(
        path=str(path),
        backup=str(backup),
        before_sha256=before_digest,
        after_sha256=after_digest,
        replacement_count=count,
    )


def report_path(
    stamp: str,
    operation: str,
) -> Path:
    return (
        REPORT_ROOT
        / f"{stamp}__{operation}.json"
    )


def write_report(
    *,
    stamp: str,
    operation: str,
    initial_matches: Sequence[Match],
    mutations: Sequence[Mutation],
    remaining_matches: Sequence[Match],
) -> Path:
    historical = report_path(
        stamp,
        operation,
    )
    latest = (
        REPORT_ROOT / "latest.json"
    )

    report = {
        "schema": (
            "savant://vault/dimensions/"
            "kindred-migration-report/1.0.0"
        ),
        "operation": operation,
        "generated_at": utc_now(),
        "source_lexeme": "kinship",
        "destination_lexeme": "kindred",
        "initial_occurrence_count": len(
            initial_matches
        ),
        "initial_file_count": len(
            grouped_paths(initial_matches)
        ),
        "mutation_count": len(
            mutations
        ),
        "replacement_count": sum(
            mutation.replacement_count
            for mutation in mutations
        ),
        "remaining_occurrence_count": len(
            remaining_matches
        ),
        "passed": (
            operation != "verify"
            or not remaining_matches
        ),
        "initial_matches": [
            asdict(match)
            for match in initial_matches
        ],
        "mutations": [
            asdict(mutation)
            for mutation in mutations
        ],
        "remaining_matches": [
            asdict(match)
            for match in remaining_matches
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
    matches = discover_matches()

    report = write_report(
        stamp=stamp,
        operation="plan",
        initial_matches=matches,
        mutations=[],
        remaining_matches=matches,
    )

    result = {
        "operation": "plan_kindred_migration",
        "passed": True,
        "occurrence_count": len(matches),
        "file_count": len(
            grouped_paths(matches)
        ),
        "report": str(report),
        "matches": [
            asdict(match)
            for match in matches
        ],
    }

    print(
        json.dumps(
            result,
            indent=2,
            sort_keys=True,
        )
    )

    return 0


def run_apply() -> int:
    stamp = timestamp_slug()
    initial_matches = discover_matches()
    mutations: list[Mutation] = []

    for path in grouped_paths(
        initial_matches
    ):
        mutations.append(
            mutate_file(
                path,
                stamp,
            )
        )

    remaining_matches = discover_matches()

    report = write_report(
        stamp=stamp,
        operation="apply",
        initial_matches=initial_matches,
        mutations=mutations,
        remaining_matches=remaining_matches,
    )

    result = {
        "operation": "apply_kindred_migration",
        "passed": not remaining_matches,
        "initial_occurrence_count": len(
            initial_matches
        ),
        "mutated_file_count": len(
            mutations
        ),
        "replacement_count": sum(
            mutation.replacement_count
            for mutation in mutations
        ),
        "remaining_occurrence_count": len(
            remaining_matches
        ),
        "report": str(report),
    }

    print(
        json.dumps(
            result,
            indent=2,
            sort_keys=True,
        )
    )

    return 0 if not remaining_matches else 1


def run_verify() -> int:
    stamp = timestamp_slug()
    matches = discover_matches()

    report = write_report(
        stamp=stamp,
        operation="verify",
        initial_matches=matches,
        mutations=[],
        remaining_matches=matches,
    )

    result = {
        "operation": "verify_kindred_migration",
        "passed": not matches,
        "remaining_occurrence_count": len(
            matches
        ),
        "remaining_file_count": len(
            grouped_paths(matches)
        ),
        "report": str(report),
        "remaining_matches": [
            asdict(match)
            for match in matches
        ],
    }

    print(
        json.dumps(
            result,
            indent=2,
            sort_keys=True,
        )
    )

    return 0 if not matches else 1


def parse_arguments(
    argv: Sequence[str],
) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Migrate Savant lexical uses of "
            "kinship to kindred."
        )
    )

    parser.add_argument(
        "command",
        choices=(
            "plan",
            "apply",
            "verify",
        ),
    )

    return parser.parse_args(argv)


def main(
    argv: Sequence[str] | None = None,
) -> int:
    arguments = parse_arguments(
        argv
        if argv is not None
        else sys.argv[1:]
    )

    if arguments.command == "plan":
        return run_plan()

    if arguments.command == "apply":
        return run_apply()

    if arguments.command == "verify":
        return run_verify()

    raise RuntimeError(
        f"Unsupported command: {arguments.command}"
    )


if __name__ == "__main__":
    raise SystemExit(main())
