from __future__ import annotations

from pathlib import Path
import sys

SERVICES = Path(__file__).resolve().parents[1] / "services"

if str(SERVICES) not in sys.path:
    sys.path.insert(0, str(SERVICES))

from ONTOLOGY_RUNTIME import OntologyRuntime
from ENTITY_VALIDATOR import validate_entities
from ENTITY_GRAPH import build_entity_graph


class Kernel:
    def __init__(self):
        self.runtime = OntologyRuntime()

    def boot(self):
        validation = validate_entities()
        graph = build_entity_graph()

        return {
            "ok": validation["ok"],
            "entities": len(self.runtime.all()),
            "nodes": len(graph["nodes"]),
            "edges": len(graph["edges"]),
            "validation": validation,
        }


kernel = Kernel()


if __name__ == "__main__":
    print(kernel.boot())
