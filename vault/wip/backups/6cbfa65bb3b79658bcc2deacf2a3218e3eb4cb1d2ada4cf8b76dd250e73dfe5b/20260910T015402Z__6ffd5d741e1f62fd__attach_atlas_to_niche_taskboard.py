#!/usr/bin/env python3

from __future__ import annotations

import argparse
import ast
import json
import os
import re
import tempfile
from pathlib import Path
from typing import Any


schema_version = (
    "savant.assurance."
    "attach-atlas-to-niche-taskboard.v1"
)

authority_effect = "none"

server_path = Path(
    "/root/savant-runtime"
    "/ontology/obelisks/_template/segue/gates/_template/segue/"
    "innates/_template/segue/exiles/niche/apps/taskboard/server.py"
)

adapter_path = Path(
    "/root/savant-runtime"
    "/ontology/obelisks/_template/segue/gates/_template/segue/"
    "innates/_template/segue/exiles/niche/apps/taskboard/"
    "atlas_adapter.py"
)


import_block = '''from atlas_adapter import (
    reject_atlas_mutation,
    try_handle_get as try_handle_atlas_get,
)
'''

get_guard = '''        if try_handle_atlas_get(self):
            return

'''

mutation_guard_template = '''        if reject_atlas_mutation(self):
            return

'''


class MigrationError(
    RuntimeError
):
    pass


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


def parse_python(
    text: str,
    path: Path,
):
    try:
        return ast.parse(
            text,
            filename=str(
                path
            ),
        )

    except SyntaxError as exc:
        raise MigrationError(
            f"python parse failure: {exc}"
        ) from exc


def method_records(
    text: str,
) -> dict[
    str,
    list[
        tuple[
            int,
            int,
        ]
    ],
]:
    tree = parse_python(
        text,
        server_path,
    )

    lines = text.splitlines(
        keepends=True
    )

    line_offsets = [0]

    total = 0

    for line in lines:
        total += len(
            line
        )

        line_offsets.append(
            total
        )

    records: dict[
        str,
        list[
            tuple[
                int,
                int,
            ]
        ],
    ] = {}

    for node in ast.walk(
        tree
    ):
        if not isinstance(
            node,
            ast.FunctionDef,
        ):
            continue

        if node.name not in {
            "do_GET",
            "do_POST",
            "do_PUT",
            "do_PATCH",
            "do_DELETE",
        }:
            continue

        if not node.body:
            raise MigrationError(
                f"{node.name} has no body"
            )

        first = node.body[
            0
        ]

        insertion_line = (
            first.lineno
            - 1
        )

        insertion_offset = line_offsets[
            insertion_line
        ]

        records.setdefault(
            node.name,
            [],
        ).append(
            (
                insertion_offset,
                first.col_offset,
            )
        )

    return records


def import_insertion_offset(
    text: str,
) -> int:
    tree = parse_python(
        text,
        server_path,
    )

    lines = text.splitlines(
        keepends=True
    )

    line_offsets = [0]

    total = 0

    for line in lines:
        total += len(
            line
        )

        line_offsets.append(
            total
        )

    body = list(
        tree.body
    )

    index = 0

    if (
        body
        and isinstance(
            body[0],
            ast.Expr,
        )
        and isinstance(
            body[0].value,
            ast.Constant,
        )
        and isinstance(
            body[0].value.value,
            str,
        )
    ):
        index = 1

    while (
        index < len(
            body
        )
        and isinstance(
            body[index],
            ast.ImportFrom,
        )
        and body[index].module
        == "__future__"
    ):
        index += 1

    while (
        index < len(
            body
        )
        and isinstance(
            body[index],
            (
                ast.Import,
                ast.ImportFrom,
            ),
        )
    ):
        index += 1

    if index == 0:
        return 0

    preceding = body[
        index - 1
    ]

    end_line = getattr(
        preceding,
        "end_lineno",
        preceding.lineno,
    )

    return line_offsets[
        end_line
    ]


