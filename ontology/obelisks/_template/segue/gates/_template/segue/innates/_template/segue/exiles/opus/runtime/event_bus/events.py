from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict
from uuid import uuid4


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def event(
    *,
    type: str,
    source: str,
    payload: Dict[str, Any] | None = None,
    request_id: str | None = None,
    response_id: str | None = None,
    authority: Dict[str, Any] | None = None,
    lineage: Dict[str, Any] | None = None,
    graph: Dict[str, Any] | None = None,
    **extra: Any
) -> Dict[str, Any]:
    return {
        "id": f"evt_{uuid4().hex}",
        "type": type,
        "source": source,
        "request_id": request_id,
        "response_id": response_id,
        "authority": authority or {
            "owner": source,
            "source": "runtime_event_bus"
        },
        "lineage": lineage or {
            "created_by": source,
            "depends_on": [x for x in [request_id, response_id] if x]
        },
        "graph": graph or {
            "source_node": source,
            "relation": "emits_event",
            "target_node": f"event:{type}"
        },
        "payload": payload or {},
        "extra": extra,
        "timestamps": {
            "created_utc": utc_now()
        }
    }
