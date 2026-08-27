#!/usr/bin/env python3
from __future__ import annotations

import argparse
from collections import Counter
from copy import deepcopy
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys
from typing import Any, Mapping


ROOT = Path(
    os.environ.get(
        "SAVANT_ROOT",
        "/root/savant-runtime",
    )
).expanduser().absolute()

if str(ROOT) not in sys.path:
    sys.path.insert(
        0,
        str(ROOT),
    )


from runtime.lineage.engine import LineageGraph  # noqa: E402
from runtime.lineage.model import stable_hash  # noqa: E402

from runtime.lineage.projection import (  # noqa: E402
    family_projection,
)

from runtime.lineage.registry import (  # noqa: E402
    DEFAULT_ROLE_REGISTRY,
    LineageRoleRegistry,
)


DEFAULT_LINEAGE_GRAPH = (
    ROOT
    / "vault"
    / "lineage"
    / "functional_lineage_graph.json"
)

DEFAULT_RUNTIME_GRAPH = (
    ROOT
    / "vault"
    / "graphs"
    / "runtime_graph.json"
)

DEFAULT_LINEAGE_ENGINE = (
    ROOT
    / "runtime"
    / "palaver"
    / "lineage"
    / "lineage_engine.py"
)


def stable_id(
    value: str,
) -> str:
    return stable_hash(
        value
    )[:16]


def refresh_lineage_projection(
    *,
    root: Path = ROOT,
    role_registry: Path = (
        DEFAULT_ROLE_REGISTRY
    ),
    lineage_engine: Path = (
        DEFAULT_LINEAGE_ENGINE
    ),
    timeout: int = 180,
) -> dict[str, Any]:
    if not lineage_engine.is_file():
        raise FileNotFoundError(
            "lineage compiler missing: "
            f"{lineage_engine}"
        )

    command = [
        sys.executable,
        str(lineage_engine),
        "--root",
        str(root),
        "--roles",
        str(role_registry),
    ]

    process = subprocess.run(
        command,
        cwd=str(root),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=timeout,
        check=False,
    )

    if process.returncode != 0:
        raise RuntimeError(
            "lineage compiler failed\n"
            f"stdout:\n{process.stdout[-6000:]}\n"
            f"stderr:\n{process.stderr[-6000:]}"
        )

    report: dict[str, Any] = {
        "returncode": (
            process.returncode
        ),
        "stdout": (
            process.stdout[-6000:]
        ),
        "stderr": (
            process.stderr[-6000:]
        ),
    }

    stripped = process.stdout.strip()

    if stripped:
        try:
            decoded = json.loads(
                stripped
            )

            if isinstance(
                decoded,
                Mapping,
            ):
                report[
                    "compiler_report"
                ] = dict(
                    decoded
                )

        except json.JSONDecodeError:
            pass

    return report


def load_lineage_graph(
    *,
    lineage_path: Path = (
        DEFAULT_LINEAGE_GRAPH
    ),
    role_registry: Path = (
        DEFAULT_ROLE_REGISTRY
    ),
) -> tuple[
    LineageGraph,
    dict[str, Any],
]:
    if not lineage_path.is_file():
        raise FileNotFoundError(
            "functional lineage graph "
            f"missing: {lineage_path}"
        )

    try:
        payload = json.loads(
            lineage_path.read_text(
                encoding="utf-8"
            )
        )
    except (
        OSError,
        UnicodeError,
        json.JSONDecodeError,
    ) as exc:
        raise RuntimeError(
            "cannot read functional "
            f"lineage graph: {exc}"
        ) from exc

    if not isinstance(
        payload,
        Mapping,
    ):
        raise RuntimeError(
            "functional lineage graph "
            "must be an object"
        )

    registry = (
        LineageRoleRegistry.load(
            role_registry
        )
    )

    graph = (
        LineageGraph.from_projection(
            payload,
            registry=registry,
        )
    )

    return (
        graph,
        dict(payload),
    )


def _normalized_kind(
    payload: Mapping[
        str,
        Any,
    ],
) -> str:
    kind = str(
        payload.get(
            "kind",
            "instance",
        )
    )

    aliases = {
        "filesystem_directory": (
            "directory"
        ),
        "filesystem_file": "file",
    }

    return aliases.get(
        kind,
        kind,
    )


