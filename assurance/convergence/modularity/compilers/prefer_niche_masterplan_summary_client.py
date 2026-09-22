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
    "prefer-niche-masterplan-summary-client.v1"
)

authority_effect = "none"

runtime_root = Path(
    "/root/savant-runtime"
)

taskboard_root = (
    runtime_root
    / "ontology"
    / "obelisks"
    / "_template"
    / "segue"
    / "gates"
    / "_template"
    / "segue"
    / "innates"
    / "_template"
    / "segue"
    / "exiles"
    / "niche"
    / "apps"
    / "taskboard"
)

app_path = (
    taskboard_root
    / "app.js"
)

full_request = (
    'api("/api/masterplan"),'
)

summary_request = (
    'api("/api/masterplan/summary"),'
)


class MigrationError(
    RuntimeError
):
    pass


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


def validate_source(
    text: str,
) -> None:
    required = (
        "const state = {",
        "masterplan: null,",
        "masterplanIntegrity: null,",
        "async function loadCore(",
        "masterplanResult,",
        "masterplanIntegrityResult,",
        "state.masterplan = "
        "masterplanResult.value;",
        "state.masterplanIntegrity = "
        "masterplanIntegrityResult.value;",
        'api("/api/masterplan/integrity")',
    )

    missing = [
        fragment
        for fragment
        in required
        if fragment not in text
    ]

    if missing:
        raise MigrationError(
            "niche masterplan client "
            "integration prerequisite missing: "
            + ", ".join(
                missing
            )
        )


def transform(
    original: str,
) -> tuple[
    str,
    str,
]:
    validate_source(
        original
    )

    full_count = original.count(
        full_request
    )

    summary_count = original.count(
        summary_request
    )

    if (
        full_count == 0
        and summary_count == 1
    ):
        return (
            original,
            "already_present",
        )

    if (
        full_count != 1
        or summary_count != 0
    ):
        raise MigrationError(
            "masterplan request shape mismatch: "
            f"full={full_count}, "
            f"summary={summary_count}"
        )

    migrated = original.replace(
        full_request,
        summary_request,
        1,
    )

    validate_result(
        migrated
    )

    return (
        migrated,
        "replaced",
    )


def validate_result(
    text: str,
) -> None:
    validate_source(
        text
    )

    require_once(
        text,
        summary_request,
        "summary masterplan request",
    )

    if full_request in text:
        raise MigrationError(
            "full masterplan graph request "
            "still present in client"
        )

    require_once(
        text,
        'api("/api/masterplan/integrity")',
        "masterplan integrity request",
    )

    require_once(
        text,
        "state.masterplan = "
        "masterplanResult.value;",
        "masterplan assignment",
    )

    require_once(
        text,
        "state.masterplanIntegrity = "
        "masterplanIntegrityResult.value;",
        "masterplan integrity assignment",
    )


def atomic_write(
    path: Path,
    text: str,
) -> None:
    mode = path.stat().st_mode

    descriptor, temporary_name = (
        tempfile.mkstemp(
            prefix=path.name + ".",
            suffix=".tmp",
            dir=str(
                path.parent
            ),
        )
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
    if not app_path.is_file():
        raise MigrationError(
            "taskboard client unavailable"
        )

    original = app_path.read_text(
        encoding="utf-8"
    )

    migrated, disposition = (
        transform(
            original
        )
    )

    changed = (
        migrated != original
    )

    if apply and changed:
        atomic_write(
            app_path,
            migrated,
        )

        try:
            current = app_path.read_text(
                encoding="utf-8"
            )

            validate_result(
                current
            )

        except Exception:
            atomic_write(
                app_path,
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
        "projection_only":
            True,
        "mutation_authority_added":
            False,
        "parallel_refresh_loop_added":
            False,
        "authoritative_graph_duplicated":
            False,
        "raw_masterplan_graph_transferred":
            False,
        "client":
            str(
                app_path
            ),
        "request":
            "/api/masterplan/summary",
        "integrity_request":
            "/api/masterplan/integrity",
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
