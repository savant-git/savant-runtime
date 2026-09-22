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
    "attach-niche-masterplan-integrity-client.v1"
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


state_anchor = """  masterplan: null,
"""

state_source = """  masterplan: null,
  masterplanIntegrity: null,
"""

request_anchor = """    api("/api/masterplan"),
"""

request_source = """    api("/api/masterplan"),
    api("/api/masterplan/integrity"),
"""

result_anchor = """    masterplanResult,
"""

result_source = """    masterplanResult,
    masterplanIntegrityResult,
"""

assignment_anchor = """  if (masterplanResult.status === "fulfilled") {
    state.masterplan = masterplanResult.value;
  }
"""

assignment_source = """  if (masterplanResult.status === "fulfilled") {
    state.masterplan = masterplanResult.value;
  }

  if (masterplanIntegrityResult.status === "fulfilled") {
    state.masterplanIntegrity = masterplanIntegrityResult.value;
  }
"""


class MigrationError(
    RuntimeError
):
    pass


def require_once(
    text: str,
    fragment: str,
    name: str,
) -> None:
    count = text.count(
        fragment
    )

    if count != 1:
        raise MigrationError(
            f"{name} expected once, found {count}"
        )


def require_client_shape(
    text: str,
) -> None:
    required = (
        '"use strict";',
        "const state = {",
        "async function api(",
        "async function loadCore(",
        'api("/api/masterplan")',
        "masterplanResult",
        "renderAll()",
    )

    missing = [
        fragment
        for fragment
        in required
        if fragment not in text
    ]

    if missing:
        raise MigrationError(
            "taskboard client shape mismatch: "
            + ", ".join(
                missing
            )
        )


def add_state(
    text: str,
) -> tuple[
    str,
    str,
]:
    if (
        "masterplanIntegrity: null,"
        in text
    ):
        return (
            text,
            "already_present",
        )

    require_once(
        text,
        state_anchor,
        "masterplan state anchor",
    )

    return (
        text.replace(
            state_anchor,
            state_source,
            1,
        ),
        "added",
    )


def add_request(
    text: str,
) -> tuple[
    str,
    str,
]:
    if (
        'api("/api/masterplan/integrity")'
        in text
    ):
        return (
            text,
            "already_present",
        )

    require_once(
        text,
        request_anchor,
        "masterplan request anchor",
    )

    return (
        text.replace(
            request_anchor,
            request_source,
            1,
        ),
        "added",
    )


def add_result_binding(
    text: str,
) -> tuple[
    str,
    str,
]:
    if (
        "masterplanIntegrityResult,"
        in text
    ):
        return (
            text,
            "already_present",
        )

    require_once(
        text,
        result_anchor,
        "masterplan result anchor",
    )

    return (
        text.replace(
            result_anchor,
            result_source,
            1,
        ),
        "added",
    )


def add_assignment(
    text: str,
) -> tuple[
    str,
    str,
]:
    if (
        "state.masterplanIntegrity = "
        "masterplanIntegrityResult.value;"
        in text
    ):
        return (
            text,
            "already_present",
        )

    require_once(
        text,
        assignment_anchor,
        "masterplan assignment anchor",
    )

    return (
        text.replace(
            assignment_anchor,
            assignment_source,
            1,
        ),
        "added",
    )


def validate_result(
    text: str,
) -> None:
    required = (
        "masterplanIntegrity: null,",
        'api("/api/masterplan/integrity")',
        "masterplanIntegrityResult,",
        "state.masterplanIntegrity = "
        "masterplanIntegrityResult.value;",
    )

    missing = [
        fragment
        for fragment
        in required
        if fragment not in text
    ]

    if missing:
        raise MigrationError(
            "masterplan integrity client "
            "integration incomplete: "
            + ", ".join(
                missing
            )
        )

    exact_once = (
        "masterplanIntegrity: null,",
        'api("/api/masterplan/integrity")',
        "masterplanIntegrityResult,",
        "state.masterplanIntegrity = "
        "masterplanIntegrityResult.value;",
    )

    for fragment in exact_once:
        count = text.count(
            fragment
        )

        if count != 1:
            raise MigrationError(
                "masterplan integrity client "
                "fragment must occur once: "
                f"{fragment!r} found {count}"
            )


def transform(
    original: str,
) -> tuple[
    str,
    dict[str, str],
]:
    require_client_shape(
        original
    )

    migrated = original

    migrated, state_disposition = (
        add_state(
            migrated
        )
    )

    migrated, request_disposition = (
        add_request(
            migrated
        )
    )

    migrated, result_disposition = (
        add_result_binding(
            migrated
        )
    )

    migrated, assignment_disposition = (
        add_assignment(
            migrated
        )
    )

    validate_result(
        migrated
    )

    return (
        migrated,
        {
            "state":
                state_disposition,
            "request":
                request_disposition,
            "result_binding":
                result_disposition,
            "assignment":
                assignment_disposition,
        },
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

    temporary = Path(
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
            temporary,
            mode,
        )

        os.replace(
            temporary,
            path,
        )

    finally:
        if temporary.exists():
            temporary.unlink()


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

    migrated, dispositions = (
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
        "mutation_authority_added":
            False,
        "parallel_refresh_loop_added":
            False,
        "client":
            str(
                app_path
            ),
        "endpoint":
            "/api/masterplan/integrity",
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
