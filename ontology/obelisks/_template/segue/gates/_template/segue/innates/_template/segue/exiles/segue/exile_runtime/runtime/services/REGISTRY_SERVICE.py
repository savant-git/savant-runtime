from __future__ import annotations

import json
from pathlib import Path

from ENTITY_DISCOVERY import discover_entities


def collect_registry_area(area: str):
    rows = {}

    for entity in discover_entities():
        base = Path(entity.path) / "registry" / area

        rows[entity.id] = {
            "entity": entity.id,
            "type": entity.type,
            "registry_area": area,
            "path": str(base),
            "exists": base.is_dir(),
            "files": sorted(str(p) for p in base.glob("*")) if base.exists() else [],
        }

    return rows


if __name__ == "__main__":
    report = {
        "capabilities": collect_registry_area("capabilities"),
        "contracts": collect_registry_area("contracts"),
        "defaults": collect_registry_area("defaults"),
        "interfaces": collect_registry_area("interfaces"),
        "manifests": collect_registry_area("manifests"),
        "schemas": collect_registry_area("schemas"),
        "templates": collect_registry_area("templates"),
        "versions": collect_registry_area("versions"),
    }

    print(json.dumps(report, indent=2))
