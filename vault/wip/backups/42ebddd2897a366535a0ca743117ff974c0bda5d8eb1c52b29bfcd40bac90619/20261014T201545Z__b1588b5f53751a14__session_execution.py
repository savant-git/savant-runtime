
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


schema = "savant://runtime/urge/session-execution/1.1.0"
owner = "exile:urge"


class session_execution_error(ValueError):
    pass


def _selected_projection(
    execution: Mapping[str, Any],
    timeline: Mapping[str, Any],
) -> dict[str, Any]:
    best = execution["best"]
    selected_digest = best["payload_digest"]

    matches = [
        record
        for record in timeline["history"]
        if record["provenance"]["payload_digest"]
        == selected_digest
    ]

    if len(matches) != 1:
        raise session_execution_error(
            "selected candidate must have exactly "
            "one recorded timeline identity"
        )

    selected = matches[0]

    return {
        "candidate_digest": best["digest"],
        "payload_digest": selected_digest,
        "iteration_id": selected["id"],
        "iteration_number": selected["number"],
        "cycle": best["cycle"],
        "score": best["assessment"]["score"],
        "required_met": best["assessment"][
            "required_met"
        ],
        "assessment_digest": best["assessment"][
            "digest"
        ],
        "stop_reason": execution["stop_reason"],
        "lineage": deepcopy(execution["lineage"]),
        "payload": deepcopy(best["payload"]),
    }


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

    if (
        on_iteration is not None
        and not callable(on_iteration)
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

    observation_failures: list[dict[str, Any]] = []

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

        timeline = append(
            timeline,
            result={
                "payload": deepcopy(payload),
                "assessment": judged,
                "context": deepcopy(dict(context)),
            },
            provenance={
                "owner": owner,
                "job_id": work.id,
                "job_digest": context["job"][
                    "digest"
                ],
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

        if on_iteration is not None:
            try:
                on_iteration(
                    deepcopy(projection(timeline))
                )
            except Exception as exc:
                observation_failures.append({
                    "iteration_id": timeline[
                        "active"
                    ][-1],
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                })

        return raw

    observed_engine = engine(
        evaluator=observed_evaluator,
        reviser=runner.reviser,
        run_policy=runner.policy,
    )

    execution = observed_engine.run(
        work,
        initial_payload=initial_payload,
    )

    selected = _selected_projection(
        execution,
        timeline,
    )

    if timeline["status"] == "running":
        timeline = pause(timeline)

    return {
        "schema": schema,
        "owner": owner,
        "authority_effect": "none",
        "execution": execution,
        "timeline": verify(timeline),
        "projection": projection(timeline),
        "selected": selected,
        "observation_failures": (
            observation_failures
        ),
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
