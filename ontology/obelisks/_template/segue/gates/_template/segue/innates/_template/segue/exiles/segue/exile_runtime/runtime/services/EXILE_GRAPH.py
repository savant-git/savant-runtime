from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
EXILES = ROOT.parent


def build_graph():
    nodes = []
    edges = []

    for exile in sorted(EXILES.iterdir()):
        if not exile.is_dir() or exile.name == "segue":
            continue

        nodes.append({
            "id": f"exile:{exile.name}",
            "type": "exile",
            "path": str(exile),
        })

        edges.append({
            "source": "ontology:exiles",
            "target": f"exile:{exile.name}",
            "relation": "contains",
        })

    nodes.append({
        "id": "runtime:exile_runtime",
        "type": "runtime_layer",
        "path": str(ROOT),
    })

    edges.append({
        "source": "ontology:exiles",
        "target": "runtime:exile_runtime",
        "relation": "governed_by",
    })

    return {
        "nodes": nodes,
        "edges": edges,
    }


if __name__ == "__main__":
    print(json.dumps(build_graph(), indent=2))
