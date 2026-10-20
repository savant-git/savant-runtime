
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from iteration_controller import digest, verify


class evidence_error(ValueError):
    pass


def project(
    session: Mapping[str, Any],
) -> dict[str, Any]:
    current = verify(session)
    previous = None
    entries = []

    for index, entry in enumerate(
        current["history"],
        1,
    ):
        if entry["iteration"] != index:
            raise evidence_error(
                "iteration sequence mismatch"
            )

        if entry["previous"] != previous:
            raise evidence_error(
                "iteration lineage mismatch"
            )

        content = dict(entry)
        signature = content.pop("digest", None)

        if signature != digest(content):
            raise evidence_error(
                "iteration digest mismatch"
            )

        execution = entry["execution"]

        if not isinstance(execution, Mapping):
            raise evidence_error(
                "invalid execution evidence"
            )

        entries.append({
            "iteration": index,
            "result": entry["result"],
            "execution": dict(execution),
            "digest": signature,
            "previous_digest": previous,
            "recorded_at": entry["recorded_at"],
        })

        previous = signature

    limit = current["iteration_limit"]

    return {
        "session_id": current["session_id"],
        "goal": current["goal"],
        "state": current["state"],
        "completed_iterations": len(entries),
        "iteration_limit": limit,
        "remaining_iterations": limit - len(entries),
        "progress": len(entries) / limit,
        "latest_result": (
            entries[-1]["result"]
            if entries
            else None
        ),
        "latest_execution": (
            entries[-1]["execution"]
            if entries
            else None
        ),
        "history": entries,
        "session_digest": current["digest"],
    }
