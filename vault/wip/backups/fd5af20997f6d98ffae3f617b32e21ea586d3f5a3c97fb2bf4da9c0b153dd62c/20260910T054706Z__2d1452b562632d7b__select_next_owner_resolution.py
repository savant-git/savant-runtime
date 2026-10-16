#!/usr/bin/env python3

from __future__ import annotations

import ast
import hashlib
import json
import subprocess
import sys
from collections import Counter
from pathlib import Path
from typing import Any


schema = "savant.assurance.next-owner-resolution.v4"

runtime_root = Path("/root/savant-runtime")

modularity_root = (
    runtime_root
    / "assurance/convergence/modularity"
)

inventory_scanner = (
    modularity_root
    / "scanners/inventory_modular_primitive_convergence.py"
)

candidate_inventory_paths = (
    modularity_root
    / "runtime/modular-primitive-convergence-inventory.json",
    modularity_root
    / "runtime/reports/modular-primitive-convergence-inventory.json",
    runtime_root
    / "runtime/reports/modular-primitive-convergence-inventory.json",
    runtime_root
    / "runtime/reports/modular-primitive-convergence.json",
)

excluded_parts = {
    ".git",
    ".hg",
    ".svn",
    "__pycache__",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".tox",
    ".venv",
    "venv",
    "node_modules",
}

generic_names = {
    "digest",
    "fingerprint",
    "canonical_json",
    "canonical_json_bytes",
    "load_json",
    "load_module",
    "normalize_text",
    "normalize_strings",
    "stable_id",
    "write_json",
    "clamp",
    "ensure_list",
    "require_list",
    "require_object",
}


class SelectionError(RuntimeError):
    pass


def digest_text(value: str) -> str:
    return hashlib.sha256(
        value.encode("utf-8")
    ).hexdigest()


def json_objects_from_text(
    text: str,
) -> list[dict[str, Any]]:
    decoder = json.JSONDecoder()
    objects: list[dict[str, Any]] = []
    index = 0

    while index < len(text):
        start = text.find("{", index)

        if start < 0:
            break

        try:
            value, end = decoder.raw_decode(
                text[start:]
            )
        except json.JSONDecodeError:
            index = start + 1
            continue

        if isinstance(value, dict):
            objects.append(value)

        index = start + end

    return objects


def looks_like_inventory(
    value: dict[str, Any],
) -> bool:
    return bool(
        {
            "duplicate_implementation_groups",
            "duplicate_groups",
            "families",
            "groups",
        }
        & set(value)
    )


def load_json_file(
    path: Path,
) -> dict[str, Any] | None:
    if not path.is_file():
        return None

    try:
        value = json.loads(
            path.read_text(encoding="utf-8")
        )
    except Exception:
        return None

    if (
        isinstance(value, dict)
        and looks_like_inventory(value)
    ):
        return value

    return None


def existing_inventory() -> tuple[
    dict[str, Any],
    str,
] | None:
    for path in candidate_inventory_paths:
        value = load_json_file(path)

        if value is not None:
            return value, str(path)

    return None


def regenerate_inventory() -> tuple[
    dict[str, Any],
    str,
]:
    if not inventory_scanner.is_file():
        raise SelectionError(
            f"inventory scanner missing: {inventory_scanner}"
        )

    process = subprocess.run(
        [
            sys.executable,
            str(inventory_scanner),
            "inventory",
        ],
        cwd=str(runtime_root),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )

    if process.returncode != 0:
        detail = (
            process.stderr.strip()
            or process.stdout.strip()
            or f"exit {process.returncode}"
        )

        raise SelectionError(
            "inventory scanner failed: "
            + detail
        )

    existing = existing_inventory()

    if existing is not None:
        return existing

    inventories = [
        value
        for value in json_objects_from_text(
            process.stdout
        )
        if looks_like_inventory(value)
    ]

    if len(inventories) != 1:
        raise SelectionError(
            "inventory scanner completed but no "
            "unambiguous convergence inventory "
            "could be resolved"
        )

    return (
        inventories[0],
        "inventory-scanner:stdout",
    )


def load_inventory() -> tuple[
    dict[str, Any],
    str,
]:
    existing = existing_inventory()

    if existing is not None:
        return existing

    return regenerate_inventory()


def normalize_path(
    value: Any,
) -> Path | None:
    if not isinstance(value, str):
        return None

    value = value.strip()

    if not value:
        return None

    path = Path(value)

    if not path.is_absolute():
        path = runtime_root / path

    try:
        path.relative_to(runtime_root)
    except ValueError:
        return None

    if any(
        part in excluded_parts
        for part in path.parts
    ):
        return None

    return path


def family_name(
    family: dict[str, Any],
) -> str:
    for key in (
        "name",
        "function_name",
        "symbol",
        "primitive",
    ):
        value = family.get(key)

        if (
            isinstance(value, str)
            and value.strip()
        ):
            return value.strip()

    return ""


def occurrences(
    family: dict[str, Any],
) -> list[dict[str, Any]]:
    for key in (
        "occurrences",
        "members",
        "implementations",
        "copies",
    ):
        value = family.get(key)

        if isinstance(value, list):
            return [
                item
                for item in value
                if isinstance(item, dict)
            ]

    return []


def occurrence_path(
    occurrence: dict[str, Any],
) -> Path | None:
    for key in (
        "path",
        "file",
        "source_path",
        "filename",
    ):
        path = normalize_path(
            occurrence.get(key)
        )

        if path is not None:
            return path

    return None


def duplicate_families(
    inventory: dict[str, Any],
) -> list[dict[str, Any]]:
    for key in (
        "duplicate_implementation_groups",
        "duplicate_groups",
        "families",
        "groups",
    ):
        value = inventory.get(key)

        if isinstance(value, list):
            return [
                item
                for item in value
                if isinstance(item, dict)
            ]

    return []


