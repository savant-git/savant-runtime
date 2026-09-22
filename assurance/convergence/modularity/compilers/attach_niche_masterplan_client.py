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
    "attach-niche-masterplan-client.v1"
)

authority_effect = "none"

runtime_root = Path(
    "/root/savant-runtime"
)

app_path = (
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
    / "app.js"
)

state_anchor = """  dashboard: null,
  engineState: null,
"""

state_replacement = """  dashboard: null,
  masterplan: null,
  engineState: null,
"""

request_anchor = """    api("/api/dashboard"),
    api("/api/state"),
"""

request_replacement = """    api("/api/dashboard"),
    api("/api/masterplan"),
    api("/api/state"),
"""

result_anchor = """    dashboardResult,
    engineResult,
"""

result_replacement = """    dashboardResult,
    masterplanResult,
    engineResult,
"""

assignment_anchor = """  if (dashboardResult.status === "fulfilled") {
    state.dashboard = dashboardResult.value;
  }

  if (engineResult.status === "fulfilled") {
"""

assignment_replacement = """  if (dashboardResult.status === "fulfilled") {
    state.dashboard = dashboardResult.value;
  }

  if (masterplanResult.status === "fulfilled") {
    state.masterplan = masterplanResult.value;
  }

  if (engineResult.status === "fulfilled") {
"""

required_existing_fragments = (
    '"use strict";',
    "const state = {",
    "async function api(path, options = {})",
    "async function loadCore()",
    'api("/api/tasks?include_terminal=true")',
    'api("/api/dashboard")',
    'api("/api/state")',
    'api("/api/history")',
    "Promise.allSettled([",
    "renderAll();",
)

completed_fragments = (
    "masterplan: null,",
    'api("/api/masterplan")',
    "masterplanResult,",
    'masterplanResult.status === "fulfilled"',
    "state.masterplan = masterplanResult.value;",
)


class MigrationError(
    RuntimeError
):
    pass


def read_app() -> str:
    if not app_path.is_file():
        raise MigrationError(
            "taskboard app unavailable"
        )

    return app_path.read_text(
        encoding="utf-8"
    )


def ensure_live_shape(
    text: str,
) -> None:
    missing = [
        fragment
        for fragment
        in required_existing_fragments
        if fragment not in text
    ]

    if missing:
        raise MigrationError(
            "taskboard client shape mismatch: "
            + ", ".join(
                missing
            )
        )


def replace_once(
    text: str,
    anchor: str,
    replacement: str,
    label: str,
) -> tuple[str, str]:
    if replacement in text:
        return (
            text,
            "already_present",
        )

    count = text.count(
        anchor
    )

    if count != 1:
        raise MigrationError(
            f"{label} anchor count "
            f"expected 1, found {count}"
        )

    return (
        text.replace(
            anchor,
            replacement,
            1,
        ),
        "added",
    )


def validate_transformed(
    text: str,
) -> None:
    missing = [
        fragment
        for fragment
        in completed_fragments
        if fragment not in text
    ]

    if missing:
        raise MigrationError(
            "transformed client incomplete: "
            + ", ".join(
                missing
            )
        )

    if text.count(
        'api("/api/masterplan")'
    ) != 1:
        raise MigrationError(
            "masterplan request must occur once"
        )

    if text.count(
        "masterplan: null,"
    ) != 1:
        raise MigrationError(
            "masterplan state slot must occur once"
        )

    if text.count(
        "state.masterplan = "
        "masterplanResult.value;"
    ) != 1:
        raise MigrationError(
            "masterplan state assignment "
            "must occur once"
        )


def transform(
    original: str,
) -> tuple[
    str,
    dict[str, str],
]:
    ensure_live_shape(
        original
    )

    migrated = original

    dispositions: dict[
        str,
        str,
    ] = {}

    (
        migrated,
        dispositions["state"],
    ) = replace_once(
        migrated,
        state_anchor,
        state_replacement,
        "state",
    )

    (
        migrated,
        dispositions["request"],
    ) = replace_once(
        migrated,
        request_anchor,
        request_replacement,
        "request",
    )

    (
        migrated,
        dispositions["result_binding"],
    ) = replace_once(
        migrated,
        result_anchor,
        result_replacement,
        "result binding",
    )

    (
        migrated,
        dispositions["assignment"],
    ) = replace_once(
        migrated,
        assignment_anchor,
        assignment_replacement,
        "assignment",
    )

    validate_transformed(
        migrated
    )

    return (
        migrated,
        dispositions,
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
    original = read_app()

    (
        migrated,
        dispositions,
    ) = transform(
        original
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
            current = read_app()

            validate_transformed(
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
        "app":
            str(
                app_path
            ),
        "endpoint":
            "/api/masterplan",
        "projection_owner":
            "exile:niche",
        "mutation_authority_added":
            False,
        "dispositions":
            dispositions,
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
                    "apply":
                        arguments.apply,
                    "status":
                        "failed",
                    "error":
                        str(exc),
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
