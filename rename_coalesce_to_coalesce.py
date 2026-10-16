#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any


DEFAULT_ROOT = Path("/root/savant-runtime")

SKIP_DIRECTORY_NAMES = {
    ".git",
    ".hg",
    ".svn",
    "__pycache__",
    "node_modules",
    ".venv",
    "venv",
    "dist",
}

SKIP_SUFFIXES = {
    ".pyc",
    ".pyo",
    ".so",
    ".a",
    ".o",
    ".class",
    ".jar",
    ".zip",
    ".gz",
    ".bz2",
    ".xz",
    ".7z",
    ".tar",
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".webp",
    ".ico",
    ".pdf",
    ".woff",
    ".woff2",
    ".ttf",
    ".otf",
}

REPLACEMENTS = (
    ("COALESCE", "COALESCE"),
    ("Coalesce", "Coalesce"),
    ("coalesce", "coalesce"),
)


def replace_identity(value: str) -> str:
    result = value

    for old, new in REPLACEMENTS:
        result = result.replace(old, new)

    return result


def skipped(path: Path, root: Path) -> bool:
    try:
        relative = path.relative_to(root)
    except ValueError:
        return True

    return any(
        part in SKIP_DIRECTORY_NAMES
        for part in relative.parts
    )


def candidate_paths(root: Path) -> list[Path]:
    found: list[Path] = []

    for directory, directories, files in os.walk(
        root,
        topdown=True,
        followlinks=False,
    ):
        current = Path(directory)

        directories[:] = [
            name
            for name in directories
            if name not in SKIP_DIRECTORY_NAMES
        ]

        if skipped(current, root):
            continue

        for name in files:
            path = current / name

            if path.suffix.lower() in SKIP_SUFFIXES:
                continue

            if path.is_symlink():
                continue

            found.append(path)

    return sorted(found)


def read_text(path: Path) -> str | None:
    try:
        raw = path.read_bytes()
    except OSError:
        return None

    if b"\x00" in raw:
        return None

    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return None


def content_changes(
    root: Path,
) -> list[dict[str, Any]]:
    changes: list[dict[str, Any]] = []

    for path in candidate_paths(root):
        original = read_text(path)

        if original is None:
            continue

        updated = replace_identity(original)

        if updated == original:
            continue

        changes.append(
            {
                "path": path,
                "original": original,
                "updated": updated,
            }
        )

    return changes


def rename_candidates(
    root: Path,
) -> list[tuple[Path, Path]]:
    candidates: list[tuple[Path, Path]] = []

    for directory, directories, files in os.walk(
        root,
        topdown=False,
        followlinks=False,
    ):
        current = Path(directory)

        if skipped(current, root):
            continue

        for name in files:
            source = current / name

            if source.is_symlink():
                continue

            replacement = replace_identity(name)

            if replacement != name:
                candidates.append(
                    (
                        source,
                        current / replacement,
                    )
                )

        for name in directories:
            source = current / name

            if (
                name in SKIP_DIRECTORY_NAMES
                or source.is_symlink()
            ):
                continue

            replacement = replace_identity(name)

            if replacement != name:
                candidates.append(
                    (
                        source,
                        current / replacement,
                    )
                )

    candidates.sort(
        key=lambda item: (
            -len(item[0].parts),
            str(item[0]),
        )
    )

    return candidates


def validate_rename_collisions(
    candidates: list[tuple[Path, Path]],
) -> None:
    sources = {
        source
        for source, _ in candidates
    }

    targets: dict[Path, Path] = {}

    for source, target in candidates:
        previous = targets.get(target)

        if (
            previous is not None
            and previous != source
        ):
            raise RuntimeError(
                "rename collision: "
                f"{previous} and {source} -> {target}"
            )

        targets[target] = source

        if (
            target.exists()
            and target not in sources
            and target != source
        ):
            raise RuntimeError(
                "rename target already exists: "
                f"{source} -> {target}"
            )


def manifest_view(
    root: Path,
    contents: list[dict[str, Any]],
    renames: list[tuple[Path, Path]],
) -> dict[str, Any]:
    return {
        "schema": "savant://coalesce/identity-migration/1",
        "operation": "rename-coalesce-to-coalesce",
        "root": str(root),
        "content_files": [
            str(item["path"])
            for item in contents
        ],
        "renames": [
            {
                "from": str(source),
                "to": str(target),
            }
            for source, target in renames
        ],
        "content_file_count": len(contents),
        "rename_count": len(renames),
    }


def write_content(
    changes: list[dict[str, Any]],
) -> None:
    for item in changes:
        path: Path = item["path"]
        updated: str = item["updated"]

        temporary = path.with_name(
            path.name + ".coalesce-migration-tmp"
        )

        stat = path.stat()

        temporary.write_text(
            updated,
            encoding="utf-8",
        )

        os.chmod(
            temporary,
            stat.st_mode,
        )

        os.replace(
            temporary,
            path,
        )


def apply_renames(
    candidates: list[tuple[Path, Path]],
) -> list[tuple[Path, Path]]:
    completed: list[tuple[Path, Path]] = []

    for source, target in candidates:
        if not source.exists():
            continue

        target.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        source.rename(target)

        completed.append(
            (
                source,
                target,
            )
        )

    return completed


def remaining_matches(
    root: Path,
) -> list[str]:
    matches: list[str] = []

    for path in candidate_paths(root):
        if "coalesce" in path.name.lower():
            matches.append(
                f"path:{path}"
            )

        text = read_text(path)

        if text is None:
            continue

        if "coalesce" in text.lower():
            matches.append(
                f"content:{path}"
            )

    return matches


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Deterministically migrate the Savant "
            "identity Coalesce to Coalesce."
        )
    )

    parser.add_argument(
        "--root",
        type=Path,
        default=DEFAULT_ROOT,
    )

    parser.add_argument(
        "--apply",
        action="store_true",
    )

    args = parser.parse_args()

    root = args.root.resolve()

    if not root.is_dir():
        raise RuntimeError(
            f"root does not exist: {root}"
        )

    contents = content_changes(root)
    renames = rename_candidates(root)

    validate_rename_collisions(
        renames
    )

    manifest = manifest_view(
        root,
        contents,
        renames,
    )

    if not args.apply:
        manifest["applied"] = False

        print(
            json.dumps(
                manifest,
                indent=2,
                sort_keys=True,
            )
        )

        return 0

    write_content(contents)

    completed = apply_renames(
        renames
    )

    leftovers = remaining_matches(
        root
    )

    result = {
        **manifest,
        "applied": True,
        "completed_rename_count": len(
            completed
        ),
        "remaining_coalesce_matches": leftovers,
        "passed": not leftovers,
    }

    print(
        json.dumps(
            result,
            indent=2,
            sort_keys=True,
        )
    )

    if leftovers:
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
