from __future__ import annotations

import hashlib
import json
import math
from datetime import datetime, timezone
from typing import Any, Mapping

schema = "savant://runtime/urge/iteration-controller/1.0.0"

states = frozenset({
    "ready",
    "running",
    "paused",
    "completed",
    "failed",
})


class iteration_error(ValueError):
    pass


def canonical(value: Any) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def digest(value: Any) -> str:
    return hashlib.sha256(
        canonical(value).encode("utf-8")
    ).hexdigest()


def timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def positive_integer(value: Any, name: str) -> int:
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or value < 1
    ):
        raise iteration_error(
            f"{name} must be a positive integer"
        )
    return value


def positive_interval(value: Any) -> float:
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(value)
        or value <= 0
    ):
        raise iteration_error(
            "interval_seconds must be positive and finite"
        )
    return float(value)


def seal(value: Mapping[str, Any]) -> dict[str, Any]:
    result = dict(value)
    result.pop("digest", None)
    result["digest"] = digest(result)
    return result


def verify(value: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise iteration_error("session must be a mapping")

    result = dict(value)
    signature = result.pop("digest", None)

    if signature != digest(result):
        raise iteration_error("session digest mismatch")

    if result.get("schema") != schema:
        raise iteration_error("unsupported schema")

    if result.get("state") not in states:
        raise iteration_error("invalid state")

    goal = result.get("goal")
    if not isinstance(goal, str) or not goal.strip():
        raise iteration_error("invalid goal")

    limit = positive_integer(
        result.get("iteration_limit"),
        "iteration_limit",
    )
    positive_interval(result.get("interval_seconds"))

    history = result.get("history")
    if not isinstance(history, list):
        raise iteration_error("invalid history")

    if len(history) > limit:
        raise iteration_error("iteration limit exceeded")

    for index, entry in enumerate(history, 1):
        if not isinstance(entry, dict):
            raise iteration_error("invalid history entry")
        if entry.get("iteration") != index:
            raise iteration_error("invalid iteration sequence")

    if (
        result["state"] == "completed"
        and len(history) != limit
    ):
        raise iteration_error("incomplete session")

    result["digest"] = signature
    return result


def create(
    *,
    session_id: str,
    goal: str,
    iteration_limit: int,
    interval_seconds: float,
    settings: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    if not isinstance(session_id, str) or not session_id.strip():
        raise iteration_error("session_id is required")

    if not isinstance(goal, str) or not goal.strip():
        raise iteration_error("goal is required")

    limit = positive_integer(
        iteration_limit,
        "iteration_limit",
    )
    interval = positive_interval(interval_seconds)

    if settings is None:
        settings = {}

    if not isinstance(settings, Mapping):
        raise iteration_error("settings must be a mapping")

    return seal({
        "schema": schema,
        "session_id": session_id.strip(),
        "goal": goal.strip(),
        "iteration_limit": limit,
        "interval_seconds": interval,
        "settings": dict(settings),
        "state": "ready",
        "history": [],
        "created_at": timestamp(),
        "updated_at": timestamp(),
    })


def transition(
    session: Mapping[str, Any],
    action: str,
) -> dict[str, Any]:
    current = verify(session)

    transitions = {
        ("ready", "start"): "running",
        ("running", "pause"): "paused",
        ("paused", "resume"): "running",
        ("ready", "fail"): "failed",
        ("running", "fail"): "failed",
        ("paused", "fail"): "failed",
    }

    target = transitions.get((current["state"], action))

    if target is None:
        raise iteration_error("invalid state transition")

    current["state"] = target
    current["updated_at"] = timestamp()
    return seal(current)


def configure(
    session: Mapping[str, Any],
    settings: Mapping[str, Any],
) -> dict[str, Any]:
    current = verify(session)

    if current["state"] not in {"ready", "paused"}:
        raise iteration_error(
            "settings may change only while ready or paused"
        )

    if not isinstance(settings, Mapping):
        raise iteration_error("settings must be a mapping")

    forbidden = {
        "goal",
        "iteration_limit",
        "interval_seconds",
        "session_id",
        "schema",
        "history",
        "state",
        "digest",
    }

    if forbidden.intersection(settings):
        raise iteration_error(
            "session identity and timing are immutable"
        )

    updated = dict(current["settings"])
    updated.update(settings)

    current["settings"] = updated
    current["updated_at"] = timestamp()
    return seal(current)


def record(
    session: Mapping[str, Any],
    *,
    result: Any,
    execution: Mapping[str, Any],
) -> dict[str, Any]:
    current = verify(session)

    if current["state"] != "running":
        raise iteration_error("session is not running")

    if not isinstance(execution, Mapping):
        raise iteration_error("execution evidence is required")

    if not execution:
        raise iteration_error("execution evidence cannot be empty")

    iteration = len(current["history"]) + 1

    if iteration > current["iteration_limit"]:
        raise iteration_error("iteration limit reached")

    previous = (
        current["history"][-1]["digest"]
        if current["history"]
        else None
    )

    entry = {
        "iteration": iteration,
        "previous": previous,
        "result": result,
        "execution": dict(execution),
        "recorded_at": timestamp(),
    }
    entry["digest"] = digest(entry)

    current["history"] = [
        *current["history"],
        entry,
    ]

    if iteration == current["iteration_limit"]:
        current["state"] = "completed"

    current["updated_at"] = timestamp()
    return seal(current)


def next_iteration(
    session: Mapping[str, Any],
) -> dict[str, Any]:
    current = verify(session)

    if current["state"] != "running":
        raise iteration_error("session is not running")

    return {
        "session_id": current["session_id"],
        "goal": current["goal"],
        "iteration": len(current["history"]) + 1,
        "iteration_limit": current["iteration_limit"],
        "interval_seconds": current["interval_seconds"],
        "settings": dict(current["settings"]),
        "previous_result": (
            current["history"][-1]["result"]
            if current["history"]
            else None
        ),
        "previous_digest": (
            current["history"][-1]["digest"]
            if current["history"]
            else None
        ),
    }
