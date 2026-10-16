
from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from typing import Any, Mapping


schema = "savant://runtime/urge/session-timeline/1.0.0"
owner = "exile:urge"


class timeline_error(ValueError):
    pass


def _digest(value: Any) -> str:
    try:
        encoded = json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise timeline_error(
            "timeline must be canonical-json serializable"
        ) from exc

    return hashlib.sha256(encoded).hexdigest()


def _integer(value: Any, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise timeline_error(f"{name} must be an integer")
    return value


def _seal(value: Mapping[str, Any]) -> dict[str, Any]:
    result = deepcopy(dict(value))
    result.pop("digest", None)
    result["digest"] = _digest(result)
    return result


def verify(value: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise timeline_error("timeline must be a mapping")

    current = deepcopy(dict(value))
    recorded = current.pop("digest", None)

    if not isinstance(recorded, str):
        raise timeline_error("timeline digest is missing")

    if recorded != _digest(current):
        raise timeline_error("timeline integrity mismatch")

    if current.get("schema") != schema:
        raise timeline_error("unsupported timeline schema")

    if current.get("owner") != owner:
        raise timeline_error("incorrect timeline owner")

    if current.get("status") not in (
        "ready",
        "running",
        "paused",
        "completed",
    ):
        raise timeline_error("invalid timeline status")

    history = current.get("history")
    active = current.get("active")

    if not isinstance(history, list):
        raise timeline_error("history must be a list")

    if not isinstance(active, list):
        raise timeline_error("active must be a list")

    ids: set[str] = set()

    for record in history:
        if not isinstance(record, dict):
            raise timeline_error("invalid history record")

        identity = record.get("id")
        if not isinstance(identity, str) or not identity:
            raise timeline_error("invalid iteration identity")

        if identity in ids:
            raise timeline_error("duplicate iteration identity")

        ids.add(identity)

    if any(identity not in ids for identity in active):
        raise timeline_error("active timeline has unknown records")

    if len(active) != len(set(active)):
        raise timeline_error("active timeline contains duplicates")

    limit = _integer(current.get("limit"), "limit")

    if limit < 1:
        raise timeline_error("limit must be positive")

    if len(active) > limit:
        raise timeline_error("active timeline exceeds limit")

    return _seal(current)


def create(
    message_id: str,
    *,
    limit: int,
) -> dict[str, Any]:
    if not isinstance(message_id, str) or not message_id.strip():
        raise timeline_error("message_id is required")

    limit = _integer(limit, "limit")

    if limit < 1:
        raise timeline_error("limit must be positive")

    return _seal({
        "schema": schema,
        "owner": owner,
        "message_id": message_id.strip(),
        "limit": limit,
        "status": "ready",
        "history": [],
        "active": [],
        "events": [],
    })


def _transition(
    value: Mapping[str, Any],
    *,
    action: str,
    allowed: tuple[str, ...],
    target: str,
) -> dict[str, Any]:
    current = verify(value)

    if current["status"] not in allowed:
        raise timeline_error(
            f"{action} is not allowed from {current['status']}"
        )

    current["status"] = target
    current["events"].append({
        "sequence": len(current["events"]) + 1,
        "action": action,
        "active": list(current["active"]),
    })

    return _seal(current)


def start(value: Mapping[str, Any]) -> dict[str, Any]:
    return _transition(
        value,
        action="start",
        allowed=("ready",),
        target="running",
    )


def pause(value: Mapping[str, Any]) -> dict[str, Any]:
    return _transition(
        value,
        action="pause",
        allowed=("running",),
        target="paused",
    )


def resume(value: Mapping[str, Any]) -> dict[str, Any]:
    return _transition(
        value,
        action="resume",
        allowed=("paused",),
        target="running",
    )


def complete(value: Mapping[str, Any]) -> dict[str, Any]:
    current = verify(value)

    if len(current["active"]) != current["limit"]:
        raise timeline_error(
            "cannot complete before all iterations exist"
        )

    return _transition(
        current,
        action="complete",
        allowed=("running",),
        target="completed",
    )


def append(
    value: Mapping[str, Any],
    *,
    result: Mapping[str, Any],
    provenance: Mapping[str, Any],
) -> dict[str, Any]:
    current = verify(value)

    if current["status"] != "running":
        raise timeline_error("timeline is not running")

    if len(current["active"]) >= current["limit"]:
        raise timeline_error("iteration limit reached")

    if not isinstance(result, Mapping):
        raise timeline_error("result must be a mapping")

    if not isinstance(provenance, Mapping) or not provenance:
        raise timeline_error("provenance is required")

    identity = f"iteration-{len(current['history']) + 1}"

    record = {
        "id": identity,
        "number": len(current["active"]) + 1,
        "parent": (
            current["active"][-1]
            if current["active"]
            else None
        ),
        "result": deepcopy(dict(result)),
        "provenance": deepcopy(dict(provenance)),
    }

    current["history"].append(record)
    current["active"].append(identity)

    current["events"].append({
        "sequence": len(current["events"]) + 1,
        "action": "append",
        "iteration_id": identity,
    })

    return _seal(current)


def rewind(
    value: Mapping[str, Any],
    *,
    keep: int,
) -> dict[str, Any]:
    current = verify(value)
    keep = _integer(keep, "keep")

    if current["status"] != "paused":
        raise timeline_error("pause before rewinding")

    if not 0 <= keep < len(current["active"]):
        raise timeline_error("invalid rewind position")

    removed = current["active"][keep:]
    current["active"] = current["active"][:keep]

    current["events"].append({
        "sequence": len(current["events"]) + 1,
        "action": "rewind",
        "keep": keep,
        "superseded": removed,
    })

    return _seal(current)


def projection(value: Mapping[str, Any]) -> dict[str, Any]:
    current = verify(value)

    records = {
        record["id"]: record
        for record in current["history"]
    }

    active = [
        deepcopy(records[identity])
        for identity in current["active"]
    ]

    return {
        "schema": schema,
        "message_id": current["message_id"],
        "status": current["status"],
        "limit": current["limit"],
        "completed": len(active),
        "remaining": current["limit"] - len(active),
        "active": active,
        "latest": active[-1] if active else None,
        "superseded_count": (
            len(current["history"]) - len(active)
        ),
        "digest": current["digest"],
    }
