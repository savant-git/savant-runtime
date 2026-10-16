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
    "attach-atlas-to-niche-taskboard.v2"
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

get_guard_lines = (
    "if try_handle_atlas_get(self):",
    "    return",
    "",
)

mutation_guard_lines = (
    "if reject_atlas_mutation(self):",
    "    return",
    "",
)


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
    tree = parse_python(text)
    offsets = offsets_for_text(text)

    body = list(tree.body)
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


def method_node(
    text: str,
    method_name: str,
) -> ast.FunctionDef | ast.AsyncFunctionDef:
    tree = parse_python(text)

    matches = [
        node
        for node
        in ast.walk(tree)
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

    if len(matches) != 1:
        raise MigrationError(
            f"{method_name} expected once, "
            f"found {len(matches)}"
        )

    method = matches[0]

    if not method.body:
        raise MigrationError(
            f"{method_name} has no body"
        )

    return method


def render_guard(
    base_indent: int,
    lines: tuple[str, ...],
) -> str:
    indentation = " " * base_indent

    rendered = []

    for line in lines:
        if not line:
            rendered.append("\n")
            continue

        rendered.append(
            indentation
            + line
            + "\n"
        )

    return "".join(rendered)


def add_import(
    text: str,
) -> tuple[
    str,
    bool,
]:
    if (
        "try_handle_get as try_handle_atlas_get"
        in text
        and "reject_atlas_mutation"
        in text
    ):
        return (
            text,
            False,
        )

    if (
        "try_handle_atlas_get"
        in text
        or "reject_atlas_mutation"
        in text
    ):
        raise MigrationError(
            "partial Atlas adapter import already exists"
        )

    offset = import_insertion_offset(
        text
    )

    prefix = text[:offset]
    suffix = text[offset:]

    separator = (
        ""
        if prefix.endswith("\n\n")
        or not prefix
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


def add_method_guard(
    text: str,
    method_name: str,
    marker: str,
    guard_lines: tuple[str, ...],
) -> tuple[
    str,
    bool,
]:
    if marker in text:
        return (
            text,
            False,
        )

    method = method_node(
        text,
        method_name,
    )

    first_statement = method.body[0]

    base_indent = (
        first_statement.col_offset
    )

    if base_indent <= method.col_offset:
        raise MigrationError(
            f"{method_name} body indentation invalid"
        )

    offsets = offsets_for_text(text)

    insertion_offset = offsets[
        first_statement.lineno - 1
    ]

    guard = render_guard(
        base_indent,
        guard_lines,
    )

    migrated = (
        text[:insertion_offset]
        + guard
        + text[insertion_offset:]
    )

    parse_python(
        migrated
    )

    return (
        migrated,
        True,
    )


def validate_get_guard(
    text: str,
) -> None:
    method = method_node(
        text,
        "do_GET",
    )

    first = method.body[0]

    if not isinstance(
        first,
        ast.If,
    ):
        raise MigrationError(
            "Atlas GET guard is not first in do_GET"
        )

    expression = ast.unparse(
        first.test
    )

    if expression != (
        "try_handle_atlas_get(self)"
    ):
        raise MigrationError(
            "unexpected first do_GET guard: "
            + expression
        )


def validate_mutation_guard(
    text: str,
    method_name: str,
) -> None:
    method = method_node(
        text,
        method_name,
    )

    first = method.body[0]

    if not isinstance(
        first,
        ast.If,
    ):
        raise MigrationError(
            f"Atlas mutation guard is not first in {method_name}"
        )

    expression = ast.unparse(
        first.test
    )

    if expression != (
        "reject_atlas_mutation(self)"
    ):
        raise MigrationError(
            f"unexpected first {method_name} guard: "
            + expression
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
        tree = parse_python(text)

        exists = any(
            isinstance(
                node,
                (
                    ast.FunctionDef,
                    ast.AsyncFunctionDef,
                ),
            )
            and node.name == method_name
            for node
            in ast.walk(tree)
        )

        if not exists:
            continue

        migrated, did_change = add_method_guard(
            text,
            method_name,
            "if reject_atlas_mutation(self):",
            mutation_guard_lines,
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


def validate_result(
    text: str,
) -> None:
    parse_python(text)

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

    validate_get_guard(
        text
    )

    tree = parse_python(text)

    mutation_methods = [
        node.name
        for node
        in ast.walk(tree)
        if isinstance(
            node,
            (
                ast.FunctionDef,
                ast.AsyncFunctionDef,
            ),
        )
        and node.name
        in {
            "do_POST",
            "do_PUT",
            "do_PATCH",
            "do_DELETE",
        }
    ]

    for method_name in mutation_methods:
        validate_mutation_guard(
            text,
            method_name,
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
) -> dict[str, Any]:
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

    migrated, get_changed = add_method_guard(
        migrated,
        "do_GET",
        "if try_handle_atlas_get(self):",
        get_guard_lines,
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
            installed = server_path.read_text(
                encoding="utf-8"
            )

            validate_result(
                installed
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
