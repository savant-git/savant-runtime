#!/usr/bin/env python3

from __future__ import annotations

import ast
from pathlib import Path


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

targets = (
    "negative_knowledge.py",
    "production_pipeline.py",
    "production_stable.py",
    "realization_adapter.py",
    "recursive_pipeline.py",
)

verified_body = """def require_object(
    value: Any,
    name: str,
) -> dict[str, Any]:
    if not isinstance(
        value,
        dict,
    ):
        raise TypeError(
            f"{name} must be an object"
        )

    return value"""


def function_span(
    text: str,
) -> tuple[int, int]:
    tree = ast.parse(
        text
    )

    matches = [
        node
        for node in tree.body
        if isinstance(
            node,
            (
                ast.FunctionDef,
                ast.AsyncFunctionDef,
            ),
        )
        and node.name
        == "require_object"
    ]

    if len(matches) != 1:
        raise RuntimeError(
            "expected exactly one "
            "top-level require_object"
        )

    node = matches[0]

    lines = text.splitlines(
        keepends=True
    )

    start = sum(
        len(line)
        for line in lines[
            : node.lineno - 1
        ]
    )

    end = sum(
        len(line)
        for line in lines[
            : node.end_lineno
        ]
    )

    while (
        end < len(text)
        and text[end] == "\n"
    ):
        end += 1

    return start, end


def insertion_point(
    text: str,
) -> int:
    marker = (
        'authority_effect = "none"'
    )

    index = text.find(
        marker
    )

    if index < 0:
        raise RuntimeError(
            "authority_effect marker "
            "not found"
        )

    end = text.find(
        "\n",
        index,
    )

    if end < 0:
        raise RuntimeError(
            "authority_effect line "
            "is unterminated"
        )

    return end + 1


def load_module_available(
    text: str,
) -> bool:
    tree = ast.parse(
        text
    )

    return any(
        isinstance(
            node,
            ast.FunctionDef,
        )
        and node.name == "load_module"
        for node in tree.body
    )


def loader_block() -> str:
    return """

primitives_path = (
    source_root
    / "primitives.py"
)

primitives = load_module(
    "savant_underscore_vessel_primitives",
    primitives_path,
)

require_object = (
    primitives.require_object
)
"""


def migrate(
    path: Path,
) -> None:
    text = path.read_text(
        encoding="utf-8"
    )

    if (
        "primitives.require_object"
        in text
    ):
        print(
            f"already migrated: {path}"
        )
        return

    if not load_module_available(
        text
    ):
        raise RuntimeError(
            "load_module unavailable: "
            f"{path}"
        )

    start, end = (
        function_span(
            text
        )
    )

    current = text[
        start:end
    ].strip()

    if current != (
        verified_body.strip()
    ):
        raise RuntimeError(
            "verified require_object "
            "body mismatch: "
            f"{path}"
        )

    reduced = (
        text[:start]
        + text[end:]
    )

    point = insertion_point(
        reduced
    )

    migrated = (
        reduced[:point]
        + loader_block()
        + reduced[point:]
    )

    ast.parse(
        migrated
    )

    path.write_text(
        migrated,
        encoding="utf-8",
    )

    print(
        f"migrated: {path}"
    )


def main() -> int:
    for name in targets:
        path = (
            source_root
            / name
        )

        if not path.is_file():
            raise RuntimeError(
                "target unavailable: "
                f"{path}"
            )

        migrate(
            path
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
