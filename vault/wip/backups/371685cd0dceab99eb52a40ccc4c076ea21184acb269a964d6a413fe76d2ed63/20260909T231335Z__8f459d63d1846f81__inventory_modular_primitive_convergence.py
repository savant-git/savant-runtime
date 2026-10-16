#!/usr/bin/env python3

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import math
import os
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable


schema = "savant.assurance.modular-primitive-convergence.v1"
authority_effect = "none"

default_root = Path("/root/savant-runtime")

excluded_directory_names = frozenset(
    {
        ".git",
        ".hypothesis",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        ".venv",
        "__pycache__",
        "backups",
        "dist",
        "node_modules",
        "venv",
        "venvs",
    }
)

excluded_path_parts = frozenset(
    {
        "projections",
        "snapshots",
    }
)

minimum_statement_count = 1
minimum_ast_size = 8


@dataclass(frozen=True)
class function_record:
    path: str
    name: str
    qualified_name: str
    line: int
    end_line: int
    statement_count: int
    ast_size: int
    semantic_digest: str


def canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def digest(value: Any) -> str:
    return hashlib.sha256(
        canonical_json(value).encode("utf-8")
    ).hexdigest()


def normalized_constant(value: Any) -> Any:
    if value is Ellipsis:
        return {
            "$python_constant": "ellipsis",
        }

    if value is None:
        return None

    if isinstance(
        value,
        (
            bool,
            int,
            str,
        ),
    ):
        return value

    if isinstance(value, float):
        if math.isnan(value):
            return {
                "$python_constant": "nan",
            }

        if math.isinf(value):
            return {
                "$python_constant": (
                    "positive_infinity"
                    if value > 0
                    else "negative_infinity"
                ),
            }

        return value

    if isinstance(value, bytes):
        return {
            "$python_constant": "bytes",
            "hex": value.hex(),
        }

    if isinstance(value, complex):
        return {
            "$python_constant": "complex",
            "real": normalized_constant(
                value.real
            ),
            "imag": normalized_constant(
                value.imag
            ),
        }

    if isinstance(value, tuple):
        return {
            "$python_constant": "tuple",
            "items": [
                normalized_constant(item)
                for item in value
            ],
        }

    if isinstance(value, frozenset):
        normalized_items = [
            normalized_constant(item)
            for item in value
        ]

        normalized_items.sort(
            key=canonical_json
        )

        return {
            "$python_constant": "frozenset",
            "items": normalized_items,
        }

    return {
        "$python_constant": (
            f"{type(value).__module__}."
            f"{type(value).__qualname__}"
        ),
        "representation": repr(value),
    }


def normalized_node(node: Any) -> Any:
    if isinstance(
        node,
        (
            ast.FunctionDef,
            ast.AsyncFunctionDef,
        ),
    ):
        return {
            "type": type(node).__name__,
            "args": normalized_node(
                node.args
            ),
            "body": [
                normalized_node(item)
                for item in node.body
            ],
            "decorator_list": [
                normalized_node(item)
                for item in node.decorator_list
            ],
            "returns": normalized_node(
                node.returns
            ),
            "type_comment": (
                node.type_comment
            ),
        }

    if isinstance(node, ast.arg):
        return {
            "type": "arg",
            "annotation": normalized_node(
                node.annotation
            ),
            "type_comment": (
                node.type_comment
            ),
        }

    if isinstance(node, ast.Name):
        return {
            "type": "Name",
            "id": node.id,
            "ctx": type(
                node.ctx
            ).__name__,
        }

    if isinstance(node, ast.Constant):
        return {
            "type": "Constant",
            "value": normalized_constant(
                node.value
            ),
        }

    if isinstance(node, ast.AST):
        result: dict[str, Any] = {
            "type": type(node).__name__,
        }

        for field in node._fields:
            if field in {
                "name",
                "lineno",
                "col_offset",
                "end_lineno",
                "end_col_offset",
            }:
                continue

            result[field] = (
                normalized_node(
                    getattr(
                        node,
                        field,
                        None,
                    )
                )
            )

        return result

    if isinstance(node, list):
        return [
            normalized_node(item)
            for item in node
        ]

    if isinstance(node, tuple):
        return [
            normalized_node(item)
            for item in node
        ]

    return normalized_constant(node)


def semantic_function_digest(
    node: (
        ast.FunctionDef
        | ast.AsyncFunctionDef
    ),
) -> str:
    return digest(
        normalized_node(node)
    )


def ast_size(node: ast.AST) -> int:
    return sum(
        1
        for _ in ast.walk(node)
    )


