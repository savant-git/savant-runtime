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
    "structure-intelligence-write-json-migration.v1"
)

authority_effect = "none"

target_group_id = (
    "primitive-db982e76409469cdcf25"
)

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
    / "structure-intelligence"
    / "source"
)

primitives_path = (
    source_root
    / "primitives.py"
)

target_paths = (
    source_root
    / "compile_migration_manifest.py",
    source_root
    / "compile_structure_intelligence.py",
)

function_name = "write_json"

shared_import = (
    "from primitives import write_json"
)

safe_builtins = {
    "Exception",
    "False",
    "None",
    "True",
    "TypeError",
    "ValueError",
    "bool",
    "bytes",
    "dict",
    "float",
    "int",
    "isinstance",
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


def named_function(
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

    return (
        segment.rstrip()
        + "\n\n"
    )


def import_bindings(
    module: ast.Module,
) -> dict[str, str]:
    result: dict[str, str] = {}

    for node in module.body:
        if isinstance(
            node,
            ast.Import,
        ):
            for alias in node.names:
                bound = (
                    alias.asname
                    or alias.name.split(".")[0]
                )

                statement = (
                    f"import {alias.name}"
                )

                if alias.asname:
                    statement += (
                        f" as {alias.asname}"
                    )

                result[
                    bound
                ] = statement

        elif isinstance(
            node,
            ast.ImportFrom,
        ):
            if (
                node.module is None
                or node.level
            ):
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

                result[
                    bound
                ] = statement

    return result


def function_globals(
    function: ast.FunctionDef,
) -> set[str]:
    local_names: set[str] = set()

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
        local_names.add(
            argument.arg
        )

    if function.args.vararg:
        local_names.add(
            function.args.vararg.arg
        )

    if function.args.kwarg:
        local_names.add(
            function.args.kwarg.arg
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
            local_names.add(
                node.id
            )

        elif (
            isinstance(
                node,
                (
                    ast.FunctionDef,
                    ast.AsyncFunctionDef,
                    ast.ClassDef,
                ),
            )
            and node is not function
        ):
            local_names.add(
                node.name
            )

        elif isinstance(
            node,
            ast.Import,
        ):
            for alias in node.names:
                local_names.add(
                    alias.asname
                    or alias.name.split(".")[0]
                )

        elif isinstance(
            node,
            ast.ImportFrom,
        ):
            for alias in node.names:
                if alias.name != "*":
                    local_names.add(
                        alias.asname
                        or alias.name
                    )

    loaded_names = {
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
        loaded_names
        - local_names
        - safe_builtins
    )


def import_signature(
    statement: str,
) -> str:
    parsed = ast.parse(
        statement
    )

    if len(parsed.body) != 1:
        raise RuntimeError(
            "invalid import statement"
        )

    return ast.dump(
        parsed.body[0],
        annotate_fields=True,
        include_attributes=False,
    )


def has_import(
    text: str,
    statement: str,
) -> bool:
    wanted = import_signature(
        statement
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


def import_insertion_line(
    text: str,
    path: Path,
) -> int:
    module = parse_module(
        text,
        path,
    )

    line = 0

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
            line = int(
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
            line = int(
                node.end_lineno
                or node.lineno
            )
            continue

        break

    return line


def add_import(
    text: str,
    path: Path,
    statement: str,
) -> str:
    if has_import(
        text,
        statement,
    ):
        return text

    lines = text.splitlines(
        keepends=True
    )

    lines.insert(
        import_insertion_line(
            text,
            path,
        ),
        statement + "\n",
    )

    return "".join(
        lines
    )


def remove_function(
    text: str,
    function: ast.FunctionDef,
) -> str:
    if function.end_lineno is None:
        raise RuntimeError(
            "function end line unavailable"
        )

    lines = text.splitlines(
        keepends=True
    )

    start = function.lineno - 1
    end = function.end_lineno

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


def primitive_insertion_line(
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

        if (
            isinstance(
                test,
                ast.Compare,
            )
            and isinstance(
                test.left,
                ast.Name,
            )
            and test.left.id
            == "__name__"
        ):
            return node.lineno - 1

    return len(
        lines
    )


def resolve_family() -> tuple[
    str,
    list[str],
]:
    canonical_signature: str | None = None
    canonical_source: str | None = None

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

        function = named_function(
            module,
            function_name,
        )

        if function is None:
            if has_import(
                text,
                shared_import,
            ):
                continue

            raise RuntimeError(
                "write_json unavailable: "
                + str(path)
            )

        signature = normalized_function(
            function
        )

        if canonical_signature is None:
            canonical_signature = (
                signature
            )

            canonical_source = (
                source_segment(
                    text,
                    function,
                )
            )

        elif (
            signature
            != canonical_signature
        ):
            raise RuntimeError(
                "write_json implementations differ"
            )

        bindings = import_bindings(
            module
        )

        unresolved: list[str] = []

        for name in sorted(
            function_globals(
                function
            )
        ):
            statement = bindings.get(
                name
            )

            if statement is None:
                unresolved.append(
                    name
                )
                continue

            previous = (
                required_imports.get(
                    name
                )
            )

            if (
                previous is not None
                and previous != statement
            ):
                raise RuntimeError(
                    "dependency mismatch for "
                    + name
                )

            required_imports[
                name
            ] = statement

        if unresolved:
            raise RuntimeError(
                "consumer-local dependencies "
                "prevent convergence in "
                + str(path)
                + ": "
                + ", ".join(
                    unresolved
                )
            )

    if canonical_source is None:
        if not primitives_path.is_file():
            raise RuntimeError(
                "incomplete prior migration"
            )

        primitive_text = (
            primitives_path.read_text(
                encoding="utf-8"
            )
        )

        primitive_module = parse_module(
            primitive_text,
            primitives_path,
        )

        existing = named_function(
            primitive_module,
            function_name,
        )

        if existing is None:
            raise RuntimeError(
                "incomplete prior migration"
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


def initial_primitives_text() -> str:
    if primitives_path.exists():
        return primitives_path.read_text(
            encoding="utf-8"
        )

    return (
        "from __future__ import annotations\n\n"
    )


def add_primitive(
    text: str,
    source: str,
) -> tuple[
    str,
    str,
]:
    module = parse_module(
        text,
        primitives_path,
    )

    existing = named_function(
        module,
        function_name,
    )

    incoming_module = ast.parse(
        source
    )

    incoming = named_function(
        incoming_module,
        function_name,
    )

    if incoming is None:
        raise RuntimeError(
            "incoming write_json unavailable"
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
                "a different write_json"
            )

        return (
            text,
            "already_present",
        )

    lines = text.splitlines(
        keepends=True
    )

    insertion = primitive_insertion_line(
        text
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
        prefix + source,
    )

    migrated = "".join(
        lines
    )

    compile_text(
        migrated,
        primitives_path,
    )

    return (
        migrated,
        "added",
    )


def transform_primitives(
    source: str,
    required_imports: list[str],
) -> tuple[
    str,
    str,
]:
    text = initial_primitives_text()

    migrated = text

    for statement in required_imports:
        migrated = add_import(
            migrated,
            primitives_path,
            statement,
        )

    (
        migrated,
        disposition,
    ) = add_primitive(
        migrated,
        source,
    )

    compile_text(
        migrated,
        primitives_path,
    )

    return (
        migrated,
        disposition,
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

    function = named_function(
        module,
        function_name,
    )

    if function is None:
        if has_import(
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

    migrated = add_import(
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
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    mode = (
        path.stat().st_mode
        if path.exists()
        else 0o100644
    )

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
            mode & 0o7777,
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
    (
        shared_source,
        required_imports,
    ) = resolve_family()

    primitive_existed = (
        primitives_path.exists()
    )

    primitive_original = (
        primitives_path.read_text(
            encoding="utf-8"
        )
        if primitive_existed
        else None
    )

    (
        primitive_migrated,
        primitive_disposition,
    ) = transform_primitives(
        shared_source,
        required_imports,
    )

    originals: dict[
        Path,
        str,
    ] = {}

    transformations: dict[
        Path,
        tuple[str, str],
    ] = {}

    for path in target_paths:
        originals[
            path
        ] = path.read_text(
            encoding="utf-8"
        )

        transformations[
            path
        ] = transform_target(
            path
        )

    results: list[
        dict[str, str]
    ] = []

    if apply:
        written_targets: list[
            Path
        ] = []

        primitive_written = False

        try:
            current_primitive = (
                primitive_original
                if primitive_original
                is not None
                else ""
            )

            if (
                primitive_migrated
                != current_primitive
            ):
                atomic_write(
                    primitives_path,
                    primitive_migrated,
                )

                primitive_written = True

            for path in target_paths:
                (
                    migrated,
                    disposition,
                ) = transformations[
                    path
                ]

                if disposition == "migrated":
                    atomic_write(
                        path,
                        migrated,
                    )

                    written_targets.append(
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
                written_targets
            ):
                atomic_write(
                    path,
                    originals[
                        path
                    ],
                )

            if primitive_written:
                if primitive_existed:
                    atomic_write(
                        primitives_path,
                        primitive_original
                        or "",
                    )

                elif primitives_path.exists():
                    primitives_path.unlink()

            raise

    else:
        for path in target_paths:
            _, disposition = (
                transformations[
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
            "name":
                function_name,
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
                for result in results
                if result[
                    "disposition"
                ] == "migrated"
            ),
        "already_migrated_count":
            sum(
                1
                for result in results
                if result[
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
