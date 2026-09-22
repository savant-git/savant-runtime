#!/usr/bin/env python3

from __future__ import annotations

import argparse
import ast
import copy
import json
import os
import tempfile
from pathlib import Path
from typing import Any


schema_version = (
    "savant.assurance."
    "vessel-load-module-production-migration.v1"
)

authority_effect = "none"

target_group_id = (
    "primitive-cfb51b345c26d3cb3451"
)

primitive_name = (
    "load_module_production"
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
    / "vessel"
    / "source"
)

primitives_path = (
    source_root
    / "primitives.py"
)

target_paths = (
    source_root
    / "production_pipeline.py",
    source_root
    / "production_stable.py",
)

source_name = "load_module"

shared_import = (
    "from primitives import "
    "load_module_production as load_module"
)

safe_builtins = {
    "Exception",
    "False",
    "ImportError",
    "None",
    "RuntimeError",
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
            f"expected exactly one "
            f"top-level {name}"
        )

    return matches[0]


def normalized_function(
    node: ast.FunctionDef,
) -> str:
    normalized = copy.deepcopy(
        node
    )

    normalized.name = (
        "__vessel_load_module__"
    )

    return ast.dump(
        normalized,
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


def rename_function_source(
    source: str,
) -> str:
    module = ast.parse(
        source
    )

    function = named_function(
        module,
        source_name,
    )

    if function is None:
        raise RuntimeError(
            "source load_module unavailable"
        )

    function.name = primitive_name

    ast.fix_missing_locations(
        module
    )

    return (
        ast.unparse(
            module
        ).rstrip()
        + "\n\n"
    )


def import_bindings(
    module: ast.Module,
) -> dict[str, str]:
    result: dict[
        str,
        str,
    ] = {}

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
    locals_seen: set[str] = set()

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
        locals_seen.add(
            argument.arg
        )

    if function.args.vararg:
        locals_seen.add(
            function.args.vararg.arg
        )

    if function.args.kwarg:
        locals_seen.add(
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
            locals_seen.add(
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
            locals_seen.add(
                node.name
            )

        elif isinstance(
            node,
            ast.Import,
        ):
            for alias in node.names:
                locals_seen.add(
                    alias.asname
                    or alias.name.split(".")[0]
                )

        elif isinstance(
            node,
            ast.ImportFrom,
        ):
            for alias in node.names:
                if alias.name != "*":
                    locals_seen.add(
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
        - locals_seen
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
    canonical: str | None = None
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
            source_name,
        )

        if function is None:
            if has_import(
                text,
                shared_import,
            ):
                continue

            raise RuntimeError(
                "load_module unavailable: "
                + str(path)
            )

        normalized = normalized_function(
            function
        )

        if canonical is None:
            canonical = normalized
            canonical_source = (
                source_segment(
                    text,
                    function,
                )
            )

        elif normalized != canonical:
            raise RuntimeError(
                "production load_module "
                "implementations differ"
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
                "consumer-local dependencies: "
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

        existing = named_function(
            primitive_module,
            primitive_name,
        )

        if existing is None:
            raise RuntimeError(
                "incomplete migration state"
            )

        return (
            source_segment(
                primitive_text,
                existing,
            ),
            [],
        )

    return (
        rename_function_source(
            canonical_source
        ),
        sorted(
            set(
                required_imports.values()
            )
        ),
    )


def add_primitive(
    text: str,
    source: str,
) -> tuple[str, str]:
    module = parse_module(
        text,
        primitives_path,
    )

    existing = named_function(
        module,
        primitive_name,
    )

    incoming_module = ast.parse(
        source
    )

    incoming = named_function(
        incoming_module,
        primitive_name,
    )

    if incoming is None:
        raise RuntimeError(
            "incoming primitive unavailable"
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
                "existing production primitive "
                "differs"
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
    imports: list[str],
) -> tuple[str, str]:
    text = primitives_path.read_text(
        encoding="utf-8"
    )

    migrated = text

    for statement in imports:
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
) -> tuple[str, str]:
    original = path.read_text(
        encoding="utf-8"
    )

    module = parse_module(
        original,
        path,
    )

    function = named_function(
        module,
        source_name,
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
            "incomplete target migration: "
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
    (
        shared_source,
        required_imports,
    ) = resolve_family()

    primitive_original = (
        primitives_path.read_text(
            encoding="utf-8"
        )
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
        written: list[
            Path
        ] = []

        primitive_written = False

        try:
            if (
                primitive_migrated
                != primitive_original
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
                    originals[
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
                primitive_name,
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
