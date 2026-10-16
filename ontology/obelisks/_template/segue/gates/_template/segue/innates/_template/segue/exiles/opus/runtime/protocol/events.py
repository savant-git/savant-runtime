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