def should_skip(
    root: Path,
    path: Path,
) -> bool:
    try:
        relative = (
            path.relative_to(root)
        )
    except ValueError:
        return True

    parts = relative.parts

    if any(
        part
        in excluded_directory_names
        for part in parts[:-1]
    ):
        return True

    if any(
        part in excluded_path_parts
        for part in parts[:-1]
    ):
        return True

    return False


def python_paths(
    root: Path,
) -> Iterable[Path]:
    for path in sorted(
        root.rglob("*.py")
    ):
        if not path.is_file():
            continue

        if should_skip(
            root,
            path,
        ):
            continue

        yield path


def qualified_functions(
    tree: ast.AST,
) -> Iterable[
    tuple[
        (
            ast.FunctionDef
            | ast.AsyncFunctionDef
        ),
        str,
    ]
]:
    def walk(
        node: ast.AST,
        prefix: tuple[str, ...],
    ) -> Iterable[
        tuple[
            (
                ast.FunctionDef
                | ast.AsyncFunctionDef
            ),
            str,
        ]
    ]:
        for child in (
            ast.iter_child_nodes(node)
        ):
            if isinstance(
                child,
                (
                    ast.FunctionDef,
                    ast.AsyncFunctionDef,
                ),
            ):
                qualified = ".".join(
                    (
                        *prefix,
                        child.name,
                    )
                )

                yield child, qualified

                yield from walk(
                    child,
                    (
                        *prefix,
                        child.name,
                    ),
                )

            elif isinstance(
                child,
                ast.ClassDef,
            ):
                yield from walk(
                    child,
                    (
                        *prefix,
                        child.name,
                    ),
                )

            else:
                yield from walk(
                    child,
                    prefix,
                )

    yield from walk(
        tree,
        (),
    )


def inspect_file(
    root: Path,
    path: Path,
) -> tuple[
    list[function_record],
    dict[str, Any] | None,
]:
    relative = (
        path.relative_to(root)
        .as_posix()
    )

    try:
        source = path.read_text(
            encoding="utf-8"
        )
    except (
        OSError,
        UnicodeError,
    ) as exc:
        return [], {
            "path": relative,
            "reason": "read_error",
            "detail": str(exc),
        }

    try:
        tree = ast.parse(
            source,
            filename=str(path),
        )
    except SyntaxError as exc:
        return [], {
            "path": relative,
            "reason": "syntax_error",
            "line": exc.lineno,
            "offset": exc.offset,
            "detail": exc.msg,
        }

    records: list[
        function_record
    ] = []

    for (
        node,
        qualified_name,
    ) in qualified_functions(tree):
        size = ast_size(node)
        statement_count = len(
            node.body
        )

        if (
            statement_count
            < minimum_statement_count
        ):
            continue

        if size < minimum_ast_size:
            continue

        records.append(
            function_record(
                path=relative,
                name=node.name,
                qualified_name=(
                    qualified_name
                ),
                line=node.lineno,
                end_line=getattr(
                    node,
                    "end_lineno",
                    node.lineno,
                ),
                statement_count=(
                    statement_count
                ),
                ast_size=size,
                semantic_digest=(
                    semantic_function_digest(
                        node
                    )
                ),
            )
        )

    return records, None


def common_scope(
    paths: Iterable[str],
) -> str:
    values = [
        Path(path).parts[:-1]
        for path in paths
    ]

    if not values:
        return "."

    common: list[str] = []

    for columns in zip(*values):
        first = columns[0]

        if not all(
            value == first
            for value in columns
        ):
            break

        common.append(first)

    if not common:
        return "."

    return Path(
        *common
    ).as_posix()


def owner_hint(
    scope: str,
) -> dict[str, Any]:
    parts = Path(scope).parts

    if "rubric" in parts:
        index = parts.index(
            "rubric"
        )

        return {
            "classification": (
                "existing_rubric_scope"
            ),
            "scope": Path(
                *parts[: index + 1]
            ).as_posix(),
            "authority_effect": "none",
        }

    if "exiles" in parts:
        index = parts.index(
            "exiles"
        )

        if len(parts) > index + 1:
            exile = parts[
                index + 1
            ]

            return {
                "classification": (
                    "exile_local_owner_"
                    "unresolved"
                ),
                "exile": exile,
                "scope": scope,
                "authority_effect": "none",
            }

    if scope.startswith(
        "tools/niche/masterplan"
    ):
        return {
            "classification": (
                "niche_masterplan_"
                "shared_scope"
            ),
            "scope": (
                "tools/niche/masterplan"
            ),
            "authority_effect": "none",
        }

    return {
        "classification": (
            "shared_owner_unresolved"
        ),
        "scope": scope,
        "authority_effect": "none",
    }


