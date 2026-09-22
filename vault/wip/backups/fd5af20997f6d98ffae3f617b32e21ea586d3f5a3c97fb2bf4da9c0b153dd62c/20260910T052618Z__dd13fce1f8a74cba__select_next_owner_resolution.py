#!/usr/bin/env python3

from __future__ import annotations

import json
import subprocess
import sys
from collections import Counter
from pathlib import Path
from typing import Any


schema = "savant.assurance.next-owner-resolution.v3"

runtime_root = Path(
    "/root/savant-runtime"
)

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

excluded_roots = {
    ".git",
    "__pycache__",
    "node_modules",
    ".venv",
    "venv",
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
    keys = set(value)

    return bool(
        {
            "duplicate_implementation_groups",
            "duplicate_groups",
            "families",
            "groups",
        }
        & keys
    )


def load_json_file(
    path: Path,
) -> dict[str, Any] | None:
    if not path.is_file():
        return None

    try:
        value = json.loads(
            path.read_text(
                encoding="utf-8",
            )
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

    objects = json_objects_from_text(
        process.stdout
    )

    inventories = [
        value
        for value in objects
        if looks_like_inventory(value)
    ]

    if len(inventories) == 1:
        return (
            inventories[0],
            "inventory-scanner:stdout",
        )

    raise SelectionError(
        "inventory scanner completed but no "
        "unambiguous convergence inventory "
        "could be resolved"
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
        part in excluded_roots
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

    relative_parts = [
        path.relative_to(
            runtime_root
        ).parts
        for path in paths
    ]

    prefix: list[str] = []

    for column in zip(
        *relative_parts
    ):
        if len(set(column)) != 1:
            break

        prefix.append(column[0])

    if not prefix:
        return None

    candidate = runtime_root.joinpath(
        *prefix
    )

    if candidate.suffix:
        candidate = candidate.parent

    return candidate


def top_level_distribution(
    paths: list[Path],
) -> dict[str, int]:
    counter: Counter[str] = Counter()

    for path in paths:
        relative = path.relative_to(
            runtime_root
        )

        if relative.parts:
            counter[
                relative.parts[0]
            ] += 1

    return dict(
        sorted(counter.items())
    )


def select(
    inventory: dict[str, Any],
    inventory_source: str,
) -> dict[str, Any]:
    candidates: list[
        tuple[
            tuple[int, int, int, int, str],
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
            for occurrence in occurrences(
                family
            )
            if (
                path := occurrence_path(
                    occurrence
                )
            )
            is not None
        ]

        if len(paths) < 2:
            continue

        name = family_name(
            family
        )

        owner_candidate = (
            common_owner_candidate(
                paths
            )
        )

        distribution = (
            top_level_distribution(
                paths
            )
        )

        owner_depth = (
            len(
                owner_candidate.relative_to(
                    runtime_root
                ).parts
            )
            if owner_candidate
            else 0
        )

        score = (
            1 if name in generic_names else 0,
            1 if len(distribution) > 1 else 0,
            -owner_depth,
            -len(paths),
            name,
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
                            str(
                                owner_candidate
                            )
                            if owner_candidate
                            else None
                        ),
                    "generic_name":
                        name
                        in generic_names,
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

    print(
        json.dumps(
            select(
                inventory,
                source,
            ),
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
