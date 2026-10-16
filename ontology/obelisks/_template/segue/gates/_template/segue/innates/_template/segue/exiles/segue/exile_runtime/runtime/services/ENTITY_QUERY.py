from __future__ import annotations

import json
from ENTITY_DISCOVERY import discover_entities
from ENTITY_MODEL import entity_to_dict


def query_by_type(entity_type: str):
    return [
        entity_to_dict(e)
        for e in discover_entities()
        if e.type == entity_type
    ]


def query_by_id(entity_id: str):
    for entity in discover_entities():
        if entity.id == entity_id:
            return entity_to_dict(entity)
    return None


if __name__ == "__main__":
    print(json.dumps({
        "exiles": query_by_type("exile"),
        "runtime_layers": query_by_type("runtime_layer"),
        "ontology_levels": query_by_type("ontology_level"),
        "segues": query_by_type("segue"),
    }, indent=2))
