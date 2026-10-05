from __future__ import annotations

import sys
from pathlib import Path

SERVICES = Path(__file__).resolve().parents[1] / "services"

if str(SERVICES) not in sys.path:
    sys.path.insert(0, str(SERVICES))

from EXILE_AUTHORITY_REGISTRY import collect_authority
from EXILE_CANON_REGISTRY import collect_canon
from EXILE_LINEAGE_REGISTRY import collect_lineage


class KnowledgeKernel:

    def authority(self):
        return collect_authority()

    def canon(self):
        return collect_canon()

    def lineage(self):
        return collect_lineage()

    def all(self):
        return {
            "authority": self.authority(),
            "canon": self.canon(),
            "lineage": self.lineage(),
        }


knowledge_kernel = KnowledgeKernel()
