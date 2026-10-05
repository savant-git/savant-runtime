from __future__ import annotations

import json
from collections import Counter

from ENTITY_DISCOVERY import discover_entities
from ENTITY_VALIDATOR import validate_entities


def summary():
    entities = discover_entities()
    types = Counter(entity.type for entity in entities)
    validation = validate_entities()

    return {
        "entity_count": len(entities),
        "types": dict(sorted(types.items())),
        "validation_ok": validation["ok"],
        "validation_error_count": len(validation["errors"]),
    }


if __name__ == "__main__":
    print(json.dumps(summary(), indent=2))
