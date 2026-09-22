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
    "vessel-load-module-recursive-migration.v1"
)

authority_effect = "none"

runtime_root = Path(
    "/root/savant-runtime"
)

source_root = (
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
    / "underscore"
    / "rubric"
    / "vessel"
    / "source"
)

primitives_path = (
    source_root
    / "primitives.py"
)

target_paths = (
    source_root
    / "recursive_pipeline.py",
    source_root
    / "underscore_pipeline.py",
)

target_group_id = (
    "primitive-1116a2b273621880eb9d"
)

shared_import = (
    "from primitives import load_module"
)

allowed_builtin_globals = {
    "Exception",
    "ImportError",
    "RuntimeError",
    "TypeError",
    "ValueError",
    "bool",
    "bytes",
    "dict",
    "float",
    "int",
    "len",
    "list",
    "object",
    "set",
    "str",
    "tuple",
}


def parse_module(
    text: str,
    path: Path,
) -> ast.Module:
    try:
        return ast.parse(
            text,
            filename=str(path),
        )

    except SyntaxError as exc:
        raise RuntimeError(
            f"unable to parse {path}: {exc}"
        ) from exc


def top_level_function(
    module: ast.Module,
    name: str,
) -> ast.FunctionDef | None:
    matches = [
        node
        for node in module.body
        if (
            isinstance(
                node,
                ast.FunctionDef,
            )
            and node.name == name
        )
    ]

    if not matches:
        return None

    if len(matches) != 1:
        raise RuntimeError(
            f"expected one top-level {name}, "
            f"found {len(matches)}"
        )

    return matches[0]


def normalized_function(
    node: ast.FunctionDef,
) -> str:
    return ast.dump(
        node,
        annotate_fields=True,
        include_attributes=False,
    )


def source_segment(
    text: str,
    node: ast.AST,
) -> str:
    segment = ast.get_source_segment(
        text,
        node,
    )

    if segment is None:
        raise RuntimeError(
            "unable to recover function source"
        )

    return segment.rstrip() + "\n\n"


def module_import_bindings(
    module: ast.Module,
) -> dict[str, str]:
    bindings: dict[str, str] = {}

    for node in module.body:
        if isinstance(
            node,
            ast.Import,
        ):
            for alias in node.names:
                bound = (
                    alias.asname
                    or alias.name.split(
                        "."
                    )[0]
                )

                if alias.asname:
                    statement = (
                        f"import {alias.name} "
                        f"as {alias.asname}"
                    )
                else:
                    statement = (
                        f"import {alias.name}"
                    )

                bindings[bound] = statement

        elif isinstance(
            node,
            ast.ImportFrom,
        ):
            if node.module is None:
                continue

            if node.level:
                continue

            for alias in node.names:
                if alias.name == "*":
                    continue

                bound = (
                    alias.asname
                    or alias.name
                )

                statement = (
                    f"from {node.module} "
                    f"import {alias.name}"
                )

                if alias.asname:
                    statement += (
                        f" as {alias.asname}"
                    )

                bindings[bound] = statement

    return bindings


def function_globals(
    function: ast.FunctionDef,
) -> set[str]:
    parameters: set[str] = set()

    for argument in (
        list(
            function.args.posonlyargs
        )
        + list(
            function.args.args
        )
        + list(
            function.args.kwonlyargs
        )
    ):
        parameters.add(
            argument.arg
        )

    if function.args.vararg:
        parameters.add(
            function.args.vararg.arg
        )

    if function.args.kwarg:
        parameters.add(
            function.args.kwarg.arg
        )

    local_bindings: set[str] = set(
        parameters
    )

    for node in ast.walk(
        function
    ):
        if (
            isinstance(
                node,
                ast.Name,
            )
            and isinstance(
                node.ctx,
                (
                    ast.Store,
                    ast.Del,
                ),
            )
        ):
            local_bindings.add(
                node.id
            )

        elif isinstance(
            node,
            (
                ast.FunctionDef,
                ast.AsyncFunctionDef,
                ast.ClassDef,
            ),
        ) and node is not function:
            local_bindings.add(
                node.name
            )

        elif isinstance(
            node,
            ast.Import,
        ):
            for alias in node.names:
                local_bindings.add(
                    alias.asname
                    or alias.name.split(
                        "."
                    )[0]
                )

        elif isinstance(
            node,
            ast.ImportFrom,
        ):
            for alias in node.names:
                if alias.name != "*":
                    local_bindings.add(
                        alias.asname
                        or alias.name
                    )

    loaded = {
        node.id
        for node in ast.walk(
            function
        )
        if (
            isinstance(
                node,
                ast.Name,
            )
            and isinstance(
                node.ctx,
                ast.Load,
            )
        )
    }

    return (
        loaded
        - local_bindings
        - allowed_builtin_globals
    )