def common_owner_candidate(
    paths: list[Path],
) -> Path | None:
    if not paths:
        return None

    relatives = [
        path.relative_to(runtime_root).parts
        for path in paths
    ]

    prefix: list[str] = []

    for column in zip(*relatives):
        if len(set(column)) != 1:
            break

        prefix.append(column[0])

    if not prefix:
        return None

    candidate = runtime_root.joinpath(*prefix)

    if candidate.suffix:
        candidate = candidate.parent

    return candidate


def top_level_distribution(
    paths: list[Path],
) -> dict[str, int]:
    counter: Counter[str] = Counter()

    for path in paths:
        relative = path.relative_to(runtime_root)

        if relative.parts:
            counter[relative.parts[0]] += 1

    return dict(sorted(counter.items()))


def normalized_function(
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
        raise SelectionError(
            "function normalization failed"
        )

    rebuilt.name = "__primitive__"

    return ast.dump(
        rebuilt,
        annotate_fields=True,
        include_attributes=False,
    )


def inspect_functions(
    path: Path,
) -> list[dict[str, Any]]:
    if not path.is_file():
        return []

    try:
        text = path.read_text(
            encoding="utf-8"
        )
        tree = ast.parse(
            text,
            filename=str(path),
        )
    except (OSError, UnicodeError, SyntaxError):
        return []

    result: list[dict[str, Any]] = []

    for node in tree.body:
        if not isinstance(
            node,
            (
                ast.FunctionDef,
                ast.AsyncFunctionDef,
            ),
        ):
            continue

        normalized = normalized_function(node)

        result.append(
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
                "digest": digest_text(
                    normalized
                ),
                "source": ast.get_source_segment(
                    text,
                    node,
                ),
            }
        )

    return result


def exact_shared_functions(
    paths: list[Path],
) -> list[dict[str, Any]]:
    if len(paths) < 2:
        return []

    by_path = {
        str(path): inspect_functions(path)
        for path in paths
    }

    digest_sets = [
        {
            item["digest"]
            for item in functions
        }
        for functions in by_path.values()
    ]

    if not digest_sets:
        return []

    shared = set.intersection(*digest_sets)

    result: list[dict[str, Any]] = []

    for function_digest in sorted(shared):
        members: list[dict[str, Any]] = []

        for path, functions in by_path.items():
            matching = [
                item
                for item in functions
                if item["digest"]
                == function_digest
            ]

            if len(matching) != 1:
                members = []
                break

            item = matching[0]

            members.append(
                {
                    "path": path,
                    "name": item["name"],
                    "line": item["line"],
                    "end_line": item["end_line"],
                    "async": item["async"],
                    "source": item["source"],
                }
            )

        if members:
            result.append(
                {
                    "digest":
                        function_digest,
                    "member_count":
                        len(members),
                    "members":
                        members,
                }
            )

    return result


def candidate_score(
    *,
    name: str,
    paths: list[Path],
    owner: Path | None,
    distribution: dict[str, int],
    exact_count: int,
) -> tuple[
    int,
    int,
    int,
    int,
    int,
    str,
]:
    owner_depth = (
        len(
            owner.relative_to(
                runtime_root
            ).parts
        )
        if owner
        else 0
    )

    return (
        0 if exact_count else 1,
        1 if name in generic_names else 0,
        1 if len(distribution) > 1 else 0,
        -owner_depth,
        -len(paths),
        name,
    )


def select(
    inventory: dict[str, Any],
    inventory_source: str,
) -> dict[str, Any]:
    candidates: list[
        tuple[
            tuple[
                int,
                int,
                int,
                int,
                int,
                str,
            ],
            dict[str, Any],
        ]
    ] = []

    for family in duplicate_families(
        inventory
    ):
        disposition = family.get(
            "disposition"
        )

        if disposition == "instance":
            continue

        paths = [
            path
            for occurrence
            in occurrences(family)
            if (
                path := occurrence_path(
                    occurrence
                )
            )
            is not None
        ]

        paths = list(dict.fromkeys(paths))

        if len(paths) < 2:
            continue

        name = family_name(family)

        owner = common_owner_candidate(
            paths
        )

        distribution = (
            top_level_distribution(paths)
        )

        exact = exact_shared_functions(
            paths
        )

        score = candidate_score(
            name=name,
            paths=paths,
            owner=owner,
            distribution=distribution,
            exact_count=len(exact),
        )

        candidates.append(
            (
                score,
                {
                    "name": name,
                    "disposition":
                        disposition,
                    "occurrence_count":
                        len(paths),
                    "paths": [
                        str(path)
                        for path in paths
                    ],
                    "top_level_distribution":
                        distribution,
                    "common_owner_candidate":
                        (
                            str(owner)
                            if owner
                            else None
                        ),
                    "generic_name":
                        name
                        in generic_names,
                    "exact_shared_function_count":
                        len(exact),
                    "exact_shared_functions":
                        exact,
                },
            )
        )

    candidates.sort(
        key=lambda item: item[0]
    )

    return {
        "schema": schema,
        "inventory_source":
            inventory_source,
        "remaining_candidate_count":
            len(candidates),
        "next":
            (
                candidates[0][1]
                if candidates
                else None
            ),
    }


def main() -> int:
    inventory, source = load_inventory()

    result = select(
        inventory,
        source,
    )

    print(
        json.dumps(
            result,
            indent=2,
            sort_keys=True,
        )
    )

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SelectionError as exc:
        print(
            f"{schema}: {exc}",
            file=sys.stderr,
        )
        raise SystemExit(1)
