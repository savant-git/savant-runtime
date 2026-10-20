
from __future__ import annotations

import inspect
from collections.abc import Awaitable, Callable, Mapping
from typing import Any

from opus_method_compiler import (
    digest,
    verify_plan,
)


class method_execution_error(RuntimeError):
    pass


class opus_method_execution:
    def __init__(
        self,
        execute: Callable[
            [dict[str, Any]],
            Mapping[str, Any]
            | Awaitable[Mapping[str, Any]],
        ],
    ) -> None:
        if not callable(execute):
            raise TypeError(
                "execute must be callable"
            )

        self.execute = execute

    async def run(
        self,
        plan: Mapping[str, Any],
    ) -> dict[str, Any]:
        verified = verify_plan(plan)

        participants = {
            participant["id"]: participant
            for participant in verified["participants"]
        }

        results: dict[int, dict[str, Any]] = {}
        evidence: list[dict[str, Any]] = []

        for step in verified["steps"]:
            identity = step["participant"]

            if identity not in participants:
                raise method_execution_error(
                    "unknown participant"
                )

            dependencies = [
                results[index]
                for index in step["dependencies"]
            ]

            request = {
                "goal": verified["goal"],
                "method": verified["method"],
                "participant": dict(
                    participants[identity]
                ),
                "role": step["role"],
                "instruction": step["instruction"],
                "step": step["index"],
                "dependencies": dependencies,
                "previous_result": verified[
                    "previous_result"
                ],
                "plan_digest": verified["digest"],
            }

            response = self.execute(request)

            if inspect.isawaitable(response):
                response = await response

            if not isinstance(response, Mapping):
                raise method_execution_error(
                    "executor returned an invalid response"
                )

            result = response.get("result")
            execution = response.get("execution")

            if result is None:
                raise method_execution_error(
                    "executor returned no result"
                )

            if (
                not isinstance(execution, Mapping)
                or not execution
            ):
                raise method_execution_error(
                    "executor returned no provenance"
                )

            record = {
                "step": step["index"],
                "participant": identity,
                "role": step["role"],
                "dependencies": list(
                    step["dependencies"]
                ),
                "result": result,
                "execution": dict(execution),
            }

            record["digest"] = digest(record)
            results[step["index"]] = record
            evidence.append(record)

        if not evidence:
            raise method_execution_error(
                "no steps executed"
            )

        return {
            "result": evidence[-1]["result"],
            "execution": {
                "method": verified["method"],
                "plan_digest": verified["digest"],
                "step_count": len(evidence),
                "steps": evidence,
                "final_step_digest": evidence[-1][
                    "digest"
                ],
            },
        }
