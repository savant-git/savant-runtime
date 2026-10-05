#!/usr/bin/env python3
from __future__ import annotations

from collections.abc import (
    Mapping,
    Sequence,
)
from copy import deepcopy
import json
from pathlib import Path
from typing import Any, Iterable

from ..engine import LineageGraph
from .common import (
    add_binding_once,
    add_many_bindings,
    string_ids,
)


DEFAULT_IGNORE_NAMES = {
    ".git",
    ".venv",
    ".venv_voice",
    "node_modules",
    "__pycache__",
    "site-packages",
    "exports",
    "repair_backups",
    "source",
}


def _provenance(
    source_path: Path | str,
    adapter: str,
) -> dict[str, Any]:
    source = str(
        source_path
    )

    return {
        "created_by": adapter,
        "created_from": [
            source
        ],
        "source_files": [
            source
        ],
    }


def _node_payload(
    document: Mapping[
        str,
        Any,
    ],
    *,
    source_path: Path | str,
) -> dict[str, Any]:
    payload = deepcopy(
        dict(document)
    )

    payload.setdefault(
        "provenance",
        {},
    )

    if isinstance(
        payload["provenance"],
        Mapping,
    ):
        provenance = dict(
            payload["provenance"]
        )
    else:
        provenance = {
            "original": deepcopy(
                payload["provenance"]
            )
        }

    source = str(
        source_path
    )

    sources = provenance.get(
        "source_files",
        [],
    )

    if not isinstance(
        sources,
        list,
    ):
        sources = [
            sources
        ]

    if source not in sources:
        sources.append(
            source
        )

    provenance[
        "source_files"
    ] = sources

    provenance.setdefault(
        "adapter",
        "authority_document",
    )

    payload[
        "provenance"
    ] = provenance

    payload.setdefault(
        "metadata",
        {},
    )

    if isinstance(
        payload["metadata"],
        Mapping,
    ):
        metadata = dict(
            payload["metadata"]
        )
    else:
        metadata = {
            "original": deepcopy(
                payload["metadata"]
            )
        }

    metadata.setdefault(
        "authority_source_path",
        source,
    )

    payload[
        "metadata"
    ] = metadata

    return payload


