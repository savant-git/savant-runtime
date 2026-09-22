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
    "stabilize-atlas-binary-values.v1"
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


old_canonical = '''def canonical_json_bytes(
    value: Any,
) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(
            ",",
            ":",
        ),
    ).encode(
        "utf-8"
    )
'''

new_canonical = '''def normalize_json_value(
    value: Any,
) -> Any:
    if isinstance(
        value,
        bytes,
    ):
        return {
            "$binary_hex":
                value.hex(),
        }

    if isinstance(
        value,
        bytearray,
    ):
        return {
            "$binary_hex":
                bytes(
                    value
                ).hex(),
        }

    if isinstance(
        value,
        memoryview,
    ):
        return {
            "$binary_hex":
                value.tobytes().hex(),
        }

    if isinstance(
        value,
        dict,
    ):
        return {
            str(
                key
            ):
                normalize_json_value(
                    member
                )
            for key, member
            in sorted(
                value.items(),
                key=lambda item:
                    str(
                        item[
                            0
                        ]
                    ),
            )
        }

    if isinstance(
        value,
        (
            list,
            tuple,
        ),
    ):
        return [
            normalize_json_value(
                member
            )
            for member
            in value
        ]

    if isinstance(
        value,
        set,
    ):
        normalized_members = [
            normalize_json_value(
                member
            )
            for member
            in value
        ]

        return sorted(
            normalized_members,
            key=lambda member:
                json.dumps(
                    member,
                    ensure_ascii=False,
                    sort_keys=True,
                    separators=(
                        ",",
                        ":",
                    ),
                ),
        )

    if isinstance(
        value,
        Path,
    ):
        return str(
            value
        )

    if (
        value is None
        or isinstance(
            value,
            (
                str,
                int,
                float,
                bool,
            ),
        )
    ):
        return value

    raise AtlasError(
        "unsupported canonical JSON value type: "
        + type(
            value
        ).__name__
    )


def canonical_json_bytes(
    value: Any,
) -> bytes:
    return json.dumps(
        normalize_json_value(
            value
        ),
        ensure_ascii=False,
        sort_keys=True,
        separators=(
            ",",
            ":",
        ),
    ).encode(
        "utf-8"
    )
'''


def validate_result(
    text: str,
) -> None:
    if text.count(
        "def normalize_json_value("
    ) != 1:
        raise MigrationError(
            "binary-safe normalization missing or duplicated"
        )

    if text.count(
        "def canonical_json_bytes("
    ) != 1:
        raise MigrationError(
            "canonical JSON function missing or duplicated"
        )

    if text.count(
        '"$binary_hex"'
    ) != 3:
        raise MigrationError(
            "binary normalization shape mismatch"
        )

    if old_canonical in text:
        raise MigrationError(
            "old canonical JSON implementation remains"
        )

    compile(
        text,
        str(
            atlas_path
        ),
        "exec",
    )


def transform(
    original: str,
) -> tuple[
    str,
    str,
]:
    old_count = original.count(
        old_canonical
    )

    normalized_count = original.count(
        "def normalize_json_value("
    )

    if (
        old_count == 1
        and normalized_count == 0
    ):
        migrated = original.replace(
            old_canonical,
            new_canonical,
            1,
        )

        validate_result(
            migrated
        )

        return (
            migrated,
            "binary_normalization_added",
        )

    if (
        old_count == 0
        and normalized_count == 1
    ):
        validate_result(
            original
        )

        return (
            original,
            "already_present",
        )

    raise MigrationError(
        "atlas canonical JSON shape mismatch: "
        f"old={old_count}, "
        f"normalized={normalized_count}"
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

    migrated, disposition = transform(
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
        "binary_encoding":
            "lowercase-hex",
        "binary_marker":
            "$binary_hex",
        "disposition":
            disposition,
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
