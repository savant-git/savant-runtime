from __future__ import annotations

import json
from pathlib import Path

from ENTITY_DISCOVERY import discover_entities


def contracts():

    registry = {}

    for entity in discover_entities():

        d = Path(entity.path) / "registry" / "contracts"

        registry[entity.id] = sorted(
            p.stem
            for p in d.glob("*.json")
        ) if d.exists() else []

    return registry


if __name__ == "__main__":
    print(json.dumps(contracts(), indent=2))
