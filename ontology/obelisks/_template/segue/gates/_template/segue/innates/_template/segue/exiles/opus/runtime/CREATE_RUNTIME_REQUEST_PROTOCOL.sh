#!/usr/bin/env bash
set -euo pipefail

ROOT="/root/savant-runtime"
EXILES_ROOT="$ROOT/ontology/obelisks/_template/segue/gates/_template/segue/innates/_template/segue/exiles"
OPUS="$EXILES_ROOT/opus"

mkdir -p \
  "$OPUS/runtime/protocol" \
  "$OPUS/canon" \
  "$OPUS/registry/protocol" \
  "$OPUS/graph" \
  "$OPUS/authority" \
  "$OPUS/lineage"

cat > "$OPUS/canon/runtime_request_protocol.md" <<'MD'
# RUNTIME REQUEST PROTOCOL
# STATUS: CANON
# OWNER: OPUS
# PURPOSE: SHARED REQUEST/RESPONSE ABI FOR ALL EXILES

All exiles must communicate through a shared runtime request/response object.

The protocol exposes:

- id
- type
- source
- destination
- authority
- lineage
- graph
- context
- payload
- attachments
- metadata
- timestamps

No exile should depend on another exile's private internal format.
MD

cat > "$OPUS/registry/protocol/runtime_request_schema.json" <<'JSON'
{
  "id": "runtime_request_schema",
  "type": "schema",
  "owner": "opus",
  "status": "active",
  "required": [
    "id",
    "type",
    "source",
    "destination",
    "payload",
    "timestamps"
  ],
  "fields": {
    "id": "string",
    "type": "string",
    "source": "string",
    "destination": "string",
    "authority": "object",
    "lineage": "object",
    "graph": "object",
    "context": "object",
    "payload": "object",
    "attachments": "array",
    "metadata": "object",
    "timestamps": "object"
  }
}
JSON

cat > "$OPUS/runtime/protocol/metadata.py" <<'PY'
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict
from uuid import uuid4


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_id(prefix: str = "req") -> str:
    return f"{prefix}_{uuid4().hex}"


def timestamps() -> Dict[str, str]:
    now = utc_now()
    return {
        "created_utc": now,
        "updated_utc": now
    }


def metadata(**values: Any) -> Dict[str, Any]:
    return {
        "runtime": "savant",
        "protocol": "runtime_request_v1",
        **values
    }
PY

cat > "$OPUS/runtime/protocol/authority.py" <<'PY'
from __future__ import annotations

from typing import Any, Dict


def authority(
    *,
    owner: str,
    source: str = "runtime",
    confidence: str = "confirmed",
    policy: str = "authority_before_inference",
    **extra: Any
) -> Dict[str, Any]:
    return {
        "owner": owner,
        "source": source,
        "confidence": confidence,
        "policy": policy,
        **extra
    }
PY

cat > "$OPUS/runtime/protocol/lineage.py" <<'PY'
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
PY

cat > "$OPUS/runtime/protocol/graph.py" <<'PY'
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
PY

cat > "$OPUS/runtime/protocol/attachments.py" <<'PY'
from __future__ import annotations

from typing import Any, Dict


def attachment(
    *,
    id: str,
    type: str,
    uri: str,
    mime_type: str | None = None,
    role: str | None = None,
    **extra: Any
) -> Dict[str, Any]:
    return {
        "id": id,
        "type": type,
        "uri": uri,
        "mime_type": mime_type,
        "role": role,
        **extra
    }
PY

cat > "$OPUS/runtime/protocol/request.py" <<'PY'
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
PY

cat > "$OPUS/runtime/protocol/response.py" <<'PY'
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
PY

cat > "$OPUS/runtime/protocol/events.py" <<'PY'
from __future__ import annotations

from typing import Any, Dict

from protocol.metadata import new_id, timestamps


def runtime_event(
    *,
    type: str,
    source: str,
    payload: Dict[str, Any] | None = None,
    request_id: str | None = None,
    response_id: str | None = None,
    **extra: Any
) -> Dict[str, Any]:
    return {
        "id": new_id("evt"),
        "type": type,
        "source": source,
        "request_id": request_id,
        "response_id": response_id,
        "payload": payload or {},
        "extra": extra,
        "timestamps": timestamps()
    }
PY

cat > "$OPUS/runtime/protocol/validation.py" <<'PY'
from __future__ import annotations

from typing import Any, Dict, Tuple


REQUEST_REQUIRED = [
    "id",
    "type",
    "source",
    "destination",
    "payload",
    "timestamps"
]


def validate_request(obj: Dict[str, Any]) -> Tuple[bool, list[str]]:
    missing = [k for k in REQUEST_REQUIRED if k not in obj]
    return not missing, missing
PY

touch "$OPUS/runtime/__init__.py"
touch "$OPUS/runtime/protocol/__init__.py"

echo "[OK] Runtime request protocol installed."
find "$OPUS/runtime/protocol" -maxdepth 1 -type f | sort
