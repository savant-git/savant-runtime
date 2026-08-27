from __future__ import annotations

import json
from pathlib import Path

from ENTITY_DISCOVERY import discover_entities


def capabilities():

    registry = {}

    for entity in discover_entities():

        capdir = Path(entity.path) / "registry" / "capabilities"

        registry[entity.id] = sorted(
            p.stem
            for p in capdir.glob("*.json")
        ) if capdir.exists() else []

    return registry


if __name__ == "__main__":
    print(json.dumps(capabilities(), indent=2))
