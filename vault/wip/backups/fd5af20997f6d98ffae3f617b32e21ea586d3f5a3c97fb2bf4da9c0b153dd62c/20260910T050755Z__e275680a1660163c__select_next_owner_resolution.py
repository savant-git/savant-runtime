#!/usr/bin/env python3

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any


schema = "savant.assurance.next-owner-resolution.v1"

inventory_path = Path(
    "/root/savant-runtime/runtime/reports/"
    "modular-primitive-convergence-inventory.json"
)

runtime_root = Path(
    "/root/savant-runtime"
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


def load_inventory() -> dict[str, Any]:
    if not inventory_path.is_file():
        raise SelectionError(
            f"inventory missing: {inventory_path}"
        )

    try:
        value = json.loads(
            inventory_path.read_text(
                encoding="utf-8",
            )
        )
    except Exception as exc:
        raise SelectionError(
            f"inventory unreadable: {exc}"
        ) from exc

    if not isinstance(value, dict):
        raise SelectionError(
            "inventory root must be an object"
        )

    return value


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
    candidates: list[Any] = []

    for key in (
        "duplicate_implementation_groups",
        "duplicate_groups",
        "families",
        "groups",
    ):
        value = inventory.get(key)

        if isinstance(value, list):
            candidates = value
            break

    return [
        item
        for item in candidates
        if isinstance(item, dict)
    ]


def common_owner_candidate(
    paths: list[Path],
) -> Path | None:
    if not paths:
        return None

    relative_parts = [
        path.relative_to(runtime_root).parts
        for path in paths
    ]

    prefix: list[str] = []

    for column in zip(*relative_parts):
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


def disposition(
    family: dict[str, Any],
) -> str:
    value = family.get("disposition")

    return (
        value
        if isinstance(value, str)
        else ""
    )


def select() -> dict[str, Any]:
    inventory = load_inventory()

    candidates: list[
        tuple[
            tuple[int, int, int, str],
            dict[str, Any],
        ]
    ] = []

    for family in duplicate_families(
        inventory
    ):
        disp = disposition(family)

        if disp == "instance":
            continue

        members = occurrences(family)

        paths = [
            path
            for item in members
            if (
                path := occurrence_path(
                    item
                )
            )
            is not None
        ]

        if len(paths) < 2:
            continue

        name = family_name(family)

        owner_candidate = (
            common_owner_candidate(paths)
        )

        distribution = (
            top_level_distribution(paths)
        )

        generic_penalty = (
            1
            if name in generic_names
            else 0
        )

        cross_domain = (
            1
            if len(distribution) > 1
            else 0
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
            generic_penalty,
            cross_domain,
            -owner_depth,
            name,
        )

        candidates.append(
            (
                score,
                {
                    "name": name,
                    "disposition": disp,
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

    if not candidates:
        return {
            "schema": schema,
            "next": None,
            "reason":
                "no unresolved duplicate family "
                "with at least two live paths",
        }

    candidates.sort(
        key=lambda item: item[0]
    )

    return {
        "schema": schema,
        "next": candidates[0][1],
        "remaining_candidate_count":
            len(candidates),
    }


def main() -> int:
    result = select()

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
