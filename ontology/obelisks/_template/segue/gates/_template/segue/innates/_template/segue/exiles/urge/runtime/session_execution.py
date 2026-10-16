
from __future__ import annotations

from copy import deepcopy
from typing import Any, Callable, Mapping

from .iteration import engine, job
from .session_control import (
    controller,
    session_cancelled,
)
from .session_timeline import (
    append,
    create,
    pause,
    projection,
    resume,
    start,
    verify,
)


schema = "savant://runtime/urge/session-execution/1.2.0"
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
    control: controller | None = None,
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

    if control is not None and not isinstance(
        control,
        controller,
    ):
        raise session_execution_error(
            "control must be a session controller"
        )

    control = control or controller()
    control.start()

    timeline = start(
        create(
            message_id,
            limit=runner.policy.max_candidates,
        )
    )

    observation_failures: list[dict[str, Any]] = []

    def synchronize_timeline() -> None:
        nonlocal timeline

        state = control.projection()["status"]

        if (
            state == "paused"
            and timeline["status"] == "running"
        ):
            timeline = pause(timeline)

        elif (
            state == "running"
            and timeline["status"] == "paused"
        ):
            timeline = resume(timeline)

    def checkpoint() -> None:
        synchronize_timeline()
        control.checkpoint()
        synchronize_timeline()

    def observed_evaluator(
        payload: Any,
        context: Mapping[str, Any],
    ) -> Any:
        nonlocal timeline

        checkpoint()

        raw = runner.evaluator(
            payload,
            context,
        )

        checkpoint()

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

    def observed_reviser(
        payload: Any,
        pressure: Mapping[str, Any],
    ) -> Any:
        checkpoint()

        result = runner.reviser(
            payload,
            pressure,
        )

        checkpoint()
        return result

    observed_engine = engine(
        evaluator=observed_evaluator,
        reviser=observed_reviser,
        run_policy=runner.policy,
    )

    try:
        execution = observed_engine.run(
            work,
            initial_payload=initial_payload,
        )

        checkpoint()

        selected = _selected_projection(
            execution,
            timeline,
        )

        control.complete()

    except session_cancelled:
        return {
            "schema": schema,
            "owner": owner,
            "status": "cancelled",
            "execution": None,
            "timeline": verify(timeline),
            "projection": projection(timeline),
            "selected": None,
            "control": control.projection(),
            "observation_failures": (
                observation_failures
            ),
        }

    except Exception:
        if control.projection()["status"] in (
            "ready",
            "running",
            "paused",
        ):
            control.fail()
        raise

    if timeline["status"] == "running":
        timeline = pause(timeline)

    return {
        "schema": schema,
        "owner": owner,
        "status": "completed",
        "authority_effect": "none",
        "execution": execution,
        "timeline": verify(timeline),
        "projection": projection(timeline),
        "selected": selected,
        "control": control.projection(),
        "observation_failures": (
            observation_failures
        ),
        "boundaries": {
            "executes_provider": False,
            "owns_provider_routing": False,
            "mutates_canon": False,
            "mutates_source": False,
            "supports_live_observation": True,
            "supports_live_pause": True,
            "supports_execution_rewind": False,
            "supports_execution_resume": True,
            "supports_cooperative_cancel": True,
        },
    }


__all__ = [
    "execute",
    "owner",
    "schema",
    "session_execution_error",
]
