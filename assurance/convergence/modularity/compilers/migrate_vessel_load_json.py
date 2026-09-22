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
    "vessel-load-json-migration.v1"
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

target_paths = tuple(
    source_root / name
    for name in (
        "negative_knowledge.py",
        "production_pipeline.py",
        "production_stable.py",
        "recursive_pipeline.py",
        "underscore_pipeline.py",
    )
)

shared_import = (
    "from primitives import load_json"
)

shared_function_source = """def load_json(
    path: str,
) -> dict[str, Any]:
    if path == "-":
        raw = sys.stdin.read()

    else:
        raw = Path(
            path
        ).read_text(
            encoding="utf-8"
        )

    return require_object(
        json.loads(
            raw
        ),
        "input",
    )


"""


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
            "unable to parse: "
            + str(path)
            + ": "
            + str(exc)
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
            "multiple top-level "
            + name
            + " definitions found"
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


def expected_function() -> ast.FunctionDef:
    module = ast.parse(
        shared_function_source
    )

    node = named_function(
        module,
        "load_json",
    )

    if node is None:
        raise RuntimeError(
            "expected load_json unavailable"
        )

    return node


def has_shared_import(
    module: ast.Module,
) -> bool:
    for node in module.body:
        if not isinstance(
            node,
            ast.ImportFrom,
        ):
            continue

        if node.module != "primitives":
            continue

        for alias in node.names:
            if (
                alias.name == "load_json"
                and (
                    alias.asname is None
                    or alias.asname == "load_json"
                )
            ):
                return True

    return False


def import_insertion_line(
    module: ast.Module,
) -> int:
    last_import_line = 0

    for node in module.body:
        if isinstance(
            node,
            (
                ast.Import,
                ast.ImportFrom,
            ),
        ):
            last_import_line = max(
                last_import_line,
                int(
                    node.end_lineno
                    or node.lineno
                ),
            )
            continue

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
            continue

        break

    if last_import_line <= 0:
        raise RuntimeError(
            "unable to resolve import block"
        )

    return last_import_line


def add_shared_import(
    text: str,
    path: Path,
) -> str:
    module = parse_module(
        text,
        path,
    )

    if has_shared_import(
        module
    ):
        return text

    line_number = (
        import_insertion_line(
            module
        )
    )

    lines = text.splitlines(
        keepends=True
    )

    lines.insert(
        line_number,
        shared_import + "\n",
    )

    return "".join(
        lines
    )


def remove_function(
    text: str,
    node: ast.FunctionDef,
) -> str:
    if (
        node.lineno is None
        or node.end_lineno is None
    ):
        raise RuntimeError(
            "load_json source range unavailable"
        )

    lines = text.splitlines(
        keepends=True
    )

    start = node.lineno - 1
    end = node.end_lineno

    while (
        end < len(lines)
        and lines[end].strip() == ""
    ):
        end += 1

    lines[
        start:end
    ] = []

    return "".join(
        lines
    )


def compile_text(
    text: str,
    path: Path,
) -> None:
    try:
        compile(
            text,
            str(path),
            "exec",
        )

    except Exception as exc:
        raise RuntimeError(
            "compiled migration is invalid: "
            + str(path)
            + ": "
            + str(exc)
        ) from exc


def ensure_import(
    text: str,
    statement: str,
    matcher,
) -> str:
    module = parse_module(
        text,
        primitives_path,
    )

    if matcher(
        module
    ):
        return text

    insertion = import_insertion_line(
        module
    )

    lines = text.splitlines(
        keepends=True
    )

    lines.insert(
        insertion,
        statement + "\n",
    )

    return "".join(
        lines
    )


def has_import_name(
    module: ast.Module,
    name: str,
) -> bool:
    for node in module.body:
        if not isinstance(
            node,
            ast.Import,
        ):
            continue

        for alias in node.names:
            if (
                alias.name == name
                and (
                    alias.asname is None
                    or alias.asname == name
                )
            ):
                return True

    return False


def has_from_import(
    module: ast.Module,
    module_name: str,
    name: str,
) -> bool:
    for node in module.body:
        if not isinstance(
            node,
            ast.ImportFrom,
        ):
            continue

        if node.module != module_name:
            continue

        for alias in node.names:
            if (
                alias.name == name
                and (
                    alias.asname is None
                    or alias.asname == name
                )
            ):
                return True

    return False


def ensure_dependencies(
    text: str,
) -> str:
    migrated = text

    migrated = ensure_import(
        migrated,
        "import json",
        lambda module: has_import_name(
            module,
            "json",
        ),
    )

    migrated = ensure_import(
        migrated,
        "import sys",
        lambda module: has_import_name(
            module,
            "sys",
        ),
    )

    migrated = ensure_import(
        migrated,
        "from pathlib import Path",
        lambda module: has_from_import(
            module,
            "pathlib",
            "Path",
        ),
    )

    migrated = ensure_import(
        migrated,
        "from typing import Any",
        lambda module: has_from_import(
            module,
            "typing",
            "Any",
        ),
    )

    return migrated


