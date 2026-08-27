from __future__ import annotations

from ENTITY_DISCOVERY import discover_entities
from ENTITY_VALIDATOR import validate_entities
from ENTITY_GRAPH import build_entity_graph

print()

print("==========")

print("Entities:", len(discover_entities()))

print()

graph = build_entity_graph()

print("Nodes:", len(graph["nodes"]))
print("Edges:", len(graph["edges"]))

print()

validation = validate_entities()

if validation["ok"]:
    print("Validation: PASS")
else:
    print("Validation: FAIL")
    print(len(validation["errors"]), "issues")

print()

print("==========")