def has_import_statement(
    text: str,
    statement: str,
) -> bool:
    wanted = ast.dump(
        ast.parse(
            statement
        ).body[0],
        annotate_fields=True,
        include_attributes=False,
    )

    module = ast.parse(
        text
    )

    for node in module.body:
        if not isinstance(
            node,
            (
                ast.Import,
                ast.ImportFrom,
            ),
        ):
            continue

        current = ast.dump(
            node,
            annotate_fields=True,
            include_attributes=False,
        )

        if current == wanted:
            return True

    return False


def import_insertion_index(
    text: str,
    path: Path,
) -> int:
    module = parse_module(
        text,
        path,
    )

    last = 0

    for node in module.body:
        if (
            isinstance(
                node,
                ast.Expr,
            )
            and isinstance(
                node.value,
                ast.Constant,
            )
            and isinstance(
                node.value.value,
                str,
            )
        ):
            last = int(
                node.end_lineno
                or node.lineno
            )
            continue

        if isinstance(
            node,
            (
                ast.Import,
                ast.ImportFrom,
            ),
        ):
            last = int(
                node.end_lineno
                or node.lineno
            )
            continue

        break

    return last


def add_import_statement(
    text: str,
    path: Path,
    statement: str,
) -> str:
    if has_import_statement(
        text,
        statement,
    ):
        return text

    lines = text.splitlines(
        keepends=True
    )

    insertion = import_insertion_index(
        text,
        path,
    )

    lines.insert(
        insertion,
        statement + "\n",
    )

    return "".join(
        lines
    )


def remove_function(
    text: str,
    node: ast.FunctionDef,
) -> str:
    if node.end_lineno is None:
        raise RuntimeError(
            "function end line unavailable"
        )

    lines = text.splitlines(
        keepends=True
    )

    start = (
        node.lineno - 1
    )
    end = node.end_lineno

    while (
        end < len(lines)
        and lines[end].strip() == ""
    ):
        end += 1

    del lines[
        start:end
    ]

    return "".join(
        lines
    )


def compile_text(
    text: str,
    path: Path,
) -> None:
    compile(
        text,
        str(path),
        "exec",
    )


def primitive_function_insertion(
    text: str,
) -> int:
    module = parse_module(
        text,
        primitives_path,
    )

    lines = text.splitlines(
        keepends=True
    )

    for node in module.body:
        if not isinstance(
            node,
            ast.If,
        ):
            continue

        test = node.test

        if not isinstance(
            test,
            ast.Compare,
        ):
            continue

        if (
            isinstance(
                test.left,
                ast.Name,
            )
            and test.left.id
            == "__name__"
        ):
            return (
                node.lineno - 1
            )

    return len(
        lines
    )


def append_primitive_function(
    text: str,
    function_source: str,
) -> str:
    module = parse_module(
        text,
        primitives_path,
    )

    existing = top_level_function(
        module,
        "load_module",
    )

    incoming_module = ast.parse(
        function_source
    )

    incoming = top_level_function(
        incoming_module,
        "load_module",
    )

    if incoming is None:
        raise RuntimeError(
            "incoming load_module unavailable"
        )

    if existing is not None:
        if (
            normalized_function(
                existing
            )
            != normalized_function(
                incoming
            )
        ):
            raise RuntimeError(
                "primitives.py already owns "
                "a different load_module"
            )

        return text

    lines = text.splitlines(
        keepends=True
    )

    insertion = (
        primitive_function_insertion(
            text
        )
    )

    prefix = ""

    if (
        insertion > 0
        and lines[
            insertion - 1
        ].strip()
    ):
        prefix = "\n"

    lines.insert(
        insertion,
        prefix
        + function_source,
    )

    result = "".join(
        lines
    )

    compile_text(
        result,
        primitives_path,
    )

    return result


def resolve_family() -> tuple[
    str,
    list[str],
]:
    canonical_source: str | None = None
    canonical_ast: str | None = None
    required_imports: dict[
        str,
        str,
    ] = {}

    for path in target_paths:
        if not path.is_file():
            raise RuntimeError(
                "target unavailable: "
                + str(path)
            )

        text = path.read_text(
            encoding="utf-8"
        )

        module = parse_module(
            text,
            path,
        )

        function = top_level_function(
            module,
            "load_module",
        )

        if function is None:
            if has_import_statement(
                text,
                shared_import,
            ):
                continue

            raise RuntimeError(
                "load_module unavailable in "
                + str(path)
            )

        normalized = normalized_function(
            function
        )

        if canonical_ast is None:
            canonical_ast = normalized
            canonical_source = source_segment(
                text,
                function,
            )

        elif normalized != canonical_ast:
            raise RuntimeError(
                "target load_module "
                "implementations differ"
            )

        import_bindings = (
            module_import_bindings(
                module
            )
        )

        unresolved: list[str] = []

        for name in sorted(
            function_globals(
                function
            )
        ):
            statement = (
                import_bindings.get(
                    name
                )
            )

            if statement is None:
                unresolved.append(
                    name
                )
                continue

            existing = (
                required_imports.get(
                    name
                )
            )

            if (
                existing is not None
                and existing != statement
            ):
                raise RuntimeError(
                    "load_module import "
                    "dependency differs for "
                    + name
                )

            required_imports[
                name
            ] = statement

        if unresolved:
            raise RuntimeError(
                "load_module has consumer-local "
                "global dependencies in "
                + str(path)
                + ": "
                + ", ".join(
                    unresolved
                )
            )

    if canonical_source is None:
        primitive_text = (
            primitives_path.read_text(
                encoding="utf-8"
            )
        )

        primitive_module = parse_module(
            primitive_text,
            primitives_path,
        )

        existing = top_level_function(
            primitive_module,
            "load_module",
        )

        if existing is None:
            raise RuntimeError(
                "migration state is incomplete"
            )

        canonical_source = (
            source_segment(
                primitive_text,
                existing,
            )
        )

    return (
        canonical_source,
        sorted(
            set(
                required_imports.values()
            )
        ),
    )