def disposition(
    records: list[
        function_record
    ],
) -> str:
    unique_paths = {
        record.path
        for record in records
    }

    if len(unique_paths) < 2:
        return "preserve"

    scope = common_scope(
        sorted(unique_paths)
    )

    if scope == ".":
        return (
            "investigate_shared_primitive"
        )

    if scope.startswith(
        "tools/niche/masterplan"
    ):
        return "instance"

    if "/rubric" in f"/{scope}":
        return "instance"

    return "investigate_owner"


def compile_inventory(
    root: Path,
) -> dict[str, Any]:
    records: list[
        function_record
    ] = []

    parse_failures: list[
        dict[str, Any]
    ] = []

    scanned_files = 0

    for path in python_paths(root):
        scanned_files += 1

        (
            file_records,
            failure,
        ) = inspect_file(
            root,
            path,
        )

        records.extend(
            file_records
        )

        if failure is not None:
            parse_failures.append(
                failure
            )

    by_digest: dict[
        str,
        list[function_record],
    ] = defaultdict(list)

    name_digests: dict[
        str,
        set[str],
    ] = defaultdict(set)

    for record in records:
        by_digest[
            record.semantic_digest
        ].append(record)

        name_digests[
            record.name
        ].add(
            record.semantic_digest
        )

    groups: list[
        dict[str, Any]
    ] = []

    for (
        semantic_digest,
        members,
    ) in by_digest.items():
        paths = sorted(
            {
                member.path
                for member in members
            }
        )

        if len(paths) < 2:
            continue

        names = sorted(
            {
                member.name
                for member in members
            }
        )

        scope = common_scope(
            paths
        )

        group = {
            "group_id": (
                "primitive-"
                + semantic_digest[:20]
            ),
            "semantic_digest": (
                semantic_digest
            ),
            "names": names,
            "occurrence_count": len(
                members
            ),
            "file_count": len(paths),
            "paths": paths,
            "narrowest_common_scope": (
                scope
            ),
            "owner_hint": owner_hint(
                scope
            ),
            "disposition": (
                disposition(members)
            ),
            "authority_effect": "none",
            "members": [
                {
                    "path": member.path,
                    "name": member.name,
                    "qualified_name": (
                        member
                        .qualified_name
                    ),
                    "line": member.line,
                    "end_line": (
                        member.end_line
                    ),
                    "statement_count": (
                        member
                        .statement_count
                    ),
                    "ast_size": (
                        member.ast_size
                    ),
                }
                for member in sorted(
                    members,
                    key=lambda item: (
                        item.path,
                        item.line,
                        item.qualified_name,
                    ),
                )
            ],
        }

        groups.append(group)

    groups.sort(
        key=lambda item: (
            -item[
                "occurrence_count"
            ],
            -item["file_count"],
            item[
                "semantic_digest"
            ],
        )
    )

    same_name_different_substance = [
        {
            "name": name,
            "semantic_variant_count": (
                len(digests)
            ),
        }
        for (
            name,
            digests,
        ) in sorted(
            name_digests.items()
        )
        if len(digests) > 1
    ]

    same_name_different_substance.sort(
        key=lambda item: (
            -item[
                "semantic_variant_count"
            ],
            item["name"],
        )
    )

    disposition_counts = Counter(
        group["disposition"]
        for group in groups
    )

    duplicate_occurrences = sum(
        group["occurrence_count"]
        for group in groups
    )

    duplicate_files = {
        path
        for group in groups
        for path in group["paths"]
    }

    report = {
        "schema": schema,
        "authority_effect": (
            authority_effect
        ),
        "root": str(root),
        "semantics": {
            "filesystem_presence_is_"
            "authority": False,
            "inventory_is_authority": (
                False
            ),
            "automatic_mutation": False,
            "automatic_owner_assignment": (
                False
            ),
            "semantic_identity_basis": (
                "normalized_python_ast"
            ),
            "same_name_is_not_identity": (
                True
            ),
            "shared_implementation_"
            "requires_authority_"
            "preserving_migration": True,
        },
        "counts": {
            "python_files_scanned": (
                scanned_files
            ),
            "functions_inspected": len(
                records
            ),
            "parse_failures": len(
                parse_failures
            ),
            "duplicate_implementation_"
            "groups": len(groups),
            "duplicate_implementation_"
            "occurrences": (
                duplicate_occurrences
            ),
            "files_participating_in_"
            "duplicate_implementations": (
                len(duplicate_files)
            ),
            "same_name_different_"
            "substance": len(
                same_name_different_substance
            ),
        },
        "disposition_counts": dict(
            sorted(
                disposition_counts.items()
            )
        ),
        "groups": groups,
        "same_name_different_substance": (
            same_name_different_substance
        ),
        "parse_failures": (
            parse_failures
        ),
    }

    report[
        "semantic_fingerprint"
    ] = digest(report)

    return report


