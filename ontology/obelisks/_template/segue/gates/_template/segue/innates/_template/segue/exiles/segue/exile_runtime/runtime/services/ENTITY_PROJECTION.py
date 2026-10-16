from __future__ import annotations

import json
from pathlib import Path

from ENTITY_DISCOVERY import discover_entities


def project_docs():
    rows = []

    for entity in discover_entities():
        rows.append({
            "id": entity.id,
            "type": entity.type,
            "status": entity.status,
            "path": entity.path,
            "purpose": entity.data.get("purpose", ""),
            "rule": entity.data.get("rule", ""),
        })

    return rows


def project_paths():
    return {
        entity.id: entity.path
        for entity in discover_entities()
    }


if __name__ == "__main__":
    print(json.dumps({
        "docs": project_docs(),
        "paths": project_paths(),
    }, indent=2))