def transform_primitives(
    function_source: str,
    imports: list[str],
) -> tuple[
    str,
    str,
]:
    original = (
        primitives_path.read_text(
            encoding="utf-8"
        )
    )

    migrated = original

    for statement in imports:
        migrated = add_import_statement(
            migrated,
            primitives_path,
            statement,
        )

    before_module = parse_module(
        migrated,
        primitives_path,
    )

    existed_before = (
        top_level_function(
            before_module,
            "load_module",
        )
        is not None
    )

    migrated = append_primitive_function(
        migrated,
        function_source,
    )

    compile_text(
        migrated,
        primitives_path,
    )

    return (
        migrated,
        (
            "already_present"
            if existed_before
            else "added"
        ),
    )


def transform_target(
    path: Path,
) -> tuple[
    str,
    str,
]:
    original = path.read_text(
        encoding="utf-8"
    )

    module = parse_module(
        original,
        path,
    )

    function = top_level_function(
        module,
        "load_module",
    )

    if function is None:
        if has_import_statement(
            original,
            shared_import,
        ):
            compile_text(
                original,
                path,
            )

            return (
                original,
                "already_migrated",
            )

        raise RuntimeError(
            "incomplete migration state: "
            + str(path)
        )

    migrated = remove_function(
        original,
        function,
    )

    migrated = add_import_statement(
        migrated,
        path,
        shared_import,
    )

    compile_text(
        migrated,
        path,
    )

    return (
        migrated,
        "migrated",
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
    if not primitives_path.is_file():
        raise RuntimeError(
            "primitives.py unavailable"
        )

    (
        function_source,
        required_imports,
    ) = resolve_family()

    (
        primitive_text,
        primitive_disposition,
    ) = transform_primitives(
        function_source,
        required_imports,
    )

    target_originals: dict[
        Path,
        str,
    ] = {}

    target_changes: dict[
        Path,
        tuple[str, str],
    ] = {}

    for path in target_paths:
        target_originals[path] = (
            path.read_text(
                encoding="utf-8"
            )
        )

        target_changes[path] = (
            transform_target(
                path
            )
        )

    primitive_original = (
        primitives_path.read_text(
            encoding="utf-8"
        )
    )

    results: list[
        dict[str, str]
    ] = []

    if apply:
        written: list[
            Path
        ] = []

        primitive_written = False

        try:
            if (
                primitive_text
                != primitive_original
            ):
                atomic_write(
                    primitives_path,
                    primitive_text,
                )

                primitive_written = True

            for path in target_paths:
                migrated, disposition = (
                    target_changes[
                        path
                    ]
                )

                if disposition == "migrated":
                    atomic_write(
                        path,
                        migrated,
                    )

                    written.append(
                        path
                    )

                results.append(
                    {
                        "path":
                            str(path),
                        "disposition":
                            disposition,
                    }
                )

        except Exception:
            for path in reversed(
                written
            ):
                atomic_write(
                    path,
                    target_originals[
                        path
                    ],
                )

            if primitive_written:
                atomic_write(
                    primitives_path,
                    primitive_original,
                )

            raise

    else:
        for path in target_paths:
            _, disposition = (
                target_changes[
                    path
                ]
            )

            results.append(
                {
                    "path":
                        str(path),
                    "disposition":
                        disposition,
                }
            )

    return {
        "schema":
            schema_version,
        "authority_effect":
            authority_effect,
        "target_group_id":
            target_group_id,
        "apply":
            apply,
        "status":
            "passed",
        "primitive": {
            "path":
                str(
                    primitives_path
                ),
            "disposition":
                primitive_disposition,
        },
        "required_imports":
            required_imports,
        "target_count":
            len(
                target_paths
            ),
        "migrated_count":
            sum(
                1
                for item in results
                if item[
                    "disposition"
                ] == "migrated"
            ),
        "already_migrated_count":
            sum(
                1
                for item in results
                if item[
                    "disposition"
                ] == "already_migrated"
            ),
        "targets":
            results,
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
                    "target_group_id":
                        target_group_id,
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
