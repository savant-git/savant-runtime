#!/usr/bin/env python3
from __future__ import annotations

from collections.abc import (
    Iterable,
    Mapping,
    Sequence,
)
from copy import deepcopy
from pathlib import Path
from typing import Any

from ..engine import LineageGraph
from ..model import LineageValidationError

from ..references import (
    SAVANT_ROOT,
    resolve_reference,
    source_path_from_context,
)


def string_ids(
    value: Any,
) -> list[str]:
    if isinstance(
        value,
        str,
    ):
        stripped = value.strip()

        return (
            [stripped]
            if stripped
            else []
        )

    if isinstance(
        value,
        Mapping,
    ):
        for key in (
            "id",
            "parent",
            "child",
            "target",
            "source",
            "ref",
        ):
            candidate = value.get(
                key
            )

            if (
                isinstance(
                    candidate,
                    str,
                )
                and candidate.strip()
            ):
                return [
                    candidate.strip()
                ]

        return []

    if (
        not isinstance(
            value,
            Sequence,
        )
        or isinstance(
            value,
            (
                bytes,
                bytearray,
            ),
        )
    ):
        return []

    result: list[str] = []

    for item in value:
        for candidate in string_ids(
            item
        ):
            if candidate not in result:
                result.append(
                    candidate
                )

    return result


def _normalization_metadata(
    metadata: Mapping[
        str,
        Any,
    ] | None,
    resolutions: Iterable[Any],
) -> dict[str, Any]:
    result = deepcopy(
        dict(
            metadata
            or {}
        )
    )

    changes = [
        resolution.to_dict()
        for resolution in resolutions
        if resolution.changed
    ]

    if not changes:
        return result

    existing = result.get(
        "reference_normalization"
    )

    normalized_existing: list[Any]

    if isinstance(
        existing,
        list,
    ):
        normalized_existing = deepcopy(
            existing
        )

    elif existing is None:
        normalized_existing = []

    else:
        normalized_existing = [
            deepcopy(
                existing
            )
        ]

    normalized_existing.extend(
        changes
    )

    result[
        "reference_normalization"
    ] = normalized_existing

    return result


def add_binding_once(
    graph: LineageGraph,
    *,
    parent: str,
    child: str,
    role: str,
    continuation: str = "neutral",
    scope: str = "global",
    order: int = 0,
    provenance: Mapping[
        str,
        Any,
    ] | None = None,
    metadata: Mapping[
        str,
        Any,
    ] | None = None,
    inheritance: Mapping[
        str,
        Any,
    ] | None = None,
    propagation: Mapping[
        str,
        Any,
    ] | None = None,
    status: str = "active",
    reference_root: Path | str = SAVANT_ROOT,
) -> None:
    raw_parent = str(
        parent
    ).strip()

    raw_child = str(
        child
    ).strip()

    if (
        not raw_parent
        or not raw_child
    ):
        return

    source_path = source_path_from_context(
        provenance,
        metadata,
    )

    parent_resolution = resolve_reference(
        raw_parent,
        root=reference_root,
        source_path=source_path,
    )

    child_resolution = resolve_reference(
        raw_child,
        root=reference_root,
        source_path=source_path,
    )

    canonical_parent = (
        parent_resolution.canonical
    )

    canonical_child = (
        child_resolution.canonical
    )

    if (
        not canonical_parent
        or not canonical_child
        or canonical_parent
        == canonical_child
    ):
        return

    payload: dict[
        str,
        Any,
    ] = {
        "kind": "segue",
        "type": "lineage",
        "parent": canonical_parent,
        "child": canonical_child,
        "role": role,
        "continuation": continuation,
        "scope": scope,
        "order": order,
        "status": status,
        "provenance": deepcopy(
            dict(
                provenance
                or {}
            )
        ),
        "metadata": (
            _normalization_metadata(
                metadata,
                (
                    parent_resolution,
                    child_resolution,
                ),
            )
        ),
    }

    if inheritance is not None:
        payload[
            "inheritance"
        ] = deepcopy(
            dict(inheritance)
        )

    if propagation is not None:
        payload[
            "propagation"
        ] = deepcopy(
            dict(propagation)
        )

    try:
        graph.add_binding(
            payload
        )

    except LineageValidationError as exc:
        message = str(
            exc
        )

        if message.startswith(
            "duplicate lineage relationship:"
        ):
            return

        raise


def add_many_bindings(
    graph: LineageGraph,
    *,
    parents: Iterable[str],
    child: str,
    role: str,
    continuation: str = "neutral",
    provenance: Mapping[
        str,
        Any,
    ] | None = None,
    metadata: Mapping[
        str,
        Any,
    ] | None = None,
    reference_root: Path | str = SAVANT_ROOT,
) -> None:
    for order, parent in enumerate(
        parents
    ):
        add_binding_once(
            graph,
            parent=parent,
            child=child,
            role=role,
            continuation=continuation,
            order=order,
            provenance=provenance,
            metadata=metadata,
            reference_root=reference_root,
        )
