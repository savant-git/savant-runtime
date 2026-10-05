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
    "attach-niche-masterplan-integrity-status.v1"
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


old_projection_status = '''        const projection = $("#projection-status");

        if (projection) {
            projection.textContent =
                state.lastChangedIds.size
                    ? `${state.lastChangedIds.size} task state change${state.lastChangedIds.size === 1 ? "" : "s"} observed`
                    : "projection stable";
        }
'''

new_projection_status = '''        const projection = $("#projection-status");

        if (projection) {
            const integrity =
                state.masterplanIntegrity &&
                typeof state.masterplanIntegrity === "object"
                    ? state.masterplanIntegrity
                    : null;

            const graphDigest =
                integrity &&
                typeof integrity.source_graph_digest === "string"
                    ? integrity.source_graph_digest.slice(0, 12)
                    : null;

            const identityCount =
                integrity &&
                Number.isFinite(integrity.identity_count)
                    ? integrity.identity_count
                    : null;

            const lineageCount =
                integrity &&
                Number.isFinite(integrity.lineage_count)
                    ? integrity.lineage_count
                    : null;

            const duplicateCount =
                integrity &&
                Number.isFinite(
                    integrity.duplicate_identity_group_count
                )
                    ? integrity.duplicate_identity_group_count
                    : null;

            const taskChangeLabel =
                state.lastChangedIds.size
                    ? `${state.lastChangedIds.size} task state change${state.lastChangedIds.size === 1 ? "" : "s"} observed`
                    : "projection stable";

            const masterplanLabel =
                integrity
                    ? [
                        "masterplan linked",
                        graphDigest
                            ? `graph ${graphDigest}`
                            : null,
                        identityCount !== null
                            ? `${identityCount} identities`
                            : null,
                        lineageCount !== null
                            ? `${lineageCount} lineage records`
                            : null,
                        duplicateCount !== null
                            ? `${duplicateCount} duplicate identity groups`
                            : null,
                    ]
                        .filter(Boolean)
                        .join(" · ")
                    : "masterplan integrity unavailable";

            projection.textContent =
                `${taskChangeLabel} · ${masterplanLabel}`;
        }
'''


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
        '"use strict";',
        "const state = {",
        "masterplanIntegrity: null,",
        "function renderStatus()",
        'const projection = $("#projection-status");',
        "state.lastChangedIds.size",
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


def already_integrated(
    text: str,
) -> bool:
    required = (
        "const integrity =",
        "state.masterplanIntegrity",
        '"masterplan linked"',
        '"masterplan integrity unavailable"',
        "integrity.source_graph_digest",
        "integrity.identity_count",
        "integrity.lineage_count",
        "integrity.duplicate_identity_group_count",
    )

    return all(
        fragment in text
        for fragment
        in required
    )


def validate_result(
    text: str,
) -> None:
    required = (
        "function renderStatus()",
        "const integrity =",
        "state.masterplanIntegrity",
        "const graphDigest =",
        "const identityCount =",
        "const lineageCount =",
        "const duplicateCount =",
        "const taskChangeLabel =",
        "const masterplanLabel =",
        '"masterplan linked"',
        '"masterplan integrity unavailable"',
        "integrity.source_graph_digest.slice(0, 12)",
        "integrity.identity_count",
        "integrity.lineage_count",
        "integrity.duplicate_identity_group_count",
        "projection.textContent =",
        "`${taskChangeLabel} · ${masterplanLabel}`",
    )

    missing = [
        fragment
        for fragment
        in required
        if fragment not in text
    ]

    if missing:
        raise MigrationError(
            "masterplan integrity status "
            "integration incomplete: "
            + ", ".join(
                missing
            )
        )

    unique = (
        '"masterplan linked"',
        '"masterplan integrity unavailable"',
        "`${taskChangeLabel} · ${masterplanLabel}`",
    )

    for fragment in unique:
        count = text.count(
            fragment
        )

        if count != 1:
            raise MigrationError(
                "masterplan integrity status "
                "fragment must occur once: "
                f"{fragment!r} found {count}"
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

    if already_integrated(
        original
    ):
        validate_result(
            original
        )

        return (
            original,
            "already_present",
        )

    require_once(
        original,
        old_projection_status,
        "projection status render block",
    )

    migrated = original.replace(
        old_projection_status,
        new_projection_status,
        1,
    )

    validate_result(
        migrated
    )

    return (
        migrated,
        "added",
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

    migrated, disposition = transform(
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
        "parallel_state_added":
            False,
        "parallel_refresh_loop_added":
            False,
        "new_dom_surface_added":
            False,
        "client":
            str(
                app_path
            ),
        "surface":
            "#projection-status",
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
