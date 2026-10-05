#!/usr/bin/env python3

from __future__ import annotations

import ast
import os
import stat
import sys
from pathlib import Path


schema = (
    "savant.assurance."
    "converge-opus-provider-response-text.v1"
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


def find_function(
    tree: ast.Module,
    *,
    local_name: str,
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
            and node.name == local_name
        )
    ]

    if len(matches) != 1:
        raise ConvergenceError(
            f"{path}: expected exactly one "
            f"{local_name}, found {len(matches)}"
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
            "response-text function source"
        )

    normalized = "".join(
        source.split()
    )

    required = tuple(
        "".join(fragment.split())
        for fragment in (
            'data.get("output_text")',
            "direct.strip()",
            "texts:list[str]=[]",
            'data.get("output",[])',
            'item.get("content",[])',
            'content.get("text")',
            "texts.append(text)",
            '"\\n".join(texts).strip()',
        )
    )

    missing = [
        fragment
        for fragment in required
        if fragment not in normalized
    ]

    if missing:
        raise ConvergenceError(
            f"{path}: selected function no longer "
            "matches the established shared "
            "response-text primitive"
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
    local_name: str,
) -> str:
    tree = parse_module(
        text,
        path,
    )

    node = find_function(
        tree,
        local_name=local_name,
        path=path,
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
    parse_module(
        text,
        path,
    )

    if import_line not in text:
        raise ConvergenceError(
            f"{path}: shared response-text "
            "import missing"
        )

    if f"def {local_name}(" in text:
        raise ConvergenceError(
            f"{path}: duplicated local "
            f"{local_name} remains"
        )


def converge(
    path: Path,
    *,
    local_name: str,
    import_line: str,
) -> bool:
    if not path.is_file():
        raise ConvergenceError(
            f"missing provider: {path}"
        )

    original = path.read_text(
        encoding="utf-8",
    )

    if (
        import_line in original
        and f"def {local_name}("
        not in original
    ):
        validate(
            original,
            path,
            local_name=local_name,
            import_line=import_line,
        )

        return False

    modified = remove_function(
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
            "owner": str(providers_root),
            "primitive":
                "response_text.response_text",
            "instances": len(targets),
            "public_openai_symbol_preserved":
                True,
            "private_groq_symbol_preserved":
                True,
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
