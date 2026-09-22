#!/usr/bin/env python3

from __future__ import annotations

import ast
import hashlib
import os
import stat
import sys
from pathlib import Path


schema = (
    "savant.assurance."
    "converge-opus-runtime-normalized-strings.v1"
)

runtime_root = Path(
    "/root/savant-runtime/ontology/obelisks/_template/segue/"
    "gates/_template/segue/innates/_template/segue/exiles/"
    "opus/runtime"
)

shared_path = (
    runtime_root
    / "normalization.py"
)

targets = (
    runtime_root / "model_projection.py",
    runtime_root / "resilient_text.py",
    runtime_root / "router.py",
)

local_name = "_normalized"

shared_import = (
    "from .normalization import "
    "normalized_strings as _normalized"
)

expected_digest = (
    "de732205b11e8cc9dc68211bbcc0add31f24aca74ccfa83fd148f8b4df329b45"
)


class ConvergenceError(RuntimeError):
    pass


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


def normalized_digest(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
) -> str:
    rebuilt = ast.parse(
        ast.unparse(node)
    ).body[0]

    if not isinstance(
        rebuilt,
        (
            ast.FunctionDef,
            ast.AsyncFunctionDef,
        ),
    ):
        raise ConvergenceError(
            "function normalization failed"
        )

    rebuilt.name = "__primitive__"

    substance = ast.dump(
        rebuilt,
        annotate_fields=True,
        include_attributes=False,
    )

    return hashlib.sha256(
        substance.encode("utf-8")
    ).hexdigest()


def find_function(
    tree: ast.Module,
    *,
    name: str,
) -> (
    ast.FunctionDef
    | ast.AsyncFunctionDef
    | None
):
    matches = [
        node
        for node in tree.body
        if (
            isinstance(
                node,
                (
                    ast.FunctionDef,
                    ast.AsyncFunctionDef,
                ),
            )
            and node.name == name
        )
    ]

    if len(matches) > 1:
        raise ConvergenceError(
            f"multiple top-level functions named {name}"
        )

    if not matches:
        return None

    return matches[0]


def verify_shared() -> None:
    if not shared_path.is_file():
        raise ConvergenceError(
            f"shared primitive missing: {shared_path}"
        )

    text = shared_path.read_text(
        encoding="utf-8",
    )

    tree = parse_module(
        text,
        shared_path,
    )

    node = find_function(
        tree,
        name="normalized_strings",
    )

    if node is None:
        raise ConvergenceError(
            "shared normalized_strings primitive missing"
        )

    digest = normalized_digest(node)

    if digest != expected_digest:
        raise ConvergenceError(
            "shared normalized_strings substance "
            "does not match the selected implementation"
        )


def line_start_offset(
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


def line_end_offset(
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


def remove_local_function(
    text: str,
    path: Path,
) -> str:
    tree = parse_module(
        text,
        path,
    )

    node = find_function(
        tree,
        name=local_name,
    )

    if node is None:
        return text

    digest = normalized_digest(node)

    if digest != expected_digest:
        raise ConvergenceError(
            f"{path}: {local_name} substance changed; "
            "refusing convergence"
        )

    start = line_start_offset(
        text,
        node.lineno,
    )

    end = line_end_offset(
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

    if not import_nodes:
        return (
            shared_import
            + "\n"
            + text
        )

    last = import_nodes[-1]

    offset = line_end_offset(
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


def validate(
    text: str,
    path: Path,
) -> None:
    tree = parse_module(
        text,
        path,
    )

    if shared_import not in text:
        raise ConvergenceError(
            f"{path}: shared normalization import missing"
        )

    if find_function(
        tree,
        name=local_name,
    ) is not None:
        raise ConvergenceError(
            f"{path}: duplicated local "
            f"{local_name} remains"
        )


def atomic_write(
    path: Path,
    text: str,
) -> None:
    mode = stat.S_IMODE(
        path.stat().st_mode
    )

    temporary = path.with_name(
        f".{path.name}.normalized-strings.tmp"
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


def converge(
    path: Path,
) -> bool:
    if not path.is_file():
        raise ConvergenceError(
            f"runtime module missing: {path}"
        )

    original = path.read_text(
        encoding="utf-8",
    )

    tree = parse_module(
        original,
        path,
    )

    existing = find_function(
        tree,
        name=local_name,
    )

    if (
        existing is None
        and shared_import in original
    ):
        validate(
            original,
            path,
        )

        return False

    modified = remove_local_function(
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

    if modified == original:
        return False

    atomic_write(
        path,
        modified,
    )

    return True


def main() -> int:
    verify_shared()

    changed = {
        str(path): converge(path)
        for path in targets
    }

    print(
        {
            "schema": schema,
            "owner": str(runtime_root),
            "primitive":
                "normalization.normalized_strings",
            "instances": len(targets),
            "local_symbol_preserved":
                "_normalized",
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
