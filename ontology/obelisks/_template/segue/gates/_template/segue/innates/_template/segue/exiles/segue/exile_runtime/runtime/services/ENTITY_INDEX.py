from __future__ import annotations

import json
from pathlib import Path

from ENTITY_DISCOVERY import discover_entities
from ENTITY_MODEL import entity_to_dict


INDEX = Path("/root/savant-runtime/ontology/entity_index.json")


def build_index():
    rows = [entity_to_dict(e) for e in discover_entities()]

    INDEX.write_text(
        json.dumps(rows, indent=2),
        encoding="utf-8"
    )

    return INDEX


if __name__ == "__main__":
    print(build_index())
