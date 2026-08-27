#!/usr/bin/env python3

import json
from pathlib import Path

ROOT = Path.home() / "savant-runtime"

REGISTRY = {
    "graph": {
        "title": "Graph Observatory",
        "api": "/api/graph",
        "kind": "topology",
        "authority": True,
    },
    "authority": {
        "title": "Authority Observatory",
        "api": "/api/observatory/authority",
        "kind": "authority",
        "authority": True,
    },
    "lineage": {
        "title": "Lineage Observatory",
        "api": "/api/observatory/lineage",
        "kind": "lineage",
        "authority": True,
    },
    "search": {
        "title": "Search Observatory",
        "api": "/api/observatory/search",
        "kind": "discovery",
        "authority": False,
    },
}

out = (
    ROOT
    / "vault"
    / "registry"
    / "observatory_registry.json"
)

out.parent.mkdir(
    parents=True,
    exist_ok=True
)

out.write_text(
    json.dumps(
        REGISTRY,
        indent=2
    )
)

print(out)