def add_import(
    text: str,
) -> tuple[
    str,
    bool,
]:
    if (
        "try_handle_atlas_get"
        in text
        and "reject_atlas_mutation"
        in text
    ):
        return (
            text,
            False,
        )

    offset = import_insertion_offset(
        text
    )

    migrated = (
        text[
            :offset
        ]
        + "\n"
        + import_block
        + text[
            offset:
        ]
    )

    return (
        migrated,
        True,
    )


def add_method_guard(
    text: str,
    method_name: str,
    guard: str,
) -> tuple[
    str,
    bool,
]:
    if guard.strip() in text:
        return (
            text,
            False,
        )

    records = method_records(
        text
    )

    locations = records.get(
        method_name,
        [],
    )

    if len(
        locations
    ) != 1:
        raise MigrationError(
            f"{method_name} expected once, "
            f"found {len(locations)}"
        )

    offset, body_indent = locations[
        0
    ]

    if body_indent < 4:
        raise MigrationError(
            f"{method_name} body indentation invalid"
        )

    indentation = " " * body_indent

    normalized_guard = "".join(
        (
            indentation
            + line.lstrip()
            if line.strip()
            else line
        )
        for line
        in guard.splitlines(
            keepends=True
        )
    )

    migrated = (
        text[
            :offset
        ]
        + normalized_guard
        + text[
            offset:
        ]
    )

    return (
        migrated,
        True,
    )


def add_mutation_guards(
    text: str,
) -> tuple[
    str,
    list[str],
]:
    changed_methods = []

    records = method_records(
        text
    )

    for method_name in (
        "do_POST",
        "do_PUT",
        "do_PATCH",
        "do_DELETE",
    ):
        locations = records.get(
            method_name,
            [],
        )

        if not locations:
            continue

        migrated, changed = add_method_guard(
            text,
            method_name,
            mutation_guard_template,
        )

        if changed:
            text = migrated

            changed_methods.append(
                method_name
            )

            records = method_records(
                text
            )

    return (
        text,
        changed_methods,
    )


def validate_result(
    text: str,
) -> None:
    parse_python(
        text,
        server_path,
    )

    if text.count(
        "try_handle_atlas_get"
    ) < 2:
        raise MigrationError(
            "atlas GET adapter not installed"
        )

    if text.count(
        "reject_atlas_mutation"
    ) < 1:
        raise MigrationError(
            "atlas mutation boundary unavailable"
        )

    records = method_records(
        text
    )

    if len(
        records.get(
            "do_GET",
            [],
        )
    ) != 1:
        raise MigrationError(
            "Niche GET handler ambiguous"
        )

    compile(
        text,
        str(
            server_path
        ),
        "exec",
    )


def migrate(
    apply: bool,
) -> dict[
    str,
    Any,
]:
    if not server_path.is_file():
        raise MigrationError(
            "Niche taskboard server unavailable"
        )

    if not adapter_path.is_file():
        raise MigrationError(
            "Atlas adapter unavailable"
        )

    adapter_text = adapter_path.read_text(
        encoding="utf-8"
    )

    compile(
        adapter_text,
        str(
            adapter_path
        ),
        "exec",
    )

    original = server_path.read_text(
        encoding="utf-8"
    )

    migrated, import_changed = add_import(
        original
    )

    migrated, get_changed = add_method_guard(
        migrated,
        "do_GET",
        get_guard,
    )

    migrated, mutation_methods = add_mutation_guards(
        migrated
    )

    validate_result(
        migrated
    )

    changed = (
        migrated != original
    )

    if apply and changed:
        atomic_write(
            server_path,
            migrated,
        )

        try:
            validate_result(
                server_path.read_text(
                    encoding="utf-8"
                )
            )

        except Exception:
            atomic_write(
                server_path,
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
                server_path
            ),
        "atlas_adapter":
            str(
                adapter_path
            ),
        "projection_only":
            True,
        "mutation_authority_added":
            False,
        "import_changed":
            import_changed,
        "get_handler_changed":
            get_changed,
        "mutation_handlers_changed":
            mutation_methods,
        "routes": [
            "/atlas",
            "/atlas/",
            "/atlas/assets/*",
            "/api/atlas",
            "/api/atlas/summary",
            "/api/atlas/self-check",
            "/api/atlas/health",
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
