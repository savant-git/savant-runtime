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
    "converge-palaver-runtime-json-bytes.v1"
)

runtime_root = Path(
    "/root/savant-runtime/ontology/obelisks/_template/segue/"
    "gates/_template/segue/innates/_template/segue/exiles/"
    "palaver/runtime"
)

shared_path = (
    runtime_root
    / "json_encoding.py"
)

targets = {
    runtime_root / "attachment_api.py": {
        "local_name": "encode_json",
        "import_line": (
            "from .json_encoding import json_bytes as encode_json"
        ),
    },
    runtime_root / "compat_gateway.py": {
        "local_name": "json_bytes",
        "import_line": (
            "from .json_encoding import json_bytes"
        ),
    },
    runtime_root / "plan_b_resilient.py": {
        "local_name": "_json_bytes",
        "import_line": (
            "from .json_encoding import json_bytes as _json_bytes"
        ),
    },
}

expected_digest = (
    "8c86225e7d3e9c7ca78e9b3d508b96f"
    "dad7d7fc0eb22edad9354f1bde741232b"
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
        name="json_bytes",
    )

    if node is None:
        raise ConvergenceError(
            "shared json_bytes primitive missing"
        )

    digest = normalized_digest(node)

    if digest != expected_digest:
        raise ConvergenceError(
            "shared json_bytes substance "
            "does not match selected implementation"
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
    local_name: str,
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
    import_line: str,
) -> str:
    if import_line in text:
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
            import_line
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
        + import_line
        + "\n"
        + text[offset:]
    )


def validate(
    text: str,
    path: Path,
    *,
    local_name: str,
    import_line: str,
) -> None:
    tree = parse_module(
        text,
        path,
    )

    if import_line not in text:
        raise ConvergenceError(
            f"{path}: shared json_bytes import missing"
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
        f".{path.name}.json-bytes.tmp"
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
    *,
    local_name: str,
    import_line: str,
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
        and import_line in original
    ):
        validate(
            original,
            path,
            local_name=local_name,
            import_line=import_line,
        )

        return False

    modified = remove_local_function(
        original,
        path,
        local_name,
    )

    modified = insert_import(
        modified,
        path,
        import_line,
    )

    validate(
        modified,
        path,
        local_name=local_name,
        import_line=import_line,
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

    changed: dict[str, bool] = {}

    for path, contract in targets.items():
        changed[str(path)] = converge(
            path,
            local_name=contract[
                "local_name"
            ],
            import_line=contract[
                "import_line"
            ],
        )

    print(
        {
            "schema": schema,
            "owner": str(runtime_root),
            "primitive":
                "json_encoding.json_bytes",
            "instances": len(targets),
            "symbols_preserved": {
                "attachment_api":
                    "encode_json",
                "compat_gateway":
                    "json_bytes",
                "plan_b_resilient":
                    "_json_bytes",
            },
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