def _authority_flag(
    payload: Mapping[
        str,
        Any,
    ],
) -> bool:
    authority = payload.get(
        "authority"
    )

    if isinstance(
        authority,
        bool,
    ):
        return authority

    if authority not in (
        None,
        "",
        [],
        {},
    ):
        return True

    return (
        _normalized_kind(
            payload
        )
        in {
            "authority",
            "archetype",
            "meta_archetype",
            "ontology",
            "policy",
            "runtime",
            "template",
        }
    )


def _desired_node_id(
    canonical_id: str,
    payload: Mapping[
        str,
        Any,
    ],
) -> str:
    if canonical_id == "fs:.":
        return "savant-runtime"

    if canonical_id.startswith(
        "fs:"
    ):
        legacy_id = payload.get(
            "legacy_id"
        )

        if (
            isinstance(
                legacy_id,
                str,
            )
            and legacy_id.strip()
        ):
            return legacy_id.strip()

    return canonical_id


def projected_node_ids(
    graph: LineageGraph,
) -> dict[str, str]:
    desired = {
        canonical_id: (
            _desired_node_id(
                canonical_id,
                payload,
            )
        )
        for canonical_id, payload
        in graph.nodes.items()
    }

    counts = Counter(
        desired.values()
    )

    result: dict[
        str,
        str,
    ] = {}

    occupied: set[str] = set()

    for canonical_id in sorted(
        graph.nodes
    ):
        candidate = desired[
            canonical_id
        ]

        if (
            counts[candidate] == 1
            and candidate
            not in occupied
        ):
            projected = candidate

        else:
            projected = (
                canonical_id
            )

        if projected in occupied:
            projected = (
                "node:"
                + stable_id(
                    canonical_id
                )
            )

        occupied.add(
            projected
        )

        result[
            canonical_id
        ] = projected

    return result


def _project_ids(
    values: list[str],
    node_ids: Mapping[
        str,
        str,
    ],
) -> list[str]:
    return [
        node_ids.get(
            value,
            value,
        )
        for value in values
    ]


def _node_relationship_ids(
    graph: LineageGraph,
    node_id: str,
) -> list[str]:
    binding_ids = {
        binding.id
        for binding
        in graph.incoming_bindings(
            node_id,
            active_only=False,
        )
    }

    binding_ids.update(
        binding.id
        for binding
        in graph.outgoing_bindings(
            node_id,
            active_only=False,
        )
    )

    return sorted(
        binding_ids
    )


