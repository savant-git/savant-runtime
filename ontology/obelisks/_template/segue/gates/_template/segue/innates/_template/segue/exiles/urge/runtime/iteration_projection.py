
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from iteration_controller import verify


def project(
    session: Mapping[str, Any],
) -> dict[str, Any]:
    value = verify(session)

    history = value["history"]
    count = len(history)
    limit = value["iteration_limit"]

    return {
        "session_id": value["session_id"],
        "goal": value["goal"],
        "state": value["state"],
        "iteration_limit": limit,
        "completed_iterations": count,
        "remaining_iterations": limit - count,
        "interval_seconds": value["interval_seconds"],
        "progress": count / limit,
        "can_start": value["state"] == "ready",
        "can_pause": value["state"] == "running",
        "can_resume": value["state"] == "paused",
        "can_edit_settings": value["state"] in {
            "ready",
            "paused",
        },
        "timing_locked": True,
        "latest_result": (
            history[-1]["result"]
            if history
            else None
        ),
        "latest_execution": (
            history[-1]["execution"]
            if history
            else None
        ),
        "digest": value["digest"],
        "updated_at": value["updated_at"],
    }


def timeline(
    session: Mapping[str, Any],
) -> list[dict[str, Any]]:
    value = verify(session)

    return [
        {
            "iteration": entry["iteration"],
            "result": entry["result"],
            "execution": entry["execution"],
            "recorded_at": entry["recorded_at"],
            "digest": entry["digest"],
            "previous": entry["previous"],
        }
        for entry in value["history"]
    ]
