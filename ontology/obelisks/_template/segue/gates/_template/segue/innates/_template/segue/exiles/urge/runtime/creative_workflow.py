from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

try:
    from . import creative_execution
    from . import creative_session
except ImportError:
    import creative_execution
    import creative_session


schema = "savant://runtime/urge/creative-workflow/1.0.0"
owner = "exile:urge"


class creative_workflow_error(ValueError):
    pass


def _text(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise creative_workflow_error(
            f"{name} must be a nonempty string"
        )
    return value.strip()


def _initial_session(
    session: Mapping[str, Any],
) -> bool:
    return (
        session.get("approved") is None
        and not session.get("candidates")
    )


def execute(
    session: Mapping[str, Any],
    *,
    instruction: str,
    opus_execute: Callable[
        [Mapping[str, Any]],
        Mapping[str, Any],
    ],
) -> dict[str, Any]:
    instruction = _text(
        instruction,
        "instruction",
    )

    initial = _initial_session(session)

    if initial and session.get("continuity") is True:
        execution_session = (
            creative_session.set_continuity(
                session,
                False,
            )
        )
    else:
        execution_session = session

    result = creative_execution.execute(
        execution_session,
        instruction=instruction,
        opus_execute=opus_execute,
    )

    if initial and session.get("continuity") is True:
        result["session"] = (
            creative_session.set_continuity(
                result["session"],
                True,
            )
        )

    return {
        "schema": schema,
        "owner": owner,
        "candidate_id": result["candidate_id"],
        "status": result["status"],
        "request": result["request"],
        "session": result["session"],
    }


def approve(
    session: Mapping[str, Any],
    artifact_id: str,
) -> dict[str, Any]:
    artifact_id = _text(
        artifact_id,
        "artifact_id",
    )

    candidate = next(
        (
            item
            for item in session["candidates"]
            if item["artifact_id"] == artifact_id
        ),
        None,
    )

    if candidate is None:
        raise creative_workflow_error(
            "candidate does not exist"
        )

    if candidate["status"] != "pending":
        raise creative_workflow_error(
            "candidate is not pending"
        )

    if session.get("continuity"):
        if candidate["parent"] != session.get("approved"):
            raise creative_workflow_error(
                "candidate baseline is no longer current"
            )

    return creative_execution.approve(
        session,
        artifact_id,
    )


def reject(
    session: Mapping[str, Any],
    artifact_id: str,
) -> dict[str, Any]:
    return creative_execution.reject(
        session,
        _text(artifact_id, "artifact_id"),
    )


def set_continuity(
    session: Mapping[str, Any],
    enabled: bool,
) -> dict[str, Any]:
    return creative_session.set_continuity(
        session,
        enabled,
    )


def approved_artifact(
    session: Mapping[str, Any],
) -> dict[str, Any] | None:
    approved = session.get("approved")

    if approved is None:
        return None

    for candidate in session["candidates"]:
        if candidate["artifact_id"] == approved:
            if candidate["status"] != "approved":
                raise creative_workflow_error(
                    "approved artifact has invalid status"
                )
            return dict(candidate)

    raise creative_workflow_error(
        "approved artifact cannot be resolved"
    )


def candidates(
    session: Mapping[str, Any],
    *,
    status: str | None = None,
) -> list[dict[str, Any]]:
    values = session["candidates"]

    if status is not None:
        values = [
            candidate
            for candidate in values
            if candidate["status"] == status
        ]

    return [
        dict(candidate)
        for candidate in values
    ]
