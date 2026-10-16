from __future__ import annotations

import json
from pathlib import Path

from ENTITY_DISCOVERY import discover_entities


def events():

    registry = {}

    for entity in discover_entities():

        d = Path(entity.path) / "interface" / "events"

        registry[entity.id] = sorted(
            p.name
            for p in d.glob("*")
        ) if d.exists() else []

    return registry


if __name__ == "__main__":
    print(json.dumps(events(), indent=2))
