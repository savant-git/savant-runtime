#!/usr/bin/env python3

from __future__ import annotations

import asyncio
import json
import os
import re
import sys
import time
from typing import Any

import chimera as core
import chimera_resilient as resilient


default_structured_max_tokens = 4096
default_structured_retries = 2


def env_int(name: str, default: int) -> int:
    raw = os.environ.get(name, "").strip()

    if not raw:
        return default

    try:
        value = int(raw)
    except ValueError:
        return default

    return max(value, 0)


def is_gemini_three(model: str) -> bool:
    normalized = model.casefold()

    match = re.search(
        r"gemini(?:/|[-_])?gemini-(\d+)",
        normalized,
    )

    if match:
        try:
            return int(match.group(1)) >= 3
        except ValueError:
            return False

    return "gemini/gemini-3" in normalized


def strip_single_json_fence(text: str) -> str:
    stripped = text.strip()

    match = re.fullmatch(
        r"```(?:json)?\s*(.*?)\s*```",
        stripped,
        flags=re.IGNORECASE | re.DOTALL,
    )

    if match:
        return match.group(1).strip()

    return stripped


def extract_top_level_json_object(text: str) -> dict[str, Any]:
    candidate = strip_single_json_fence(text)

    if not candidate:
        raise ValueError(
            "model response was empty"
        )

    try:
        value = json.loads(candidate)
    except json.JSONDecodeError as exc:
        first = candidate.find("{")
        last = candidate.rfind("}")

        if first < 0:
            raise ValueError(
                "model response contained no top-level JSON object"
            ) from exc

        if last < first:
            raise ValueError(
                "model response contained an unterminated top-level JSON object"
            ) from exc

        outer = candidate[first : last + 1].strip()

        prefix = candidate[:first].strip()
        suffix = candidate[last + 1 :].strip()

        if prefix or suffix:
            try:
                value = json.loads(outer)
            except json.JSONDecodeError as outer_exc:
                raise ValueError(
                    "model response contained malformed top-level JSON"
                ) from outer_exc
        else:
            raise ValueError(
                "model response contained malformed top-level JSON"
            ) from exc

    if not isinstance(value, dict):
        raise ValueError(
            "model response top level was not a JSON object"
        )

    return value


def validate_phase_shape(
    phase: str,
    value: dict[str, Any],
) -> None:
    if phase == "tribunal":
        required = {
            "verdicts",
            "cross_claim_conflicts",
            "unknowns",
            "tribunal_summary",
        }

    elif phase == "synthesis":
        required = {
            "answer",
            "supported_claim_ids",
            "rejected_claim_ids",
            "unresolved_claim_ids",
            "unknowns",
            "next_tests",
            "confidence",
            "authority_effect",
        }

    else:
        required = set()

    missing = sorted(
        required - set(value)
    )

    if missing:
        raise ValueError(
            "structured response missing required top-level keys: "
            + ", ".join(missing)
        )

    if phase == "tribunal":
        if not isinstance(
            value["verdicts"],
            list,
        ):
            raise ValueError(
                "tribunal verdicts must be a list"
            )

        if not isinstance(
            value["cross_claim_conflicts"],
            list,
        ):
            raise ValueError(
                "tribunal cross_claim_conflicts must be a list"
            )

    if phase == "synthesis":
        if not isinstance(
            value["answer"],
            str,
        ):
            raise ValueError(
                "synthesis answer must be a string"
            )

        for key in (
            "supported_claim_ids",
            "rejected_claim_ids",
            "unresolved_claim_ids",
            "unknowns",
            "next_tests",
        ):
            if not isinstance(
                value[key],
                list,
            ):
                raise ValueError(
                    f"synthesis {key} must be a list"
                )


