
from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any


class provider_execution_error(RuntimeError):
    pass


class iteration_executor:
    def __init__(
        self,
        execute: Callable[
            [Mapping[str, Any]], Mapping[str, Any]
        ],
    ) -> None:
        if not callable(execute):
            raise TypeError("execute must be callable")

        self.execute = execute

    def __call__(
        self,
        request: Mapping[str, Any],
    ) -> dict[str, Any]:
        if not isinstance(request, Mapping):
            raise provider_execution_error(
                "iteration request must be a mapping"
            )

        required = (
            "session_id",
            "goal",
            "iteration",
            "settings",
        )

        for field in required:
            if field not in request:
                raise provider_execution_error(
                    f"missing request field: {field}"
                )

        response = self.execute(dict(request))

        if not isinstance(response, Mapping):
            raise provider_execution_error(
                "provider returned an invalid response"
            )

        if "result" not in response:
            raise provider_execution_error(
                "provider returned no result"
            )

        execution = response.get("execution")

        if not isinstance(execution, Mapping):
            raise provider_execution_error(
                "provider evidence must be a mapping"
            )

        required_evidence = (
            "provider",
            "model",
            "method",
        )

        for field in required_evidence:
            value = execution.get(field)

            if not isinstance(value, str) or not value.strip():
                raise provider_execution_error(
                    f"missing execution evidence: {field}"
                )

        return {
            "result": response["result"],
            "execution": dict(execution),
        }
