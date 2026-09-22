#!/usr/bin/env python3

from __future__ import annotations

import argparse
import ast
import json
import os
import tempfile
from pathlib import Path
from typing import Any


schema_version = (
    "savant.assurance."
    "attach-atlas-to-niche-taskboard.v3"
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


class MigrationError(
    RuntimeError
):
    pass


def parse_python(
    text: str,
):
    try:
        return ast.parse(
            text,
            filename=str(
                server_path
            ),
        )

    except SyntaxError as exc:
        raise MigrationError(
            "existing Niche server is not valid Python: "
            f"{exc}"
        ) from exc


def offsets_for_text(
    text: str,
) -> list[int]:
    offsets = [0]
    total = 0

    for line in text.splitlines(
        keepends=True
    ):
        total += len(line)
        offsets.append(total)

    return offsets


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
            handle.write(text)
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


def import_insertion_offset(
    text: str,
) -> int:
    tree = parse_python(
        text
    )

    offsets = offsets_for_text(
        text
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
        index < len(body)
        and isinstance(
            body[index],
            ast.ImportFrom,
        )
        and body[index].module
        == "__future__"
    ):
        index += 1

    while (
        index < len(body)
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

    previous = body[
        index - 1
    ]

    end_lineno = getattr(
        previous,
        "end_lineno",
        previous.lineno,
    )

    return offsets[
        end_lineno
    ]


def method_nodes(
    text: str,
    method_name: str,
) -> list[
    ast.FunctionDef
    | ast.AsyncFunctionDef
]:
    tree = parse_python(
        text
    )

    return [
        node
        for node
        in ast.walk(
            tree
        )
        if isinstance(
            node,
            (
                ast.FunctionDef,
                ast.AsyncFunctionDef,
            ),
        )
        and node.name
        == method_name
    ]


def method_node(
    text: str,
    method_name: str,
) -> (
    ast.FunctionDef
    | ast.AsyncFunctionDef
):
    matches = method_nodes(
        text,
        method_name,
    )

    if len(
        matches
    ) != 1:
        raise MigrationError(
            f"{method_name} expected once, "
            f"found {len(matches)}"
        )

    method = matches[
        0
    ]

    if not method.body:
        raise MigrationError(
            f"{method_name} has no body"
        )

    return method


def call_name(
    expression: ast.expr,
) -> str | None:
    if not isinstance(
        expression,
        ast.Call,
    ):
        return None

    function = expression.func

    if isinstance(
        function,
        ast.Name,
    ):
        return function.id

    return None


def first_guard_name(
    method: (
        ast.FunctionDef
        | ast.AsyncFunctionDef
    ),
) -> str | None:
    if not method.body:
        return None

    first = method.body[
        0
    ]

    if not isinstance(
        first,
        ast.If,
    ):
        return None

    return call_name(
        first.test
    )


def add_import(
    text: str,
) -> tuple[
    str,
    bool,
]:
    has_get = (
        "try_handle_get as try_handle_atlas_get"
        in text
    )

    has_mutation = (
        "reject_atlas_mutation"
        in text
    )

    if (
        has_get
        and has_mutation
    ):
        return (
            text,
            False,
        )

    if (
        has_get
        or has_mutation
    ):
        raise MigrationError(
            "partial Atlas adapter import already exists"
        )

    offset = import_insertion_offset(
        text
    )

    prefix = text[
        :offset
    ]

    suffix = text[
        offset:
    ]

    separator = (
        ""
        if (
            not prefix
            or prefix.endswith(
                "\n\n"
            )
        )
        else "\n"
    )

    return (
        prefix
        + separator
        + import_block
        + "\n"
        + suffix,
        True,
    )


def render_guard(
    indent: int,
    guard_name: str,
) -> str:
    indentation = (
        " " * indent
    )

    return (
        f"{indentation}if "
        f"{guard_name}(self):\n"
        f"{indentation}    return\n\n"
    )


def add_guard_to_method(
    text: str,
    method_name: str,
    guard_name: str,
) -> tuple[
    str,
    bool,
]:
    method = method_node(
        text,
        method_name,
    )

    existing_guard = first_guard_name(
        method
    )

    if existing_guard == guard_name:
        return (
            text,
            False,
        )

    offsets = offsets_for_text(
        text
    )

    first_statement = method.body[
        0
    ]

    indent = first_statement.col_offset

    if indent <= method.col_offset:
        raise MigrationError(
            f"{method_name} body indentation invalid"
        )

    insertion_offset = offsets[
        first_statement.lineno - 1
    ]

    migrated = (
        text[
            :insertion_offset
        ]
        + render_guard(
            indent,
            guard_name,
        )
        + text[
            insertion_offset:
        ]
    )

    parse_python(
        migrated
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
    changed = []

    for method_name in (
        "do_POST",
        "do_PUT",
        "do_PATCH",
        "do_DELETE",
    ):
        matches = method_nodes(
            text,
            method_name,
        )

        if not matches:
            continue

        if len(
            matches
        ) != 1:
            raise MigrationError(
                f"{method_name} expected at most once, "
                f"found {len(matches)}"
            )

        migrated, did_change = add_guard_to_method(
            text,
            method_name,
            "reject_atlas_mutation",
        )

        text = migrated

        if did_change:
            changed.append(
                method_name
            )

    return (
        text,
        changed,
    )


def validate_method_guard(
    text: str,
    method_name: str,
    expected_guard: str,
) -> None:
    method = method_node(
        text,
        method_name,
    )

    actual = first_guard_name(
        method
    )

    if actual != expected_guard:
        raise MigrationError(
            f"{expected_guard} is not first in "
            f"{method_name}; found {actual!r}"
        )


def validate_result(
    text: str,
) -> None:
    parse_python(
        text
    )

    if text.count(
        "try_handle_get as try_handle_atlas_get"
    ) != 1:
        raise MigrationError(
            "Atlas GET adapter import missing or duplicated"
        )

    if text.count(
        "reject_atlas_mutation"
    ) < 1:
        raise MigrationError(
            "Atlas mutation adapter unavailable"
        )

    validate_method_guard(
        text,
        "do_GET",
        "try_handle_atlas_get",
    )

    for method_name in (
        "do_POST",
        "do_PUT",
        "do_PATCH",
        "do_DELETE",
    ):
        matches = method_nodes(
            text,
            method_name,
        )

        if not matches:
            continue

        if len(
            matches
        ) != 1:
            raise MigrationError(
                f"{method_name} expected at most once, "
                f"found {len(matches)}"
            )

        validate_method_guard(
            text,
            method_name,
            "reject_atlas_mutation",
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

    parse_python(
        original
    )

    migrated, import_changed = add_import(
        original
    )

    migrated, get_changed = add_guard_to_method(
        migrated,
        "do_GET",
        "try_handle_atlas_get",
    )

    (
        migrated,
        mutation_methods,
    ) = add_mutation_guards(
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
        "projection_only":
            True,
        "mutation_authority_added":
            False,
        "target":
            str(
                server_path
            ),
        "atlas_adapter":
            str(
                adapter_path
            ),
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
