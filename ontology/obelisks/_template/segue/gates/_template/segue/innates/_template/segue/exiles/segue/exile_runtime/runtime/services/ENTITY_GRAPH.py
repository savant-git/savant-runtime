from __future__ import annotations

import json
from pathlib import Path

from ENTITY_DISCOVERY import discover_entities


def build_entity_graph():
    entities = discover_entities()

    nodes = []
    edges = []

    by_path = {Path(e.path): e for e in entities}

    for entity in entities:
        path = Path(entity.path)

        nodes.append({
            "id": entity.id,
            "type": entity.type,
            "status": entity.status,
            "path": entity.path,
        })

        parent = path.parent

        while parent != parent.parent:
            if parent in by_path:
                edges.append({
                    "source": by_path[parent].id,
                    "target": entity.id,
                    "relation": "contains",
                })
                break
            parent = parent.parent

    return {
        "nodes": nodes,
        "edges": edges,
    }


if __name__ == "__main__":
    print(json.dumps(build_entity_graph(), indent=2))
