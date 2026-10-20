
from __future__ import annotations

import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any


class opus_iteration_error(RuntimeError):
    pass


def _opus_runtime() -> Path:
    return (
        Path(__file__).resolve().parents[2]
        / "opus"
        / "runtime"
    )


def _orchestrator():
    runtime = _opus_runtime()

    if not runtime.is_dir():
        raise opus_iteration_error(
            "opus runtime directory is unavailable"
        )

    location = str(runtime)

    if location not in sys.path:
        sys.path.insert(0, location)

    from cognitive_orchestrator import orchestrate_text

    return orchestrate_text


def _text(value: Any) -> str:
    if isinstance(value, str):
        return value.strip()

    return ""


class opus_iteration_adapter:
    def __init__(
        self,
        providers: Sequence[Mapping[str, Any]],
        executor: Any = None,
    ) -> None:
        if isinstance(providers, (str, bytes)):
            raise TypeError("providers must be a sequence")

        self.providers = [
            dict(provider)
            for provider in providers
        ]

        if not self.providers:
            raise opus_iteration_error(
                "at least one provider is required"
            )

        self.executor = executor

    def __call__(
        self,
        iteration: Mapping[str, Any],
    ) -> dict[str, Any]:
        goal = _text(iteration.get("goal"))

        if not goal:
            raise opus_iteration_error(
                "iteration goal is required"
            )

        number = iteration.get("iteration")

        if (
            isinstance(number, bool)
            or not isinstance(number, int)
            or number < 1
        ):
            raise opus_iteration_error(
                "invalid iteration number"
            )

        settings = iteration.get("settings", {})

        if not isinstance(settings, Mapping):
            raise opus_iteration_error(
                "invalid iteration settings"
            )

        method = settings.get("method", "combine")

        if method not in {
            "combine",
            "idealize",
            "collab",
            "cascade",
            "council",
            "dialectic",
            "swarm",
            "relay",
            "evolve",
        }:
            raise opus_iteration_error(
                "unsupported orchestration method"
            )

        previous = iteration.get("previous_result")

        request = {
            "goal": goal,
            "prompt": (
                f"Goal: {goal}\n"
                f"Iteration: {number}\n"
                f"Orchestration method requested: {method}\n"
                f"Previous result: {previous!r}\n"
                "Produce a substantive improvement. "
                "Identify unresolved assumptions and "
                "do not invent evidence."
            ),
            "required_capabilities": [
                "text_inference"
            ],
            "urge": {
                "session_id": iteration.get(
                    "session_id"
                ),
                "iteration": number,
                "method": method,
                "previous_digest": iteration.get(
                    "previous_digest"
                ),
            },
        }

        orchestrate = _orchestrator()

        response = orchestrate(
            request,
            self.providers,
            executor=self.executor,
        )

        if not isinstance(response, Mapping):
            raise opus_iteration_error(
                "opus returned an invalid response"
            )

        if not response.get("ok"):
            raise opus_iteration_error(
                str(
                    response.get("error")
                    or "opus execution failed"
                )
            )

        result = _text(response.get("text"))

        if not result:
            raise opus_iteration_error(
                "opus returned no text"
            )

        provider = response.get("provider")
        model = response.get("model")

        if not provider or not model:
            raise opus_iteration_error(
                "opus execution provenance is incomplete"
            )

        return {
            "result": result,
            "execution": {
                "provider": str(provider),
                "model": str(model),
                "method": str(method),
                "iteration": number,
                "required_capabilities": [
                    "text_inference"
                ],
                "eligible_provider_count": response.get(
                    "eligible_provider_count"
                ),
                "opus_response": dict(response),
                "method_execution_verified": False,
            },
        }
