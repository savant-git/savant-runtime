#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any

import yaml


ROOT = Path(__file__).resolve().parent
DEFAULT_REGISTRY = ROOT / "kindred_registry.yaml"

ID_PATTERN = re.compile(
    r"^kindred:[a-z][a-z0-9_-]*$"
)


def string_list(
    value: Any,
) -> list[str]:
    if value is None:
        return []

    if isinstance(value, str):
        value = value.strip()
        return [value] if value else []

    if isinstance(value, list):
        return [
            str(item).strip()
            for item in value
            if str(item).strip()
        ]

    return [str(value).strip()]


def find_cycle(
    graph: dict[str, set[str]],
) -> list[str] | None:
    state: dict[str, int] = {}
    stack: list[str] = []
    positions: dict[str, int] = {}

    def visit(
        node: str,
    ) -> list[str] | None:
        state[node] = 1
        positions[node] = len(stack)
        stack.append(node)

        for target in sorted(
            graph.get(node, set())
        ):
            target_state = state.get(
                target,
                0,
            )

            if target_state == 0:
                cycle = visit(target)

                if cycle:
                    return cycle

            elif target_state == 1:
                start = positions[target]

                return [
                    *stack[start:],
                    target,
                ]

        stack.pop()
        positions.pop(node, None)
        state[node] = 2

        return None

    for node in sorted(graph):
        if state.get(node, 0) != 0:
            continue

        cycle = visit(node)

        if cycle:
            return cycle

    return None


def validate(
    data: dict[str, Any],
) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []

    records = data.get(
        "kindreds",
        [],
    )

    if not isinstance(records, list):
        return [
            {
                "code": "kindred.registry.invalid",
                "severity": "error",
                "message": "kindreds must be a list",
            }
        ]

    by_id: dict[str, dict[str, Any]] = {}
    canonical_owners: dict[
        str,
        list[str],
    ] = defaultdict(list)

    for index, record in enumerate(records):
        if not isinstance(record, dict):
            issues.append(
                {
                    "code": "kindred.record.invalid",
                    "severity": "error",
                    "index": index,
                }
            )
            continue

        kindred_id = str(
            record.get("id", "")
        ).strip()

        canonical = str(
            record.get("canonical", "")
        ).strip()

        if not kindred_id:
            issues.append(
                {
                    "code": "kindred.id.missing",
                    "severity": "error",
                    "index": index,
                }
            )
            continue

        if not ID_PATTERN.fullmatch(
            kindred_id
        ):
            issues.append(
                {
                    "code": "kindred.id.invalid",
                    "severity": "error",
                    "kindred_id": kindred_id,
                }
            )

        if kindred_id in by_id:
            issues.append(
                {
                    "code": "kindred.id.duplicate",
                    "severity": "error",
                    "kindred_id": kindred_id,
                }
            )

        by_id[kindred_id] = record

        if not canonical:
            issues.append(
                {
                    "code": "kindred.canonical.missing",
                    "severity": "error",
                    "kindred_id": kindred_id,
                }
            )
        else:
            canonical_owners[
                canonical.casefold()
            ].append(kindred_id)

        for required in (
            "members",
            "provenance",
            "lineage",
        ):
            if required not in record:
                issues.append(
                    {
                        "code": (
                            "kindred.required.missing"
                        ),
                        "severity": "error",
                        "kindred_id": kindred_id,
                        "field": required,
                    }
                )

    for canonical, owners in sorted(
        canonical_owners.items()
    ):
        if len(owners) > 1:
            issues.append(
                {
                    "code": (
                        "kindred.canonical.duplicate"
                    ),
                    "severity": "error",
                    "canonical": canonical,
                    "owners": owners,
                }
            )

    inheritance_graph: dict[
        str,
        set[str],
    ] = {
        kindred_id: set()
        for kindred_id in by_id
    }

    dependency_graph: dict[
        str,
        set[str],
    ] = {
        kindred_id: set()
        for kindred_id in by_id
    }

    for kindred_id, record in by_id.items():
        for field in (
            "parents",
            "children",
            "dependencies",
        ):
            seen: set[str] = set()

            for target in string_list(
                record.get(field)
            ):
                if target == kindred_id:
                    issues.append(
                        {
                            "code": (
                                "kindred.reference.self"
                            ),
                            "severity": "error",
                            "kindred_id": kindred_id,
                            "field": field,
                            "target": target,
                        }
                    )

                if target not in by_id:
                    issues.append(
                        {
                            "code": (
                                "kindred.reference."
                                "unresolved"
                            ),
                            "severity": "error",
                            "kindred_id": kindred_id,
                            "field": field,
                            "target": target,
                        }
                    )

                if target in seen:
                    issues.append(
                        {
                            "code": (
                                "kindred.reference."
                                "duplicate"
                            ),
                            "severity": "warning",
                            "kindred_id": kindred_id,
                            "field": field,
                            "target": target,
                        }
                    )

                seen.add(target)

        for parent in string_list(
            record.get("parents")
        ):
            inheritance_graph[
                kindred_id
            ].add(parent)

        for dependency in string_list(
            record.get("dependencies")
        ):
            dependency_graph[
                kindred_id
            ].add(dependency)

        for relationship in record.get(
            "relationships",
            [],
        ):
            if isinstance(relationship, str):
                target = relationship

            elif isinstance(
                relationship,
                dict,
            ):
                target = str(
                    relationship.get(
                        "target",
                        "",
                    )
                ).strip()

            else:
                issues.append(
                    {
                        "code": (
                            "kindred.relationship."
                            "invalid"
                        ),
                        "severity": "error",
                        "kindred_id": kindred_id,
                    }
                )
                continue

            if target and target not in by_id:
                issues.append(
                    {
                        "code": (
                            "kindred.relationship."
                            "unresolved"
                        ),
                        "severity": "error",
                        "kindred_id": kindred_id,
                        "target": target,
                    }
                )

    inheritance_cycle = find_cycle(
        inheritance_graph
    )

    if inheritance_cycle:
        issues.append(
            {
                "code": (
                    "kindred.inheritance.cycle"
                ),
                "severity": "error",
                "cycle": inheritance_cycle,
            }
        )

    dependency_cycle = find_cycle(
        dependency_graph
    )

    if dependency_cycle:
        issues.append(
            {
                "code": (
                    "kindred.dependency.cycle"
                ),
                "severity": "error",
                "cycle": dependency_cycle,
            }
        )

    return issues


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="kindred-validator"
    )

    parser.add_argument(
        "--registry",
        default=str(DEFAULT_REGISTRY),
    )

    args = parser.parse_args()

    path = Path(
        args.registry
    ).expanduser().resolve()

    with path.open(
        "r",
        encoding="utf-8",
    ) as handle:
        data = yaml.safe_load(handle)

    issues = validate(data)

    errors = [
        issue
        for issue in issues
        if issue.get("severity") == "error"
    ]

    warnings = [
        issue
        for issue in issues
        if issue.get("severity") == "warning"
    ]

    print(
        json.dumps(
            {
                "valid": not errors,
                "error_count": len(errors),
                "warning_count": len(warnings),
                "issues": issues,
            },
            indent=2,
            sort_keys=True,
        )
    )

    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
