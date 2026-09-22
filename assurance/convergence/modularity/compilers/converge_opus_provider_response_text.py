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
    "converge-opus-provider-response-text.v2"
)

providers_root = Path(
    "/root/savant-runtime/ontology/obelisks/_template/segue/"
    "gates/_template/segue/innates/_template/segue/exiles/"
    "opus/runtime/providers"
)

shared_path = (
    providers_root
    / "response_text.py"
)

targets = {
    providers_root / "groq_text.py": {
        "local_name": "_response_text",
        "import_line": (
            "from .response_text import "
            "response_text as _response_text"
        ),
    },
    providers_root / "openai_text.py": {
        "local_name": "response_text",
        "import_line": (
            "from .response_text import response_text"
        ),
    },
}

expected_digest = (
    "fa43ec21bc6d5a5e751bcc2d4e1fc7a67dd5a037ec29d6105ea57d0060ada44c"
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
        f".{path.name}.response-text.tmp"
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


def normalized_digest(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
) -> str:
    normalized = ast.parse(
        ast.unparse(node)
    ).body[0]

    if not isinstance(
        normalized,
        (
            ast.FunctionDef,
            ast.AsyncFunctionDef,
        ),
    ):
        raise ConvergenceError(
            "function normalization failed"
        )

    normalized.name = "__primitive__"

    substance = ast.dump(
        normalized,
        annotate_fields=True,
        include_attributes=False,
    )

    return hashlib.sha256(
        substance.encode("utf-8")
    ).hexdigest()


def find_local_function(
    tree: ast.Module,
    *,
    local_name: str,
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
            and node.name == local_name
        )
    ]

    if len(matches) > 1:
        raise ConvergenceError(
            f"multiple local functions named {local_name}"
        )

    if not matches:
        return None

    return matches[0]


def verify_shared_primitive() -> None:
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

    node = find_local_function(
        tree,
        local_name="response_text",
    )

    if node is None:
        raise ConvergenceError(
            "shared response_text primitive missing"
        )

    digest = normalized_digest(node)

    if digest != expected_digest:
        raise ConvergenceError(
            "shared response_text primitive no longer "
            "matches the selected convergence substance"
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

    node = find_local_function(
        tree,
        local_name=local_name,
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


def validate_target(
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
            f"{path}: shared response_text import missing"
        )

    node = find_local_function(
        tree,
        local_name=local_name,
    )

    if node is not None:
        raise ConvergenceError(
            f"{path}: local duplicated {local_name} remains"
        )


def converge_target(
    path: Path,
    *,
    local_name: str,
    import_line: str,
) -> bool:
    if not path.is_file():
        raise ConvergenceError(
            f"provider missing: {path}"
        )

    original = path.read_text(
        encoding="utf-8",
    )

    tree = parse_module(
        original,
        path,
    )

    existing = find_local_function(
        tree,
        local_name=local_name,
    )

    if (
        existing is None
        and import_line in original
    ):
        validate_target(
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

    validate_target(
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
    verify_shared_primitive()

    changed: dict[str, bool] = {}

    for path, contract in targets.items():
        changed[str(path)] = converge_target(
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
            "owner": str(providers_root),
            "primitive":
                "response_text.response_text",
            "instances": len(targets),
            "changed": changed,
            "partial_prior_convergence_supported":
                True,
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
