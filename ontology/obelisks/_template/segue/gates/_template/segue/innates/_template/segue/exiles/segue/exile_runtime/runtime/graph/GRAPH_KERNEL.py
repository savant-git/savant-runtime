from __future__ import annotations

import sys
from pathlib import Path

SERVICES = Path(__file__).resolve().parents[1] / "services"

if str(SERVICES) not in sys.path:
    sys.path.insert(0, str(SERVICES))

from ENTITY_GRAPH import build_entity_graph


class GraphKernel:

    def graph(self):
        return build_entity_graph()

    def nodes(self):
        return self.graph()["nodes"]

    def edges(self):
        return self.graph()["edges"]


graph_kernel = GraphKernel()
