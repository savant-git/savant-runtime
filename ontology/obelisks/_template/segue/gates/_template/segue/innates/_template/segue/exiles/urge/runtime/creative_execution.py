from __future__ import annotations

import hashlib
import inspect
import json
from collections.abc import Callable, Mapping
from typing import Any

try:
    from . import creative_session
except ImportError:
    import creative_session


schema = "savant://runtime/urge/creative-execution/1.0.0"


class creative_execution_error(RuntimeError):
    pass


def _required_text(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise creative_execution_error(
            f"{name} must be a nonempty string"
        )
    return value.strip()


def _json_copy(value: Any) -> Any:
    try:
        return json.loads(
            json.dumps(
                value,
                sort_keys=True,
                ensure_ascii=False,
                allow_nan=False,
            )
        )
    except (TypeError, ValueError) as exc:
        raise creative_execution_error(
            "execution data must be JSON serializable"
        ) from exc


def _candidate_id(
    session_id: str,
    instruction: str,
    baseline: str | None,
    result: Mapping[str, Any],
) -> str:
    identity = {
        "session_id": session_id,
        "instruction": instruction,
        "baseline": baseline,
        "result": result,
    }

    encoded = json.dumps(
        identity,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")

    return "creative:" + hashlib.sha256(
        encoded
    ).hexdigest()


def _approved_artifact(
    session: Mapping[str, Any],
) -> Mapping[str, Any] | None:
    approved = session.get("approved")

    if approved is None:
        return None

    for candidate in session["candidates"]:
        if (
            candidate["artifact_id"] == approved
            and candidate["status"] == "approved"
        ):
            return candidate

    raise creative_execution_error(
        "approved baseline cannot be resolved"
    )


def build_request(
    session: Mapping[str, Any],
    instruction: str,
) -> dict[str, Any]:
    instruction = _required_text(
        instruction,
        "instruction",
    )

    request = creative_session.refinement_request(
        session,
        instruction,
    )

    baseline = _approved_artifact(session)

    if request["continuity"] and baseline is None:
        raise creative_execution_error(
            "approved baseline required"
        )

    execution = (
        baseline["execution"]
        if baseline is not None
        else None
    )

    baseline_reference = None

    if execution is not None:
        baseline_reference = execution.get(
            "artifact_reference"
        )

    if (
        request["continuity"]
        and baseline_reference is None
    ):
        raise creative_execution_error(
            "approved baseline has no usable "
            "artifact reference"
        )

    return {
        "schema": schema,
        "owner": "exile:urge",
        "executor_owner": "exile:opus",
        "session_id": request["session_id"],
        "brief": request["brief"],
        "instruction": instruction,
        "operation": (
            "refine"
            if request["continuity"]
            else "generate"
        ),
        "continuity": request["continuity"],
        "baseline_artifact_id": (
            request["baseline_artifact_id"]
            if request["continuity"]
            else None
        ),
        "baseline_artifact_reference": (
            _json_copy(baseline_reference)
            if request["continuity"]
            else None
        ),
    }


def execute(
    session: Mapping[str, Any],
    *,
    instruction: str,
    opus_execute: Callable[
        [Mapping[str, Any]],
        Mapping[str, Any],
    ],
) -> dict[str, Any]:
    if not callable(opus_execute):
        raise creative_execution_error(
            "opus_execute must be callable"
        )

    request = build_request(
        session,
        instruction,
    )

    result = opus_execute(
        _json_copy(request)
    )

    if inspect.isawaitable(result):
        raise creative_execution_error(
            "asynchronous opus execution requires "
            "an awaited adapter"
        )

    if not isinstance(result, Mapping):
        raise creative_execution_error(
            "opus must return a mapping"
        )

    result = _json_copy(dict(result))

    if result.get("status") != "succeeded":
        raise creative_execution_error(
            "opus execution did not succeed"
        )

    if result.get("owner") != "exile:opus":
        raise creative_execution_error(
            "opus ownership evidence missing"
        )

    reference = result.get(
        "artifact_reference"
    )

    if not isinstance(reference, Mapping):
        raise creative_execution_error(
            "opus result has no artifact reference"
        )

    if not reference:
        raise creative_execution_error(
            "artifact reference is empty"
        )

    provider = _required_text(
        result.get("provider"),
        "provider",
    )

    model = _required_text(
        result.get("model"),
        "model",
    )

    execution_id = _required_text(
        result.get("execution_id"),
        "execution_id",
    )

    result["provider"] = provider
    result["model"] = model
    result["execution_id"] = execution_id

    artifact_id = _candidate_id(
        request["session_id"],
        instruction,
        request["baseline_artifact_id"],
        result,
    )

    existing = {
        candidate["artifact_id"]
        for candidate in session["candidates"]
    }

    if artifact_id in existing:
        raise creative_execution_error(
            "duplicate execution result"
        )

    updated = creative_session.propose(
        session,
        artifact_id=artifact_id,
        instruction=instruction,
        execution=result,
    )

    return {
        "schema": schema,
        "request": request,
        "candidate_id": artifact_id,
        "session": updated,
        "status": "pending_approval",
    }


def approve(
    session: Mapping[str, Any],
    artifact_id: str,
) -> dict[str, Any]:
    return creative_session.decide(
        session,
        artifact_id=artifact_id,
        approve=True,
    )


def reject(
    session: Mapping[str, Any],
    artifact_id: str,
) -> dict[str, Any]:
    return creative_session.decide(
        session,
        artifact_id=artifact_id,
        approve=False,
    )


def generate_request(
    session: Mapping[str, Any],
    instruction: str,
) -> dict[str, Any]:
    if session.get("approved") is not None:
        raise creative_execution_error(
            "session already has an approved design; "
            "use build_request for refinement"
        )

    request = creative_session.refinement_request(
        creative_session.set_continuity(
            session,
            False,
        ),
        instruction,
    )

    return {
        "schema": schema,
        "owner": "exile:urge",
        "executor_owner": "exile:opus",
        "session_id": request["session_id"],
        "brief": request["brief"],
        "instruction": request["instruction"],
        "operation": "generate",
        "continuity": False,
        "baseline_artifact_id": None,
        "baseline_artifact_reference": None,
    }
