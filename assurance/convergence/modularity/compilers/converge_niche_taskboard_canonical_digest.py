#!/usr/bin/env python3

from __future__ import annotations

import ast
import os
import stat
import sys
from pathlib import Path


schema = (
    "savant.assurance."
    "converge-niche-taskboard-canonical-digest.v1"
)

taskboard_root = Path(
    "/root/savant-runtime/ontology/obelisks/_template/segue/"
    "gates/_template/segue/innates/_template/segue/exiles/"
    "niche/apps/taskboard"
)

shared_path = (
    taskboard_root
    / "projection_primitives.py"
)

targets = (
    taskboard_root
    / "masterplan_index_projection.py",
    taskboard_root
    / "masterplan_lineage_projection.py",
)

function_name = "canonical_digest"

shared_import = (
    "from .projection_primitives import canonical_digest"
)

required_fragments = (
    "json.dumps(",
    "ensure_ascii=False",
    "sort_keys=True",
    'separators=(",", ":")',
    '.encode(',
    '"utf-8"',
    "hashlib.sha256(",
    ".hexdigest()",
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
        f".{path.name}.canonical-digest.tmp"
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


def verify_function(
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
            f"{path}: cannot recover "
            f"{function_name} source"
        )

    normalized = source.replace(
        " ",
        "",
    ).replace(
        "\n",
        "",
    )

    normalized_required = [
        fragment.replace(
            " ",
            "",
        ).replace(
            "\n",
            "",
        )
        for fragment in required_fragments
    ]

    missing = [
        fragment
        for fragment in normalized_required
        if fragment not in normalized
    ]

    if missing:
        raise ConvergenceError(
            f"{path}: {function_name} "
            "does not match the established "
            "taskboard canonical digest primitive"
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

    verify_function(
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
        + text[end:]
    )


def import_insert_offset(
    text: str,
    tree: ast.Module,
) -> int:
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
        node = import_nodes[-1]

        return end_offset(
            text,
            getattr(
                node,
                "end_lineno",
                node.lineno,
            ),
        )

    return 0


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

    offset = import_insert_offset(
        text,
        tree,
    )

    if offset == 0:
        return (
            shared_import
            + "\n"
            + text
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


def already_converged(
    text: str,
) -> bool:
    return (
        shared_import in text
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
            f"{path}: shared digest import missing"
        )

    if f"def {function_name}(" in text:
        raise ConvergenceError(
            f"{path}: duplicated local "
            f"{function_name} remains"
        )


def converge(
    path: Path,
) -> bool:
    if not path.is_file():
        raise ConvergenceError(
            f"missing projection: {path}"
        )

    original = path.read_text(
        encoding="utf-8",
    )

    if already_converged(
        original
    ):
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
            "owner": str(taskboard_root),
            "primitive":
                "projection_primitives.canonical_digest",
            "instances": len(targets),
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
