#!/usr/bin/env python3

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable


schema = "savant.assurance.migrate-active-kinship-to-kindred.v2"
authority_effect = "none"

root = Path("/root/savant-runtime")

legacy_term = "kinship"
canonical_term = "kindred"

excluded_directory_names = {
    ".git",
    ".hg",
    ".svn",
    "__pycache__",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".tox",
    ".venv",
    "venv",
    "node_modules",
}

preserved_roots = (
    root / "vault" / "wip" / "backups",
    root / "runtime" / "reports",
)

historical_name_fragments = (
    "backup",
    "snapshot",
    "sdump",
    "archive",
    "historical",
)

candidate_suffixes = {
    ".py",
    ".json",
    ".jsonl",
    ".yaml",
    ".yml",
    ".toml",
    ".ini",
    ".cfg",
    ".conf",
    ".service",
    ".socket",
    ".path",
    ".target",
    ".sh",
    ".bash",
    ".zsh",
    ".md",
    ".txt",
    ".html",
    ".css",
    ".js",
    ".mjs",
    ".cjs",
    ".ts",
    ".tsx",
    ".jsx",
    ".sql",
    ".graphql",
}

candidate_names_without_suffix = {
    "makefile",
    "dockerfile",
}

term_pattern = re.compile(
    r"kinship",
    re.IGNORECASE,
)


class MigrationError(RuntimeError):
    pass


def is_under(
    path: Path,
    parent: Path,
) -> bool:
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


def is_preserved(
    path: Path,
) -> bool:
    resolved = path.resolve()

    for preserved_root in preserved_roots:
        if is_under(
            resolved,
            preserved_root.resolve(),
        ):
            return True

    relative = resolved.relative_to(
        root.resolve()
    )

    for part in relative.parts:
        lowered = part.lower()

        if any(
            fragment in lowered
            for fragment in historical_name_fragments
        ):
            return True

    return False


def is_candidate(
    path: Path,
) -> bool:
    if not path.is_file():
        return False

    lowered = path.name.lower()

    if lowered in candidate_names_without_suffix:
        return True

    return path.suffix.lower() in candidate_suffixes


def iter_candidates() -> Iterable[Path]:
    for directory, dirs, files in os.walk(
        root
    ):
        dirs[:] = sorted(
            name
            for name in dirs
            if name not in excluded_directory_names
        )

        directory_path = Path(directory)

        for filename in sorted(files):
            path = directory_path / filename

            if is_candidate(path):
                yield path


def replacement_for(
    match: re.Match[str],
) -> str:
    value = match.group(0)

    if value.isupper():
        return canonical_term.upper()

    if value[:1].isupper():
        return canonical_term.capitalize()

    return canonical_term


def count_matches(
    path: Path,
) -> int:
    count = 0

    try:
        with path.open(
            "r",
            encoding="utf-8",
            errors="strict",
        ) as handle:
            for line in handle:
                count += len(
                    term_pattern.findall(line)
                )

    except (
        UnicodeDecodeError,
        OSError,
    ):
        return 0

    return count


def sha256_file(
    path: Path,
) -> str:
    digest = hashlib.sha256()

    with path.open(
        "rb"
    ) as handle:
        while True:
            chunk = handle.read(
                1024 * 1024
            )

            if not chunk:
                break

            digest.update(chunk)

    return digest.hexdigest()


def backup_path(
    source: Path,
    run_id: str,
) -> Path:
    return (
        root
        / "vault"
        / "wip"
        / "backups"
        / "kindred-terminology-migration"
        / run_id
        / source.relative_to(root)
    )


def backup_file(
    source: Path,
    run_id: str,
) -> Path:
    destination = backup_path(
        source,
        run_id,
    )

    destination.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    shutil.copy2(
        source,
        destination,
    )

    return destination


def migrate_file(
    path: Path,
) -> tuple[int, str, str]:
    before_digest = sha256_file(
        path
    )

    stat = path.stat()

    fd, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=str(path.parent),
    )

    temporary = Path(
        temporary_name
    )

    occurrences = 0

    try:
        with os.fdopen(
            fd,
            "w",
            encoding="utf-8",
            newline="",
        )
