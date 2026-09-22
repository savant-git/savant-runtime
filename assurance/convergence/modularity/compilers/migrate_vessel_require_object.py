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
    "vessel-require-object-migration.v2"
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
        "realization_adapter.py",
        "recursive_pipeline.py",
    )
)

shared_import = (
    "from primitives import require_object"
)

expected_function_source = """
def require_object(
    value: Any,
    name: str,
) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise TypeError(
            f"{name} must be an object"
        )

    return value
"""


def canonical_json(
    value: Any,
) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


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
            "unable to parse target: "
            + str(path)
            + ": "
            + str(exc)
        ) from exc


def expected_function_ast() -> ast.FunctionDef:
    module = ast.parse(
        expected_function_source
    )

    node = module.body[0]

    if not isinstance(
        node,
        ast.FunctionDef,
    ):
        raise RuntimeError(
            "internal expected primitive "
            "definition is invalid"
        )

    return node


expected_function = (
    expected_function_ast()
)


def normalized_function(
    node: ast.FunctionDef,
) -> str:
    return ast.dump(
        node,
        annotate_fields=True,
        include_attributes=False,
    )


expected_function_normalized = (
    normalized_function(
        expected_function
    )
)


def local_require_object(
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
            == "require_object"
        )
    ]

    if not matches:
        return None

    if len(matches) != 1:
        raise RuntimeError(
            "multiple top-level "
            "require_object definitions found"
        )

    return matches[0]


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
                alias.name
                == "require_object"
                and (
                    alias.asname is None
                    or alias.asname
                    == "require_object"
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

        break

    if last_import_line <= 0:
        raise RuntimeError(
            "unable to resolve import block"
        )

    return last_import_line


def remove_local_function(
    text: str,
    node: ast.FunctionDef,
) -> str:
    if (
        node.lineno is None
        or node.end_lineno is None
    ):
        raise RuntimeError(
            "require_object source range "
            "is unavailable"
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

    del lines[
        start:end
    ]

    return "".join(lines)


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

    return "".join(lines)


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


def primitive_available() -> None:
    if not primitives_path.is_file():
        raise RuntimeError(
            "shared primitive unavailable: "
            + str(primitives_path)
        )

    text = primitives_path.read_text(
        encoding="utf-8"
    )

    module = parse_module(
        text,
        primitives_path,
    )

    node = local_require_object(
        module
    )

    if node is None:
        raise RuntimeError(
            "shared primitives file does not "
            "define require_object"
        )

    if (
        normalized_function(node)
        != expected_function_normalized
    ):
        raise RuntimeError(
            "shared require_object no longer "
            "matches the verified primitive"
        )


def transform(
    path: Path,
) -> tuple[str, str]:
    if not path.is_file():
        raise RuntimeError(
            "target unavailable: "
            + str(path)
        )

    original = path.read_text(
        encoding="utf-8"
    )

    module = parse_module(
        original,
        path,
    )

    node = local_require_object(
        module
    )

    imported = has_shared_import(
        module
    )

    if node is None:
        if not imported:
            raise RuntimeError(
                "target has neither local nor "
                "shared require_object: "
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

    if (
        normalized_function(node)
        != expected_function_normalized
    ):
        raise RuntimeError(
            "local require_object differs from "
            "verified convergence primitive: "
            + str(path)
        )

    migrated = remove_local_function(
        original,
        node,
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


def migrate(
    apply: bool,
) -> dict[str, Any]:
    primitive_available()

    transformed: dict[
        Path,
        tuple[str, str]
    ] = {}

    originals: dict[
        Path,
        str,
    ] = {}

    for path in target_paths:
        originals[path] = (
            path.read_text(
                encoding="utf-8"
            )
        )

        transformed[path] = (
            transform(
                path
            )
        )

    results: list[
        dict[str, Any]
    ] = []

    if apply:
        written: list[Path] = []

        try:
            for path in target_paths:
                text, disposition = (
                    transformed[path]
                )

                if disposition == "migrated":
                    atomic_write(
                        path,
                        text,
                    )
                    written.append(
                        path
                    )

                results.append(
                    {
                        "path": str(path),
                        "disposition": (
                            disposition
                        ),
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

            raise

    else:
        for path in target_paths:
            _, disposition = (
                transformed[path]
            )

            results.append(
                {
                    "path": str(path),
                    "disposition": (
                        disposition
                    ),
                }
            )

    migrated_count = sum(
        1
        for result in results
        if result["disposition"]
        == "migrated"
    )

    already_migrated_count = sum(
        1
        for result in results
        if result["disposition"]
        == "already_migrated"
    )

    return {
        "schema": schema_version,
        "authority_effect": (
            authority_effect
        ),
        "apply": apply,
        "shared_primitive": str(
            primitives_path
        ),
        "target_count": len(
            target_paths
        ),
        "migrated_count": (
            migrated_count
        ),
        "already_migrated_count": (
            already_migrated_count
        ),
        "targets": results,
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
        report = {
            "schema": schema_version,
            "authority_effect": (
                authority_effect
            ),
            "apply": (
                arguments.apply
            ),
            "status": "failed",
            "error": str(exc),
        }

        print(
            json.dumps(
                report,
                indent=2,
                sort_keys=True,
            )
        )

        return 1

    report["status"] = "passed"

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
