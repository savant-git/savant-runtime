#!/usr/bin/env bash
set -euo pipefail

ROOT="/root/savant-runtime"
EXILES_ROOT="$ROOT/ontology/obelisks/_template/segue/gates/_template/segue/innates/_template/segue/exiles"
OPUS="$EXILES_ROOT/opus"

mkdir -p \
  "$OPUS/runtime/event_bus" \
  "$OPUS/registry/events" \
  "$OPUS/canon" \
  "$OPUS/graph" \
  "$OPUS/lineage" \
  "$OPUS/observatory/events"

cat > "$OPUS/canon/runtime_event_bus.md" <<'MD'
# RUNTIME EVENT BUS
# STATUS: CANON
# OWNER: OPUS
# PURPOSE: SHARED EVENT STREAM FOR ALL EXILES

All significant runtime actions should emit events.

Events must expose:

- id
- type
- source
- payload
- request_id
- response_id
- lineage
- authority
- graph
- timestamps

Events should not require direct coupling between exiles.
MD

cat > "$OPUS/registry/events/event_types.json" <<'JSON'
{
  "id": "runtime_event_types",
  "owner": "opus",
  "status": "active",
  "events": [
    "speech.started",
    "speech.finished",
    "speech.failed",
    "persona.selected",
    "persona.changed",
    "provider.selected",
    "provider.failed",
    "provider.fallback",
    "api.request",
    "api.response",
    "api.error",
    "memory.read",
    "memory.write",
    "graph.query",
    "graph.result",
    "observatory.metric",
    "registry.lookup",
    "authority.validation",
    "lineage.created"
  ]
}
JSON

cat > "$OPUS/runtime/event_bus/bus.py" <<'PY'
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable, Dict, List

from event_bus.events import event


OPUS_ROOT = Path(__file__).resolve().parents[1]
EVENT_LOG = OPUS_ROOT.parent / "observatory" / "events" / "runtime_events.jsonl"

_SUBSCRIBERS: Dict[str, List[Callable[[Dict[str, Any]], None]]] = {}


def ensure_log() -> None:
    EVENT_LOG.parent.mkdir(parents=True, exist_ok=True)
    EVENT_LOG.touch(exist_ok=True)


def publish(
    *,
    type: str,
    source: str,
    payload: Dict[str, Any] | None = None,
    request_id: str | None = None,
    response_id: str | None = None,
    **extra: Any
) -> Dict[str, Any]:
    ensure_log()

    row = event(
        type=type,
        source=source,
        payload=payload or {},
        request_id=request_id,
        response_id=response_id,
        **extra
    )

    with EVENT_LOG.open("a", encoding="utf-8") as w:
        w.write(json.dumps(row, ensure_ascii=False) + "\n")

    for fn in _SUBSCRIBERS.get(type, []):
        fn(row)

    for fn in _SUBSCRIBERS.get("*", []):
        fn(row)

    return row


def subscribe(type: str, handler: Callable[[Dict[str, Any]], None]) -> None:
    _SUBSCRIBERS.setdefault(type, []).append(handler)


def recent(limit: int = 50) -> List[Dict[str, Any]]:
    ensure_log()

    lines = EVENT_LOG.read_text(encoding="utf-8", errors="replace").splitlines()
    rows = []

    for line in lines[-limit:]:
        try:
            rows.append(json.loads(line))
        except Exception:
            continue

    return rows
PY

cat > "$OPUS/runtime/event_bus/events.py" <<'PY'
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
PY

cat > "$OPUS/runtime/event_bus/__init__.py" <<'PY'
from event_bus.bus import publish, recent, subscribe
PY

cat > "$OPUS/graph/runtime_event_bus.json" <<'JSON'
{
  "id": "opus:runtime_event_bus",
  "type": "runtime_bus",
  "owner": "exile:opus",
  "relation": "coordinates_runtime_events",
  "authority": "runtime_patch",
  "description": "Shared event bus for runtime events emitted by all exiles."
}
JSON

echo "[OK] Runtime event bus installed."
find "$OPUS/runtime/event_bus" "$OPUS/registry/events" "$OPUS/observatory/events" -maxdepth 2 -type f | sort
