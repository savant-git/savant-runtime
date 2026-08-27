from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from projectors.base import read_json_safe


def project_graph(
    root: str,
) -> Dict[str, Any]:
    base = Path(root)

    nodes: List[
        Dict[str, Any]
    ] = []

    edges: List[
        Dict[str, Any]
    ] = []

    if not base.exists():
        return {
            "owner": "filament",
            "projection": "graph",
            "root": str(base),
            "nodes": [],
            "edges": [],
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

        node_id = (
            data.get("id")
            or str(
                entity.parent
            )
        )

        nodes.append(
            {
                "id": node_id,
                "type": data.get(
                    "type",
                    "unknown",
                ),
                "path": str(
                    entity.parent
                ),
                "status": data.get(
                    "status",
                    "unknown",
                ),
            }
        )

        parent = (
            entity.parent.parent
        )

        parent_entity = (
            parent
            / "entity.json"
        )

        if parent_entity.exists():
            parent_data = (
                read_json_safe(
                    parent_entity
                )
            )

            edges.append(
                {
                    "source": (
                        parent_data.get(
                            "id"
                        )
                        or str(parent)
                    ),
                    "target": node_id,
                    "relation": (
                        "contains"
                    ),
                }
            )

    return {
        "owner": "filament",
        "projection": "graph",
        "root": str(base),
        "nodes": nodes,
        "edges": edges,
        "authority_effect": "none",
        "rebuildable": True,
    }
