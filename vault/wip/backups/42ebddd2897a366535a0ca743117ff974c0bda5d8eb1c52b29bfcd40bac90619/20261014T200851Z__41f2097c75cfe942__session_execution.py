
from __future__ import annotations

from copy import deepcopy
from typing import Any, Callable, Mapping

from .iteration import engine, job
from .session_timeline import (
    append,
    create,
    pause,
    projection,
    start,
    verify,
)


schema = "savant://runtime/urge/session-execution/1.0.0"
owner = "exile:urge"


class session_execution_error(ValueError):
    pass


def execute(
    *,
    message_id: str,
    work: job,
    runner: engine,
    initial_payload: Any | None = None,
    on_iteration: Callable[
        [Mapping[str, Any]], None
    ] | None = None,
) -> dict[str, Any]:
    if not isinstance(work, job):
        raise session_execution_error(
            "work must be an urge job"
        )

    if not isinstance(runner, engine):
        raise session_execution_error(
            "runner must be an urge engine"
        )

    if on_iteration is not None and not callable(
        on_iteration
    ):
        raise session_execution_error(
            "on_iteration must be callable"
        )

    timeline = start(
        create(
            message_id,
            limit=runner.policy.max_candidates,
        )
    )

    def observed_evaluator(
        payload: Any,
        context: Mapping[str, Any],
    ) -> Any:
        nonlocal timeline

        raw = runner.evaluator(
            payload,
            context,
        )

        judged = runner._normalize_assessment(
            raw,
            work,
        )

        next_timeline = append(
            timeline,
            result={
                "payload": deepcopy(payload),
                "assessment": judged,
                "context": deepcopy(dict(context)),
            },
            provenance={
                "owner": owner,
                "job_id": work.id,
                "job_digest": context[
                    "job"
                ]["digest"],
                "payload_digest": context[
                    "payload_digest"
                ],
                "parent_payload_digest": context[
                    "parent_payload_digest"
                ],
                "cycle": context["cycle"],
                "candidate_index": context[
                    "candidate_index"
                ],
            },
        )

        timeline = next_timeline

        if on_iteration is not None:
            on_iteration(
                deepcopy(
                    projection(timeline)
                )
            )

        return raw

    observed_engine = engine(
        evaluator=observed_evaluator,
        reviser=runner.reviser,
        run_policy=runner.policy,
    )

    result = observed_engine.run(
        work,
        initial_payload=initial_payload,
    )

    if timeline["status"] == "running":
        timeline = pause(timeline)

    return {
        "schema": schema,
        "owner": owner,
        "authority_effect": "none",
        "execution": result,
        "timeline": verify(timeline),
        "projection": projection(timeline),
        "boundaries": {
            "executes_provider": False,
            "owns_provider_routing": False,
            "mutates_canon": False,
            "mutates_source": False,
            "supports_live_observation": True,
            "supports_live_pause": False,
            "supports_execution_rewind": False,
            "supports_execution_resume": False,
        },
    }


__all__ = [
    "execute",
    "owner",
    "schema",
    "session_execution_error",
]