def _iter_parent_specs(
    value: Any,
) -> list[
    tuple[
        str,
        str,
        str,
    ]
]:
    result: list[
        tuple[
            str,
            str,
            str,
        ]
    ] = []

    if isinstance(
        value,
        str,
    ):
        stripped = value.strip()

        if stripped:
            result.append(
                (
                    stripped,
                    "generic",
                    "neutral",
                )
            )

        return result

    if isinstance(
        value,
        Mapping,
    ):
        parent = ""

        for key in (
            "id",
            "parent",
            "source",
            "target",
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
                parent = (
                    candidate.strip()
                )
                break

        if parent:
            role = str(
                value.get(
                    "role",
                    "generic",
                )
            ).strip() or "generic"

            continuation = str(
                value.get(
                    "continuation",
                    "neutral",
                )
            ).strip() or "neutral"

            result.append(
                (
                    parent,
                    role,
                    continuation,
                )
            )

        return result

    if (
        isinstance(
            value,
            Sequence,
        )
        and not isinstance(
            value,
            (
                str,
                bytes,
                bytearray,
            ),
        )
    ):
        for item in value:
            result.extend(
                _iter_parent_specs(
                    item
                )
            )

    return result


def _recognized_relationship(
    source_id: str,
    relationship: Mapping[
        str,
        Any,
    ],
) -> tuple[
    str,
    str,
    str,
    str,
] | None:
    relation = str(
        relationship.get(
            "type"
        )
        or relationship.get(
            "relation"
        )
        or relationship.get(
            "kind"
        )
        or ""
    ).strip().casefold()

    target_ids = string_ids(
        relationship.get(
            "target"
        )
        or relationship.get(
            "to"
        )
        or relationship.get(
            "child"
        )
        or relationship.get(
            "parent"
        )
        or relationship.get(
            "id"
        )
    )

    if (
        not relation
        or not target_ids
    ):
        return None

    target = target_ids[0]

    parent_first = {
        "contains": (
            "composition",
            "neutral",
        ),
        "composes": (
            "composition",
            "neutral",
        ),
        "composition": (
            "composition",
            "neutral",
        ),
        "owns": (
            "ownership",
            "neutral",
        ),
        "owner_of": (
            "ownership",
            "neutral",
        ),
        "parent_of": (
            "generic",
            "neutral",
        ),
        "classifies": (
            "classification",
            "preserving",
        ),
        "includes": (
            "membership",
            "preserving",
        ),
        "precedes": (
            "sequence",
            "neutral",
        ),
        "projects": (
            "projection",
            "projecting",
        ),
        "exposes": (
            "exposure",
            "projecting",
        ),
    }

    target_first = {
        "child_of": (
            "generic",
            "neutral",
        ),
        "member_of": (
            "membership",
            "preserving",
        ),
        "classified_by": (
            "classification",
            "preserving",
        ),
        "depends_on": (
            "dependency",
            "neutral",
        ),
        "requires": (
            "dependency",
            "neutral",
        ),
        "derived_from": (
            "source",
            "neutral",
        ),
        "source": (
            "source",
            "neutral",
        ),
        "inherits": (
            "pattern",
            "preserving",
        ),
        "extends": (
            "pattern",
            "preserving",
        ),
        "implements": (
            "implementation",
            "projecting",
        ),
        "supersedes": (
            "supersession",
            "transforming",
        ),
        "attached_to": (
            "attachment",
            "neutral",
        ),
        "view_of": (
            "projection",
            "projecting",
        ),
    }

    if relation in parent_first:
        (
            role,
            continuation,
        ) = parent_first[
            relation
        ]

        return (
            source_id,
            target,
            role,
            continuation,
        )

    if relation in target_first:
        (
            role,
            continuation,
        ) = target_first[
            relation
        ]

        return (
            target,
            source_id,
            role,
            continuation,
        )

    return None


def ingest_authority_document(
    graph: LineageGraph,
    document: Mapping[
        str,
        Any,
    ],
    *,
    source_path: Path | str,
) -> int:
    if (
        document.get("kind")
        == "segue"
        and document.get("type")
        == "lineage"
    ):
        graph.add_binding(
            document
        )

        return 1

    raw_id = document.get(
        "id"
    )

    if (
        not isinstance(
            raw_id,
            str,
        )
        or not raw_id.strip()
    ):
        return 0

    node_id = raw_id.strip()

    graph.add_node(
        node_id,
        _node_payload(
            document,
            source_path=(
                source_path
            ),
        ),
    )

    provenance = _provenance(
        source_path,
        "authority_adapter",
    )

    metadata = {
        "adapter": "authority",
        "source_path": str(
            source_path
        ),
    }

    bindings_before = len(
        graph.bindings
    )

    for field_name in (
        "meta_archetype",
        "archetype",
        "template",
        "inherits",
        "extends",
    ):
        add_many_bindings(
            graph,
            parents=string_ids(
                document.get(
                    field_name
                )
            ),
            child=node_id,
            role="pattern",
            continuation="preserving",
            provenance=provenance,
            metadata={
                **metadata,
                "source_field": (
                    field_name
                ),
            },
        )

    for field_name in (
        "dependencies",
        "depends_on",
        "requires",
    ):
        add_many_bindings(
            graph,
            parents=string_ids(
                document.get(
                    field_name
                )
            ),
            child=node_id,
            role="dependency",
            provenance=provenance,
            metadata={
                **metadata,
                "source_field": (
                    field_name
                ),
            },
        )

    lineage = document.get(
        "lineage"
    )

    if isinstance(
        lineage,
        Mapping,
    ):
        for (
            parent,
            role,
            continuation,
        ) in _iter_parent_specs(
            lineage.get(
                "parents"
            )
        ):
            add_binding_once(
                graph,
                parent=parent,
                child=node_id,
                role=role,
                continuation=(
                    continuation
                ),
                provenance=provenance,
                metadata={
                    **metadata,
                    "source_field": (
                        "lineage.parents"
                    ),
                },
            )

        add_many_bindings(
            graph,
            parents=string_ids(
                lineage.get(
                    "mothers"
                )
            ),
            child=node_id,
            role="source",
            provenance=provenance,
            metadata={
                **metadata,
                "source_field": (
                    "lineage.mothers"
                ),
            },
        )

        add_many_bindings(
            graph,
            parents=string_ids(
                lineage.get(
                    "fathers"
                )
            ),
            child=node_id,
            role="pattern",
            continuation="preserving",
            provenance=provenance,
            metadata={
                **metadata,
                "source_field": (
                    "lineage.fathers"
                ),
            },
        )

        for child_id in string_ids(
            lineage.get(
                "children"
            )
        ):
            add_binding_once(
                graph,
                parent=node_id,
                child=child_id,
                role="generic",
                provenance=provenance,
                metadata={
                    **metadata,
                    "source_field": (
                        "lineage.children"
                    ),
                },
            )

        for child_id in string_ids(
            lineage.get(
                "daughters"
            )
        ):
            add_binding_once(
                graph,
                parent=node_id,
                child=child_id,
                role="generic",
                continuation=(
                    "preserving"
                ),
                provenance=provenance,
                metadata={
                    **metadata,
                    "source_field": (
                        "lineage.daughters"
                    ),
                },
            )

        for child_id in string_ids(
            lineage.get(
                "sons"
            )
        ):
            add_binding_once(
                graph,
                parent=node_id,
                child=child_id,
                role="generic",
                continuation=(
                    "projecting"
                ),
                provenance=provenance,
                metadata={
                    **metadata,
                    "source_field": (
                        "lineage.sons"
                    ),
                },
            )

        for old_id in string_ids(
            lineage.get(
                "supersedes"
            )
        ):
            add_binding_once(
                graph,
                parent=old_id,
                child=node_id,
                role="supersession",
                continuation=(
                    "transforming"
                ),
                provenance=provenance,
                metadata={
                    **metadata,
                    "source_field": (
                        "lineage.supersedes"
                    ),
                },
            )

        for origin_id in string_ids(
            lineage.get(
                "composed_from"
            )
        ):
            add_binding_once(
                graph,
                parent=origin_id,
                child=node_id,
                role="source",
                provenance=provenance,
                metadata={
                    **metadata,
                    "source_field": (
                        "lineage."
                        "composed_from"
                    ),
                },
            )

    for field_name in (
        "parent",
        "parent_id",
        "parents",
    ):
        add_many_bindings(
            graph,
            parents=string_ids(
                document.get(
                    field_name
                )
            ),
            child=node_id,
            role="generic",
            provenance=provenance,
            metadata={
                **metadata,
                "source_field": (
                    field_name
                ),
            },
        )

    for field_name in (
        "children",
        "child_ids",
    ):
        for child_id in string_ids(
            document.get(
                field_name
            )
        ):
            add_binding_once(
                graph,
                parent=node_id,
                child=child_id,
                role="generic",
                provenance=provenance,
                metadata={
                    **metadata,
                    "source_field": (
                        field_name
                    ),
                },
            )

    composition = document.get(
        "composition"
    )

    if isinstance(
        composition,
        Mapping,
    ):
        for child_id in string_ids(
            composition.get(
                "children"
            )
        ):
            add_binding_once(
                graph,
                parent=node_id,
                child=child_id,
                role="composition",
                provenance=provenance,
                metadata={
                    **metadata,
                    "source_field": (
                        "composition.children"
                    ),
                },
            )

    relationships = document.get(
        "relationships"
    )

    if (
        isinstance(
            relationships,
            Sequence,
        )
        and not isinstance(
            relationships,
            (
                str,
                bytes,
                bytearray,
            ),
        )
    ):
        for relationship in relationships:
            if not isinstance(
                relationship,
                Mapping,
            ):
                continue

            recognized = (
                _recognized_relationship(
                    node_id,
                    relationship,
                )
            )

            if recognized is None:
                continue

            (
                parent,
                child,
                role,
                continuation,
            ) = recognized

            add_binding_once(
                graph,
                parent=parent,
                child=child,
                role=role,
                continuation=(
                    continuation
                ),
                provenance=provenance,
                metadata={
                    **metadata,
                    "source_field": (
                        "relationships"
                    ),
                    "relationship": (
                        deepcopy(
                            dict(
                                relationship
                            )
                        )
                    ),
                },
            )

    return (
        1
        + len(graph.bindings)
        - bindings_before
    )


def iter_json_documents(
    roots: Iterable[
        Path | str
    ],
    *,
    ignored_names: Iterable[
        str
    ] = DEFAULT_IGNORE_NAMES,
):
    ignored = set(
        ignored_names
    )

    seen: set[Path] = set()

    for raw_root in roots:
        root = Path(
            raw_root
        ).expanduser().resolve()

        if not root.exists():
            continue

        candidates = (
            [root]
            if root.is_file()
            else sorted(
                root.rglob(
                    "*.json"
                )
            )
        )

        for path in candidates:
            resolved = path.resolve()

            if (
                resolved in seen
                or any(
                    part in ignored
                    for part in path.parts
                )
            ):
                continue

            seen.add(
                resolved
            )

            try:
                payload = json.loads(
                    path.read_text(
                        encoding="utf-8"
                    )
                )
            except (
                OSError,
                UnicodeError,
                json.JSONDecodeError,
            ):
                continue

            if isinstance(
                payload,
                Mapping,
            ):
                yield (
                    path,
                    payload,
                )

            elif isinstance(
                payload,
                list,
            ):
                for item in payload:
                    if isinstance(
                        item,
                        Mapping,
                    ):
                        yield (
                            path,
                            item,
                        )


def ingest_authority_roots(
    graph: LineageGraph,
    roots: Iterable[
        Path | str
    ],
) -> dict[str, int]:
    documents = 0
    emitted = 0

    for (
        path,
        document,
    ) in iter_json_documents(
        roots
    ):
        emitted += (
            ingest_authority_document(
                graph,
                document,
                source_path=path,
            )
        )

        documents += 1

    return {
        "documents": documents,
        "emitted": emitted,
    }
