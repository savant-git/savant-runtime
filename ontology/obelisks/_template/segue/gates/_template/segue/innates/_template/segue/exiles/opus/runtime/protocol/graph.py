from __future__ import annotations

from typing import Any, Dict, List


def graph(
    *,
    source_node: str,
    target_node: str,
    relation: str,
    edges: List[Dict[str, Any]] | None = None,
    **extra: Any
) -> Dict[str, Any]:
    return {
        "source_node": source_node,
        "target_node": target_node,
        "relation": relation,
        "edges": edges or [],
        **extra
    }
