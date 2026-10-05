from __future__ import annotations

from typing import Any, Dict, List


def lineage(
    *,
    created_by: str,
    depends_on: List[str] | None = None,
    derived_from: List[str] | None = None,
    **extra: Any
) -> Dict[str, Any]:
    return {
        "created_by": created_by,
        "depends_on": depends_on or [],
        "derived_from": derived_from or [],
        **extra
    }