def write_report(
    report: dict[str, Any],
    output: Path | None,
) -> None:
    rendered = json.dumps(
        report,
        ensure_ascii=False,
        sort_keys=True,
        indent=2,
        allow_nan=False,
    )

    if output is None:
        print(rendered)
        return

    output.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    temporary = output.with_name(
        output.name + ".tmp"
    )

    temporary.write_text(
        rendered + "\n",
        encoding="utf-8",
    )

    os.replace(
        temporary,
        output,
    )


def self_check() -> dict[str, Any]:
    first = ast.parse(
        """
def alpha(value):
    return {"value": value}
"""
    ).body[0]

    second = ast.parse(
        """
def beta(value):
    return {"value": value}
"""
    ).body[0]

    third = ast.parse(
        """
def gamma(value):
    return {"other": value}
"""
    ).body[0]

    ellipsis_node = ast.parse(
        """
def delta():
    return ...
"""
    ).body[0]

    bytes_node = ast.parse(
        """
def epsilon():
    return b"abc"
"""
    ).body[0]

    first_digest = (
        semantic_function_digest(
            first
        )
    )

    second_digest = (
        semantic_function_digest(
            second
        )
    )

    third_digest = (
        semantic_function_digest(
            third
        )
    )

    ellipsis_digest = (
        semantic_function_digest(
            ellipsis_node
        )
    )

    bytes_digest = (
        semantic_function_digest(
            bytes_node
        )
    )

    if first_digest != second_digest:
        raise RuntimeError(
            "function-name-independent "
            "semantic identity failed"
        )

    if first_digest == third_digest:
        raise RuntimeError(
            "semantic distinction failed"
        )

    if not ellipsis_digest:
        raise RuntimeError(
            "ellipsis normalization failed"
        )

    if not bytes_digest:
        raise RuntimeError(
            "bytes normalization failed"
        )

    scope = common_scope(
        (
            "tools/niche/masterplan/a.py",
            "tools/niche/masterplan/b.py",
        )
    )

    if (
        scope
        != "tools/niche/masterplan"
    ):
        raise RuntimeError(
            "common scope failed"
        )

    first_report = {
        "schema": schema,
        "scope": scope,
        "digest": first_digest,
    }

    second_report = {
        "schema": schema,
        "scope": scope,
        "digest": second_digest,
    }

    if digest(
        first_report
    ) != digest(
        second_report
    ):
        raise RuntimeError(
            "deterministic fingerprint "
            "failed"
        )

    return {
        "schema": schema,
        "authority_effect": "none",
        "self_check": "passed",
        "semantic_identity": "passed",
        "semantic_distinction": (
            "passed"
        ),
        "constant_normalization": (
            "passed"
        ),
        "scope_derivation": "passed",
        "determinism": "passed",
    }


def parser() -> (
    argparse.ArgumentParser
):
    value = argparse.ArgumentParser(
        prog=(
            "inventory_modular_"
            "primitive_convergence"
        )
    )

    subparsers = (
        value.add_subparsers(
            dest="command",
            required=True,
        )
    )

    inventory = (
        subparsers.add_parser(
            "inventory"
        )
    )

    inventory.add_argument(
        "--root",
        default=str(
            default_root
        ),
    )

    inventory.add_argument(
        "--output",
    )

    subparsers.add_parser(
        "self-check"
    )

    return value


def main(
    argv: list[str] | None = None,
) -> int:
    arguments = (
        parser().parse_args(argv)
    )

    if (
        arguments.command
        == "self-check"
    ):
        print(
            json.dumps(
                self_check(),
                ensure_ascii=False,
                sort_keys=True,
                indent=2,
                allow_nan=False,
            )
        )
        return 0

    root = Path(
        arguments.root
    ).resolve()

    if not root.is_dir():
        raise SystemExit(
            "runtime root does not "
            f"exist: {root}"
        )

    output = (
        Path(
            arguments.output
        ).resolve()
        if arguments.output
        else None
    )

    report = compile_inventory(
        root
    )

    write_report(
        report,
        output,
    )

    return 0


if __name__ == "__main__":
    sys.exit(
        main()
    )
