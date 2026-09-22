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
    "converge-envoy-trait-primitives.v1"
)

runtime_root = Path(
    "/root/savant-runtime/ontology/obelisks/_template/segue/"
    "gates/_template/segue/innates/_template/segue/exiles/"
    "envoy/runtime"
)

shared_path = (
    runtime_root
    / "trait_primitives.py"
)

targets = (
    runtime_root / "trait_adjudication.py",
    runtime_root / "trait_evaluation.py",
    runtime_root / "trait_experiment.py",
)

shared_import = (
    "from .trait_primitives import "
    "canonical_json, digest, normalize_term"
)

expected_digests = {
    "canonical_json":
        "4a374e228e6bc0e2bd5fedc5fe82a40512d0f7bcf70f93a4a6e3b39c08f91daa",
    "digest":
        "c18a70725c9f3ee28cc2263e2cac8eea7deb3bc686a8f3c25d8bbc7314b4578d",
    "normalize_term":
        "b8161f4ed4b397031889782580d6c5e96630e6eefeec168ed67e250f392a98f6",
}

primitive_names = (
    "canonical_json",
    "digest",
    "normalize_term",
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
        encoding="utf-8",
    )

    tree = parse_module(
        text,
        shared_path,
    )

    for name in primitive_names:
        node = find_function(
            tree,
            name,
        )

        if node is None:
            raise ConvergenceError(
                f"shared primitive missing: {name}"
            )

        digest_value = normalized_digest(
            node
        )

        if (
            digest_value
            != expected_digests[name]
        ):
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

    digest_value = normalized_digest(
        node
    )

    if (
        digest_value
        != expected_digests[name]
    ):
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
            f"{path}: shared trait primitive import missing"
        )

    for name in primitive_names:
        if find_function(
            tree,
            name,
        ) is not None:
            raise ConvergenceError(
                f"{path}: duplicated local {name} remains"
            )

    if find_function(
        tree,
        "main",
    ) is None:
        raise ConvergenceError(
            f"{path}: local main entrypoint was lost"
        )


def atomic_write(
    path: Path,
    text: str,
) -> None:
    mode = stat.S_IMODE(
        path.stat().st_mode
    )

    temporary = path.with_name(
        f".{path.name}.trait-primitives.tmp"
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

    original_tree = parse_module(
        original,
        path,
    )

    existing_count = sum(
        find_function(
            original_tree,
            name,
        )
        is not None
        for name in primitive_names
    )

    if (
        existing_count == 0
        and shared_import in original
    ):
        validate(
            original,
            path,
        )

        return False

    modified = original

    for name in primitive_names:
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
                "trait_primitives",
            "primitives": list(
                primitive_names
            ),
            "instances": len(targets),
            "main_entrypoint_preserved":
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
