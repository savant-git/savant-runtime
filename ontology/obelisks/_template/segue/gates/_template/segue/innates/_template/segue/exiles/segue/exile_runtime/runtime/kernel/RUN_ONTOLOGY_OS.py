from __future__ import annotations

from ONTOLOGY_OS import ontology_os

state = ontology_os.boot()

print("ONTOLOGY_OS_BOOT")
print("OK:", state["kernel"]["ok"])
print("ENTITIES:", state["kernel"]["entities"])
print("NODES:", state["graph"]["nodes"])
print("EDGES:", state["graph"]["edges"])
