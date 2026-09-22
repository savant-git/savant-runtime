#!/usr/bin/env python3
"""
Bounded lexical audit for Savant.

This module searches eligible source files without traversing backups,
generated dimensional records, dependency trees, caches, binary files,
or oversized files.

It reports historical uses of `kinship` for governed migration to `kindred`.
It never rewrites files.
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Final, Iterator


SAVANT_ROOT: Final[Path] = Path("/root/savant-runtime")
DIMENSIONS_ROOT: Final[Path] = (
    SAVANT_ROOT / "vault" / "dimensions"
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
        "generated",
        "node_modules",
        "quarantine",
        "reports",
        "vendor",
        "venv",
    }
)

EXCLUDED_DIMENSION_KEYS: Final[frozenset[str]] = frozenset(
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


def is_generated_dimension_path(path: Path) -> bool:
    try:
        relative = path.relative_to(DIMENSIONS_ROOT)
    except ValueError:
        return False

    if not relative.parts:
        return False

    return relative.parts[0] in EXCLUDED_DIMENSION_KEYS


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
        return

    for current_root, directory_names, file_names in os.walk(
        root,
        topdown=True,
        followlinks=False,
    ):
        current = Path(current_root)

        directory_names[:] = sorted(
            name
            for name in directory_names
            if not should_prune_directory(current / name)
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


def contains_nul_prefix(path: Path) -> bool:
    try:
        with path.open("rb") as handle:
            return b"\x00" in handle.read(8192)
    except OSError:
        return True


def kinship_occurrences(
    root: Path = SAVANT_ROOT,
) -> list[str]:
    occurrences: list[str] = []

    for path in iter_candidate_files(root):
        if contains_nul_prefix(path):
            continue

        try:
            with path.open(
                "r",
                encoding="utf-8",
                errors="strict",
            ) as handle:
                for line_number, line in enumerate(handle, start=1):
                    if KINSHIP_PATTERN.search(line):
                        occurrences.append(
                            f"{path}:{line_number}"
                        )
        except (OSError, UnicodeDecodeError):
            continue

    return occurrences


if __name__ == "__main__":
    for occurrence in kinship_occurrences():
        print(occurrence)
