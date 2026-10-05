from __future__ import annotations

import sys
from pathlib import Path

SERVICES = Path(__file__).resolve().parents[1] / "services"

if str(SERVICES) not in sys.path:
    sys.path.insert(0, str(SERVICES))

from REGISTRY_SERVICE import collect_registry_area


class RegistryKernel:

    def area(self, name: str):
        return collect_registry_area(name)

    def all(self):
        return {
            name: self.area(name)
            for name in [
                "capabilities",
                "contracts",
                "defaults",
                "interfaces",
                "manifests",
                "schemas",
                "templates",
                "versions",
            ]
        }


registry_kernel = RegistryKernel()
