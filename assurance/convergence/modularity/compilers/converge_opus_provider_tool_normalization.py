#!/usr/bin/env python3

from __future__ import annotations

import ast
import os
import stat
import sys
from pathlib import Path


schema = (
    "savant.assurance."
    "converge-opus-provider-tool-normalization.v2"
)

providers_root = Path(
    "/root/savant-runtime/ontology/obelisks/_template/segue/"
    "gates/_template/segue/innates/_template/segue/exiles/"
    "opus/runtime/providers"
)

shared_path = (
    providers_root
    / "tool_normalization.py"
)

targets = (
    providers_root / "deepseek_text.py",
    providers_root / "fireworks_text.py",
)

function_name = "_normalize_tools"

shared_import = (
    "from .tool_normalization import "
    "make_tool_normalizer"
)

binding = (
    "_normalize_tools = "
    "make_tool_normalizer(ProviderError)"
)


class ConvergenceError(RuntimeError):
    pass


def atomic_write(
    path: Path,
    text: str,
) -> None:
    mode = stat.S_IMODE(
        path.stat().st_mode
    )

    temporary = path.with_name(
        f".{path.name}.opus-convergence.tmp"
    )

    temporary.write_text(
        text,
        encoding="utf-8",
    )

    os.chmod(
        temporary,
        mode,
    )

    os.replace(
        temporary,
        path,
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
        raise ConvergenceError(
            f"cannot parse {path}: {exc}"
        ) from exc


def find_function(
    tree: ast.Module,
    path: Path,
) -> ast.FunctionDef:
    matches = [
        node
        for node in tree.body
        if (
            isinstance(
                node,
                ast.FunctionDef,
            )
            and node.name == function_name
        )
    ]

    if len(matches) != 1:
        raise ConvergenceError(
            f"{path}: expected exactly one "
            f"{function_name}, found {len(matches)}"
        )

    return matches[0]


def verify_expected_function(
    node: ast.FunctionDef,
    text: str,
    path: Path,
) -> None:
    source = ast.get_source_segment(
        text,
        node,
    )

    if source is None:
        raise ConvergenceError(
            f"{path}: cannot recover function source"
        )

    required = (
        "text inference tools must be a list",
        "text inference tool definition ",
        "text inference tool requires name",
        "text inference tool parameters ",
        '"type": "function"',
        '"parameters": parameters',
        "ProviderError",
    )

    missing = [
        fragment
        for fragment in required
        if fragment not in source
    ]

    if missing:
        raise ConvergenceError(
            f"{path}: local {function_name} "
            "does not match the established "
            "duplicate implementation"
        )


def line_offset(
    text: str,
    line_number: int,
) -> int:
    lines = text.splitlines(
        keepends=True
    )

    return sum(
        len(line)
        for line in lines[
            : line_number - 1
        ]
    )


def end_offset(
    text: str,
    line_number: int,
) -> int:
    lines = text.splitlines(
        keepends=True
    )

    return sum(
        len(line)
        for line in lines[
            :line_number
        ]
    )


def remove_function(
    text: str,
    path: Path,
) -> str:
    tree = parse_module(
        text,
        path,
    )

    node = find_function(
        tree,
        path,
    )

    verify_expected_function(
        node,
        text,
        path,
    )

    start = line_offset(
        text,
        node.lineno,
    )

    end = end_offset(
        text,
        getattr(
            node,
            "end_lineno",
            node.lineno,
        ),
    )

    while (
        end < len(text)
        and text[end] == "\n"
    ):
        end += 1

    return (
        text[:start]
        + binding
        + "\n\n"
        + text[end:]
    )


def insert_import(
    text: str,
    path: Path,
) -> str:
    if shared_import in text:
        return text

    tree = parse_module(
        text,
        path,
    )

    import_nodes = [
        node
        for node in tree.body
        if isinstance(
            node,
            (
                ast.Import,
                ast.ImportFrom,
            ),
        )
    ]

    if import_nodes:
        last = import_nodes[-1]

        offset = end_offset(
            text,
            getattr(
                last,
                "end_lineno",
                last.lineno,
            ),
        )

        prefix = text[:offset]

        if not prefix.endswith("\n"):
            prefix += "\n"

        return (
            prefix
            + shared_import
            + "\n"
            + text[offset:]
        )

    future_nodes = [
        node
        for node in tree.body
        if (
            isinstance(
                node,
                ast.ImportFrom,
            )
            and node.module == "__future__"
        )
    ]

    if future_nodes:
        last = future_nodes[-1]

        offset = end_offset(
            text,
            getattr(
                last,
                "end_lineno",
                last.lineno,
            ),
        )

        return (
            text[:offset]
            + shared_import
            + "\n"
            + text[offset:]
        )

    return (
        shared_import
        + "\n"
        + text
    )


def already_converged(
    text: str,
) -> bool:
    return (
        shared_import in text
        and binding in text
        and f"def {function_name}("
        not in text
    )


def validate(
    text: str,
    path: Path,
) -> None:
    parse_module(
        text,
        path,
    )

    if shared_import not in text:
        raise ConvergenceError(
            f"{path}: shared import missing"
        )

    if binding not in text:
        raise ConvergenceError(
            f"{path}: shared binding missing"
        )

    if f"def {function_name}(" in text:
        raise ConvergenceError(
            f"{path}: duplicate local function remains"
        )


def converge(
    path: Path,
) -> bool:
    if not path.is_file():
        raise ConvergenceError(
            f"missing provider: {path}"
        )

    original = path.read_text(
        encoding="utf-8",
    )

    if already_converged(original):
        validate(
            original,
            path,
        )
        return False

    modified = remove_function(
        original,
        path,
    )

    modified = insert_import(
        modified,
        path,
    )

    validate(
        modified,
        path,
    )

    atomic_write(
        path,
        modified,
    )

    return True


def main() -> int:
    if not shared_path.is_file():
        raise ConvergenceError(
            f"shared primitive missing: {shared_path}"
        )

    changed = {
        str(path): converge(path)
        for path in targets
    }

    print(
        {
            "schema": schema,
            "primitive":
                "tool_normalization.normalize_tools",
            "owner": str(providers_root),
            "instances": 2,
            "changed": changed,
            "authority_effect": "none",
        }
    )

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ConvergenceError as exc:
        print(
            f"{schema}: {exc}",
            file=sys.stderr,
        )
        raise SystemExit(1)
