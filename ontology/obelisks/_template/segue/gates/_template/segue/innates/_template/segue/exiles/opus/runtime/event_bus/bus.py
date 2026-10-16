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
