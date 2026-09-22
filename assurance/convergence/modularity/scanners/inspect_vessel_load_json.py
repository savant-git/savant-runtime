#!/usr/bin/env python3

from __future__ import annotations

import ast
from pathlib import Path


source_root = Path(
    "/root/savant-runtime/ontology/obelisks/_template/segue/gates/"
    "_template/segue/innates/_template/segue/exiles/underscore/"
    "rubric/vessel/source"
)

targets = (
    "negative_knowledge.py",
    "production_pipeline.py",
    "production_stable.py",
    "recursive_pipeline.py",
    "underscore_pipeline.py",
)


def source_segment(
    text: str,
    node: ast.AST,
) -> str:
    segment = ast.get_source_segment(
        text,
        node,
    )

    if segment is None:
        raise RuntimeError(
            "unable to recover source segment"
        )

    return segment


def inspect_target(
    path: Path,
) -> None:
    text = path.read_text(
        encoding="utf-8",
    )

    module = ast.parse(
        text,
        filename=str(path),
    )

    matches = [
        node
        for node in module.body
        if (
            isinstance(
                node,
                ast.FunctionDef,
            )
            and node.name == "load_json"
        )
    ]

    if len(matches) != 1:
        raise RuntimeError(
            f"{path}: expected exactly one "
            f"top-level load_json, found "
            f"{len(matches)}"
        )

    function = matches[0]

    parameters = {
        argument.arg
        for argument in (
            list(
                function.args.posonlyargs
            )
            + list(
                function.args.args
            )
            + list(
                function.args.kwonlyargs
            )
        )
    }

    if function.args.vararg:
        parameters.add(
            function.args.vararg.arg
        )

    if function.args.kwarg:
        parameters.add(
            function.args.kwarg.arg
        )

    assigned = set()

    for node in ast.walk(
        function
    ):
        if (
            isinstance(
                node,
                ast.Name,
            )
            and isinstance(
                node.ctx,
                (
                    ast.Store,
                    ast.Del,
                ),
            )
        ):
            assigned.add(
                node.id
            )

    loaded = {
        node.id
        for node in ast.walk(
            function
        )
        if (
            isinstance(
                node,
                ast.Name,
            )
            and isinstance(
                node.ctx,
                ast.Load,
            )
        )
    }

    globals_used = sorted(
        loaded
        - parameters
        - assigned
    )

    print(
        "=" * 80
    )
    print(
        path
    )
    print(
        "globals_used:",
        ", ".join(
            globals_used
        )
        or "(none)",
    )
    print(
        "-" * 80
    )
    print(
        source_segment(
            text,
            function,
        )
    )
    print()


def main() -> int:
    for name in targets:
        path = source_root / name

        if not path.is_file():
            raise RuntimeError(
                "target unavailable: "
                + str(path)
            )

        inspect_target(
            path
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
