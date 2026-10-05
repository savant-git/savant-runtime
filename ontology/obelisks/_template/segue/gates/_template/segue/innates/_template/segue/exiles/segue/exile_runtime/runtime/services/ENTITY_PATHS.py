from __future__ import annotations

import json
from pathlib import Path

from ENTITY_DISCOVERY import discover_entities


CANONICAL_AREAS = [
    "apps",
    "authority",
    "cache",
    "canon",
    "composition",
    "dynamic",
    "evolution",
    "facets",
    "graph",
    "interface",
    "introspection",
    "lifecycle",
    "lineage",
    "metrics",
    "observatory",
    "registry",
    "runtime",
    "sessions",
    "state",
    "static",
    "tests",
    "validation",
    "segue",
]


def paths_for(entity):
    base = Path(entity.path)

    return {
        area: str(base / area)
        for area in CANONICAL_AREAS
    }


def all_paths():
    return {
        entity.id: paths_for(entity)
        for entity in discover_entities()
    }


if __name__ == "__main__":
    print(json.dumps(all_paths(), indent=2))
