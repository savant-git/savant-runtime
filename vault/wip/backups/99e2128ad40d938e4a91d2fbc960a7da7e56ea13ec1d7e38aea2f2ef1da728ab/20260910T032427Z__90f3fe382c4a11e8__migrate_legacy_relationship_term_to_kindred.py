#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import os
import re
import tempfile
from pathlib import Path


schema = "savant.assurance.migrate-legacy-relationship-term-to-kindred.v3"
authority_effect = "none"

root = Path("/root/savant-runtime")

legacy_term = "".join(("kin", "ship"))
canonical_term = "kindred"

self_path = (
    root
    / "assurance"
    / "convergence"
    / "modularity"
    / "compilers"
    / "migrate_legacy_relationship_term_to_kindred.py"
)

checker_path = (
    root
    / "assurance"
    / "convergence"
    / "modularity"
    / "checkers"
    / "check_kindred_terminology.py"
)

excluded_roots = (
    root / "authority",
    root / "canon-system",
    root / "vault",
    root / "runtime" / "reports",
)

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

pattern = re.compile(
    re.escape(legacy_term),
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


def excluded(
    path: Path,
) -> bool:
    resolved = path.resolve()

    if resolved in {
        self_path.resolve(),
        checker_path.resolve(),
    }:
        return True

    return any(
        is_under(
            resolved,
            excluded_root.resolve(),
        )
        for excluded_root in excluded_roots
    )


def iter_candidates():
    for directory, dirs, filenames in os.walk(root):
        directory_path = Path(directory)

        dirs[:] = [
            name
            for name in sorted(dirs)
            if (
                name not in excluded_directory_names
                and not excluded(
                    directory_path / name
                )
            )
        ]

        for filename in sorted(filenames):
            path = directory_path / filename

            if excluded(path):
                continue

            if (
                not path.is_file()
                or path.suffix.lower()
                not in candidate_suffixes
            ):
                continue

            yield path


def replacement(
    match: re.Match[str],
) -> str:
    value = match.group(0)

    if value.isupper():
        return canonical_term.upper()

    if value[:1].isupper():
        return canonical_term.capitalize()

    return canonical_term


def count_occurrences(
    path: Path,
) -> int:
    total = 0

    try:
        with path.open(
            "r",
            encoding="utf-8",
            errors="strict",
        ) as handle:
            for line in handle:
                total += len(
                    pattern.findall(line)
                )

    except (
        OSError,
        UnicodeDecodeError,
    ):
        return 0

    return total


def discover():
    matches = []

    for path in iter_candidates():
        occurrences = count_occurrences(path)

        if occurrences:
            matches.append(
                {
                    "path": str(path),
                    "occurrences": occurrences,
                }
            )

    matches.sort(
        key=lambda item: item["path"]
    )

    return matches


def migrate_file(
    path: Path,
) -> int:
    stat = path.stat()

    fd, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".kindred.tmp",
        dir=str(path.parent),
    )

    temporary = Path(temporary_name)
    occurrences = 0

    try:
        with os.fdopen(
            fd,
            "w",
            encoding="utf-8",
            newline="",
        ) as destination:
            with path.open(
                "r",
                encoding="utf-8",
                errors="strict",
                newline="",
            ) as source:
                for line in source:
                    migrated, changed = pattern.subn(
                        replacement,
                        line,
                    )

                    occurrences += changed
                    destination.write(migrated)

            destination.flush()
            os.fsync(destination.fileno())

        if occurrences == 0:
            temporary.unlink(
                missing_ok=True
            )
            return 0

        os.chmod(
            temporary,
            stat.st_mode,
        )

        try:
            os.chown(
                temporary,
                stat.st_uid,
                stat.st_gid,
            )
        except PermissionError:
            pass

        os.replace(
            temporary,
            path,
        )

        return occurrences

    except Exception:
        temporary.unlink(
            missing_ok=True
        )
        raise


def run(
    apply: bool,
):
    matches = discover()

    if not apply:
        return {
            "schema": schema,
            "authority_effect": authority_effect,
            "status": "passed",
            "apply": False,
            "canonical_term": canonical_term,
            "active_files_would_change": len(matches),
            "active_occurrences": sum(
                int(item["occurrences"])
                for item in matches
            ),
            "matches": matches,
        }

    changed_files = 0
    changed_occurrences = 0

    for item in matches:
        occurrences = migrate_file(
            Path(item["path"])
        )

        if occurrences:
            changed_files += 1
            changed_occurrences += occurrences

    remaining = discover()

    if remaining:
        raise MigrationError(
            "active legacy relationship terminology remains: "
            + json.dumps(
                remaining,
                sort_keys=True,
            )
        )

    return {
        "schema": schema,
        "authority_effect": authority_effect,
        "status": "passed",
        "apply": True,
        "canonical_term": canonical_term,
        "active_files_changed": changed_files,
        "active_occurrences_changed": changed_occurrences,
        "remaining_active_matches": [],
        "authority_mutated": False,
        "canon_mutated": False,
        "vault_mutated": False,
        "runtime_reports_mutated": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--apply",
        action="store_true",
    )

    args = parser.parse_args()

    try:
        print(
            json.dumps(
                run(args.apply),
                indent=2,
                sort_keys=True,
            )
        )
        return 0

    except Exception as exc:
        print(
            json.dumps(
                {
                    "schema": schema,
                    "authority_effect": authority_effect,
                    "status": "failed",
                    "error": str(exc),
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
