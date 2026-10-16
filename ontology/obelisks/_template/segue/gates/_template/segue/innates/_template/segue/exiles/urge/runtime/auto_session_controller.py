
from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

from . import auto_iteration
from . import creative_execution
from . import creative_session


schema = "savant://runtime/urge/auto-session-controller/1.0.0"
owner = "exile:urge"


class auto_session_controller_error(ValueError):
    pass


def _validated(
    session: Mapping[str, Any],
) -> dict[str, Any]:
    if not isinstance(session, Mapping):
        raise auto_session_controller_error(
            "session must be a mapping"
        )

    current = dict(session)

    if current.get("schema") != creative_session.schema:
        raise auto_session_controller_error(
            "unsupported session schema"
        )

    if current.get("owner") != creative_session.owner:
        raise auto_session_controller_error(
            "invalid session owner"
        )

    expected = current.pop("digest", None)

    if expected != creative_session.digest(current):
        raise auto_session_controller_error(
            "session digest mismatch"
        )

    current["digest"] = expected
    return current


def _pending(
    session: Mapping[str, Any],
) -> list[dict[str, Any]]:
    candidates = session.get("candidates")

    if not isinstance(candidates, list):
        raise auto_session_controller_error(
            "invalid candidate collection"
        )

    return [
        dict(candidate)
        for candidate in candidates
        if candidate.get("status") == "pending"
    ]


def create(
    *,
    session_id: str,
    brief: str,
    continuity: bool = True,
) -> dict[str, Any]:
    if not isinstance(continuity, bool):
        raise auto_session_controller_error(
            "continuity must be boolean"
        )

    return creative_session.create(
        session_id=session_id,
        brief=brief,
        continuity=continuity,
    )


def preview(
    session: Mapping[str, Any],
    *,
    objective: str | None = None,
    preserve_identity: bool = True,
) -> dict[str, Any]:
    current = _validated(session)

    if _pending(current):
        raise auto_session_controller_error(
            "resolve pending candidates before "
            "starting another iteration"
        )

    return auto_iteration.plan(
        current,
        objective=objective,
        preserve_identity=preserve_identity,
    )


def iterate(
    session: Mapping[str, Any],
    *,
    opus_execute: Callable[
        [Mapping[str, Any]],
        Mapping[str, Any],
    ],
    objective: str | None = None,
    preserve_identity: bool = True,
) -> dict[str, Any]:
    current = _validated(session)

    if _pending(current):
        raise auto_session_controller_error(
            "a candidate is awaiting review"
        )

    if not callable(opus_execute):
        raise auto_session_controller_error(
            "opus_execute must be callable"
        )

    result = auto_iteration.execute(
        current,
        opus_execute=opus_execute,
        objective=objective,
        preserve_identity=preserve_identity,
    )

    updated = _validated(result["session"])
    pending = _pending(updated)

    if len(pending) != 1:
        raise auto_session_controller_error(
            "expected exactly one pending candidate"
        )

    if pending[0]["artifact_id"] != result["candidate_id"]:
        raise auto_session_controller_error(
            "candidate identity mismatch"
        )

    return {
        "schema": schema,
        "owner": owner,
        "status": "pending_approval",
        "candidate_id": result["candidate_id"],
        "plan": result["plan"],
        "session": updated,
    }


def review(
    session: Mapping[str, Any],
    *,
    artifact_id: str,
    approve: bool,
) -> dict[str, Any]:
    current = _validated(session)

    if not isinstance(approve, bool):
        raise auto_session_controller_error(
            "approve must be boolean"
        )

    if not isinstance(artifact_id, str) or not artifact_id:
        raise auto_session_controller_error(
            "artifact_id must be nonempty"
        )

    pending = _pending(current)

    if len(pending) != 1:
        raise auto_session_controller_error(
            "exactly one pending candidate is required"
        )

    if pending[0]["artifact_id"] != artifact_id:
        raise auto_session_controller_error(
            "artifact_id does not match pending candidate"
        )

    if approve:
        updated = creative_execution.approve(
            current,
            artifact_id,
        )
    else:
        updated = creative_execution.reject(
            current,
            artifact_id,
        )

    updated = _validated(updated)

    return {
        "schema": schema,
        "owner": owner,
        "status": "approved" if approve else "rejected",
        "artifact_id": artifact_id,
        "session": updated,
    }


def state(
    session: Mapping[str, Any],
) -> dict[str, Any]:
    current = _validated(session)
    pending = _pending(current)

    return {
        "schema": schema,
        "owner": owner,
        "session_id": current["session_id"],
        "session_digest": current["digest"],
        "approved_artifact_id": current["approved"],
        "candidate_count": len(current["candidates"]),
        "decision_count": len(current["decisions"]),
        "pending_artifact_ids": [
            candidate["artifact_id"]
            for candidate in pending
        ],
        "can_iterate": not pending,
    }


__all__ = [
    "auto_session_controller_error",
    "create",
    "iterate",
    "owner",
    "preview",
    "review",
    "schema",
    "state",
]
