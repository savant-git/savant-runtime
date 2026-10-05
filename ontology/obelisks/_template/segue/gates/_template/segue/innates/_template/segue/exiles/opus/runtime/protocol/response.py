from __future__ import annotations

from typing import Any, Dict, List

from protocol.authority import authority as make_authority
from protocol.graph import graph as make_graph
from protocol.lineage import lineage as make_lineage
from protocol.metadata import metadata as make_metadata
from protocol.metadata import new_id, timestamps


def runtime_response(
    *,
    request: Dict[str, Any],
    ok: bool,
    payload: Dict[str, Any],
    source: str | None = None,
    destination: str | None = None,
    attachments: List[Dict[str, Any]] | None = None,
    error: str | None = None,
    metadata: Dict[str, Any] | None = None
) -> Dict[str, Any]:
    src = source or request.get("destination")
    dst = destination or request.get("source")

    return {
        "id": new_id("res"),
        "type": "runtime_response",
        "request_id": request.get("id"),
        "source": src,
        "destination": dst,
        "ok": ok,
        "error": error,
        "authority": make_authority(owner=src),
        "lineage": make_lineage(
            created_by=src,
            depends_on=[request.get("id")]
        ),
        "graph": make_graph(
            source_node=src,
            target_node=dst,
            relation="runtime_response"
        ),
        "payload": payload,
        "attachments": attachments or [],
        "metadata": metadata or make_metadata(),
        "timestamps": timestamps()
    }