class StructuredGateway(
    resilient.ResilientGateway
):
    async def complete(
        self,
        model: str,
        system_prompt: str,
        user_prompt: str,
    ) -> tuple[
        str,
        int,
        int,
        int,
        float | None,
    ]:
        if core.litellm is None:
            raise RuntimeError(
                "litellm is unavailable; run Chimera through its isolated venv"
            )

        attempt = 0
        total_started = time.monotonic()

        structured = (
            "tribunal instance" in system_prompt
            or "final synthesis instance" in system_prompt
        )

        while True:
            await self.pacer.wait(model)

            async with self._budget_lock:
                self.budget.reserve_call()

            max_tokens = self.max_tokens

            if structured:
                max_tokens = max(
                    max_tokens,
                    env_int(
                        "SAVANT_CHIMERA_STRUCTURED_MAX_TOKENS",
                        default_structured_max_tokens,
                    ),
                )

            def invoke() -> Any:
                kwargs: dict[str, Any] = {
                    "model": model,
                    "messages": [
                        {
                            "role": "system",
                            "content": system_prompt,
                        },
                        {
                            "role": "user",
                            "content": user_prompt,
                        },
                    ],
                    "max_tokens": max_tokens,
                    "timeout": self.timeout_seconds,
                }

                if is_gemini_three(model):
                    kwargs[
                        "reasoning_effort"
                    ] = "minimal"
                else:
                    kwargs[
                        "temperature"
                    ] = self.temperature

                return core.litellm.completion(
                    **kwargs
                )

            try:
                with self.traces.span(
                    "chimera.model",
                    {
                        "gen_ai.request.model": model,
                        "savant.authority_effect": (
                            core.authority_effect
                        ),
                        "savant.chimera.provider_attempt": (
                            attempt + 1
                        ),
                        "savant.chimera.structured": (
                            structured
                        ),
                        "savant.chimera.max_tokens": (
                            max_tokens
                        ),
                    },
                ):
                    response = await asyncio.wait_for(
                        asyncio.to_thread(
                            invoke
                        ),
                        timeout=(
                            self.timeout_seconds
                            + 5.0
                        ),
                    )

                latency_ms = int(
                    (
                        time.monotonic()
                        - total_started
                    )
                    * 1000
                )

                message = (
                    response
                    .choices[0]
                    .message
                )

                content = resilient.safe_text(
                    getattr(
                        message,
                        "content",
                        "",
                    )
                )

                usage = getattr(
                    response,
                    "usage",
                    None,
                )

                prompt_tokens = int(
                    getattr(
                        usage,
                        "prompt_tokens",
                        0,
                    )
                    or 0
                )

                completion_tokens = int(
                    getattr(
                        usage,
                        "completion_tokens",
                        0,
                    )
                    or 0
                )

                response_cost = None

                hidden = getattr(
                    response,
                    "_hidden_params",
                    None,
                )

                if isinstance(
                    hidden,
                    dict,
                ):
                    raw_cost = hidden.get(
                        "response_cost"
                    )

                    if isinstance(
                        raw_cost,
                        (int, float),
                    ):
                        response_cost = float(
                            raw_cost
                        )

                async with self._budget_lock:
                    self.budget.account(
                        prompt_tokens,
                        completion_tokens,
                        response_cost,
                    )

                return (
                    content,
                    latency_ms,
                    prompt_tokens,
                    completion_tokens,
                    response_cost,
                )

            except Exception as exc:
                classification = (
                    resilient.classify_provider_error(
                        exc
                    )
                )

                if classification in {
                    "not_found",
                    "quota_zero",
                    "authorization",
                }:
                    raise

                retryable = (
                    classification
                    in {
                        "rate_limited",
                        "service_unavailable",
                        "timeout",
                    }
                )

                if (
                    not retryable
                    or attempt
                    >= self.transient_retries
                ):
                    raise

                if (
                    classification
                    == "rate_limited"
                ):
                    delay = (
                        resilient.retry_after_seconds(
                            str(exc)
                        )
                    )

                    if delay is None:
                        rpm = (
                            resilient.configured_model_rpm(
                                model
                            )
                        )

                        if rpm:
                            delay = 60.0 / rpm
                        else:
                            delay = 15.0

                    delay += 0.5

                else:
                    delay = (
                        resilient.default_503_backoff_seconds
                        * (2 ** attempt)
                    )

                self.pacer.defer(
                    model,
                    delay,
                )

                attempt += 1


