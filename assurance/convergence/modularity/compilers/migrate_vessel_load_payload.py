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
    "vessel-load-payload-migration.v1"
)

authority_effect = "none"

target_group_id = (
    "primitive-6f61211d73cc5f32637f"
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
    / "divergence_compiler.py",
    source_root
    / "ideal_state.py",
)

family_names = {
    "load_json",
    "load_payload",
}

primitive_name = "load_payload"

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


def family_function(
    module: ast.Module,
) -> ast.FunctionDef | None:
    matches = [
        node
        for node in module.body
        if (
            isinstance(
                node,
                ast.FunctionDef,
            )
            and node.name
            in family_names
        )
    ]

    if not matches:
        return None

    if len(matches) != 1:
        raise RuntimeError(
            "expected exactly one "
            "target family function"
        )

    return matches[0]


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
            f"multiple top-level {name} "
            "definitions"
        )

    return matches[0]


def normalized_family_function(
    node: ast.FunctionDef,
) -> str:
    normalized = copy.deepcopy(
        node
    )

    normalized.name = (
        "__vessel_payload_primitive__"
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
    name: str,
) -> str:
    module = ast.parse(
        source
    )

    function = family_function(
        module
    )

    if function is None:
        raise RuntimeError(
            "family function unavailable"
        )

    function.name = name

    ast.fix_missing_locations(
        module
    )

    try:
        generated = ast.unparse(
            module
        )

    except Exception as exc:
        raise RuntimeError(
            "unable to normalize shared "
            "primitive source"
        ) from exc

    return (
        generated.rstrip()
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
                    or alias.name.split(
                        "."
                    )[0]
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


def has_import_statement(
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
    if has_import_statement(
        text,
        statement,
    ):
        return text

    lines = text.splitlines(
        keepends=True
    )

    insertion = import_insertion_line(
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
    function: ast.FunctionDef,
) -> str:
    if function.end_lineno is None:
        raise RuntimeError(
            "function end line unavailable"
        )

    lines = text.splitlines(
        keepends=True
    )

    start = (
        function.lineno - 1
    )

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
            return (
                node.lineno - 1
            )

    return len(
        lines
    )


def resolve_family() -> tuple[
    str,
    dict[Path, str],
    list[str],
]:
    canonical_signature: str | None = None
    canonical_source: str | None = None

    local_names: dict[
        Path,
        str,
    ] = {}

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

        function = family_function(
            module
        )

        if function is None:
            possible_imports = (
                "from primitives "
                "import load_payload",
                "from primitives "
                "import load_payload as load_json",
            )

            if any(
                has_import_statement(
                    text,
                    statement,
                )
                for statement
                in possible_imports
            ):
                continue

            raise RuntimeError(
                "target family function "
                "unavailable: "
                + str(path)
            )

        local_names[
            path
        ] = function.name

        signature = (
            normalized_family_function(
                function
            )
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
                "load_json/load_payload "
                "family implementations differ"
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
                "incomplete prior migration"
            )

        canonical_source = source_segment(
            primitive_text,
            existing,
        )

    shared_source = (
        rename_function_source(
            canonical_source,
            primitive_name,
        )
    )

    return (
        shared_source,
        local_names,
        sorted(
            set(
                required_imports.values()
            )
        ),
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
            "incoming load_payload missing"
        )

    if existing is not None:
        if (
            normalized_family_function(
                existing
            )
            != normalized_family_function(
                incoming
            )
        ):
            raise RuntimeError(
                "primitives.py already owns "
                "a different load_payload"
            )

        return (
            text,
            "already_present",
        )

    lines = text.splitlines(
        keepends=True
    )

    insertion = (
        primitive_insertion_line(
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
    shared_source: str,
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
        shared_source,
    )

    compile_text(
        migrated,
        primitives_path,
    )

    return (
        migrated,
        disposition,
    )


def target_import(
    local_name: str,
) -> str:
    if local_name == "load_payload":
        return (
            "from primitives "
            "import load_payload"
        )

    if local_name == "load_json":
        return (
            "from primitives "
            "import load_payload as load_json"
        )

    raise RuntimeError(
        "unsupported local family name: "
        + local_name
    )


def detect_existing_target_import(
    text: str,
) -> str | None:
    candidates = (
        (
            "load_payload",
            "from primitives "
            "import load_payload",
        ),
        (
            "load_json",
            "from primitives "
            "import load_payload as load_json",
        ),
    )

    for local_name, statement in candidates:
        if has_import_statement(
            text,
            statement,
        ):
            return local_name

    return None


def transform_target(
    path: Path,
    known_local_name: str | None,
) -> tuple[
    str,
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

    function = family_function(
        module
    )

    if function is None:
        existing_name = (
            detect_existing_target_import(
                original
            )
        )

        if existing_name is None:
            raise RuntimeError(
                "incomplete migration state: "
                + str(path)
            )

        compile_text(
            original,
            path,
        )

        return (
            original,
            "already_migrated",
            existing_name,
        )

    local_name = function.name

    if (
        known_local_name is not None
        and known_local_name
        != local_name
    ):
        raise RuntimeError(
            "local name changed during "
            "migration preparation"
        )

    migrated = remove_function(
        original,
        function,
    )

    migrated = add_import(
        migrated,
        path,
        target_import(
            local_name
        ),
    )

    compile_text(
        migrated,
        path,
    )

    return (
        migrated,
        "migrated",
        local_name,
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
    if not primitives_path.is_file():
        raise RuntimeError(
            "primitives.py unavailable"
        )

    (
        shared_source,
        local_names,
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
        tuple[
            str,
            str,
            str,
        ],
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
            path,
            local_names.get(
                path
            ),
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
                    local_name,
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
                        "local_name":
                            local_name,
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
                atomic_write(
                    primitives_path,
                    primitive_original,
                )

            raise

    else:
        for path in target_paths:
            (
                _,
                disposition,
                local_name,
            ) = transformations[
                path
            ]

            results.append(
                {
                    "path":
                        str(path),
                    "local_name":
                        local_name,
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
