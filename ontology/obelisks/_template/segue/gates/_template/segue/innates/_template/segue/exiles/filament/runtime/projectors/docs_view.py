from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List


def read_json_safe(
    path: Path,
) -> Dict[str, Any]:
    try:
        value = json.loads(
            path.read_text(
                encoding="utf-8"
            )
        )
    except (
        OSError,
        UnicodeDecodeError,
        json.JSONDecodeError,
    ):
        return {}

    if not isinstance(
        value,
        dict,
    ):
        return {}

    return value


def project_docs(
    root: str,
) -> Dict[str, Any]:
    base = Path(root)

    rows: List[
        Dict[str, Any]
    ] = []

    if not base.exists():
        return {
            "owner": "filament",
            "projection": "docs",
            "root": str(base),
            "entities": [],
            "authority_effect": "none",
            "rebuildable": True,
        }

    for entity in sorted(
        base.rglob(
            "entity.json"
        )
    ):
        data = read_json_safe(
            entity
        )

        if not data:
            continue

        rows.append(
            {
                "id": data.get(
                    "id"
                ),
                "type": data.get(
                    "type"
                ),
                "status": data.get(
                    "status"
                ),
                "purpose": data.get(
                    "purpose",
                    "",
                ),
                "path": str(
                    entity.parent
                ),
            }
        )

    return {
        "owner": "filament",
        "projection": "docs",
        "root": str(base),
        "entities": rows,
        "authority_effect": "none",
        "rebuildable": True,
    }
