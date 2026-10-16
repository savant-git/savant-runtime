#!/usr/bin/env python3

from __future__ import annotations

from pathlib import Path


SERVER = Path(
    "/root/savant-runtime/ontology/obelisks/_template/"
    "segue/gates/_template/segue/innates/_template/"
    "segue/exiles/niche/apps/taskboard/server.py"
)

LEGACY = (
    '/ "runtime/niche/tasks.sqlite3"'
)

CANONICAL = (
    '/ "runtime/niche/tasks.datrix"'
)


def main() -> None:
    source = SERVER.read_text(
        encoding="utf-8"
    )

    legacy_count = source.count(
        LEGACY
    )

    canonical_count = source.count(
        CANONICAL
    )

    print(
        "legacy_occurrences:",
        legacy_count,
    )

    print(
        "canonical_occurrences_before:",
        canonical_count,
    )

    if legacy_count != 1:
        raise RuntimeError(
            "refusing mutation: expected exactly "
            "one legacy taskboard persistence path, "
            f"found {legacy_count}"
        )

    migrated = source.replace(
        LEGACY,
        CANONICAL,
        1,
    )

    SERVER.write_text(
        migrated,
        encoding="utf-8",
    )

    verified = SERVER.read_text(
        encoding="utf-8"
    )

    if LEGACY in verified:
        raise RuntimeError(
            "legacy sqlite path remains after migration"
        )

    if verified.count(
        CANONICAL
    ) != canonical_count + 1:
        raise RuntimeError(
            "canonical datrix path verification failed"
        )

    print(
        "migration: PASS"
    )

    print(
        "canonical_path:",
        "/root/savant-runtime/runtime/niche/tasks.datrix",
    )


if __name__ == "__main__":
    main()
