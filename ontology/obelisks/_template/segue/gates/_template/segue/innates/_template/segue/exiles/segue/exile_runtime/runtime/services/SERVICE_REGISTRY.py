from __future__ import annotations

import json
from pathlib import Path

from ENTITY_DISCOVERY import discover_entities


def services():

    registry = {}

    for entity in discover_entities():

        d = Path(entity.path) / "runtime" / "services"

        registry[entity.id] = sorted(
            p.name
            for p in d.glob("*")
            if p.is_file()
        ) if d.exists() else []

    return registry


if __name__ == "__main__":
    print(json.dumps(services(), indent=2))
