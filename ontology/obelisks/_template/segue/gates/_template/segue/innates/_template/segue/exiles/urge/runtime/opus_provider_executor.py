
from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from typing import Any

from opus_method_compiler import compile_method
from opus_method_execution import opus_method_execution
from provider_transport import provider_transport


class opus_provider_error(RuntimeError):
    pass


class opus_provider_executor:
    def __init__(
        self,
        providers: Sequence[Mapping[str, Any]],
        *,
        timeout_seconds: float = 90.0,
    ) -> None:
        if not providers:
            raise opus_provider_error(
                "at least one provider is required"
            )

        self.providers = []

        for provider in providers:
            if not isinstance(provider, Mapping):
                raise opus_provider_error(
                    "invalid provider configuration"
                )

            required = (
                "id",
                "model",
                "endpoint",
                "credential_variable",
            )

            for field in required:
                value = provider.get(field)

                if not isinstance(value, str) or not value:
                    raise opus_provider_error(
                        f"missing provider field: {field}"
                    )

            self.providers.append(dict(provider))

        self.transport = provider_transport(
            timeout_seconds=timeout_seconds
        )

    def _provider(
        self,
        identity: str,
    ) -> dict[str, Any]:
        for provider in self.providers:
            if provider["id"] == identity:
                return provider

        raise opus_provider_error(
            "unknown provider identity"
        )

    async def execute_step(
        self,
        request: Mapping[str, Any],
    ) -> dict[str, Any]:
        participant = request.get("participant")

        if not isinstance(participant, Mapping):
            raise opus_provider_error(
                "participant is required"
            )

        identity = participant.get("id")

        if not isinstance(identity, str):
            raise opus_provider_error(
                "participant identity is required"
            )

        provider = self._provider(identity)

        dependencies = request.get(
            "dependencies",
            [],
        )

        if not isinstance(dependencies, list):
            raise opus_provider_error(
                "invalid dependencies"
            )

        prior = [
            {
                "step": item["step"],
                "participant": item["participant"],
                "result": item["result"],
            }
            for item in dependencies
        ]

        context = {
            "goal": request["goal"],
            "method": request["method"],
            "role": request["role"],
            "instruction": request["instruction"],
            "previous_iteration_result": request.get(
                "previous_result"
            ),
            "dependency_results": prior,
        }

        system = (
            "You are participating in a structured "
            "multi-agent reasoning process. "
            "Follow the assigned role. "
            "Distinguish evidence from inference. "
            "Do not invent facts, sources, tests, "
            "or completed actions. "
            "Preserve relevant provenance."
        )

        messages = [
            {
                "role": "system",
                "content": system,
            },
            {
                "role": "user",
                "content": json.dumps(
                    context,
                    ensure_ascii=False,
                    default=str,
                ),
            },
        ]

        response = await self.transport.invoke(
            endpoint=provider["endpoint"],
            credential_variable=provider[
                "credential_variable"
            ],
            model=provider["model"],
            messages=messages,
            temperature=float(
                provider.get("temperature", 0.4)
            ),
        )

        return {
            "result": response["result"],
            "execution": {
                "provider": identity,
                "model": response["model"],
                "method": request["method"],
                "role": request["role"],
                "step": request["step"],
                "response_id": response["response_id"],
                "finish_reason": response[
                    "finish_reason"
                ],
                "usage": response["usage"],
                "plan_digest": request["plan_digest"],
            },
        }

    async def run(
        self,
        *,
        goal: str,
        method: str,
        previous_result: Any = None,
    ) -> dict[str, Any]:
        participants = [
            {
                "id": provider["id"],
                "model": provider["model"],
            }
            for provider in self.providers
        ]

        plan = compile_method(
            method=method,
            goal=goal,
            participants=participants,
            previous_result=previous_result,
        )

        engine = opus_method_execution(
            self.execute_step
        )

        return await engine.run(plan)
