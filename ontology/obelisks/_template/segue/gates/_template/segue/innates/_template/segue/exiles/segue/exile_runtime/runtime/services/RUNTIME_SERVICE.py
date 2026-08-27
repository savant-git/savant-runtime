from __future__ import annotations

import json
from pathlib import Path

from ENTITY_DISCOVERY import discover_entities


def runtime_files():
    rows = {}

    for entity in discover_entities():
        runtime = Path(entity.path) / "runtime"

        rows[entity.id] = {
            "runtime": str(runtime),
            "exists": runtime.is_dir(),
            "python": sorted(str(p) for p in runtime.rglob("*.py")) if runtime.exists() else [],
            "shell": sorted(str(p) for p in runtime.rglob("*.sh")) if runtime.exists() else [],
        }

    return rows


if __name__ == "__main__":
    print(json.dumps(runtime_files(), indent=2))
