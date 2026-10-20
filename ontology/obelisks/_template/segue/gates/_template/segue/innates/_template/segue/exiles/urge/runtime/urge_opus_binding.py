
from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from opus_provider_executor import opus_provider_executor


class urge_opus_binding:
    def __init__(
        self,
        providers: Sequence[Mapping[str, Any]],
    ) -> None:
        self.engine = opus_provider_executor(
            providers
        )

    async def __call__(
        self,
        iteration: Mapping[str, Any],
    ) -> dict[str, Any]:
        goal = iteration.get("goal")
        settings = iteration.get("settings", {})

        if not isinstance(goal, str) or not goal.strip():
            raise ValueError("goal is required")

        if not isinstance(settings, Mapping):
            raise ValueError("invalid settings")

        method = settings.get(
            "method",
            "combine",
        )

        outcome = await self.engine.run(
            goal=goal,
            method=method,
            previous_result=iteration.get(
                "previous_result"
            ),
        )

        execution = dict(outcome["execution"])

        steps = execution.get("steps", [])

        if not steps:
            raise RuntimeError(
                "opus returned no executed steps"
            )

        final = steps[-1]["execution"]

        execution.update({
            "provider": final["provider"],
            "model": final["model"],
            "method": method,
            "urge_iteration": iteration["iteration"],
            "urge_session_id": iteration["session_id"],
            "previous_digest": iteration.get(
                "previous_digest"
            ),
        })

        return {
            "result": outcome["result"],
            "execution": execution,
        }
