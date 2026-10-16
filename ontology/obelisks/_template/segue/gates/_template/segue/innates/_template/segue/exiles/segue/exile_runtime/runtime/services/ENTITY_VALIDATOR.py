from __future__ import annotations

import json
from pathlib import Path

from ENTITY_DISCOVERY import discover_entities


REQUIRED_OBJECT_DIRS = [
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


def validate_entities():
    errors = []

    for entity in discover_entities():
        base = Path(entity.path)

        for rel in REQUIRED_OBJECT_DIRS:
            path = base / rel
            if not path.is_dir():
                errors.append({
                    "entity": entity.id,
                    "type": entity.type,
                    "error": "missing_required_directory",
                    "path": str(path),
                })

    return {
        "ok": not errors,
        "errors": errors,
    }


if __name__ == "__main__":
    print(json.dumps(validate_entities(), indent=2))
