#!/usr/bin/env python3
"""Generate the permanent Codex audit inventory without following symlinks."""

from __future__ import annotations

import csv
import mimetypes
import os
import stat
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "docs" / "codex-audit" / "FILE_INVENTORY.tsv"
FIELDS = (
    "relative path",
    "file type",
    "size",
    "ownership classification",
    "generated/vendor/cache/source status",
    "responsible subsystem",
    "audit status",
    "action taken",
    "validation status",
    "notes",
)


def classify(path: Path, mode: int) -> tuple[str, str, str, str, str]:
    rel = path.relative_to(ROOT).as_posix()
    top = rel.split("/", 1)[0]
    if stat.S_ISDIR(mode):
        kind = "directory"
    elif stat.S_ISLNK(mode):
        kind = "symlink"
    else:
        kind = mimetypes.guess_type(path.name)[0] or "file"

    if rel == ".git" or rel.startswith(".git/"):
        return kind, "tool-owned", "generated metadata", "version control", "Git internal; not editable source"
    if stat.S_ISLNK(mode):
        target = os.readlink(path)
        external = target.startswith("/")
        note = f"symlink target is {'external' if external else 'repository-relative'}; target not traversed"
        return kind, "project-owned", "integration link", top, note
    if top in {"_reports", "relics", "current_runtime_source_dump_"} or "source_dump" in path.name:
        return kind, "project artifact", "generated/archive", top, "retained evidence; metadata/content role reviewed separately"
    if path.suffix in {".sqlite", ".sqlite3", ".db"}:
        return kind, "project artifact", "generated database", top, "binary database; validate structurally, do not line-review"
    if path.name.endswith((".save", ".before_api_debug_20260624T223930Z", ".before_envoy_connection_20260626T074531Z")):
        return kind, "project artifact", "backup", top, "historical backup; compare with source of truth"
    if top in {"authority_graph", "vault"} or rel.startswith("canon-system/projections/"):
        return kind, "project-owned", "generated projection", top, "generator/source-of-truth relationship requires validation"
    if stat.S_ISDIR(mode):
        return kind, "project-owned", "source container", top, "directory inventory entry"
    return kind, "project-owned", "source", top, "reviewable project file"


def entries() -> list[tuple[str, os.stat_result]]:
    result: list[tuple[str, os.stat_result]] = []
    for base, dirs, files in os.walk(ROOT, topdown=True, followlinks=False):
        dirs.sort()
        files.sort()
        base_path = Path(base)
        if base_path == ROOT:
            names = dirs + files
        else:
            result.append((base_path.relative_to(ROOT).as_posix(), base_path.lstat()))
            names = files
        for name in names:
            path = base_path / name
            if path.is_symlink() or (base_path == ROOT and name in files):
                result.append((path.relative_to(ROOT).as_posix(), path.lstat()))
    return sorted({rel: info for rel, info in result}.items())


def main() -> None:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, delimiter="\t", lineterminator="\n")
        writer.writerow(FIELDS)
        for rel, info in entries():
            path = ROOT / rel
            kind, ownership, status, subsystem, notes = classify(path, info.st_mode)
            audit = "excluded" if rel == ".git" or rel.startswith(".git/") else "pending"
            action = "inventory only" if audit == "excluded" else "none yet"
            validation = "not applicable" if audit == "excluded" else "pending"
            writer.writerow((rel, kind, info.st_size, ownership, status, subsystem, audit, action, validation, notes))


if __name__ == "__main__":
    main()
