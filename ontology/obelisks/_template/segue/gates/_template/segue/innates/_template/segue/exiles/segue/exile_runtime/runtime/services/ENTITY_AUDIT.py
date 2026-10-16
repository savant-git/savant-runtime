from __future__ import annotations

import json
from pathlib import Path

from ENTITY_DISCOVERY import discover_entities
from ENTITY_MODEL import entity_to_dict
from ENTITY_GRAPH import build_entity_graph
from ENTITY_VALIDATOR import validate_entities
from ENTITY_RUNTIME_STATUS import runtime_status


OUT = Path("/root/savant-runtime/ontology/entity_audit.json")


def audit():
    entities = [entity_to_dict(e) for e in discover_entities()]
    graph = build_entity_graph()
    validation = validate_entities()
    runtime = runtime_status()

    report = {
        "entities_count": len(entities),
        "entities": entities,
        "graph": graph,
        "validation": validation,
        "runtime": runtime,
    }

    OUT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return OUT


if __name__ == "__main__":
    print(audit())
