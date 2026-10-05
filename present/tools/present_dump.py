#!/usr/bin/env python3

from __future__ import annotations

from pathlib import Path
import hashlib
import json
import os
import sys
from datetime import datetime, timezone


ROOT = Path("/root/savant-runtime/present")
OUTPUT = Path("/root/savant-runtime/present/present-current-dump.txt")


INCLUDE_SUFFIXES = {
    ".html",
    ".css",
    ".js",
    ".json",
    ".md",
    ".txt",
    ".py",
    ".conf",
}

EXCLUDE_NAMES = {
    "present-current-dump.txt",
}

MAX_FILE_BYTES = 2 * 1024 * 1024


def sha256(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)

    return digest.hexdigest()


def eligible(path: Path) -> bool:
    if not path.is_file():
        return False

    if path.name in EXCLUDE_NAMES:
        return False

    if path.suffix.lower() not in INCLUDE_SUFFIXES:
        return False

    try:
        return path.stat().st_size <= MAX_FILE_BYTES
    except OSError:
        return False


def main() -> int:
    if not ROOT.is_dir():
        print(f"ERROR: missing root: {ROOT}", file=sys.stderr)
        return 1

    files = sorted(
        (path for path in ROOT.rglob("*") if eligible(path)),
        key=lambda path: str(path.relative_to(ROOT)),
    )

    manifest = []

    for path in files:
        stat = path.stat()

        manifest.append(
            {
                "path": str(path),
                "relative_path": str(path.relative_to(ROOT)),
                "bytes": stat.st_size,
                "mode": oct(stat.st_mode & 0o7777),
                "sha256": sha256(path),
            }
        )

    with OUTPUT.open("w", encoding="utf-8") as output:
        output.write("SAVANT PRESENT CURRENT IMPLEMENTATION DUMP\n")
        output.write(
            "generated_utc="
            + datetime.now(timezone.utc).isoformat()
            + "\n"
        )
        output.write(f"root={ROOT}\n")
        output.write(f"file_count={len(files)}\n\n")

        output.write("=== MANIFEST ===\n")
        output.write(
            json.dumps(
                manifest,
                indent=2,
                ensure_ascii=False,
                sort_keys=True,
            )
        )
        output.write("\n\n")

        for path in files:
            output.write("=" * 80 + "\n")
            output.write(f"FILE: {path}\n")
            output.write(f"SHA256: {sha256(path)}\n")
            output.write("=" * 80 + "\n")

            try:
                text = path.read_text(
                    encoding="utf-8",
                    errors="replace",
                )
            except OSError as exc:
                output.write(f"[READ ERROR: {exc}]\n\n")
                continue

            output.write(text)

            if not text.endswith("\n"):
                output.write("\n")

            output.write("\n")

    print(f"WROTE: {OUTPUT}")
    print(f"FILES: {len(files)}")
    print(f"BYTES: {OUTPUT.stat().st_size}")
    print(f"SHA256: {sha256(OUTPUT)}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
