from __future__ import annotations

import sys
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]

for sub in [
    "services",
    "graph",
    "registry",
    "knowledge",
    "observatory",
    "execution",
]:
    p = BASE / sub
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from KERNEL import kernel
from GRAPH_KERNEL import graph_kernel
from REGISTRY_KERNEL import registry_kernel
from KNOWLEDGE_KERNEL import knowledge_kernel
from OBSERVATORY_KERNEL import observatory_kernel


class OntologyOS:

    def boot(self):
        observatory_kernel.emit("ontology_os.boot.started")

        state = {
            "kernel": kernel.boot(),
            "graph": {
                "nodes": len(graph_kernel.nodes()),
                "edges": len(graph_kernel.edges()),
            },
            "registry": registry_kernel.all(),
            "knowledge": knowledge_kernel.all(),
        }

        observatory_kernel.emit("ontology_os.boot.completed", {
            "entities": state["kernel"]["entities"],
            "nodes": state["graph"]["nodes"],
            "edges": state["graph"]["edges"],
            "ok": state["kernel"]["ok"],
        })

        return state


ontology_os = OntologyOS()


if __name__ == "__main__":
    print(ontology_os.boot())
