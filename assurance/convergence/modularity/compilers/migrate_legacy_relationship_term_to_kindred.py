#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import os
import re
import stat
import tempfile
from pathlib import Path


schema = "savant.assurance.migrate-legacy-relationship-term-to-kindred.v5"
authority_effect = "none"

root = Path("/root/savant-runtime")

legacy_term = "".join(("kin", "ship"))
canonical_term = "kindred"

pattern = re.compile(
    re.escape(legacy_term),
    re.IGNORECASE,
)

excluded_top_level = {
    "authority",
    "canon-system",
    "vault",
    "s3_downloads",
}

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

excluded_relative_prefixes = (
    Path("runtime/reports"),
)

generated_relative_paths = {
    Path(
        "ontology/obelisks/_template/segue/gates/_template/segue/"
        "innates/_template/segue/exiles/niche/apps/atlas/assets/atlas.json"
    ),
    Path(
        "runtime/living-state/cache.json"
    ),
}

excluded_exact_relative = {
    Path(
        "assurance/convergence/modularity/compilers/"
        "migrate_legacy_relationship_term_to_kindred.py"
    ),
    Path(
        "assurance/convergence/modularity/checkers/"
        "check_kindred_terminology.py"
    ),
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


class MigrationError(RuntimeError):
    pass


def relative(
    path: Path,
) -> Path:
    return path.relative_to(root)


def has_prefix(
    path: Path,
    prefix: Path,
) -> bool:
    return (
        len(path.parts) >= len(prefix.parts)
        and path.parts[:len(prefix.parts)]
        == prefix.parts
    )


def excluded(
    path: Path,
) -> bool:
    try:
        rel = relative(path)
    except ValueError:
        return True

    if rel in excluded_exact_relative:
        return True

    if rel in generated_relative_paths:
        return True

    if (
        rel.parts
        and rel.parts[0] in excluded_top_level
    ):
        return True

    return any(
        has_prefix(rel, prefix)
        for prefix in excluded_relative_prefixes
    )


def regular_file_without_symlink(
    path: Path,
) -> bool:
    try:
        info = path.lstat()
    except OSError:
        return False

    return (
        not stat.S_ISLNK(info.st_mode)
        and stat.S_ISREG(info.st_mode)
    )


def candidate(
    path: Path,
) -> bool:
    return (
        not excluded(path)
        and regular_file_without_symlink(path)
        and path.suffix.lower() in candidate_suffixes
    )


def iter_candidates():
    for directory, dirs, filenames in os.walk(
        root,
        topdown=True,
        followlinks=False,
    ):
        directory_path = Path(directory)

        retained = []

        for name in sorted(dirs):
            child = directory_path / name

            if name in excluded_directory_names:
                continue

            if excluded(child):
                continue

            try:
                info = child.lstat()
            except OSError:
                continue

            if stat.S_ISLNK(info.st_mode):
                continue

            if stat.S_ISDIR(info.st_mode):
                retained.append(name)

        dirs[:] = retained

        for filename in sorted(filenames):
            path = directory_path / filename

            if candidate(path):
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
                    "relative_path": str(relative(path)),
                    "occurrences": occurrences,
                }
            )

    matches.sort(
        key=lambda item: item["relative_path"]
    )

    return matches


def generated_residue():
    residue = []

    for rel in sorted(
        generated_relative_paths,
        key=str,
    ):
        path = root / rel

        if not regular_file_without_symlink(path):
            continue

        occurrences = count_occurrences(path)

        if occurrences:
            residue.append(
                {
                    "path": str(path),
                    "relative_path": str(rel),
                    "occurrences": occurrences,
                    "classification":
                        "derived-projection-or-runtime-cache",
                    "mutation":
                        "preserved",
                }
            )

    return residue


def migrate_file(
    path: Path,
) -> int:
    if not regular_file_without_symlink(path):
        raise MigrationError(
            "refusing non-regular or symlinked file: "
            + str(path)
        )

    original_stat = path.stat()

    fd, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".kindred.tmp",
        dir=str(path.parent),
    )

    temporary = Path(temporary_name)
    changed = 0

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
                    migrated, count = pattern.subn(
                        replacement,
                        line,
                    )

                    changed += count
                    destination.write(migrated)

            destination.flush()
            os.fsync(destination.fileno())

        if changed == 0:
            temporary.unlink(
                missing_ok=True
            )
            return 0

        os.chmod(
            temporary,
            stat.S_IMODE(original_stat.st_mode),
        )

        try:
            os.chown(
                temporary,
                original_stat.st_uid,
                original_stat.st_gid,
            )
        except PermissionError:
            pass

        os.replace(
            temporary,
            path,
        )

        return changed

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
            "generated_residue": generated_residue(),
            "generated_residue_mutated": False,
            "symlinks_followed": False,
        }

    changed_files = 0
    changed_occurrences = 0

    for item in matches:
        changed = migrate_file(
            Path(item["path"])
        )

        if changed:
            changed_files += 1
            changed_occurrences += changed

    remaining = discover()

    if remaining:
        raise MigrationError(
            "active implementation terminology remains: "
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
        "generated_residue": generated_residue(),
        "generated_residue_mutated": False,
        "symlinks_followed": False,
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
