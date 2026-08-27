from __future__ import annotations

import json
from pathlib import Path

from ENTITY_GRAPH import build_entity_graph


def nodes():
    return build_entity_graph()["nodes"]


def edges():
    return build_entity_graph()["edges"]


def neighbors(entity_id: str):
    graph = build_entity_graph()

    out = []

    for edge in graph["edges"]:
        if edge["source"] == entity_id:
            out.append(edge["target"])

        if edge["target"] == entity_id:
            out.append(edge["source"])

    return sorted(set(out))


if __name__ == "__main__":
    graph = build_entity_graph()

    print(json.dumps({
        "nodes": len(graph["nodes"]),
        "edges": len(graph["edges"]),
        "graph": graph,
    }, indent=2))
