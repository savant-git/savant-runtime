from __future__ import annotations

import json
from pathlib import Path


def create_entity(
    path: Path,
    *,
    entity_id: str,
    entity_type: str,
    purpose: str = "",
    status: str = "planned",
):

    data = {
        "id": entity_id,
        "type": entity_type,
        "status": status,
        "purpose": purpose,
    }

    path.mkdir(parents=True, exist_ok=True)

    (path / "entity.json").write_text(
        json.dumps(data, indent=2),
        encoding="utf-8",
    )