def project_runtime_graph(
    graph: LineageGraph,
    *,
    root: Path = ROOT,
    source_lineage_hash: str = "",
    limit: int = 0,
) -> dict[str, Any]:
    node_ids = projected_node_ids(
        graph
    )

    selected_canonical_ids = sorted(
        graph.nodes
    )

    if limit > 0:
        selected_canonical_ids = (
            selected_canonical_ids[
                :limit
            ]
        )

    selected_set = set(
        selected_canonical_ids
    )

    nodes: list[
        dict[str, Any]
    ] = []

    for canonical_id in (
        selected_canonical_ids
    ):
        payload = graph.nodes[
            canonical_id
        ]

        projected_id = node_ids[
            canonical_id
        ]

        family = family_projection(
            graph,
            canonical_id,
        )

        parent_ids = _project_ids(
            family["parent_ids"],
            node_ids,
        )

        child_ids = _project_ids(
            family["child_ids"],
            node_ids,
        )

        mothers = _project_ids(
            family["mothers"],
            node_ids,
        )

        fathers = _project_ids(
            family["fathers"],
            node_ids,
        )

        daughters = _project_ids(
            family["daughters"],
            node_ids,
        )

        sons = _project_ids(
            family["sons"],
            node_ids,
        )

        dependency_parents = [
            node_ids.get(
                binding.parent,
                binding.parent,
            )
            for binding
            in graph.incoming_bindings(
                canonical_id,
                roles=[
                    "dependency"
                ],
            )
        ]

        metadata = deepcopy(
            dict(
                payload.get(
                    "metadata"
                )
                or {}
            )
        )

        metadata.update({
            "canonical_id": (
                canonical_id
            ),
            "projected_id": (
                projected_id
            ),
            "lineage_placeholder": (
                payload.get(
                    "kind"
                )
                == "reference"
            ),
            "parent_roles": (
                deepcopy(
                    family[
                        "parent_roles"
                    ]
                )
            ),
            "child_roles": (
                deepcopy(
                    family[
                        "child_roles"
                    ]
                )
            ),
            "child_modes": (
                deepcopy(
                    family[
                        "child_modes"
                    ]
                )
            ),
        })

        kind = _normalized_kind(
            payload
        )

        node = {
            "id": projected_id,
            "canonical_id": (
                canonical_id
            ),
            "legacy_id": (
                payload.get(
                    "legacy_id"
                )
            ),
            "label": (
                payload.get(
                    "label"
                )
                or payload.get(
                    "name"
                )
                or projected_id
            ),
            "kind": kind,
            "size": (
                12
                if kind
                in {
                    "directory",
                    "runtime",
                    "ontology",
                    "authority",
                }
                else 7
            ),
            "path": (
                payload.get(
                    "path"
                )
            ),
            "authority": (
                _authority_flag(
                    payload
                )
            ),
            "provenance": (
                deepcopy(
                    payload.get(
                        "provenance"
                    )
                )
            ),
            "lineage": parent_ids,
            "parents": parent_ids,
            "mothers": mothers,
            "fathers": fathers,
            "children": child_ids,
            "daughters": daughters,
            "sons": sons,
            "relationships": (
                _node_relationship_ids(
                    graph,
                    canonical_id,
                )
            ),
            "dependencies": sorted(
                set(
                    dependency_parents
                )
            ),
            "recovery_routes": [],
            "metadata": metadata,
        }

        nodes.append(
            node
        )

    edges: list[
        dict[str, Any]
    ] = []

    role_counts: Counter[
        str
    ] = Counter()

    axis_counts: Counter[
        str
    ] = Counter()

    continuation_counts: Counter[
        str
    ] = Counter()

    bindings = sorted(
        graph.bindings.values(),
        key=lambda binding: (
            graph.registry.get(
                binding.role
            ).precedence,
            binding.order,
            binding.id,
        ),
    )

    for binding in bindings:
        if (
            binding.parent
            not in selected_set
            or binding.child
            not in selected_set
        ):
            continue

        role = graph.registry.get(
            binding.role
        )

        role_counts[
            binding.role
        ] += 1

        axis_counts[
            binding.axis
        ] += 1

        continuation_counts[
            binding.continuation
        ] += 1

        edge_kind = (
            "contains"
            if binding.role
            == "composition"
            else binding.role
        )

        edge = {
            "id": binding.id,
            "source": node_ids.get(
                binding.parent,
                binding.parent,
            ),
            "target": node_ids.get(
                binding.child,
                binding.child,
            ),
            "canonical_source": (
                binding.parent
            ),
            "canonical_target": (
                binding.child
            ),
            "kind": edge_kind,
            "role": binding.role,
            "axis": binding.axis,
            "inverse": role.inverse,
            "continuation": (
                binding.continuation
            ),
            "scope": binding.scope,
            "order": binding.order,
            "status": binding.status,
            "weight": (
                2
                if binding.role
                in {
                    "authority",
                    "composition",
                    "constraint",
                    "pattern",
                    "source",
                }
                else 1
            ),
            "symbolic_parent_alias": (
                graph.registry
                .symbolic_parent_alias(
                    binding.role
                )
            ),
            "symbolic_child_alias": (
                graph.registry
                .symbolic_child_alias(
                    binding.continuation
                )
            ),
            "inheritance": (
                binding
                .inheritance
                .to_dict()
            ),
            "propagation": (
                binding
                .propagation
                .to_dict()
            ),
            "provenance": deepcopy(
                dict(
                    binding.provenance
                )
            ),
            "metadata": deepcopy(
                dict(
                    binding.metadata
                )
            ),
        }

        edges.append(
            edge
        )

    stats = {
        "role_counts": dict(
            sorted(
                role_counts.items()
            )
        ),
        "axis_counts": dict(
            sorted(
                axis_counts.items()
            )
        ),
        "continuation_counts": dict(
            sorted(
                continuation_counts.items()
            )
        ),
        "placeholder_count": sum(
            1
            for node in nodes
            if node[
                "metadata"
            ][
                "lineage_placeholder"
            ]
        ),
        "authority_node_count": sum(
            1
            for node in nodes
            if node["authority"]
        ),
    }

    deterministic_core = {
        "schema": (
            "savant."
            "runtime_graph.v2"
        ),
        "root": str(root),
        "source_lineage_hash": (
            source_lineage_hash
        ),
        "nodes": nodes,
        "edges": edges,
        "stats": stats,
    }

    return {
        "schema": (
            "savant."
            "runtime_graph.v2"
        ),
        "generated_at": (
            datetime.now(
                timezone.utc
            ).isoformat()
        ),
        "root": str(root),
        "source": (
            "functional_lineage_graph"
        ),
        "source_lineage_hash": (
            source_lineage_hash
        ),
        "deterministic_hash": (
            stable_hash(
                deterministic_core
            )
        ),
        "node_count": len(
            nodes
        ),
        "edge_count": len(
            edges
        ),
        "stats": stats,
        "nodes": nodes,
        "edges": edges,
    }


