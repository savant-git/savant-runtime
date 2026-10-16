
from __future__ import annotations

import hashlib
import json
from collections.abc import Callable, Mapping
from typing import Any

from . import creative_execution


schema = "savant://runtime/urge/auto-iteration/1.0.0"
owner = "exile:urge"

_directions = (
    (
        "form",
        "Improve silhouette, proportion, visual balance, "
        "and recognition at small sizes.",
    ),
    (
        "identity",
        "Strengthen distinctive visual identity while "
        "preserving the defining geometry and character.",
    ),
    (
        "material",
        "Refine surface treatment, material coherence, "
        "light response, and perceptual depth.",
    ),
    (
        "clarity",
        "Remove unnecessary visual complexity and "
        "improve hierarchy, contrast, and legibility.",
    ),
    (
        "craft",
        "Improve edge precision, contour continuity, "
        "spacing, alignment, and overall finish.",
    ),
    (
        "expression",
        "Explore a more distinctive creative expression "
        "without sacrificing recognizability.",
    ),
)


class auto_iteration_error(ValueError):
    pass


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _digest(value: Any) -> str:
    return hashlib.sha256(
        _canonical(value)
    ).hexdigest()


def _required_text(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise auto_iteration_error(
            f"{name} must be nonempty text"
        )
    return value.strip()


def _session_id(session: Mapping[str, Any]) -> str:
    return _required_text(
        session.get("session_id"),
        "session_id",
    )


def _candidate_count(session: Mapping[str, Any]) -> int:
    candidates = session.get("candidates")

    if not isinstance(candidates, list):
        raise auto_iteration_error(
            "session candidates must be a list"
        )

    return len(candidates)


def _direction(
    session: Mapping[str, Any],
) -> tuple[str, str]:
    index = _candidate_count(session) % len(_directions)
    return _directions[index]


def plan(
    session: Mapping[str, Any],
    *,
    objective: str | None = None,
    preserve_identity: bool = True,
) -> dict[str, Any]:
    if not isinstance(session, Mapping):
        raise auto_iteration_error(
            "session must be a mapping"
        )

    session_id = _session_id(session)
    brief = _required_text(
        session.get("brief"),
        "brief",
    )

    if objective is not None:
        objective = _required_text(
            objective,
            "objective",
        )

    direction, emphasis = _direction(session)

    continuity = session.get("continuity")

    if not isinstance(continuity, bool):
        raise auto_iteration_error(
            "session continuity must be boolean"
        )

    approved = session.get("approved")

    if continuity and approved is None:
        raise auto_iteration_error(
            "continuity requires an approved baseline"
        )

    instructions = [
        "Create one meaningful design iteration.",
        f"Original design brief: {brief}",
        f"Creative focus: {direction}.",
        emphasis,
    ]

    if objective:
        instructions.append(
            f"Additional objective: {objective}"
        )

    if preserve_identity:
        instructions.append(
            "Preserve defining identity, recognizable "
            "geometry, and established design intent. "
            "Avoid arbitrary changes."
        )

    instructions.extend((
        "Prefer deliberate improvements to decorative "
        "noise or random transformations.",
        "Produce a visually coherent, production-quality "
        "result suitable for direct comparison.",
    ))

    instruction = "\n".join(instructions)

    result = {
        "schema": schema,
        "owner": owner,
        "session_id": session_id,
        "mode": "auto",
        "direction": direction,
        "objective": objective,
        "preserve_identity": preserve_identity,
        "continuity": continuity,
        "baseline_artifact_id": (
            approved if continuity else None
        ),
        "instruction": instruction,
        "selection_policy": "deterministic-round-robin",
        "provider_selection": "existing-executor",
        "approval_policy": "manual",
    }

    result["digest"] = _digest(result)
    return result


def execute(
    session: Mapping[str, Any],
    *,
    opus_execute: Callable[
        [Mapping[str, Any]],
        Mapping[str, Any],
    ],
    objective: str | None = None,
    preserve_identity: bool = True,
) -> dict[str, Any]:
    decision = plan(
        session,
        objective=objective,
        preserve_identity=preserve_identity,
    )

    execution = creative_execution.execute(
        session,
        instruction=decision["instruction"],
        opus_execute=opus_execute,
    )

    if execution.get("status") != "pending_approval":
        raise auto_iteration_error(
            "iteration did not produce a pending candidate"
        )

    return {
        "schema": schema,
        "owner": owner,
        "mode": "auto",
        "plan": decision,
        "execution": execution,
        "candidate_id": execution["candidate_id"],
        "session": execution["session"],
        "status": "pending_approval",
    }


__all__ = [
    "auto_iteration_error",
    "execute",
    "owner",
    "plan",
    "schema",
]