def primitive_insertion_line(
    module: ast.Module,
    line_count: int,
) -> int:
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

        if not (
            isinstance(
                test.left,
                ast.Name,
            )
            and test.left.id
            == "__name__"
        ):
            continue

        return node.lineno - 1

    return line_count


def add_shared_function(
    text: str,
) -> tuple[str, str]:
    module = parse_module(
        text,
        primitives_path,
    )

    existing = named_function(
        module,
        "load_json",
    )

    if existing is not None:
        expected = expected_function()

        if (
            normalized_function(
                existing
            )
            != normalized_function(
                expected
            )
        ):
            raise RuntimeError(
                "existing shared load_json "
                "differs from expected substance"
            )

        return (
            text,
            "already_present",
        )

    if (
        named_function(
            module,
            "require_object",
        )
        is None
    ):
        raise RuntimeError(
            "shared require_object unavailable"
        )

    migrated = ensure_dependencies(
        text
    )

    module = parse_module(
        migrated,
        primitives_path,
    )

    lines = migrated.splitlines(
        keepends=True
    )

    insertion = primitive_insertion_line(
        module,
        len(lines),
    )

    prefix = ""

    if (
        insertion > 0
        and lines[
            insertion - 1
        ].strip() != ""
    ):
        prefix = "\n"

    lines.insert(
        insertion,
        prefix
        + shared_function_source,
    )

    result = "".join(
        lines
    )

    compile_text(
        result,
        primitives_path,
    )

    return (
        result,
        "added",
    )


def verify_family() -> None:
    expected = normalized_function(
        expected_function()
    )

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

        local = named_function(
            module,
            "load_json",
        )

        if local is None:
            if has_shared_import(
                module
            ):
                continue

            raise RuntimeError(
                "target has neither local nor "
                "shared load_json: "
                + str(path)
            )

        if (
            normalized_function(
                local
            )
            != expected
        ):
            raise RuntimeError(
                "load_json family member "
                "differs semantically: "
                + str(path)
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

    local = named_function(
        module,
        "load_json",
    )

    if local is None:
        if not has_shared_import(
            module
        ):
            raise RuntimeError(
                "incomplete prior load_json "
                "migration: "
                + str(path)
            )

        compile_text(
            original,
            path,
        )

        return (
            original,
            "already_migrated",
        )

    migrated = remove_function(
        original,
        local,
    )

    migrated = add_shared_import(
        migrated,
        path,
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
            dir=str(path.parent),
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


def focused_check() -> None:
    namespace: dict[str, Any] = {}

    exec(
        """
from __future__ import annotations
import json
import sys
from pathlib import Path
from typing import Any

def require_object(value, label):
    if not isinstance(value, dict):
        raise TypeError(label)
    return value

"""
        + shared_function_source,
        namespace,
    )

    load_json = namespace[
        "load_json"
    ]

    temporary_descriptor, temporary_name = (
        tempfile.mkstemp(
            suffix=".json"
        )
    )

    temporary_path = Path(
        temporary_name
    )

    try:
        with os.fdopen(
            temporary_descriptor,
            "w",
            encoding="utf-8",
        ) as handle:
            handle.write(
                '{"alpha":1}'
            )

        result = load_json(
            str(
                temporary_path
            )
        )

        if result != {
            "alpha": 1,
        }:
            raise RuntimeError(
                "focused file load check failed"
            )

    finally:
        if temporary_path.exists():
            temporary_path.unlink()


def migrate(
    apply: bool,
) -> dict[str, Any]:
    if not primitives_path.is_file():
        raise RuntimeError(
            "shared primitives unavailable: "
            + str(primitives_path)
        )

    verify_family()
    focused_check()

    primitive_original = (
        primitives_path.read_text(
            encoding="utf-8"
        )
    )

    (
        primitive_migrated,
        primitive_disposition,
    ) = add_shared_function(
        primitive_original
    )

    originals: dict[
        Path,
        str,
    ] = {}

    transformed: dict[
        Path,
        tuple[str, str],
    ] = {}

    for path in target_paths:
        originals[path] = (
            path.read_text(
                encoding="utf-8"
            )
        )

        transformed[path] = (
            transform_target(
                path
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
                primitive_disposition
                == "added"
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
                ) = transformed[path]

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
                    originals[path],
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
                transformed[path]
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
        "apply":
            apply,
        "status":
            "passed",
        "focused_check":
            "passed",
        "primitive": {
            "path":
                str(
                    primitives_path
                ),
            "disposition":
                primitive_disposition,
        },
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
        report = migrate(
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
                        str(exc),
                },
                indent=2,
                sort_keys=True,
            )
        )

        return 1

    print(
        json.dumps(
            report,
            indent=2,
            sort_keys=True,
        )
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
