from __future__ import annotations

import json
from pathlib import Path

from ENTITY_DISCOVERY import discover_entities


def runtime_status():
    rows = {}

    for entity in discover_entities():
        base = Path(entity.path)
        runtime = base / "runtime"

        rows[entity.id] = {
            "id": entity.id,
            "type": entity.type,
            "runtime_path": str(runtime),
            "exists": runtime.is_dir(),
            "python_files": sorted(str(p) for p in runtime.rglob("*.py")) if runtime.exists() else [],
            "shell_files": sorted(str(p) for p in runtime.rglob("*.sh")) if runtime.exists() else [],
        }

    return rows


if __name__ == "__main__":
    print(json.dumps(runtime_status(), indent=2))
