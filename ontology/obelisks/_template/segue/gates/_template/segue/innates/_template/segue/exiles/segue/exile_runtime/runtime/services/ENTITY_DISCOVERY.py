from __future__ import annotations

import json
from pathlib import Path

from ENTITY_MODEL import entity_to_dict, read_entity


ROOT = Path("/root/savant-runtime/ontology")


def discover_entities(root: Path = ROOT):
    rows = []

    for entity_file in sorted(root.rglob("entity.json")):
        entity = read_entity(entity_file.parent)
        if entity:
            rows.append(entity)

    return rows


if __name__ == "__main__":
    print(json.dumps(
        [entity_to_dict(e) for e in discover_entities()],
        indent=2
    ))
