from __future__ import annotations

from copy import deepcopy
from typing import Any, Callable, Mapping

from .iteration import (
    criterion,
    engine,
    job,
    policy,
)
from .job_adapter import (
    adapter,
    execution_boundary,
)


schema = "savant://runtime/urge/session-work/1.0.0"
owner = "exile:urge"


class session_work_error(ValueError):
    pass


def _object(
    value: Any,
    name: str,
) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise session_work_error(
            f"{name} must be an object"
        )

    return deepcopy(dict(value))


def _strings(
    value: Any,
    name: str,
) -> tuple[str, ...]:
    if value is None:
        return ()

    if not isinstance(value, (list, tuple)):
        raise session_work_error(
            f"{name} must be an array"
        )

    if not all(
        isinstance(item, str)
        for item in value
    ):
        raise session_work_error(
            f"{name} must contain strings"
        )

    return tuple(
        dict.fromkeys(
            item.strip()
            for item in value
            if item.strip()
        )
    )


def _criteria(
    value: Any,
) -> tuple[criterion, ...]:
    if not isinstance(value, (list, tuple)):
        raise session_work_error(
            "criteria must be an array"
        )

    result = []

    for item in value:
        data = _object(item, "criterion")

        allowed = {
            "id",
            "weight",
            "target",
            "required",
        }

        if set(data) - allowed:
            raise session_work_error(
                "unknown criterion fields"
            )

        if not isinstance(data.get("id"), str):
            raise session_work_error(
                "criterion id must be a string"
            )

        result.append(criterion(**data))

    if not result:
        raise session_work_error(
            "at least one criterion is required"
        )

    return tuple(result)


def _policy(
    value: Any,
) -> policy:
    if value is None:
        return policy()

    data = _object(value, "policy")

    allowed = {
        "max_cycles",
        "branch_factor",
        "min_improvement",
        "target_score",
        "patience",
        "max_candidates",
        "max_failures",
        "preserve_alternates",
    }

    if set(data) - allowed:
        raise session_work_error(
            "unknown policy fields"
        )

    return policy(**data)


def create_resolver(
    *,
    boundary: execution_boundary,
) -> Callable[
    [Mapping[str, Any]],
    tuple[job, engine],
]:
    if not isinstance(boundary, execution_boundary):
        raise session_work_error(
            "an execution boundary is required"
        )

    bound = adapter(boundary)

    def resolve(
        request: Mapping[str, Any],
    ) -> tuple[job, engine]:
        data = _object(request, "request")
        specification = _object(
            data.get("work"),
            "work",
        )

        allowed = {
            "id",
            "objective",
            "payload",
            "criteria",
            "constraints",
            "provenance",
            "dependencies",
            "metadata",
        }

        if set(specification) - allowed:
            raise session_work_error(
                "unknown work fields"
            )

        session_id = data.get("session_id")

        if (
            not isinstance(session_id, str)
            or not session_id.strip()
            or session_id != session_id.strip()
        ):
            raise session_work_error(
                "canonical session_id is required"
            )

        work_id = specification.get(
            "id",
            session_id,
        )

        if (
            not isinstance(work_id, str)
            or not work_id.strip()
        ):
            raise session_work_error(
                "work id must be a nonempty string"
            )

        objective = specification.get("objective")

        if (
            not isinstance(objective, str)
            or not objective.strip()
        ):
            raise session_work_error(
                "objective is required"
            )

        metadata = specification.get(
            "metadata",
            {},
        )

        metadata = _object(
            metadata,
            "metadata",
        )

        work = job(
            id=work_id,
            objective=objective,
            payload=deepcopy(
                specification.get("payload")
            ),
            criteria=_criteria(
                specification.get("criteria")
            ),
            constraints=_strings(
                specification.get("constraints"),
                "constraints",
            ),
            provenance=_strings(
                specification.get("provenance"),
                "provenance",
            ),
            dependencies=_strings(
                specification.get("dependencies"),
                "dependencies",
            ),
            metadata=metadata,
        )

        runner = engine(
            evaluator=bound.evaluator,
            reviser=bound.reviser,
            run_policy=_policy(
                data.get("policy")
            ),
        )

        return work, runner

    return resolve


__all__ = [
    "create_resolver",
    "session_work_error",
    "schema",
    "owner",
]