def build_graph(
    limit: int = 0,
    *,
    refresh: bool = True,
    root: Path = ROOT,
    lineage_path: Path = (
        DEFAULT_LINEAGE_GRAPH
    ),
    role_registry: Path = (
        DEFAULT_ROLE_REGISTRY
    ),
    lineage_engine: Path = (
        DEFAULT_LINEAGE_ENGINE
    ),
) -> dict[str, Any]:
    if refresh:
        refresh_lineage_projection(
            root=root,
            role_registry=(
                role_registry
            ),
            lineage_engine=(
                lineage_engine
            ),
        )

    graph, lineage_payload = (
        load_lineage_graph(
            lineage_path=(
                lineage_path
            ),
            role_registry=(
                role_registry
            ),
        )
    )

    return project_runtime_graph(
        graph,
        root=root,
        source_lineage_hash=str(
            lineage_payload.get(
                "deterministic_hash",
                "",
            )
        ),
        limit=max(
            0,
            limit,
        ),
    )


def write_runtime_graph(
    payload: Mapping[
        str,
        Any,
    ],
    output: Path = (
        DEFAULT_RUNTIME_GRAPH
    ),
) -> None:
    output.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    output.write_text(
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


def build_parser(
) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Project the authoritative "
            "functional-lineage graph "
            "into the Palaver runtime "
            "graph compatibility surface."
        )
    )

    parser.add_argument(
        "--root",
        type=Path,
        default=ROOT,
    )

    parser.add_argument(
        "--roles",
        type=Path,
        default=(
            DEFAULT_ROLE_REGISTRY
        ),
    )

    parser.add_argument(
        "--lineage-graph",
        type=Path,
        default=(
            DEFAULT_LINEAGE_GRAPH
        ),
    )

    parser.add_argument(
        "--lineage-engine",
        type=Path,
        default=(
            DEFAULT_LINEAGE_ENGINE
        ),
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=(
            DEFAULT_RUNTIME_GRAPH
        ),
    )

    parser.add_argument(
        "--limit",
        type=int,
        default=0,
    )

    parser.add_argument(
        "--no-refresh",
        action="store_true",
    )

    return parser


def main(
) -> int:
    args = build_parser().parse_args()

    try:
        graph = build_graph(
            limit=args.limit,
            refresh=(
                not args.no_refresh
            ),
            root=(
                args.root
                .expanduser()
                .absolute()
            ),
            lineage_path=(
                args.lineage_graph
                .expanduser()
                .absolute()
            ),
            role_registry=(
                args.roles
                .expanduser()
                .absolute()
            ),
            lineage_engine=(
                args.lineage_engine
                .expanduser()
                .absolute()
            ),
        )

        write_runtime_graph(
            graph,
            args.output
            .expanduser()
            .absolute(),
        )

        print(
            json.dumps(
                {
                    "output": str(
                        args.output
                    ),
                    "schema": graph[
                        "schema"
                    ],
                    "node_count": graph[
                        "node_count"
                    ],
                    "edge_count": graph[
                        "edge_count"
                    ],
                    "source_lineage_hash": (
                        graph[
                            "source_lineage_hash"
                        ]
                    ),
                    "deterministic_hash": (
                        graph[
                            "deterministic_hash"
                        ]
                    ),
                    "stats": graph[
                        "stats"
                    ],
                },
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
        )

        return 0

    except (
        FileNotFoundError,
        OSError,
        RuntimeError,
        ValueError,
    ) as exc:
        print(
            f"runtime graph error: {exc}",
            file=sys.stderr,
        )

        return 1


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
