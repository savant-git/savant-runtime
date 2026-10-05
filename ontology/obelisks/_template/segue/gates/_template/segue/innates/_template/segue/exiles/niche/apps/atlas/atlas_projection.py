#!/usr/bin/env python3

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sqlite3
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable


schema_version = "savant.niche.atlas-projection.v1"
authority_effect = "none"
owner = "exile:niche"
projection_only = True
mutation_authority = False

runtime_root = Path(
    "/root/savant-runtime"
)

masterplan_path = (
    runtime_root
    / "authority"
    / "task-graph"
    / "masterplan.json"
)

task_store_path = (
    runtime_root
    / "runtime"
    / "niche"
    / "tasks.sqlite3"
)

authority_index_path = (
    runtime_root
    / "vault"
    / "authority"
    / "authority_index.json"
)

primary_architectural_law_path = (
    runtime_root
    / "ontology"
    / "obelisks"
    / "segue"
    / "authority_graph"
    / "canon"
    / "PRIMARY_ARCHITECTURAL_LAW.md"
)

ignored_directory_names = frozenset(
    {
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
)

task_identity_keys = (
    "task_id",
    "id",
    "record_id",
)

task_title_keys = (
    "title",
    "name",
    "summary",
    "objective",
    "label",
)

task_status_keys = (
    "status",
    "state",
    "phase",
)

task_owner_keys = (
    "owner",
    "task_owner",
    "assignee",
    "domain",
)

dependency_keys = frozenset(
    {
        "depends_on",
        "dependencies",
        "dependency_ids",
        "blocked_by",
        "requires",
        "prerequisites",
    }
)

absolute_path_pattern = re.compile(
    r"/root/savant-runtime"
    r"(?:/[A-Za-z0-9._@%+=:,~\-]+)*"
)

pathish_key_pattern = re.compile(
    r"(?:^|_)(?:path|file|target|source|root|location)(?:$|_)",
    re.IGNORECASE,
)


class AtlasError(
    RuntimeError
):
    pass


def normalize_json_value(
    value: Any,
) -> Any:
    if isinstance(
        value,
        bytes,
    ):
        return {
            "$binary_hex":
                value.hex(),
        }

    if isinstance(
        value,
        bytearray,
    ):
        return {
            "$binary_hex":
                bytes(
                    value
                ).hex(),
        }

    if isinstance(
        value,
        memoryview,
    ):
        return {
            "$binary_hex":
                value.tobytes().hex(),
        }

    if isinstance(
        value,
        dict,
    ):
        return {
            str(
                key
            ):
                normalize_json_value(
                    member
                )
            for key, member
            in sorted(
                value.items(),
                key=lambda item:
                    str(
                        item[
                            0
                        ]
                    ),
            )
        }

    if isinstance(
        value,
        (
            list,
            tuple,
        ),
    ):
        return [
            normalize_json_value(
                member
            )
            for member
            in value
        ]

    if isinstance(
        value,
        set,
    ):
        normalized_members = [
            normalize_json_value(
                member
            )
            for member
            in value
        ]

        return sorted(
            normalized_members,
            key=lambda member:
                json.dumps(
                    member,
                    ensure_ascii=False,
                    sort_keys=True,
                    separators=(
                        ",",
                        ":",
                    ),
                ),
        )

    if isinstance(
        value,
        Path,
    ):
        return str(
            value
        )

    if (
        value is None
        or isinstance(
            value,
            (
                str,
                int,
                float,
                bool,
            ),
        )
    ):
        return value

    raise AtlasError(
        "unsupported canonical JSON value type: "
        + type(
            value
        ).__name__
    )


def canonical_json_bytes(
    value: Any,
) -> bytes:
    return json.dumps(
        normalize_json_value(
            value
        ),
        ensure_ascii=False,
        sort_keys=True,
        separators=(
            ",",
            ":",
        ),
    ).encode(
        "utf-8"
    )


def digest(
    value: Any,
) -> str:
    return hashlib.sha256(
        canonical_json_bytes(
            value
        )
    ).hexdigest()


def file_sha256(
    path: Path,
) -> str | None:
    if not path.is_file():
        return None

    hasher = hashlib.sha256()

    with path.open(
        "rb"
    ) as handle:
        while True:
            chunk = handle.read(
                1024 * 1024
            )

            if not chunk:
                break

            hasher.update(
                chunk
            )

    return hasher.hexdigest()


def stable_id(
    namespace: str,
    substance: Any,
) -> str:
    return (
        f"{namespace}:"
        + digest(
            substance
        )[
            :24
        ]
    )


def relative_runtime_path(
    path: Path,
) -> str:
    if path == runtime_root:
        return "."

    return str(
        path.relative_to(
            runtime_root
        )
    )


def region_for_path(
    relative_path: str,
) -> str:
    if relative_path == ".":
        return "savant"

    first = relative_path.split(
        "/",
        1,
    )[0]

    explicit = {
        "authority":
            "authority",
        "authority_graph":
            "authority",
        "canon-system":
            "authority",
        "ontology":
            "ontology",
        "lexicon":
            "lexicon",
        "runtime":
            "runtime",
        "assurance":
            "assurance",
        "commands":
            "commands",
        "bin":
            "commands",
        "vault":
            "vault",
        "docs":
            "knowledge",
        "tools":
            "tools",
        "tests":
            "assurance",
        "edifices":
            "ontology",
    }

    return explicit.get(
        first,
        first,
    )


def authority_class_for_path(
    relative_path: str,
) -> str:
    if relative_path == ".":
        return "runtime-root"

    parts = relative_path.split(
        "/"
    )

    if (
        parts[0]
        in {
            "authority",
            "authority_graph",
            "canon-system",
        }
    ):
        return "authority-bearing"

    if (
        "authority_graph"
        in parts
        or "canon"
        in parts
        or "authority"
        in parts
    ):
        return "authority-adjacent"

    if parts[0] == "runtime":
        return "runtime-state"

    if parts[0] == "assurance":
        return "assurance"

    return "implementation"


def scan_runtime_nodes() -> tuple[
    list[dict[str, Any]],
    list[dict[str, Any]],
    dict[str, str],
]:
    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []
    node_by_path: dict[str, str] = {}

    root_node_id = "runtime:/root/savant-runtime"

    nodes.append(
        {
            "id":
                root_node_id,
            "kind":
                "runtime-root",
            "label":
                "savant-runtime",
            "path":
                str(runtime_root),
            "relative_path":
                ".",
            "region":
                "savant",
            "authority_class":
                "runtime-root",
            "depth":
                0,
            "collapsed_by_policy":
                False,
        }
    )

    node_by_path[str(runtime_root)] = root_node_id

    stack = [runtime_root]

    while stack:
        current = stack.pop()

        try:
            entries = sorted(
                os.scandir(current),
                key=lambda entry: (
                    not entry.is_dir(
                        follow_symlinks=False
                    ),
                    entry.name.casefold(),
                    entry.name,
                ),
            )

        except (
            FileNotFoundError,
            PermissionError,
            OSError,
        ):
            continue

        parent_id = node_by_path.get(
            str(current)
        )

        for entry in entries:
            entry_path = Path(entry.path)

            relative_path = relative_runtime_path(
                entry_path
            )

            is_directory = entry.is_dir(
                follow_symlinks=False
            )

            is_symlink = entry.is_symlink()

            collapsed = (
                is_directory
                and entry.name
                in ignored_directory_names
            )

            node_id = stable_id(
                "runtime",
                {
                    "path":
                        str(entry_path),
                    "kind":
                        (
                            "directory"
                            if is_directory
                            else "file"
                        ),
                },
            )

            node_by_path[
                str(entry_path)
            ] = node_id

            node = {
                "id":
                    node_id,
                "kind":
                    (
                        "directory"
                        if is_directory
                        else "file"
                    ),
                "label":
                    entry.name,
                "path":
                    str(entry_path),
                "relative_path":
                    relative_path,
                "region":
                    region_for_path(
                        relative_path
                    ),
                "authority_class":
                    authority_class_for_path(
                        relative_path
                    ),
                "depth":
                    len(
                        entry_path.relative_to(
                            runtime_root
                        ).parts
                    ),
                "collapsed_by_policy":
                    collapsed,
                "symlink":
                    is_symlink,
            }

            nodes.append(node)

            if parent_id:
                edges.append(
                    {
                        "id":
                            stable_id(
                                "edge",
                                {
                                    "type":
                                        "contains",
                                    "source":
                                        parent_id,
                                    "target":
                                        node_id,
                                },
                            ),
                        "kind":
                            "contains",
                        "source":
                            parent_id,
                        "target":
                            node_id,
                    }
                )

            if (
                is_directory
                and not collapsed
                and not is_symlink
            ):
                stack.append(
                    entry_path
                )

    nodes.sort(
        key=lambda node: (
            node.get("depth", 0),
            node.get(
                "relative_path",
                "",
            ),
            node["id"],
        )
    )

    edges.sort(
        key=lambda edge: (
            edge["kind"],
            edge["source"],
            edge["target"],
            edge["id"],
        )
    )

    return (
        nodes,
        edges,
        node_by_path,
    )


def load_json_object(
    path: Path,
) -> dict[str, Any] | None:
    if not path.is_file():
        return None

    with path.open(
        "r",
        encoding="utf-8",
    ) as handle:
        value = json.load(handle)

    if not isinstance(
        value,
        dict,
    ):
        raise AtlasError(
            f"expected JSON object: {path}"
        )

    return value


def first_scalar(
    value: dict[str, Any],
    keys: Iterable[str],
) -> str | None:
    for key in keys:
        candidate = value.get(key)

        if isinstance(
            candidate,
            (
                str,
                int,
                float,
            ),
        ):
            text = str(
                candidate
            ).strip()

            if text:
                return text

    return None


def looks_like_task(
    value: dict[str, Any],
) -> bool:
    keys = {
        str(key).casefold()
        for key
        in value.keys()
    }

    has_identity = any(
        key in keys
        for key
        in task_identity_keys
    )

    has_task_semantics = any(
        key in keys
        for key
        in (
            "title",
            "status",
            "state",
            "objective",
            "dependencies",
            "depends_on",
            "blocked_by",
            "priority",
            "task",
        )
    )

    explicit_kind = first_scalar(
        value,
        (
            "kind",
            "type",
            "record_type",
            "entity_type",
        ),
    )

    return (
        (
            isinstance(
                explicit_kind,
                str,
            )
            and "task"
            in explicit_kind.casefold()
        )
        or (
            has_identity
            and has_task_semantics
        )
    )


def walk_objects(
    value: Any,
    pointer: str = "",
):
    if isinstance(
        value,
        dict,
    ):
        yield (
            pointer or "/",
            value,
        )

        for key in sorted(
            value.keys(),
            key=lambda candidate:
                str(candidate),
        ):
            escaped = (
                str(key)
                .replace(
                    "~",
                    "~0",
                )
                .replace(
                    "/",
                    "~1",
                )
            )

            yield from walk_objects(
                value[key],
                pointer
                + "/"
                + escaped,
            )

    elif isinstance(
        value,
        list,
    ):
        for index, member in enumerate(
            value
        ):
            yield from walk_objects(
                member,
                pointer
                + "/"
                + str(index),
            )


def normalize_dependency_values(
    value: Any,
) -> list[str]:
    result: list[str] = []

    if isinstance(
        value,
        str,
    ):
        candidate = value.strip()

        if candidate:
            result.append(candidate)

    elif isinstance(
        value,
        (
            int,
            float,
        ),
    ):
        result.append(
            str(value)
        )

    elif isinstance(
        value,
        list,
    ):
        for member in value:
            result.extend(
                normalize_dependency_values(
                    member
                )
            )

    elif isinstance(
        value,
        dict,
    ):
        identity = first_scalar(
            value,
            task_identity_keys,
        )

        if identity:
            result.append(identity)

    return sorted(set(result))


def extract_dependencies(
    value: dict[str, Any],
) -> list[str]:
    result: list[str] = []

    for key, member in value.items():
        if (
            str(key).casefold()
            in dependency_keys
        ):
            result.extend(
                normalize_dependency_values(
                    member
                )
            )

    return sorted(set(result))


def collect_strings(
    value: Any,
):
    if isinstance(
        value,
        str,
    ):
        yield value

    elif isinstance(
        value,
        dict,
    ):
        for key in sorted(
            value.keys(),
            key=lambda candidate:
                str(candidate),
        ):
            member = value[key]

            if (
                pathish_key_pattern.search(
                    str(key)
                )
                and isinstance(
                    member,
                    str,
                )
            ):
                yield member

            yield from collect_strings(
                member
            )

    elif isinstance(
        value,
        list,
    ):
        for member in value:
            yield from collect_strings(
                member
            )


def explicit_runtime_paths(
    value: Any,
) -> list[str]:
    paths: set[str] = set()

    for text in collect_strings(value):
        for match in absolute_path_pattern.findall(
            text
        ):
            candidate = match.rstrip(
                ".,;:)]}>\"'"
            )

            if candidate:
                paths.add(candidate)

    return sorted(paths)


def normalize_task(
    raw: dict[str, Any],
    source: str,
    pointer: str,
) -> dict[str, Any]:
    identity = first_scalar(
        raw,
        task_identity_keys,
    )

    if not identity:
        identity = stable_id(
            "task-substance",
            raw,
        )

    title = first_scalar(
        raw,
        task_title_keys,
    ) or identity

    return {
        "identity":
            identity,
        "title":
            title,
        "status":
            first_scalar(
                raw,
                task_status_keys,
            ),
        "owner":
            first_scalar(
                raw,
                task_owner_keys,
            ),
        "dependencies":
            extract_dependencies(raw),
        "explicit_paths":
            explicit_runtime_paths(raw),
        "source":
            source,
        "source_pointer":
            pointer,
        "substance_digest":
            digest(raw),
    }


def tasks_from_masterplan(
    masterplan: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    if masterplan is None:
        return []

    return [
        normalize_task(
            value,
            "masterplan",
            pointer,
        )
        for pointer, value
        in walk_objects(masterplan)
        if looks_like_task(value)
    ]


def quote_identifier(
    value: str,
) -> str:
    return (
        '"'
        + value.replace(
            '"',
            '""',
        )
        + '"'
    )


def tasks_from_sqlite() -> list[
    dict[str, Any]
]:
    if not task_store_path.is_file():
        return []

    connection = sqlite3.connect(
        "file:"
        + str(task_store_path)
        + "?mode=ro",
        uri=True,
    )

    connection.row_factory = sqlite3.Row

    tasks: list[
        dict[str, Any]
    ] = []

    try:
        connection.execute(
            "PRAGMA query_only = ON"
        )

        tables = [
            row[0]
            for row
            in connection.execute(
                """
                SELECT name
                FROM sqlite_master
                WHERE type = 'table'
                ORDER BY name
                """
            )
            if isinstance(
                row[0],
                str,
            )
            and any(
                token
                in row[0].casefold()
                for token
                in (
                    "task",
                    "work",
                    "milestone",
                )
            )
        ]

        for table in tables:
            quoted = quote_identifier(
                table
            )

            columns = [
                row[1]
                for row
                in connection.execute(
                    f"PRAGMA table_info({quoted})"
                )
            ]

            normalized_columns = {
                str(column).casefold()
                for column
                in columns
            }

            if not any(
                key
                in normalized_columns
                for key
                in task_identity_keys
            ):
                continue

            raw_rows = [
                {
                    key:
                        row[key]
                    for key
                    in row.keys()
                }
                for row
                in connection.execute(
                    f"SELECT * FROM {quoted}"
                )
            ]

            raw_rows.sort(
                key=lambda raw:
                    canonical_json_bytes(
                        raw
                    )
            )

            for row_index, raw in enumerate(
                raw_rows
            ):
                if not looks_like_task(raw):
                    continue

                tasks.append(
                    normalize_task(
                        raw,
                        "niche-sqlite:"
                        + table,
                        "/"
                        + table
                        + "/"
                        + str(row_index),
                    )
                )

    finally:
        connection.close()

    return tasks


def merge_tasks(
    *collections,
) -> list[dict[str, Any]]:
    grouped = defaultdict(list)

    for collection in collections:
        for task in collection:
            grouped[
                task["identity"]
            ].append(task)

    result = []

    for identity in sorted(grouped):
        candidates = sorted(
            grouped[identity],
            key=lambda task: (
                0
                if task["source"]
                == "masterplan"
                else 1,
                task["source"],
                task["source_pointer"],
                task["substance_digest"],
            ),
        )

        primary = dict(
            candidates[0]
        )

        primary["sources"] = [
            {
                "source":
                    candidate["source"],
                "source_pointer":
                    candidate[
                        "source_pointer"
                    ],
                "substance_digest":
                    candidate[
                        "substance_digest"
                    ],
            }
            for candidate
            in candidates
        ]

        primary["dependencies"] = sorted(
            {
                dependency
                for candidate
                in candidates
                for dependency
                in candidate[
                    "dependencies"
                ]
            }
        )

        primary["explicit_paths"] = sorted(
            {
                path
                for candidate
                in candidates
                for path
                in candidate[
                    "explicit_paths"
                ]
            }
        )

        result.append(primary)

    return result


def nearest_known_runtime_path(
    path: str,
    node_by_path: dict[str, str],
):
    candidate = Path(path)

    while True:
        candidate_text = str(
            candidate
        )

        if candidate_text in node_by_path:
            return (
                candidate_text,
                node_by_path[
                    candidate_text
                ],
            )

        if (
            candidate == runtime_root
            or runtime_root
            not in candidate.parents
        ):
            break

        candidate = candidate.parent

    return (
        None,
        None,
    )


def task_nodes_and_edges(
    tasks: list[dict[str, Any]],
    node_by_path: dict[str, str],
):
    task_nodes = []
    edges = []

    unresolved_region_id = (
        "virtual:unresolved-tasks"
    )

    identity_to_node = {}

    for task in tasks:
        node_id = stable_id(
            "task",
            task["identity"],
        )

        identity_to_node[
            task["identity"]
        ] = node_id

        anchors = []

        for explicit_path in task[
            "explicit_paths"
        ]:
            (
                resolved_path,
                resolved_node_id,
            ) = nearest_known_runtime_path(
                explicit_path,
                node_by_path,
            )

            if resolved_node_id:
                anchors.append(
                    {
                        "requested_path":
                            explicit_path,
                        "resolved_path":
                            resolved_path,
                        "node_id":
                            resolved_node_id,
                        "method":
                            (
                                "exact-path"
                                if resolved_path
                                == explicit_path
                                else
                                "nearest-existing-ancestor"
                            ),
                    }
                )

        deduped_anchors = []

        seen = set()

        for anchor in anchors:
            if anchor["node_id"] in seen:
                continue

            seen.add(
                anchor["node_id"]
            )

            deduped_anchors.append(
                anchor
            )

        placement = (
            "explicit"
            if deduped_anchors
            else "unresolved"
        )

        task_nodes.append(
            {
                "id":
                    node_id,
                "kind":
                    "task",
                "label":
                    task["title"],
                "task_id":
                    task["identity"],
                "status":
                    task["status"],
                "owner":
                    task["owner"],
                "placement":
                    placement,
                "anchors":
                    deduped_anchors,
                "dependencies":
                    task[
                        "dependencies"
                    ],
                "sources":
                    task["sources"],
                "region":
                    (
                        "tasks"
                        if deduped_anchors
                        else
                        "unresolved-tasks"
                    ),
                "authority_class":
                    "task-projection",
            }
        )

        targets = (
            [
                anchor["node_id"]
                for anchor
                in deduped_anchors
            ]
            if deduped_anchors
            else [
                unresolved_region_id
            ]
        )

        for target in targets:
            edges.append(
                {
                    "id":
                        stable_id(
                            "edge",
                            {
                                "type":
                                    "task-anchor",
                                "source":
                                    node_id,
                                "target":
                                    target,
                            },
                        ),
                    "kind":
                        "task-anchor",
                    "source":
                        node_id,
                    "target":
                        target,
                    "placement_method":
                        placement,
                }
            )

    for task in tasks:
        source = identity_to_node.get(
            task["identity"]
        )

        if not source:
            continue

        for dependency in task[
            "dependencies"
        ]:
            target = identity_to_node.get(
                dependency
            )

            if not target:
                continue

            edges.append(
                {
                    "id":
                        stable_id(
                            "edge",
                            {
                                "type":
                                    "task-dependency",
                                "source":
                                    source,
                                "target":
                                    target,
                            },
                        ),
                    "kind":
                        "task-dependency",
                    "source":
                        source,
                    "target":
                        target,
                }
            )

    return (
        sorted(
            task_nodes,
            key=lambda node: (
                node["task_id"],
                node["id"],
            ),
        ),
        sorted(
            edges,
            key=lambda edge: (
                edge["kind"],
                edge["source"],
                edge["target"],
                edge["id"],
            ),
        ),
    )


def enhancement_contract():
    enhancements = (
        "semantic-zoom",
        "deterministic-placement",
        "unresolved-placement-quarantine",
        "authority-lens",
        "task-status-lens",
        "dependency-tracing",
        "provenance-inspection",
        "path-anchoring",
        "nearest-ancestor-recovery",
        "compound-geography",
        "stable-identities",
        "projection-digest",
        "source-fingerprints",
        "read-only-task-store",
        "renderer-separation",
        "progressive-complexity",
        "region-index",
        "authority-class-index",
        "cross-link-overlay",
        "task-source-convergence",
        "offline-core",
        "accessibility-projection",
        "mobile-composition-ready",
        "deep-link-ready",
        "incremental-render-ready",
        "search-index-ready",
        "focus-mode-ready",
        "impact-analysis-ready",
        "minimap-ready",
        "no-second-task-engine",
    )

    return list(enhancements)


def atlas_projection() -> dict[
    str,
    Any,
]:
    (
        runtime_nodes,
        containment_edges,
        node_by_path,
    ) = scan_runtime_nodes()

    masterplan = load_json_object(
        masterplan_path
    )

    tasks = merge_tasks(
        tasks_from_masterplan(
            masterplan
        ),
        tasks_from_sqlite(),
    )

    (
        task_nodes,
        task_edges,
    ) = task_nodes_and_edges(
        tasks,
        node_by_path,
    )

    unresolved_count = sum(
        1
        for node
        in task_nodes
        if node["placement"]
        == "unresolved"
    )

    nodes = runtime_nodes + [
        {
            "id":
                "virtual:unresolved-tasks",
            "kind":
                "virtual-region",
            "label":
                "unresolved task placement",
            "region":
                "unresolved-tasks",
            "authority_class":
                "projection-only",
            "task_count":
                unresolved_count,
        }
    ] + task_nodes

    edges = (
        containment_edges
        + task_edges
    )

    nodes.sort(
        key=lambda node: (
            str(
                node.get(
                    "kind",
                    "",
                )
            ),
            str(
                node.get(
                    "relative_path",
                    "",
                )
            ),
            str(
                node.get(
                    "task_id",
                    "",
                )
            ),
            node["id"],
        )
    )

    edges.sort(
        key=lambda edge: (
            edge["kind"],
            edge["source"],
            edge["target"],
            edge["id"],
        )
    )

    metrics = {
        "node_count":
            len(nodes),
        "edge_count":
            len(edges),
        "task_count":
            len(task_nodes),
        "unresolved_task_count":
            unresolved_count,
    }

    substance = {
        "schema":
            schema_version,
        "authority_effect":
            authority_effect,
        "owner":
            owner,
        "projection_only":
            True,
        "mutation_authority":
            False,
        "root":
            str(runtime_root),
        "metrics":
            metrics,
        "enhancements":
            enhancement_contract(),
        "nodes":
            nodes,
        "edges":
            edges,
    }

    return {
        **substance,
        "projection_digest":
            digest(substance),
    }


def summary_projection() -> dict[
    str,
    Any,
]:
    projection = atlas_projection()

    return {
        "schema":
            "savant.niche.atlas-summary.v1",
        "authority_effect":
            authority_effect,
        "owner":
            owner,
        "projection_only":
            True,
        "mutation_authority":
            False,
        "projection_digest":
            projection[
                "projection_digest"
            ],
        "metrics":
            projection["metrics"],
        "enhancement_count":
            len(
                projection[
                    "enhancements"
                ]
            ),
    }


def self_check() -> dict[
    str,
    Any,
]:
    first = atlas_projection()
    second = atlas_projection()

    if first != second:
        raise AtlasError(
            "atlas projection is not deterministic"
        )

    node_ids = [
        node["id"]
        for node
        in first["nodes"]
    ]

    if len(node_ids) != len(
        set(node_ids)
    ):
        raise AtlasError(
            "duplicate atlas node identity"
        )

    edge_ids = [
        edge["id"]
        for edge
        in first["edges"]
    ]

    if len(edge_ids) != len(
        set(edge_ids)
    ):
        raise AtlasError(
            "duplicate atlas edge identity"
        )

    known = set(node_ids)

    dangling = [
        edge["id"]
        for edge
        in first["edges"]
        if edge["source"]
        not in known
        or edge["target"]
        not in known
    ]

    if dangling:
        raise AtlasError(
            "dangling atlas edges detected"
        )

    return {
        "schema":
            schema_version,
        "authority_effect":
            authority_effect,
        "status":
            "passed",
        "owner":
            owner,
        "projection_only":
            True,
        "mutation_authority":
            False,
        "projection_digest":
            first[
                "projection_digest"
            ],
        **first["metrics"],
        "enhancement_count":
            len(
                first["enhancements"]
            ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "command",
        choices=(
            "project",
            "summary",
            "self-check",
        ),
        nargs="?",
        default="self-check",
    )

    arguments = parser.parse_args()

    try:
        result = (
            atlas_projection()
            if arguments.command
            == "project"
            else summary_projection()
            if arguments.command
            == "summary"
            else self_check()
        )

    except Exception as exc:
        print(
            json.dumps(
                {
                    "schema":
                        schema_version,
                    "authority_effect":
                        authority_effect,
                    "status":
                        "failed",
                    "error":
                        str(exc),
                },
                indent=2,
                sort_keys=True,
            )
        )

        return 1

    print(
        json.dumps(
            result,
            indent=2,
            sort_keys=True,
        )
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