class StructuredChimera(
    resilient.ResilientChimera
):
    def _gateway(
        self,
        budget: core.RunBudget,
    ) -> StructuredGateway:
        return StructuredGateway(
            budget=budget,
            timeout_seconds=self.timeout_seconds,
            max_tokens=self.max_tokens,
            temperature=self.temperature,
            traces=self.traces,
        )

    async def _structured_call(
        self,
        *,
        run_id: str,
        gateway: StructuredGateway,
        model: str,
        system_prompt: str,
        user_prompt: str,
        phase: str,
        generation: int,
    ) -> tuple[
        dict[str, Any],
        str,
        int,
        int,
        int,
        float | None,
    ]:
        retries = env_int(
            "SAVANT_CHIMERA_STRUCTURED_RETRIES",
            default_structured_retries,
        )

        attempt = 0
        current_system = system_prompt

        while True:
            (
                raw,
                latency_ms,
                prompt_tokens,
                completion_tokens,
                response_cost,
            ) = await gateway.complete(
                model,
                current_system,
                user_prompt,
            )

            self.store.event(
                run_id,
                f"{phase}_raw_response",
                "model_response_to_strict_structured_boundary",
                {
                    "model": model,
                    "phase": phase,
                    "attempt": attempt + 1,
                    "raw_text": raw,
                    "raw_length": len(raw),
                    "latency_ms": latency_ms,
                    "prompt_tokens": prompt_tokens,
                    "completion_tokens": completion_tokens,
                    "known_response_cost": response_cost,
                    "strict_top_level_parser": True,
                },
                generation,
            )

            try:
                parsed = (
                    extract_top_level_json_object(
                        raw
                    )
                )

                validate_phase_shape(
                    phase,
                    parsed,
                )

                self.store.event(
                    run_id,
                    f"{phase}_structured_response_valid",
                    "strict_structured_boundary_to_projection",
                    {
                        "model": model,
                        "phase": phase,
                        "attempt": attempt + 1,
                        "top_level_keys": sorted(
                            parsed.keys()
                        ),
                    },
                    generation,
                )

                return (
                    parsed,
                    raw,
                    latency_ms,
                    prompt_tokens,
                    completion_tokens,
                    response_cost,
                )

            except ValueError as exc:
                self.store.event(
                    run_id,
                    f"{phase}_structured_response_invalid",
                    "strict_structured_boundary_failure",
                    {
                        "model": model,
                        "phase": phase,
                        "attempt": attempt + 1,
                        "error": str(exc),
                        "raw_length": len(raw),
                        "raw_prefix": raw[:1000],
                        "raw_suffix": (
                            raw[-1000:]
                            if len(raw) > 1000
                            else raw
                        ),
                    },
                    generation,
                )

                if attempt >= retries:
                    raise

                attempt += 1

                if phase == "tribunal":
                    repair_instruction = """
Your prior output was incomplete or structurally invalid.

Return exactly one COMPLETE JSON object.

Every supplied claim_id must appear exactly once in verdicts.

Use extremely short rationales, maximum 12 words.
Use an empty required_test unless a test is essential.
Omit no required top-level key.
Do not write prose outside JSON.
Do not place JSON inside markdown.
Do not stop before the final closing brace.
""".strip()

                elif phase == "synthesis":
                    repair_instruction = """
Your prior output was incomplete or structurally invalid.

Return exactly one COMPLETE JSON object.

Keep answer below 120 words.
Keep each unknown below 12 words.
Keep each next test below 16 words.
Use claim IDs instead of repeating claim text.
Omit no required top-level key.
Do not write prose outside JSON.
Do not place JSON inside markdown.
Do not stop before the final closing brace.
""".strip()

                else:
                    repair_instruction = """
Return one complete valid JSON object only.
Do not emit markdown or surrounding prose.
""".strip()

                current_system = (
                    system_prompt
                    + "\n\n"
                    + repair_instruction
                )


def main() -> int:
    parser = core.build_parser()
    args = parser.parse_args()

    models = core.selected_models(
        args.models
    )

    if (
        args.command
        in {
            "run",
            "dry-run",
        }
        and not models
    ):
        print(
            "no models configured; set "
            "SAVANT_CHIMERA_MODELS or pass --models",
            file=sys.stderr,
        )
        return 2

    if args.command == "replay":
        store = core.ChimeraStore(
            core.database_path
        )

        result = store.replay(
            args.run_id
        )

        if result is None:
            print(
                f"unknown run: {args.run_id}",
                file=sys.stderr,
            )
            return 1

        print(
            json.dumps(
                result,
                indent=2,
                ensure_ascii=False,
            )
        )
        return 0

    if args.command == "capabilities":
        store = core.ChimeraStore(
            core.database_path
        )

        print(
            json.dumps(
                store.capability_matrix(),
                indent=2,
                ensure_ascii=False,
            )
        )
        return 0

    chimera = StructuredChimera(
        models=models,
        max_parallel=args.max_parallel,
        max_calls=args.max_calls,
        timeout_seconds=args.timeout,
        max_tokens=args.max_tokens,
        conflict_threshold=args.conflict_threshold,
        temperature=args.temperature,
    )

    if args.command == "dry-run":
        result = chimera.dry_run(
            args.problem
        )

        result["structured_boundary"] = {
            "strict_top_level_json": True,
            "nested_object_salvage": False,
            "phase_schema_validation": True,
            "gemini_minimal_reasoning": True,
            "structured_max_tokens": env_int(
                "SAVANT_CHIMERA_STRUCTURED_MAX_TOKENS",
                default_structured_max_tokens,
            ),
        }

        print(
            json.dumps(
                result,
                indent=2,
                ensure_ascii=False,
            )
        )

        return 0

    if args.command == "run":
        result = asyncio.run(
            chimera.run(
                args.problem
            )
        )

        print(
            json.dumps(
                result,
                indent=2,
                ensure_ascii=False,
            )
        )

        return 0

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
