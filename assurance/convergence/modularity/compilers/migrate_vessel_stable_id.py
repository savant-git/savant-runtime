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
    "vessel-stable-id-migration.v1"
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
        "divergence_compiler.py",
        "ideal_state.py",
        "negative_knowledge.py",
        "realization_adapter.py",
        "recursive_pipeline.py",
        "vessel_flow.py",
    )
)

binding_import = (
    "from primitives import bind_stable_id"
)

binding_assignment = (
    "stable_id = bind_stable_id(digest)"
)

shared_primitive_source = """
def bind_stable_id(
    digest_function: Any,
):
    if not callable(
        digest_function
    ):
        raise TypeError(
            "digest_function must be callable"
        )

    def stable_id(
        prefix: str,
        value: Any,
        width: int = 24,
    ) -> str:
        return (
            f"{prefix}_"
            f"{digest_function(value)[:width]}"
        )

    return stable_id


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


def normalized_function(
    node: ast.FunctionDef,
) -> str:
    return ast.dump(
        node,
        annotate_fields=True,
        include_attributes=False,
    )


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


def has_binding_assignment(
    module: ast.Module,
) -> bool:
    for node in module.body:
        if not isinstance(
            node,
            ast.Assign,
        ):
            continue

        if len(node.targets) != 1:
            continue

        target = node.targets[0]

        if not (
            isinstance(
                target,
                ast.Name,
            )
            and target.id == "stable_id"
        ):
            continue

        value = node.value

        if not isinstance(
            value,
            ast.Call,
        ):
            continue

        function = value.func

        if (
            isinstance(
                function,
                ast.Name,
            )
            and function.id
            == "bind_stable_id"
        ):
            return True

    return False


def has_binding_import(
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
                == "bind_stable_id"
                and (
                    alias.asname is None
                    or alias.asname
                    == "bind_stable_id"
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


def add_binding_import(
    text: str,
    path: Path,
) -> str:
    module = parse_module(
        text,
        path,
    )

    if has_binding_import(
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
        binding_import + "\n",
    )

    return "".join(
        lines
    )


def replace_function_with_binding(
    text: str,
    node: ast.FunctionDef,
) -> str:
    if (
        node.lineno is None
        or node.end_lineno is None
    ):
        raise RuntimeError(
            "stable_id source range unavailable"
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

    replacement = (
        binding_assignment
        + "\n\n"
    )

    lines[
        start:end
    ] = [
        replacement
    ]

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


def verify_original_family(
) -> str | None:
    normalized: str | None = None

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
            "stable_id",
        )

        if local is None:
            if has_binding_assignment(
                module
            ):
                continue

            raise RuntimeError(
                "target has neither local nor "
                "bound stable_id: "
                + str(path)
            )

        digest_node = named_function(
            module,
            "digest",
        )

        if digest_node is None:
            raise RuntimeError(
                "stable_id consumer has no "
                "local digest owner: "
                + str(path)
            )

        if digest_node.lineno >= local.lineno:
            raise RuntimeError(
                "digest must be defined before "
                "stable_id binding: "
                + str(path)
            )

        current = normalized_function(
            local
        )

        if normalized is None:
            normalized = current

        elif current != normalized:
            raise RuntimeError(
                "stable_id family is no longer "
                "implementation-identical: "
                + str(path)
            )

    return normalized


def ensure_typing_any(
    text: str,
    path: Path,
) -> str:
    module = parse_module(
        text,
        path,
    )

    for node in module.body:
        if not isinstance(
            node,
            ast.ImportFrom,
        ):
            continue

        if node.module != "typing":
            continue

        if any(
            alias.name == "Any"
            for alias in node.names
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
        "from typing import Any\n",
    )

    return "".join(
        lines
    )


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


def add_shared_primitive(
    text: str,
) -> tuple[str, str]:
    module = parse_module(
        text,
        primitives_path,
    )

    existing = named_function(
        module,
        "bind_stable_id",
    )

    if existing is not None:
        return (
            text,
            "already_present",
        )

    migrated = ensure_typing_any(
        text,
        primitives_path,
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

    if (
        insertion > 0
        and lines[
            insertion - 1
        ].strip() != ""
    ):
        shared = (
            "\n"
            + shared_primitive_source
        )
    else:
        shared = shared_primitive_source

    lines.insert(
        insertion,
        shared,
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
        "stable_id",
    )

    if local is None:
        if not (
            has_binding_assignment(
                module
            )
            and has_binding_import(
                module
            )
        ):
            raise RuntimeError(
                "incomplete prior stable_id "
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

    digest_node = named_function(
        module,
        "digest",
    )

    if digest_node is None:
        raise RuntimeError(
            "digest unavailable: "
            + str(path)
        )

    if digest_node.lineno >= local.lineno:
        raise RuntimeError(
            "digest occurs after stable_id: "
            + str(path)
        )

    migrated = (
        replace_function_with_binding(
            original,
            local,
        )
    )

    migrated = add_binding_import(
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


def focused_binding_check() -> None:
    namespace: dict[str, Any] = {
        "Any": Any,
    }

    exec(
        shared_primitive_source,
        namespace,
    )

    bind_stable_id = namespace[
        "bind_stable_id"
    ]

    calls: list[Any] = []

    def fixture_digest(
        value: Any,
    ) -> str:
        calls.append(
            value
        )
        return (
            "0123456789abcdef"
            "0123456789abcdef"
            "0123456789abcdef"
            "0123456789abcdef"
        )

    stable_id = bind_stable_id(
        fixture_digest
    )

    value = {
        "alpha": 1,
    }

    result = stable_id(
        "fixture",
        value,
        12,
    )

    if result != (
        "fixture_0123456789ab"
    ):
        raise RuntimeError(
            "focused stable_id behavior "
            "check failed"
        )

    if calls != [value]:
        raise RuntimeError(
            "stable_id did not delegate "
            "exactly once to bound digest"
        )

    try:
        bind_stable_id(
            None
        )

    except TypeError as exc:
        if str(exc) != (
            "digest_function must be callable"
        ):
            raise RuntimeError(
                "unexpected binder error "
                "contract"
            ) from exc

    else:
        raise RuntimeError(
            "non-callable digest accepted"
        )


def migrate(
    apply: bool,
) -> dict[str, Any]:
    if not primitives_path.is_file():
        raise RuntimeError(
            "shared primitives unavailable: "
            + str(primitives_path)
        )

    verify_original_family()
    focused_binding_check()

    primitive_original = (
        primitives_path.read_text(
            encoding="utf-8"
        )
    )

    (
        primitive_migrated,
        primitive_disposition,
    ) = add_shared_primitive(
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
                        "path": str(path),
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
                    "path": str(path),
                    "disposition":
                        disposition,
                }
            )

    migrated_count = sum(
        1
        for result in results
        if result[
            "disposition"
        ] == "migrated"
    )

    already_count = sum(
        1
        for result in results
        if result[
            "disposition"
        ] == "already_migrated"
    )

    return {
        "schema": schema_version,
        "authority_effect":
            authority_effect,
        "apply": apply,
        "primitive": {
            "path": str(
                primitives_path
            ),
            "disposition":
                primitive_disposition,
        },
        "target_count":
            len(target_paths),
        "migrated_count":
            migrated_count,
        "already_migrated_count":
            already_count,
        "focused_binding_check":
            "passed",
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

    report[
        "status"
    ] = "passed"

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
