
from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from typing import Any

from envoy_persona_bridge import (
    prompt_projection,
    select,
)
from opus_provider_executor import opus_provider_executor


class envoy_opus_error(RuntimeError):
    pass


class envoy_opus_binding:
    def __init__(
        self,
        providers: Sequence[Mapping[str, Any]],
    ) -> None:
        self.engine = opus_provider_executor(providers)

    @staticmethod
    def _settings(
        iteration: Mapping[str, Any],
    ) -> Mapping[str, Any]:
        settings = iteration.get("settings", {})

        if not isinstance(settings, Mapping):
            raise envoy_opus_error(
                "iteration settings must be a mapping"
            )

        return settings

    @staticmethod
    def _personas(
        settings: Mapping[str, Any],
    ) -> dict[str, Any] | None:
        primary = settings.get("primary_persona")

        if primary is None:
            return None

        supplemental = settings.get(
            "supplemental_personas",
            [],
        )

        return select(
            primary,
            supplemental,
        )

    async def __call__(
        self,
        iteration: Mapping[str, Any],
    ) -> dict[str, Any]:
        if not isinstance(iteration, Mapping):
            raise envoy_opus_error(
                "iteration must be a mapping"
            )

        goal = iteration.get("goal")

        if not isinstance(goal, str) or not goal.strip():
            raise envoy_opus_error("goal is required")

        settings = self._settings(iteration)
        method = settings.get("method", "combine")

        if not isinstance(method, str):
            raise envoy_opus_error(
                "method must be a string"
            )

        selected = self._personas(settings)
        previous = iteration.get("previous_result")

        if selected is None:
            execution_goal = goal
            persona_ids: list[str] = []
        else:
            projection = prompt_projection(
                selected,
                goal=goal,
                previous_result=previous,
            )

            execution_goal = (
                goal
                + "\n\nEnvoy reasoning context:\n"
                + json.dumps(
                    projection,
                    sort_keys=True,
                    ensure_ascii=False,
                    allow_nan=False,
                )
            )

            persona_ids = [
                selected["primary"],
                *selected["supplemental"],
            ]

        outcome = await self.engine.run(
            goal=execution_goal,
            method=method,
            previous_result=previous,
        )

        if not isinstance(outcome, Mapping):
            raise envoy_opus_error(
                "opus returned an invalid outcome"
            )

        evidence = outcome.get("execution")

        if not isinstance(evidence, Mapping):
            raise envoy_opus_error(
                "opus execution evidence is missing"
            )

        steps = evidence.get("steps")

        if not isinstance(steps, list) or not steps:
            raise envoy_opus_error(
                "opus returned no executed steps"
            )

        final = steps[-1].get("execution")

        if not isinstance(final, Mapping):
            raise envoy_opus_error(
                "final provider provenance is missing"
            )

        execution = dict(evidence)
        execution.update({
            "provider": final.get("provider"),
            "model": final.get("model"),
            "method": method,
            "envoy_personas": persona_ids,
            "envoy_selection_mode": (
                "combined"
                if len(persona_ids) > 1
                else "single"
                if persona_ids
                else "none"
            ),
            "urge_iteration": iteration.get("iteration"),
            "urge_session_id": iteration.get("session_id"),
            "previous_digest": iteration.get(
                "previous_digest"
            ),
        })

        return {
            "result": outcome["result"],
            "execution": execution,
        }
