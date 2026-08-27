#!/usr/bin/env python3
from __future__ import annotations

from collections import (
    Counter,
    defaultdict,
    deque,
)
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys
from typing import (
    Any,
    Mapping,
)


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


from runtime.lineage.model import stable_hash  # noqa: E402

from runtime.palaver.graph.runtime_graph_index import (  # noqa: E402
    RuntimeGraphIndex,
)


GRAPH = (
    ROOT
    / "vault"
    / "graphs"
    / "runtime_graph.json"
)

OUT = (
    ROOT
    / "vault"
    / "graphs"
    / "topology_projection.json"
)


def _weak_components(
    index: RuntimeGraphIndex,
) -> list[list[str]]:
    unvisited = set(
        index.node_ids()
    )

    components: list[
        list[str]
    ] = []

    while unvisited:
        start = min(
            unvisited
        )

        queue = deque([
            start
        ])

        component: set[str] = {
            start
        }

        unvisited.remove(
            start
        )

        while queue:
            current = (
                queue.popleft()
            )

            for neighbor in (
                index.neighbors(
                    current
                )
            ):
                if neighbor not in unvisited:
                    continue

                unvisited.remove(
                    neighbor
                )

                component.add(
                    neighbor
                )

                queue.append(
                    neighbor
                )

        components.append(
            sorted(
                component
            )
        )

    components.sort(
        key=lambda component: (
            -len(
                component
            ),
            component[0],
        )
    )

    return components


def compile_topology(
    graph_payload: Mapping[
        str,
        Any,
    ],
) -> dict[str, Any]:
    index = RuntimeGraphIndex(
        graph_payload
    )

    nodes = index.node_records()
    edges = index.edge_records()

    kind_counts = Counter(
        str(
            node.get(
                "kind",
                "unknown",
            )
        )
        for node in nodes
    )

    role_counts = Counter(
        str(
            edge.get(
                "role",
                "generic",
            )
        )
        for edge in edges
    )

    axis_counts = Counter(
        str(
            edge.get(
                "axis",
                "unspecified",
            )
        )
        for edge in edges
    )

    continuation_counts = Counter(
        str(
            edge.get(
                "continuation",
                "neutral",
            )
        )
        for edge in edges
    )

    scope_counts = Counter(
        str(
            edge.get(
                "scope",
                "global",
            )
        )
        for edge in edges
    )

    roots = [
        node_id
        for node_id
        in index.node_ids()
        if not index.incoming_edges(
            node_id
        )
    ]

    leaves = [
        node_id
        for node_id
        in index.node_ids()
        if not index.outgoing_edges(
            node_id
        )
    ]

    role_roots: dict[
        str,
        list[str],
    ] = {}

    role_leaves: dict[
        str,
        list[str],
    ] = {}

    for role in sorted(
        role_counts
    ):
        participating: set[str] = set()

        incoming_by_node: dict[
            str,
            int,
        ] = defaultdict(int)

        outgoing_by_node: dict[
            str,
            int,
        ] = defaultdict(int)

        for edge in edges:
            if edge.get(
                "role"
            ) != role:
                continue

            source = str(
                edge["source"]
            )

            target = str(
                edge["target"]
            )

            participating.add(
                source
            )

            participating.add(
                target
            )

            outgoing_by_node[
                source
            ] += 1

            incoming_by_node[
                target
            ] += 1

        role_roots[
            role
        ] = sorted(
            node_id
            for node_id
            in participating
            if incoming_by_node[
                node_id
            ] == 0
        )

        role_leaves[
            role
        ] = sorted(
            node_id
            for node_id
            in participating
            if outgoing_by_node[
                node_id
            ] == 0
        )

    authority_nodes = sorted(
        str(
            node["id"]
        )
        for node in nodes
        if node.get(
            "authority",
            False,
        )
    )

    placeholder_nodes = sorted(
        str(
            node["id"]
        )
        for node in nodes
        if (
            isinstance(
                node.get(
                    "metadata"
                ),
                Mapping,
            )
            and node[
                "metadata"
            ].get(
                "lineage_placeholder",
                False,
            )
        )
    )

    family_counts = {
        "nodes_with_mothers": sum(
            1
            for node in nodes
            if node.get(
                "mothers"
            )
        ),
        "nodes_with_fathers": sum(
            1
            for node in nodes
            if node.get(
                "fathers"
            )
        ),
        "nodes_with_daughters": sum(
            1
            for node in nodes
            if node.get(
                "daughters"
            )
        ),
        "nodes_with_sons": sum(
            1
            for node in nodes
            if node.get(
                "sons"
            )
        ),
    }

    components = _weak_components(
        index
    )

    self_loops = sorted(
        str(
            edge["id"]
        )
        for edge in edges
        if edge.get(
            "source"
        )
        == edge.get(
            "target"
        )
    )

    deterministic_core = {
        "schema": (
            "savant."
            "topology_projection.v2"
        ),
        "source_runtime_hash": (
            index.deterministic_hash
        ),
        "node_count": len(
            nodes
        ),
        "edge_count": len(
            edges
        ),
        "authority_nodes": (
            authority_nodes
        ),
        "placeholder_nodes": (
            placeholder_nodes
        ),
        "kinds": sorted(
            kind_counts
        ),
        "kind_counts": dict(
            sorted(
                kind_counts.items()
            )
        ),
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
        "scope_counts": dict(
            sorted(
                scope_counts.items()
            )
        ),
        "roots": roots,
        "leaves": leaves,
        "role_roots": role_roots,
        "role_leaves": role_leaves,
        "family_counts": (
            family_counts
        ),
        "component_count": len(
            components
        ),
        "components": components,
        "self_loops": self_loops,
    }

    return {
        "schema": (
            "savant."
            "topology_projection.v2"
        ),
        "generated_at": (
            datetime.now(
                timezone.utc
            ).isoformat()
        ),
        "source": (
            "runtime_graph"
        ),
        "source_runtime_hash": (
            index.deterministic_hash
        ),
        "source_lineage_hash": (
            index.source_lineage_hash
        ),
        "deterministic_hash": (
            stable_hash(
                deterministic_core
            )
        ),
        **{
            key: value
            for key, value
            in deterministic_core.items()
            if key
            not in {
                "schema",
                "source_runtime_hash",
            }
        },
    }


def main(
) -> int:
    if not GRAPH.is_file():
        print(
            "{}"
        )

        return 1

    graph_payload = json.loads(
        GRAPH.read_text(
            encoding="utf-8"
        )
    )

    payload = compile_topology(
        graph_payload
    )

    OUT.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    OUT.write_text(
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    print(
        json.dumps(
            {
                "output": str(
                    OUT
                ),
                "schema": payload[
                    "schema"
                ],
                "node_count": (
                    payload[
                        "node_count"
                    ]
                ),
                "edge_count": (
                    payload[
                        "edge_count"
                    ]
                ),
                "component_count": (
                    payload[
                        "component_count"
                    ]
                ),
                "deterministic_hash": (
                    payload[
                        "deterministic_hash"
                    ]
                ),
            },
            indent=2,
            sort_keys=True,
        )
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
