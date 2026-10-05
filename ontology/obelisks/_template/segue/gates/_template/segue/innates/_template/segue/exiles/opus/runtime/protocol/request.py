from __future__ import annotations

from typing import Any, Dict, List

from protocol.authority import authority as make_authority
from protocol.graph import graph as make_graph
from protocol.lineage import lineage as make_lineage
from protocol.metadata import metadata as make_metadata
from protocol.metadata import new_id, timestamps


def runtime_request(
    *,
    type: str,
    source: str,
    destination: str,
    payload: Dict[str, Any],
    context: Dict[str, Any] | None = None,
    attachments: List[Dict[str, Any]] | None = None,
    authority: Dict[str, Any] | None = None,
    lineage: Dict[str, Any] | None = None,
    graph: Dict[str, Any] | None = None,
    metadata: Dict[str, Any] | None = None,
    id: str | None = None
) -> Dict[str, Any]:
    return {
        "id": id or new_id("req"),
        "type": type,
        "source": source,
        "destination": destination,
        "authority": authority or make_authority(owner=source),
        "lineage": lineage or make_lineage(created_by=source),
        "graph": graph or make_graph(
            source_node=source,
            target_node=destination,
            relation="runtime_request"
        ),
        "context": context or {},
        "payload": payload,
        "attachments": attachments or [],
        "metadata": metadata or make_metadata(),
        "timestamps": timestamps()
    }
