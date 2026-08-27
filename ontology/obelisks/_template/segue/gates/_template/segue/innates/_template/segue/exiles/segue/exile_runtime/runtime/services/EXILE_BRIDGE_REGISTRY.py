from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
BRIDGES = ROOT / "registry" / "bridges"


def collect_bridges():
    BRIDGES.mkdir(parents=True, exist_ok=True)

    rows = []

    for path in sorted(BRIDGES.glob("*.json")):
        rows.append({
            "id": path.stem,
            "path": str(path),
        })

    return rows


if __name__ == "__main__":
    print(json.dumps(collect_bridges(), indent=2))
