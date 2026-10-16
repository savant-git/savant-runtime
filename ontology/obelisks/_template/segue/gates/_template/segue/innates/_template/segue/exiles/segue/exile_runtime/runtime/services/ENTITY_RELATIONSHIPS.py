from __future__ import annotations

import json
from pathlib import Path

from ENTITY_GRAPH import build_entity_graph


def collect_relationships():
    graph = build_entity_graph()

    relationships = {}

    for node in graph["nodes"]:
        relationships[node["id"]] = {
            "in": [],
            "out": [],
        }

    for edge in graph["edges"]:
        source = edge["source"]
        target = edge["target"]

        relationships.setdefault(source, {"in": [], "out": []})
        relationships.setdefault(target, {"in": [], "out": []})

        relationships[source]["out"].append(edge)
        relationships[target]["in"].append(edge)

    return relationships


if __name__ == "__main__":
    print(json.dumps(collect_relationships(), indent=2))
