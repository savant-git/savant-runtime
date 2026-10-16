#!/usr/bin/env python3

from __future__ import annotations

import hashlib
import json
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Mapping


_SECRET_MARKERS = (
    "api_key",
    "apikey",
    "authorization",
    "bearer",
    "credential",
    "password",
    "secret",
    "token",
)


def _is_secret_key(
    key: Any,
) -> bool:
    normalized = str(
        key or ""
    ).strip().lower()

    return any(
        marker in normalized
        for marker in _SECRET_MARKERS
    )


def sanitize(
    value: Any,
) -> Any:
    if isinstance(value, Mapping):
        output: Dict[str, Any] = {}

        for key, item in value.items():
            if _is_secret_key(key):
                output[str(key)] = "[redacted]"
            else:
                output[str(key)] = sanitize(
                    item
                )

        return output

    if isinstance(value, (list, tuple, set)):
        return [
            sanitize(item)
            for item in value
        ]

    if isinstance(
        value,
        (
            str,
            int,
            float,
            bool,
            type(None),
        ),
    ):
        return value

    return str(value)


def _hash(
    value: Any,
) -> str:
    raw = json.dumps(
        sanitize(value),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        default=str,
    ).encode("utf-8")

    return hashlib.sha256(
        raw
    ).hexdigest()


@dataclass(frozen=True)
class LineageEvent:
    sequence: int
    event_type: str
    timestamp: float
    data: Mapping[str, Any]

    def as_dict(self) -> Dict[str, Any]:
        return {
            "sequence": self.sequence,
            "event_type": self.event_type,
            "timestamp": self.timestamp,
            "data": sanitize(
                self.data
            ),
        }


@dataclass
class CognitiveLineage:
    request_id: str = field(
        default_factory=lambda: uuid.uuid4().hex
    )
    owner: str = "opus"
    events: List[LineageEvent] = field(
        default_factory=list
    )

    def record(
        self,
        event_type: str,
        data: Mapping[str, Any] | None = None,
    ) -> LineageEvent:
        event_name = str(
            event_type or ""
        ).strip()

        if not event_name:
            raise ValueError(
                "lineage event requires event_type"
            )

        event = LineageEvent(
            sequence=len(self.events) + 1,
            event_type=event_name,
            timestamp=time.time(),
            data=sanitize(
                dict(data or {})
            ),
        )

        self.events.append(
            event
        )

        return event

    def considered_provider(
        self,
        provider_id: str,
        *,
        model: str | None = None,
        eligible: bool,
        reason: str,
        capabilities: Iterable[str] | None = None,
    ) -> None:
        self.record(
            "provider.considered",
            {
                "provider": provider_id,
                "model": model,
                "eligible": bool(
                    eligible
                ),
                "reason": reason,
                "capabilities": sorted(
                    {
                        str(value)
                        for value
                        in capabilities or ()
                    }
                ),
            },
        )

    def selected_provider(
        self,
        provider_id: str,
        *,
        model: str | None = None,
        strategy: str,
        role: str = "solver",
    ) -> None:
        self.record(
            "provider.selected",
            {
                "provider": provider_id,
                "model": model,
                "strategy": strategy,
                "role": role,
            },
        )

    def provider_result(
        self,
        provider_id: str,
        *,
        model: str | None = None,
        ok: bool,
        latency_ms: float | None = None,
        role: str = "solver",
        error_type: str | None = None,
    ) -> None:
        self.record(
            "provider.result",
            {
                "provider": provider_id,
                "model": model,
                "ok": bool(ok),
                "latency_ms": latency_ms,
                "role": role,
                "error_type": error_type,
            },
        )

    def as_dict(self) -> Dict[str, Any]:
        body = {
            "owner": self.owner,
            "request_id": self.request_id,
            "events": [
                event.as_dict()
                for event in self.events
            ],
        }

        body["lineage_hash"] = _hash(
            body
        )

        return body
