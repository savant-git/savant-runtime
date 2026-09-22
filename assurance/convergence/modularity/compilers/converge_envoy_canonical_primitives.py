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
    "converge-envoy-canonical-primitives.v1"
)

runtime_root = Path(
    "/root/savant-runtime/ontology/obelisks/_template/segue/"
    "gates/_template/segue/innates/_template/segue/exiles/"
    "envoy/runtime"
)

shared_path = (
    runtime_root
    / "canonical_primitives.py"
)

targets = (
    runtime_root / "moral_self.py",
    runtime_root / "psychologist.py",
)

shared_import = (
    "from .canonical_primitives import "
    "canonical as _canonical, digest as _digest"
)

expected_digests = {
    "_canonical":
        "89a23416fb59161f09431e08664dcd97261f6afccf59bfc5c688854c6b1325d1",
    "_digest":
        "d6856a374161e017da1aefe060318b9037eac75bbf37d763973214dfefdb8125",
}

shared_names = {
    "canonical":
        expected_digests["_canonical"],
    "digest":
        expected_digests["_digest"],
}


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
            f"shared primitive module missing: {shared_path}"
        )

    text = shared_path.read_text(
        encoding="utf-8"
    )

    tree = parse_module(
        text,
        shared_path,
    )

    for name, expected in shared_names.items():
        node = find_function(
            tree,
            name,
        )

        if node is None:
            raise ConvergenceError(
                f"shared primitive missing: {name}"
            )

        actual = normalized_digest(
            node
        )

        if actual != expected:
            raise ConvergenceError(
                f"shared primitive {name} does not "
                "match selected implementation"
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


def remove_function(
    text: str,
    path: Path,
    name: str,
) -> str:
    tree = parse_module(
        text,
        path,
    )

    node = find_function(
        tree,
        name,
    )

    if node is None:
        return text

    actual = normalized_digest(
        node
    )

    expected = expected_digests[
        name
    ]

    if actual != expected:
        raise ConvergenceError(
            f"{path}: {name} substance changed; "
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
            f"{path}: shared canonical import missing"
        )

    for name in expected_digests:
        if find_function(
            tree,
            name,
        ) is not None:
            raise ConvergenceError(
                f"{path}: duplicated local {name} remains"
            )


def atomic_write(
    path: Path,
    text: str,
) -> None:
    mode = stat.S_IMODE(
        path.stat().st_mode
    )

    temporary = path.with_name(
        f".{path.name}.canonical-primitives.tmp"
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
        encoding="utf-8"
    )

    original_tree = parse_module(
        original,
        path,
    )

    existing = {
        name: (
            find_function(
                original_tree,
                name,
            )
            is not None
        )
        for name in expected_digests
    }

    if (
        not any(existing.values())
        and shared_import in original
    ):
        validate(
            original,
            path,
        )

        return False

    modified = original

    for name in expected_digests:
        modified = remove_function(
            modified,
            path,
            name,
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
            "primitive_module":
                "canonical_primitives",
            "primitives": [
                "canonical",
                "digest",
            ],
            "consumer_symbols": [
                "_canonical",
                "_digest",
            ],
            "instances":
                len(targets),
            "changed":
                changed,
            "authority_effect":
                "none",
        }
    )

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(
            main()
        )
    except ConvergenceError as exc:
        print(
            f"{schema}: {exc}",
            file=sys.stderr,
        )
        raise SystemExit(1)
