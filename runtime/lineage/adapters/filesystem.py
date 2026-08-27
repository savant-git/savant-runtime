#!/usr/bin/env python3
from __future__ import annotations

import os
from pathlib import Path
from typing import Iterable

from ..engine import LineageGraph
from ..references import filesystem_reference_id
from .common import add_binding_once


DEFAULT_SCAN_ROOTS = (
    "runtime",
    "vault",
    "sessions",
    "tests",
    "webui_ultra",
    "webui-nextgen",
    "ontology",
    "authority_graph",
    "canon",
    "canon-system",
    "tools",
    "bin",
)

DEFAULT_IGNORED_NAMES = {
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

DEFAULT_IGNORED_RELATIVE_PATHS = {
    "vault/lineage/functional_lineage_graph.json",
    "vault/lineage/lineage_index.json",
    "vault/graphs/runtime_graph.json",
    "vault/graphs/topology_projection.json",
}


def filesystem_node_id(
    root: Path,
    path: Path,
) -> str:
    return filesystem_reference_id(
        path,
        root=root,
    )


def _ignored(
    root: Path,
    path: Path,
    *,
    ignored_names: set[str],
    ignored_relative_paths: set[str],
) -> bool:
    try:
        relative = path.relative_to(
            root
        )
    except ValueError:
        return True

    if any(
        part in ignored_names
        for part in relative.parts
    ):
        return True

    return (
        relative.as_posix()
        in ignored_relative_paths
    )


def _node_payload(
    root: Path,
    path: Path,
) -> dict:
    relative = (
        "."
        if path == root
        else path.relative_to(
            root
        ).as_posix()
    )

    is_directory = path.is_dir()
    is_symlink = path.is_symlink()
    symlink_target = None

    if is_symlink:
        try:
            symlink_target = str(
                path.readlink()
            )
        except OSError:
            symlink_target = None

    return {
        "id": filesystem_node_id(
            root,
            path,
        ),
        "kind": (
            "filesystem_directory"
            if is_directory
            else "filesystem_file"
        ),
        "label": (
            root.name
            if path == root
            else path.name
        ),
        "path": relative,
        "legacy_id": (
            "savant-runtime"
            if path == root
            else relative
        ),
        "authority": (
            relative.startswith(
                (
                    "canon/",
                    "authority_graph/",
                    "ontology/",
                    "runtime/",
                )
            )
            or relative
            in {
                "canon",
                "authority_graph",
                "ontology",
                "runtime",
            }
        ),
        "provenance": {
            "adapter": "filesystem",
            "root": str(root),
            "path": relative,
        },
        "metadata": {
            "is_directory": is_directory,
            "is_file": path.is_file(),
            "is_symlink": is_symlink,
            "symlink_target": symlink_target,
        },
    }


def _add_path(
    graph: LineageGraph,
    root: Path,
    path: Path,
) -> None:
    node_id = filesystem_node_id(
        root,
        path,
    )

    graph.add_node(
        node_id,
        _node_payload(
            root,
            path,
        ),
    )

    if path == root:
        return

    parent_path = path.parent

    parent_id = filesystem_node_id(
        root,
        parent_path,
    )

    if parent_id not in graph.nodes:
        graph.add_node(
            parent_id,
            _node_payload(
                root,
                parent_path,
            ),
        )

    add_binding_once(
        graph,
        parent=parent_id,
        child=node_id,
        role="composition",
        continuation=(
            "preserving"
            if path.is_dir()
            else "projecting"
        ),
        scope="filesystem",
        provenance={
            "created_by": (
                "filesystem_adapter"
            ),
            "source_files": [
                str(path)
            ],
        },
        metadata={
            "projection": (
                "filesystem_hierarchy"
            ),
            "legacy_edge_kind": (
                "contains"
            ),
        },
        inheritance={
            "mode": "reference",
            "fields": [],
            "exclude": [],
            "conflict_policy": (
                "child_wins"
            ),
        },
        reference_root=root,
    )


def ingest_filesystem(
    graph: LineageGraph,
    root: Path | str,
    *,
    scan_roots: Iterable[
        str
    ] = DEFAULT_SCAN_ROOTS,
    ignored_names: Iterable[
        str
    ] = DEFAULT_IGNORED_NAMES,
    ignored_relative_paths: Iterable[
        str
    ] = DEFAULT_IGNORED_RELATIVE_PATHS,
    limit: int = 0,
) -> int:
    filesystem_root = Path(
        root
    ).expanduser().absolute()

    if not filesystem_root.is_dir():
        raise FileNotFoundError(
            "filesystem lineage root "
            f"missing: {filesystem_root}"
        )

    ignored_name_set = set(
        ignored_names
    )

    ignored_path_set = set(
        ignored_relative_paths
    )

    count = 0

    _add_path(
        graph,
        filesystem_root,
        filesystem_root,
    )

    count += 1

    for root_name in scan_roots:
        top = (
            filesystem_root
            / root_name
        )

        if (
            not top.exists()
            or _ignored(
                filesystem_root,
                top,
                ignored_names=(
                    ignored_name_set
                ),
                ignored_relative_paths=(
                    ignored_path_set
                ),
            )
        ):
            continue

        _add_path(
            graph,
            filesystem_root,
            top,
        )

        count += 1

        if (
            limit
            and count >= limit
        ):
            return count

        if (
            not top.is_dir()
            or top.is_symlink()
        ):
            continue

        for (
            current_text,
            directory_names,
            file_names,
        ) in os.walk(
            top,
            topdown=True,
            followlinks=False,
        ):
            current = Path(
                current_text
            )

            directory_names[:] = sorted(
                name
                for name
                in directory_names
                if not _ignored(
                    filesystem_root,
                    current / name,
                    ignored_names=(
                        ignored_name_set
                    ),
                    ignored_relative_paths=(
                        ignored_path_set
                    ),
                )
            )

            for name in directory_names:
                path = (
                    current
                    / name
                )

                _add_path(
                    graph,
                    filesystem_root,
                    path,
                )

                count += 1

                if (
                    limit
                    and count >= limit
                ):
                    return count

            for name in sorted(
                file_names
            ):
                path = (
                    current
                    / name
                )

                if _ignored(
                    filesystem_root,
                    path,
                    ignored_names=(
                        ignored_name_set
                    ),
                    ignored_relative_paths=(
                        ignored_path_set
                    ),
                ):
                    continue

                _add_path(
                    graph,
                    filesystem_root,
                    path,
                )

                count += 1

                if (
                    limit
                    and count >= limit
                ):
                    return count

    return count
