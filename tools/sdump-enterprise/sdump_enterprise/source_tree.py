
from __future__ import annotations

import gzip
from pathlib import Path
from typing import Any, Iterable


def render_source_tree(
    candidates: Iterable[Any],
    target_name: str,
) -> str:
    paths = sorted(
        (
            Path(candidate.relative_path).parts
            for candidate in candidates
        ),
        key=lambda parts: (
            tuple(part.casefold() for part in parts),
            parts,
        ),
    )

    root: dict[str, dict] = {}

    for parts in paths:
        node = root

        for part in parts:
            node = node.setdefault(part, {})

    lines = [
        "=== sdump source tree ===",
        f"{target_name}/",
    ]

    def visit(
        node: dict[str, dict],
        prefix: str,
    ) -> None:
        entries = sorted(
            node.items(),
            key=lambda item: (
                item[0].casefold(),
                item[0],
            ),
        )

        for index, (name, children) in enumerate(entries):
            last = index == len(entries) - 1
            connector = "└── " if last else "├── "

            lines.append(
                prefix
                + connector
                + name
                + ("/" if children else "")
            )

            if children:
                visit(
                    children,
                    prefix + ("    " if last else "│   "),
                )

    visit(root, "")

    lines.extend([
        "=== /sdump source tree ===",
        "",
    ])

    return "\n".join(lines) + "\n"


def append_source_tree(
    artifact: Path,
    candidates: Iterable[Any],
    target_name: str,
    compression_level: int = 6,
) -> None:
    tree = render_source_tree(
        candidates,
        target_name,
    )

    with gzip.open(
        artifact,
        "at",
        encoding="utf-8",
        newline="\n",
        compresslevel=compression_level,
    ) as handle:
        handle.write(tree)
