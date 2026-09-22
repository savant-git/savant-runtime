#!/usr/bin/env python3

from __future__ import annotations

import ast
import hashlib
import json
import sys
from pathlib import Path
from typing import Any


schema = "savant.assurance.selected-owner-family-inspection.v1"

paths = (
    Path(
        "/root/savant-runtime/ontology/obelisks/_template/segue/"
        "gates/_template/segue/innates/_template/segue/exiles/"
        "opus/runtime/providers/deepseek_text.py"
    ),
    Path(
        "/root/savant-runtime/ontology/obelisks/_template/segue/"
        "gates/_template/segue/innates/_template/segue/exiles/"
        "opus/runtime/providers/fireworks_text.py"
    ),
)


class InspectionError(RuntimeError):
    pass


def digest(value: str) -> str:
    return hashlib.sha256(
        value.encode("utf-8")
    ).hexdigest()


def normalized_function(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
) -> str:
    clone = ast.parse(
        ast.unparse(node)
    ).body[0]

    if not isinstance(
        clone,
        (ast.FunctionDef, ast.AsyncFunctionDef),
    ):
        raise InspectionError(
            "function normalization failed"
        )

    clone.name = "__primitive__"

    return ast.dump(
        clone,
        annotate_fields=True,
        include_attributes=False,
    )


def functions_for(
    path: Path,
) -> list[dict[str, Any]]:
    if not path.is_file():
        raise InspectionError(
            f"missing provider: {path}"
        )

    text = path.read_text(
        encoding="utf-8"
    )

    try:
        tree = ast.parse(
            text,
            filename=str(path),
        )
    except SyntaxError as exc:
        raise InspectionError(
            f"cannot parse {path}: {exc}"
        ) from exc

    functions: list[dict[str, Any]] = []

    for node in ast.walk(tree):
        if not isinstance(
            node,
            (ast.FunctionDef, ast.AsyncFunctionDef),
        ):
            continue

        normalized = normalized_function(node)

        functions.append(
            {
                "name": node.name,
                "line": node.lineno,
                "end_line": getattr(
                    node,
                    "end_lineno",
                    node.lineno,
                ),
                "async": isinstance(
                    node,
                    ast.AsyncFunctionDef,
                ),
                "normalized_digest":
                    digest(normalized),
                "source": ast.get_source_segment(
                    text,
                    node,
                ),
            }
        )

    return functions


def inspect() -> dict[str, Any]:
    providers = {
        str(path): functions_for(path)
        for path in paths
    }

    left = providers[str(paths[0])]
    right = providers[str(paths[1])]

    right_by_digest: dict[
        str,
        list[dict[str, Any]],
    ] = {}

    for function in right:
        right_by_digest.setdefault(
            function["normalized_digest"],
            [],
        ).append(function)

    matches: list[dict[str, Any]] = []

    for function in left:
        for candidate in right_by_digest.get(
            function["normalized_digest"],
            [],
        ):
            matches.append(
                {
                    "digest":
                        function[
                            "normalized_digest"
                        ],
                    "left": {
                        "name":
                            function["name"],
                        "line":
                            function["line"],
                        "end_line":
                            function[
                                "end_line"
                            ],
                        "source":
                            function[
                                "source"
                            ],
                    },
                    "right": {
                        "name":
                            candidate["name"],
                        "line":
                            candidate["line"],
                        "end_line":
                            candidate[
                                "end_line"
                            ],
                        "source":
                            candidate[
                                "source"
                            ],
                    },
                }
            )

    return {
        "schema": schema,
        "authority_effect": "none",
        "mutation_authority": False,
        "provider_owner":
            "/root/savant-runtime/ontology/obelisks/"
            "_template/segue/gates/_template/segue/"
            "innates/_template/segue/exiles/opus/"
            "runtime/providers",
        "providers": [
            {
                "path": path,
                "function_count":
                    len(functions),
            }
            for path, functions
            in providers.items()
        ],
        "identical_function_count":
            len(matches),
        "identical_functions":
            matches,
    }


def main() -> int:
    print(
        json.dumps(
            inspect(),
            indent=2,
            sort_keys=True,
        )
    )

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except InspectionError as exc:
        print(
            f"{schema}: {exc}",
            file=sys.stderr,
        )
        raise SystemExit(1)
