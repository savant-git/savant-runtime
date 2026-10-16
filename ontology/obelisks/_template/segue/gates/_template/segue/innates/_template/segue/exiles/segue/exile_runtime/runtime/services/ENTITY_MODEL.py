from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class Entity:
    id: str
    type: str
    status: str
    path: str
    data: dict[str, Any]


def read_entity(path: Path) -> Entity | None:
    entity_file = path / "entity.json"

    if not entity_file.is_file():
        return None

    data = json.loads(entity_file.read_text(encoding="utf-8"))

    return Entity(
        id=data.get("id", path.name),
        type=data.get("type", "unknown"),
        status=data.get("status", "unknown"),
        path=str(path),
        data=data,
    )


def entity_to_dict(entity: Entity) -> dict[str, Any]:
    return {
        "id": entity.id,
        "type": entity.type,
        "status": entity.status,
        "path": entity.path,
        "data": entity.data,
    }
