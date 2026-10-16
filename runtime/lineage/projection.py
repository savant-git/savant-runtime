#!/usr/bin/env python3
from __future__ import annotations

from collections import defaultdict
from copy import deepcopy
from typing import Any, Iterable

from .engine import LineageGraph


def _unique(
    values: Iterable[str],
) -> list[str]:
    result: list[str] = []

    for value in values:
        if value not in result:
            result.append(
                value
            )

    return result


def family_projection(
    graph: LineageGraph,
    node_id: str,
) -> dict[str, Any]:
    parents = graph.parents(
        node_id
    )

    children = graph.children(
        node_id
    )

    parent_roles: dict[
        str,
        list[str],
    ] = defaultdict(list)

    child_roles: dict[
        str,
        list[str],
    ] = defaultdict(list)

    child_modes: dict[
        str,
        list[str],
    ] = defaultdict(list)

    for item in parents:
        parent_roles[
            item["role"]
        ].append(
            item["parent"]
        )

    for item in children:
        child_roles[
            item["role"]
        ].append(
            item["child"]
        )

        child_modes[
            item["continuation"]
        ].append(
            item["child"]
        )

    mothers = _unique(
        item["parent"]
        for item in parents
        if item.get(
            "symbolic_parent_alias"
        ) == "mother"
    )

    fathers = _unique(
        item["parent"]
        for item in parents
        if item.get(
            "symbolic_parent_alias"
        ) == "father"
    )

    daughters = _unique(
        item["child"]
        for item in children
        if item.get(
            "symbolic_child_alias"
        ) == "daughter"
    )

    sons = _unique(
        item["child"]
        for item in children
        if item.get(
            "symbolic_child_alias"
        ) == "son"
    )

    return {
        "node": node_id,
        "parents": deepcopy(
            parents
        ),
        "parent_ids": _unique(
            item["parent"]
            for item in parents
        ),
        "mothers": mothers,
        "fathers": fathers,
        "parent_roles": {
            role: _unique(values)
            for role, values
            in sorted(
                parent_roles.items()
            )
        },
        "children": deepcopy(
            children
        ),
        "child_ids": _unique(
            item["child"]
            for item in children
        ),
        "daughters": daughters,
        "sons": sons,
        "child_roles": {
            role: _unique(values)
            for role, values
            in sorted(
                child_roles.items()
            )
        },
        "child_modes": {
            mode: _unique(values)
            for mode, values
            in sorted(
                child_modes.items()
            )
        },
    }


def legacy_edifice_projection(
    graph: LineageGraph,
    node_id: str,
) -> dict[str, Any]:
    family = family_projection(
        graph,
        node_id,
    )

    return {
        "parent": (
            family["parent_ids"][0]
            if family["parent_ids"]
            else None
        ),
        "parents": (
            family["parent_ids"]
        ),
        "children": (
            family["child_ids"]
        ),
        "mother": (
            family["mothers"][0]
            if family["mothers"]
            else None
        ),
        "mothers": (
            family["mothers"]
        ),
        "father": (
            family["fathers"][0]
            if family["fathers"]
            else None
        ),
        "fathers": (
            family["fathers"]
        ),
        "daughters": (
            family["daughters"]
        ),
        "sons": (
            family["sons"]
        ),
    }
