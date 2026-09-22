#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import os
import tempfile
from pathlib import Path
from typing import Any


schema_version = (
    "savant.assurance."
    "stabilize-atlas-projection.v1"
)

authority_effect = "none"

atlas_path = Path(
    "/root/savant-runtime"
    "/ontology/obelisks/_template/segue/gates/_template/segue/"
    "innates/_template/segue/exiles/niche/apps/atlas/"
    "atlas_projection.py"
)


class MigrationError(
    RuntimeError
):
    pass


volatile_file_metadata_block = '''            if not is_directory:
                try:
                    node["size"] = int(
                        entry.stat(
                            follow_symlinks=False
                        ).st_size
                    )
                except OSError:
                    node["size"] = None

'''

sqlite_iteration_old = '''            for row_index, row in enumerate(
                connection.execute(
                    f"SELECT * FROM {quoted}"
                )
            ):
                raw = {
                    key:
                        row[key]
                    for key
                    in row.keys()
                }

                if not looks_like_task(raw):
                    continue

                tasks.append(
                    normalize_task(
                        raw,
                        "niche-sqlite:"
                        + table,
                        "/"
                        + table
                        + "/"
                        + str(row_index),
                    )
                )
'''

sqlite_iteration_new = '''            raw_rows = [
                {
                    key:
                        row[key]
                    for key
                    in row.keys()
                }
                for row
                in connection.execute(
                    f"SELECT * FROM {quoted}"
                )
            ]

            raw_rows.sort(
                key=lambda raw:
                    canonical_json_bytes(
                        raw
                    )
            )

            for row_index, raw in enumerate(
                raw_rows
            ):
                if not looks_like_task(raw):
                    continue

                tasks.append(
                    normalize_task(
                        raw,
                        "niche-sqlite:"
                        + table,
                        "/"
                        + table
                        + "/"
                        + str(row_index),
                    )
                )
'''


def require_once(
    text: str,
    fragment: str,
    label: str,
) -> None:
    count = text.count(
        fragment
    )

    if count != 1:
        raise MigrationError(
            f"{label} expected once, found {count}"
        )


def transform(
    original: str,
) -> tuple[
    str,
    list[str],
]:
    migrated = original

    dispositions: list[
        str
    ] = []

    volatile_count = migrated.count(
        volatile_file_metadata_block
    )

    if volatile_count == 1:
        migrated = migrated.replace(
            volatile_file_metadata_block,
            "",
            1,
        )

        dispositions.append(
            "volatile_file_size_removed"
        )

    elif volatile_count == 0:
        dispositions.append(
            "volatile_file_size_already_absent"
        )

    else:
        raise MigrationError(
            "volatile file metadata shape mismatch"
        )

    old_sqlite_count = migrated.count(
        sqlite_iteration_old
    )

    new_sqlite_count = migrated.count(
        sqlite_iteration_new
    )

    if (
        old_sqlite_count == 1
        and new_sqlite_count == 0
    ):
        migrated = migrated.replace(
            sqlite_iteration_old,
            sqlite_iteration_new,
            1,
        )

        dispositions.append(
            "sqlite_rows_canonicalized"
        )

    elif (
        old_sqlite_count == 0
        and new_sqlite_count == 1
    ):
        dispositions.append(
            "sqlite_rows_already_canonicalized"
        )

    else:
        raise MigrationError(
            "sqlite task iteration shape mismatch: "
            f"old={old_sqlite_count}, "
            f"new={new_sqlite_count}"
        )

    validate_result(
        migrated
    )

    return (
        migrated,
        dispositions,
    )


def validate_result(
    text: str,
) -> None:
    if volatile_file_metadata_block in text:
        raise MigrationError(
            "volatile file size remains in atlas projection"
        )

    require_once(
        text,
        sqlite_iteration_new,
        "canonical sqlite iteration",
    )

    require_once(
        text,
        'schema_version = "savant.niche.atlas-projection.v1"',
        "atlas schema",
    )

    require_once(
        text,
        "def atlas_projection()",
        "atlas projection",
    )

    require_once(
        text,
        "def self_check()",
        "atlas self-check",
    )

    compile(
        text,
        str(
            atlas_path
        ),
        "exec",
    )


def atomic_write(
    path: Path,
    text: str,
) -> None:
    mode = path.stat().st_mode

    descriptor, temporary_name = tempfile.mkstemp(
        prefix=path.name + ".",
        suffix=".tmp",
        dir=str(
            path.parent
        ),
    )

    temporary_path = Path(
        temporary_name
    )

    try:
        with os.fdopen(
            descriptor,
            "w",
            encoding="utf-8",
            newline="",
        ) as handle:
            handle.write(
                text
            )

            handle.flush()

            os.fsync(
                handle.fileno()
            )

        os.chmod(
            temporary_path,
            mode,
        )

        os.replace(
            temporary_path,
            path,
        )

    finally:
        if temporary_path.exists():
            temporary_path.unlink()


def migrate(
    apply: bool,
) -> dict[str, Any]:
    if not atlas_path.is_file():
        raise MigrationError(
            "atlas projection unavailable"
        )

    original = atlas_path.read_text(
        encoding="utf-8"
    )

    migrated, dispositions = transform(
        original
    )

    changed = (
        migrated != original
    )

    if apply and changed:
        atomic_write(
            atlas_path,
            migrated,
        )

        try:
            validate_result(
                atlas_path.read_text(
                    encoding="utf-8"
                )
            )

        except Exception:
            atomic_write(
                atlas_path,
                original,
            )
            raise

    return {
        "schema":
            schema_version,
        "authority_effect":
            authority_effect,
        "status":
            "passed",
        "apply":
            apply,
        "changed":
            changed,
        "owner":
            "exile:niche",
        "target":
            str(
                atlas_path
            ),
        "projection_only":
            True,
        "mutation_authority_added":
            False,
        "dispositions":
            dispositions,
        "determinism_repairs": [
            "exclude_volatile_file_size",
            "canonicalize_sqlite_task_order",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--apply",
        action="store_true",
    )

    arguments = parser.parse_args()

    try:
        result = migrate(
            arguments.apply
        )

    except Exception as exc:
        print(
            json.dumps(
                {
                    "schema":
                        schema_version,
                    "authority_effect":
                        authority_effect,
                    "status":
                        "failed",
                    "apply":
                        arguments.apply,
                    "error":
                        str(
                            exc
                        ),
                },
                indent=2,
                sort_keys=True,
            )
        )

        return 1

    print(
        json.dumps(
            result,
            indent=2,
            sort_keys=True,
        )
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
