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
    "attach-niche-masterplan-integrity-status.v2"
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

helper_name = (
    "renderMasterplanIntegrityStatus"
)

helper_source = r'''
function renderMasterplanIntegrityStatus() {
  const projection =
    document.querySelector("#projection-status");

  if (!projection) {
    return;
  }

  const integrity =
    state.masterplanIntegrity &&
    typeof state.masterplanIntegrity === "object"
      ? state.masterplanIntegrity
      : null;

  if (!integrity) {
    return;
  }

  const graphDigest =
    typeof integrity.source_graph_digest === "string"
      ? integrity.source_graph_digest.slice(0, 12)
      : null;

  const identityCount =
    Number.isFinite(integrity.identity_count)
      ? integrity.identity_count
      : null;

  const lineageCount =
    Number.isFinite(integrity.lineage_count)
      ? integrity.lineage_count
      : null;

  const duplicateCount =
    Number.isFinite(
      integrity.duplicate_identity_group_count
    )
      ? integrity.duplicate_identity_group_count
      : null;

  const components = [
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
  ].filter(Boolean);

  const masterplanLabel =
    components.join(" · ");

  const existing =
    typeof projection.textContent === "string"
      ? projection.textContent.trim()
      : "";

  if (
    existing.includes(
      "masterplan linked"
    )
  ) {
    return;
  }

  projection.textContent =
    existing
      ? `${existing} · ${masterplanLabel}`
      : masterplanLabel;
}

'''


class MigrationError(
    RuntimeError
):
    pass


def find_function_body(
    text: str,
    function_name: str,
) -> tuple[int, int]:
    marker = (
        f"function {function_name}"
    )

    start = text.find(
        marker
    )

    if start < 0:
        raise MigrationError(
            f"{function_name} function unavailable"
        )

    brace = text.find(
        "{",
        start,
    )

    if brace < 0:
        raise MigrationError(
            f"{function_name} opening brace unavailable"
        )

    depth = 0
    quote: str | None = None
    escaped = False
    template_depth = 0
    index = brace

    while index < len(
        text
    ):
        char = text[
            index
        ]

        if quote is not None:
            if escaped:
                escaped = False

            elif char == "\\":
                escaped = True

            elif (
                quote == "`"
                and char == "$"
                and index + 1 < len(text)
                and text[index + 1] == "{"
            ):
                template_depth += 1
                index += 1

            elif (
                quote == "`"
                and char == "}"
                and template_depth > 0
            ):
                template_depth -= 1

            elif (
                char == quote
                and template_depth == 0
            ):
                quote = None

            index += 1
            continue

        if char in (
            '"',
            "'",
            "`",
        ):
            quote = char
            index += 1
            continue

        if (
            char == "/"
            and index + 1 < len(text)
        ):
            next_char = text[
                index + 1
            ]

            if next_char == "/":
                newline = text.find(
                    "\n",
                    index + 2,
                )

                if newline < 0:
                    break

                index = newline + 1
                continue

            if next_char == "*":
                end_comment = text.find(
                    "*/",
                    index + 2,
                )

                if end_comment < 0:
                    raise MigrationError(
                        "unterminated javascript comment"
                    )

                index = end_comment + 2
                continue

        if char == "{":
            depth += 1

        elif char == "}":
            depth -= 1

            if depth == 0:
                return (
                    brace,
                    index,
                )

        index += 1

    raise MigrationError(
        f"{function_name} closing brace unavailable"
    )


def validate_source(
    text: str,
) -> None:
    required = (
        "const state = {",
        "masterplanIntegrity: null,",
        "function renderAll",
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

    find_function_body(
        text,
        "renderAll",
    )


def add_helper(
    text: str,
) -> tuple[
    str,
    str,
]:
    marker = (
        f"function {helper_name}("
    )

    if marker in text:
        return (
            text,
            "already_present",
        )

    render_all_start = text.find(
        "function renderAll"
    )

    if render_all_start < 0:
        raise MigrationError(
            "renderAll insertion point unavailable"
        )

    migrated = (
        text[
            :render_all_start
        ]
        + helper_source
        + text[
            render_all_start:
        ]
    )

    return (
        migrated,
        "added",
    )


def add_render_call(
    text: str,
) -> tuple[
    str,
    str,
]:
    call = (
        "renderMasterplanIntegrityStatus();"
    )

    (
        body_start,
        body_end,
    ) = find_function_body(
        text,
        "renderAll",
    )

    body = text[
        body_start + 1:
        body_end
    ]

    if call in body:
        return (
            text,
            "already_present",
        )

    insertion = (
        "\n  "
        + call
        + "\n"
    )

    migrated = (
        text[
            :body_end
        ]
        + insertion
        + text[
            body_end:
        ]
    )

    return (
        migrated,
        "added",
    )


def validate_result(
    text: str,
) -> None:
    required = (
        "masterplanIntegrity: null,",
        "function renderMasterplanIntegrityStatus()",
        'document.querySelector("#projection-status")',
        "state.masterplanIntegrity",
        '"masterplan linked"',
        "integrity.source_graph_digest.slice(0, 12)",
        "integrity.identity_count",
        "integrity.lineage_count",
        "integrity.duplicate_identity_group_count",
        "renderMasterplanIntegrityStatus();",
    )

    missing = [
        fragment
        for fragment
        in required
        if fragment not in text
    ]

    if missing:
        raise MigrationError(
            "masterplan integrity presentation "
            "integration incomplete: "
            + ", ".join(
                missing
            )
        )

    if text.count(
        "function renderMasterplanIntegrityStatus()"
    ) != 1:
        raise MigrationError(
            "masterplan integrity renderer "
            "must occur exactly once"
        )

    (
        body_start,
        body_end,
    ) = find_function_body(
        text,
        "renderAll",
    )

    render_all_body = text[
        body_start + 1:
        body_end
    ]

    if render_all_body.count(
        "renderMasterplanIntegrityStatus();"
    ) != 1:
        raise MigrationError(
            "renderAll must invoke masterplan "
            "integrity renderer exactly once"
        )


def transform(
    original: str,
) -> tuple[
    str,
    dict[str, str],
]:
    validate_source(
        original
    )

    migrated = original

    (
        migrated,
        helper_disposition,
    ) = add_helper(
        migrated
    )

    (
        migrated,
        call_disposition,
    ) = add_render_call(
        migrated
    )

    validate_result(
        migrated
    )

    return (
        migrated,
        {
            "renderer":
                helper_disposition,
            "render_all_binding":
                call_disposition,
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
        "existing_status_preserved":
            True,
        "missing_dom_surface_is_noop":
            True,
        "client":
            str(
                app_path
            ),
        "surface":
            "#projection-status",
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
