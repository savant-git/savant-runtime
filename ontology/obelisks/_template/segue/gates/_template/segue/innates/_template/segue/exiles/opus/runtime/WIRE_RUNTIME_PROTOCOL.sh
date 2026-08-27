#!/usr/bin/env bash
set -euo pipefail

ROOT="/root/savant-runtime"
EXILES_ROOT="$ROOT/ontology/obelisks/_template/segue/gates/_template/segue/innates/_template/segue/exiles"

OPUS="$EXILES_ROOT/opus"
ENVOY="$EXILES_ROOT/envoy"
PALAVER="$EXILES_ROOT/palaver"

mkdir -p \
  "$OPUS/runtime/bridge" \
  "$OPUS/registry/bridges" \
  "$OPUS/canon" \
  "$OPUS/graph" \
  "$ENVOY/registry/contracts" \
  "$PALAVER/registry/contracts"

cat > "$OPUS/canon/runtime_protocol_wiring.md" <<'MD'
# RUNTIME PROTOCOL WIRING
# STATUS: CANON
# OWNER: OPUS
# PURPOSE: CONNECT RUNTIME REQUEST/RESPONSE PROTOCOL TO ACTIVE EXILES

All active runtime calls must pass through the Runtime Request Protocol.

Palaver owns conversation.
Envoy owns persona and voice intent.
Opus owns API orchestration.

Runtime flow:

Palaver -> Runtime Request -> Envoy
Envoy -> Runtime Request -> Opus
Opus -> Runtime Response -> Envoy
Envoy -> Runtime Response -> Palaver

Every transition should emit runtime events.
MD

cat > "$OPUS/registry/bridges/palaver_envoy_opus_runtime_bridge.json" <<'JSON'
{
  "id": "palaver_envoy_opus_runtime_bridge",
  "type": "runtime_bridge",
  "status": "active",
  "owner": "opus",
  "participants": [
    "palaver",
    "envoy",
    "opus"
  ],
  "protocol": "runtime_request_v1",
  "event_bus": "runtime_event_bus",
  "rules": [
    "Palaver does not call external voice APIs.",
    "Envoy does not orchestrate external APIs.",
    "Opus does not own persona identity.",
    "All cross-exile calls expose authority, lineage, graph, and timestamps."
  ]
}
JSON

cat > "$OPUS/runtime/bridge/runtime_bridge.py" <<'PY'
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict

OPUS_RUNTIME = Path(__file__).resolve().parents[1]

if str(OPUS_RUNTIME) not in sys.path:
    sys.path.insert(0, str(OPUS_RUNTIME))

from event_bus.bus import publish
from protocol.request import runtime_request
from protocol.response import runtime_response


def make_request(
    *,
    type: str,
    source: str,
    destination: str,
    payload: Dict[str, Any],
    context: Dict[str, Any] | None = None
) -> Dict[str, Any]:
    req = runtime_request(
        type=type,
        source=source,
        destination=destination,
        payload=payload,
        context=context or {}
    )

    publish(
        type="runtime.request.created",
        source=source,
        payload={
            "request_id": req["id"],
            "request_type": type,
            "destination": destination
        },
        request_id=req["id"]
    )

    return req


def make_response(
    *,
    request: Dict[str, Any],
    ok: bool,
    payload: Dict[str, Any],
    source: str | None = None,
    destination: str | None = None,
    error: str | None = None
) -> Dict[str, Any]:
    res = runtime_response(
        request=request,
        ok=ok,
        payload=payload,
        source=source,
        destination=destination,
        error=error
    )

    publish(
        type="runtime.response.created",
        source=res["source"],
        payload={
            "request_id": request.get("id"),
            "response_id": res["id"],
            "ok": ok,
            "error": error
        },
        request_id=request.get("id"),
        response_id=res["id"]
    )

    return res


def send_request(req: Dict[str, Any]) -> Dict[str, Any]:
    publish(
        type="runtime.request.sent",
        source=req["source"],
        payload={
            "request_id": req["id"],
            "destination": req["destination"],
            "request_type": req["type"]
        },
        request_id=req["id"]
    )
    return req


def receive_request(req: Dict[str, Any], receiver: str) -> Dict[str, Any]:
    publish(
        type="runtime.request.received",
        source=receiver,
        payload={
            "request_id": req["id"],
            "source": req["source"],
            "request_type": req["type"]
        },
        request_id=req["id"]
    )
    return req


def send_response(res: Dict[str, Any]) -> Dict[str, Any]:
    publish(
        type="runtime.response.sent",
        source=res["source"],
        payload={
            "response_id": res["id"],
            "request_id": res.get("request_id"),
            "destination": res["destination"],
            "ok": res["ok"]
        },
        request_id=res.get("request_id"),
        response_id=res["id"]
    )
    return res


def receive_response(res: Dict[str, Any], receiver: str) -> Dict[str, Any]:
    publish(
        type="runtime.response.received",
        source=receiver,
        payload={
            "response_id": res["id"],
            "request_id": res.get("request_id"),
            "source": res["source"],
            "ok": res["ok"]
        },
        request_id=res.get("request_id"),
        response_id=res["id"]
    )
    return res
PY

cat > "$OPUS/runtime/bridge/__init__.py" <<'PY'
from bridge.runtime_bridge import (
    make_request,
    make_response,
    receive_request,
    receive_response,
    send_request,
    send_response,
)
PY

cat > "$ENVOY/registry/contracts/runtime_protocol_contract.json" <<'JSON'
{
  "id": "envoy_runtime_protocol_contract",
  "type": "runtime_contract",
  "status": "active",
  "owner": "opus",
  "consumer": "envoy",
  "protocol": "runtime_request_v1",
  "rule": "Envoy receives and emits runtime request/response objects for cross-exile calls."
}
JSON

cat > "$PALAVER/registry/contracts/runtime_protocol_contract.json" <<'JSON'
{
  "id": "palaver_runtime_protocol_contract",
  "type": "runtime_contract",
  "status": "active",
  "owner": "opus",
  "consumer": "palaver",
  "protocol": "runtime_request_v1",
  "rule": "Palaver uses runtime request/response objects when delegating to Envoy or Opus."
}
JSON

cat > "$OPUS/graph/runtime_protocol_bridge.json" <<'JSON'
{
  "id": "opus:runtime_protocol_bridge",
  "type": "runtime_bridge",
  "owner": "exile:opus",
  "source": "exile:palaver",
  "target": "exile:envoy",
  "relation": "normalizes_cross_exile_runtime_calls",
  "authority": "runtime_patch"
}
JSON

touch "$OPUS/runtime/bridge/__init__.py"

echo "[OK] Runtime protocol bridge installed."
find "$OPUS/runtime/bridge" "$OPUS/registry/bridges" "$OPUS/graph" -maxdepth 2 -type f | sort
