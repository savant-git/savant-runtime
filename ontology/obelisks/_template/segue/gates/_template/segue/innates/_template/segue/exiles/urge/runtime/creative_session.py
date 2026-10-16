from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping


schema = "savant://runtime/urge/creative-session/1.0.0"
owner = "exile:urge"


class creative_session_error(ValueError):
    pass


def canonical(value: Any) -> str:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        raise creative_session_error(
            "value is not canonical-json serializable"
        ) from exc


def digest(value: Any) -> str:
    return hashlib.sha256(
        canonical(value).encode("utf-8")
    ).hexdigest()


def _text(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise creative_session_error(
            f"{name} must be a nonempty string"
        )
    return value.strip()


def _session(value: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise creative_session_error(
            "session must be a mapping"
        )

    result = dict(value)

    if result.get("schema") != schema:
        raise creative_session_error(
            "unsupported session schema"
        )

    if result.get("owner") != owner:
        raise creative_session_error(
            "invalid session owner"
        )

    candidates = result.get("candidates")
    decisions = result.get("decisions")

    if not isinstance(candidates, list):
        raise creative_session_error(
            "candidates must be a list"
        )

    if not isinstance(decisions, list):
        raise creative_session_error(
            "decisions must be a list"
        )

    if not isinstance(
        result.get("continuity"), bool
    ):
        raise creative_session_error(
            "continuity must be boolean"
        )

    expected = result.pop("digest", None)

    if expected != digest(result):
        raise creative_session_error(
            "session digest mismatch"
        )

    result["digest"] = expected
    return result


def _seal(value: dict[str, Any]) -> dict[str, Any]:
    result = dict(value)
    result.pop("digest", None)
    result["digest"] = digest(result)
    return result


def create(
    *,
    brief: str,
    session_id: str,
    continuity: bool = True,
) -> dict[str, Any]:
    return _seal({
        "schema": schema,
        "owner": owner,
        "session_id": _text(
            session_id, "session_id"
        ),
        "brief": _text(brief, "brief"),
        "continuity": bool(continuity),
        "approved": None,
        "candidates": [],
        "decisions": [],
    })


def set_continuity(
    session: Mapping[str, Any],
    enabled: bool,
) -> dict[str, Any]:
    current = _session(session)

    if not isinstance(enabled, bool):
        raise creative_session_error(
            "enabled must be boolean"
        )

    current["continuity"] = enabled
    return _seal(current)


def propose(
    session: Mapping[str, Any],
    *,
    artifact_id: str,
    instruction: str,
    execution: Mapping[str, Any],
) -> dict[str, Any]:
    current = _session(session)

    artifact_id = _text(
        artifact_id, "artifact_id"
    )
    instruction = _text(
        instruction, "instruction"
    )

    if not isinstance(execution, Mapping):
        raise creative_session_error(
            "execution must be a mapping"
        )

    if any(
        item["artifact_id"] == artifact_id
        for item in current["candidates"]
    ):
        raise creative_session_error(
            "artifact_id already exists"
        )

    parent = (
        current["approved"]
        if current["continuity"]
        else None
    )

    candidate = {
        "artifact_id": artifact_id,
        "parent": parent,
        "instruction": instruction,
        "execution": dict(execution),
        "status": "pending",
    }

    candidate["digest"] = digest(candidate)

    current["candidates"] = [
        *current["candidates"],
        candidate,
    ]

    return _seal(current)


def decide(
    session: Mapping[str, Any],
    *,
    artifact_id: str,
    approve: bool,
) -> dict[str, Any]:
    current = _session(session)

    artifact_id = _text(
        artifact_id, "artifact_id"
    )

    if not isinstance(approve, bool):
        raise creative_session_error(
            "approve must be boolean"
        )

    matches = [
        item for item in current["candidates"]
        if item["artifact_id"] == artifact_id
    ]

    if len(matches) != 1:
        raise creative_session_error(
            "candidate not found"
        )

    candidate = matches[0]

    if candidate["status"] != "pending":
        raise creative_session_error(
            "candidate already decided"
        )

    replacement = dict(candidate)
    replacement.pop("digest", None)
    replacement["status"] = (
        "approved" if approve else "rejected"
    )
    replacement["digest"] = digest(replacement)

    current["candidates"] = [
        replacement
        if item["artifact_id"] == artifact_id
        else item
        for item in current["candidates"]
    ]

    current["decisions"] = [
        *current["decisions"],
        {
            "artifact_id": artifact_id,
            "decision": (
                "approve" if approve else "reject"
            ),
        },
    ]

    if approve:
        current["approved"] = artifact_id

    return _seal(current)


def refinement_request(
    session: Mapping[str, Any],
    instruction: str,
) -> dict[str, Any]:
    current = _session(session)

    approved = current["approved"]

    if current["continuity"] and approved is None:
        raise creative_session_error(
            "continuity requires an approved baseline"
        )

    return {
        "schema": (
            "savant://runtime/urge/"
            "creative-refinement-request/1.0.0"
        ),
        "owner": owner,
        "session_id": current["session_id"],
        "brief": current["brief"],
        "instruction": _text(
            instruction, "instruction"
        ),
        "continuity": current["continuity"],
        "baseline_artifact_id": (
            approved if current["continuity"]
            else None
        ),
    }
