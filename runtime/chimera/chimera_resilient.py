#!/usr/bin/env python3

from __future__ import annotations

import asyncio
import json
import os
import re
import sys
import time
from dataclasses import asdict
from typing import Any, Sequence

import chimera as core


default_transient_retries = 2
default_structured_retries = 1
default_gemini_36_flash_rpm = 5.0
default_503_backoff_seconds = 2.0


def env_float(name: str, default: float) -> float:
    raw = os.environ.get(name, "").strip()

    if not raw:
        return default

    try:
        value = float(raw)
    except ValueError:
        return default

    if value <= 0:
        return default

    return value


def env_int(name: str, default: int) -> int:
    raw = os.environ.get(name, "").strip()

    if not raw:
        return default

    try:
        value = int(raw)
    except ValueError:
        return default

    return max(value, 0)


def model_environment_key(model: str) -> str:
    normalized = re.sub(
        r"[^A-Za-z0-9]+",
        "_",
        model,
    ).strip("_").upper()

    return f"SAVANT_CHIMERA_RPM_{normalized}"


def configured_model_rpm(model: str) -> float | None:
    specific_key = model_environment_key(model)
    specific = os.environ.get(specific_key, "").strip()

    if specific:
        try:
            value = float(specific)
        except ValueError:
            value = 0.0

        if value > 0:
            return value

    generic = os.environ.get(
        "SAVANT_CHIMERA_MODEL_RPM",
        "",
    ).strip()

    if generic:
        try:
            value = float(generic)
        except ValueError:
            value = 0.0

        if value > 0:
            return value

    if model == "gemini/gemini-3.6-flash":
        return env_float(
            "SAVANT_CHIMERA_GEMINI_36_FLASH_RPM",
            default_gemini_36_flash_rpm,
        )

    return None


def retry_after_seconds(error: str) -> float | None:
    patterns = (
        r'"retryDelay"\s*:\s*"([0-9]+(?:\.[0-9]+)?)s"',
        r"retry\s+in\s+([0-9]+(?:\.[0-9]+)?)s",
        r"retry\s+after\s+([0-9]+(?:\.[0-9]+)?)s",
    )

    for pattern in patterns:
        match = re.search(
            pattern,
            error,
            flags=re.IGNORECASE,
        )

        if match:
            try:
                return max(float(match.group(1)), 0.0)
            except ValueError:
                pass

    return None


def quota_is_structurally_zero(error: str) -> bool:
    normalized = error.casefold()

    return any(
        marker in normalized
        for marker in (
            "limit: 0",
            '"quotavalue": "0"',
            '"quotavalue":"0"',
        )
    )


def classify_provider_error(error: BaseException) -> str:
    text = f"{type(error).__name__}: {error}".casefold()

    if "404" in text or "notfounderror" in text or "not_found" in text:
        return "not_found"

    if (
        "429" in text
        or "ratelimiterror" in text
        or "resource_exhausted" in text
    ):
        if quota_is_structurally_zero(text):
            return "quota_zero"

        return "rate_limited"

    if (
        "503" in text
        or "serviceunavailableerror" in text
        or '"status": "unavailable"' in text
        or '"status":"unavailable"' in text
    ):
        return "service_unavailable"

    if (
        "401" in text
        or "403" in text
        or "authentication" in text
        or "permission_denied" in text
    ):
        return "authorization"

    if isinstance(error, asyncio.TimeoutError):
        return "timeout"

    return "provider_error"


def safe_text(value: Any) -> str:
    if value is None:
        return ""

    if isinstance(value, str):
        return value

    if isinstance(value, list):
        parts = []

        for item in value:
            if isinstance(item, str):
                parts.append(item)
                continue

            if isinstance(item, dict):
                text = item.get("text")

                if isinstance(text, str):
                    parts.append(text)

        return "\n".join(parts)

    if isinstance(value, dict):
        text = value.get("text")

        if isinstance(text, str):
            return text

    return str(value)


def extract_json_object_resilient(text: str) -> dict[str, Any]:
    text = text.strip()

    if not text:
        raise ValueError("model response was empty")

    try:
        return core.extract_json_object(text)
    except ValueError:
        pass

    candidates = []

    fenced = re.findall(
        r"```(?:json)?\s*(.*?)```",
        text,
        flags=re.IGNORECASE | re.DOTALL,
    )

    candidates.extend(fenced)

    first = text.find("{")
    last = text.rfind("}")

    if first >= 0 and last > first:
        candidates.append(text[first : last + 1])

    decoder = json.JSONDecoder()

    for candidate in candidates:
        candidate = candidate.strip()

        if not candidate:
            continue

        try:
            value = json.loads(candidate)
        except json.JSONDecodeError:
            value = None

        if isinstance(value, dict):
            return value

        for index, character in enumerate(candidate):
            if character != "{":
                continue

            try:
                value, _ = decoder.raw_decode(candidate[index:])
            except json.JSONDecodeError:
                continue

            if isinstance(value, dict):
                return value

    if first >= 0 and last < first:
        raise ValueError(
            "model response contained an unterminated JSON object"
        )

    raise ValueError(
        "model response did not contain a recoverable valid JSON object"
    )


class ProviderPacer:
    def __init__(self) -> None:
        self._locks: dict[str, asyncio.Lock] = {}
        self._next_start: dict[str, float] = {}

    async def wait(self, model: str) -> None:
        rpm = configured_model_rpm(model)

        if rpm is None:
            return

        interval = 60.0 / rpm

        lock = self._locks.setdefault(
            model,
            asyncio.Lock(),
        )

        async with lock:
            now = time.monotonic()
            allowed = self._next_start.get(model, now)

            if allowed > now:
                await asyncio.sleep(allowed - now)

            started = time.monotonic()

            self._next_start[model] = started + interval

    def defer(
        self,
        model: str,
        seconds: float,
    ) -> None:
        if seconds <= 0:
            return

        target = time.monotonic() + seconds
        current = self._next_start.get(model, 0.0)

        self._next_start[model] = max(
            current,
            target,
        )


class ResilientGateway(core.Gateway):
    def __init__(
        self,
        budget: core.RunBudget,
        timeout_seconds: float,
        max_tokens: int,
        temperature: float,
        traces: core.TraceAdapter,
    ) -> None:
        super().__init__(
            budget=budget,
            timeout_seconds=timeout_seconds,
            max_tokens=max_tokens,
            temperature=temperature,
            traces=traces,
        )

        self.pacer = ProviderPacer()
        self.transient_retries = env_int(
            "SAVANT_CHIMERA_TRANSIENT_RETRIES",
            default_transient_retries,
        )

    @staticmethod
    def _is_gemini_three_or_newer(model: str) -> bool:
        match = re.search(
            r"gemini(?:/|[-_])?gemini-(\d+)",
            model.casefold(),
        )

        if match:
            try:
                return int(match.group(1)) >= 3
            except ValueError:
                return False

        return "gemini/gemini-3" in model.casefold()

    async def complete(
        self,
        model: str,
        system_prompt: str,
        user_prompt: str,
    ) -> tuple[str, int, int, int, float | None]:
        if core.litellm is None:
            raise RuntimeError(
                "litellm is unavailable; run Chimera through its isolated venv"
            )

        attempt = 0
        total_started = time.monotonic()

        while True:
            await self.pacer.wait(model)

            async with self._budget_lock:
                self.budget.reserve_call()

            started = time.monotonic()

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
                    "max_tokens": self.max_tokens,
                    "timeout": self.timeout_seconds,
                }

                if not self._is_gemini_three_or_newer(model):
                    kwargs["temperature"] = self.temperature

                return core.litellm.completion(**kwargs)

            try:
                with self.traces.span(
                    "chimera.model",
                    {
                        "gen_ai.request.model": model,
                        "savant.authority_effect": core.authority_effect,
                        "savant.chimera.provider_attempt": attempt + 1,
                    },
                ):
                    response = await asyncio.wait_for(
                        asyncio.to_thread(invoke),
                        timeout=self.timeout_seconds + 5.0,
                    )

                latency_ms = int(
                    (time.monotonic() - total_started) * 1000
                )

                message = response.choices[0].message
                content = safe_text(
                    getattr(message, "content", "")
                )

                usage = getattr(response, "usage", None)

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

                if isinstance(hidden, dict):
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
                classification = classify_provider_error(
                    exc
                )

                if classification in {
                    "not_found",
                    "quota_zero",
                    "authorization",
                }:
                    raise

                retryable = classification in {
                    "rate_limited",
                    "service_unavailable",
                    "timeout",
                }

                if (
                    not retryable
                    or attempt >= self.transient_retries
                ):
                    raise

                if classification == "rate_limited":
                    delay = retry_after_seconds(
                        str(exc)
                    )

                    if delay is None:
                        rpm = configured_model_rpm(
                            model
                        )

                        if rpm:
                            delay = 60.0 / rpm
                        else:
                            delay = 15.0

                    delay += 0.5

                elif classification == "service_unavailable":
                    delay = (
                        default_503_backoff_seconds
                        * (2**attempt)
                    )

                else:
                    delay = (
                        default_503_backoff_seconds
                        * (2**attempt)
                    )

                self.pacer.defer(
                    model,
                    delay,
                )

                attempt += 1

                elapsed = time.monotonic() - started

                if elapsed < 0:
                    raise RuntimeError(
                        "monotonic provider timing failure"
                    )


class ResilientChimera(core.Chimera):
    def _gateway(
        self,
        budget: core.RunBudget,
    ) -> ResilientGateway:
        return ResilientGateway(
            budget=budget,
            timeout_seconds=self.timeout_seconds,
            max_tokens=self.max_tokens,
            temperature=self.temperature,
            traces=self.traces,
        )

    @staticmethod
    def _representation_for_role(
        role_name: str,
    ) -> str:
        for role in core.roles:
            if role.name == role_name:
                return role.representation

        return "unknown"

    async def _structured_call(
        self,
        *,
        run_id: str,
        gateway: ResilientGateway,
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
        structured_retries = env_int(
            "SAVANT_CHIMERA_STRUCTURED_RETRIES",
            default_structured_retries,
        )

        attempt = 0

        while True:
            (
                raw,
                latency_ms,
                prompt_tokens,
                completion_tokens,
                response_cost,
            ) = await gateway.complete(
                model,
                system_prompt,
                user_prompt,
            )

            self.store.event(
                run_id,
                f"{phase}_raw_response",
                "model_response_to_structured_boundary",
                {
                    "model": model,
                    "phase": phase,
                    "attempt": attempt + 1,
                    "raw_text": raw,
                    "latency_ms": latency_ms,
                    "prompt_tokens": prompt_tokens,
                    "completion_tokens": completion_tokens,
                    "known_response_cost": response_cost,
                },
                generation,
            )

            try:
                parsed = extract_json_object_resilient(
                    raw
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
                    "structured_boundary_failure",
                    {
                        "model": model,
                        "phase": phase,
                        "attempt": attempt + 1,
                        "error": str(exc),
                        "raw_length": len(raw),
                        "raw_prefix": raw[:1000],
                        "raw_suffix": raw[-1000:]
                        if len(raw) > 1000
                        else raw,
                    },
                    generation,
                )

                if attempt >= structured_retries:
                    raise

                attempt += 1

                system_prompt = (
                    system_prompt
                    + "\n\n"
                    + "Your previous response was not parseable as the "
                    + "required JSON object. Produce a fresh compact answer. "
                    + "Return exactly one complete JSON object. Do not use "
                    + "markdown fences, commentary, preamble, epilogue, or "
                    + "trailing text. Keep rationales concise enough that "
                    + "the JSON object finishes within the output limit."
                )

    async def _tribunal(
        self,
        run_id: str,
        problem: str,
        claims: Sequence[core.Claim],
        gateway: ResilientGateway,
        generation: int,
    ) -> dict[str, Any]:
        model = self.models[
            generation % len(self.models)
        ]

        system_prompt = """
You are a SAVANT Chimera tribunal instance.

AI output is not authority.

Judge atomic claims against supplied evidence, assumptions,
constraints, and competing claims.

Do not use majority vote.
Do not reward a claim because multiple models repeated it.
Unknown must remain unknown.
A claim with no adequate evidence may remain a useful hypothesis,
but it cannot be promoted to fact.

Keep every rationale concise.
Sampling behavior should favor deterministic, conservative,
internally consistent adjudication.

Return exactly one complete JSON object and nothing else:

{
  "verdicts": [
    {
      "claim_id": "claim id",
      "status": "supported|rejected|unresolved",
      "score": 0.0,
      "rationale": "brief reason",
      "required_test": "test needed, or empty string"
    }
  ],
  "cross_claim_conflicts": [
    {
      "left": "claim id",
      "right": "claim id",
      "rationale": "why they conflict",
      "discriminating_test": "minimum useful test"
    }
  ],
  "unknowns": ["unknown"],
  "tribunal_summary": "brief synthesis"
}
""".strip()

        user_prompt = core.canonical_json(
            {
                "problem": problem,
                "claims": self._claims_for_prompt(
                    claims
                ),
            }
        )

        (
            parsed,
            _raw,
            latency_ms,
            prompt_tokens,
            completion_tokens,
            response_cost,
        ) = await self._structured_call(
            run_id=run_id,
            gateway=gateway,
            model=model,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            phase="tribunal",
            generation=generation,
        )

        verdicts = []

        for verdict in parsed.get(
            "verdicts",
            [],
        ):
            if not isinstance(
                verdict,
                dict,
            ):
                continue

            claim_id = str(
                verdict.get(
                    "claim_id",
                    "",
                )
            ).strip()

            status = str(
                verdict.get(
                    "status",
                    "unresolved",
                )
            ).strip()

            if status not in {
                "supported",
                "rejected",
                "unresolved",
            }:
                status = "unresolved"

            try:
                score_value = float(
                    verdict.get(
                        "score",
                        0.5,
                    )
                    or 0.5
                )
            except (
                TypeError,
                ValueError,
            ):
                score_value = 0.5

            score = core.clamp(
                score_value,
                0.0,
                1.0,
            )

            normalized = {
                "claim_id": claim_id,
                "status": status,
                "score": score,
                "rationale": str(
                    verdict.get(
                        "rationale",
                        "",
                    )
                ).strip(),
                "required_test": str(
                    verdict.get(
                        "required_test",
                        "",
                    )
                ).strip(),
            }

            verdicts.append(normalized)

            if claim_id:
                self.store.update_claim_status(
                    claim_id,
                    status,
                )

        claim_index = {
            claim.claim_id: claim
            for claim in claims
        }

        for verdict in verdicts:
            claim = claim_index.get(
                verdict["claim_id"]
            )

            if claim is None:
                continue

            observed_instance = core.Instance(
                instance_id=claim.instance_id,
                model=claim.model,
                role=claim.role,
                mood=claim.mood,
                representation=(
                    self._representation_for_role(
                        claim.role
                    )
                ),
                objective="",
            )

            if verdict["status"] == "supported":
                self.store.observe_capability(
                    observed_instance,
                    success_weight=verdict[
                        "score"
                    ],
                    failure_weight=0.0,
                )

            elif verdict["status"] == "rejected":
                self.store.observe_capability(
                    observed_instance,
                    success_weight=0.0,
                    failure_weight=max(
                        verdict["score"],
                        0.25,
                    ),
                )

        validated_conflicts = []

        for conflict in parsed.get(
            "cross_claim_conflicts",
            [],
        ):
            if not isinstance(
                conflict,
                dict,
            ):
                continue

            left = str(
                conflict.get(
                    "left",
                    "",
                )
            ).strip()

            right = str(
                conflict.get(
                    "right",
                    "",
                )
            ).strip()

            if (
                left not in claim_index
                or right not in claim_index
            ):
                continue

            normalized_conflict = {
                "left": left,
                "right": right,
                "rationale": str(
                    conflict.get(
                        "rationale",
                        "",
                    )
                ).strip(),
                "discriminating_test": str(
                    conflict.get(
                        "discriminating_test",
                        "",
                    )
                ).strip(),
            }

            validated_conflicts.append(
                normalized_conflict
            )

            self.store.edge(
                run_id,
                left,
                right,
                "tribunal_contradiction",
                1.0,
                normalized_conflict[
                    "rationale"
                ],
            )

        tribunal = {
            "model": model,
            "generation": generation,
            "verdicts": verdicts,
            "cross_claim_conflicts": validated_conflicts,
            "unknowns": [
                str(value).strip()
                for value in parsed.get(
                    "unknowns",
                    [],
                )
                if str(value).strip()
            ],
            "tribunal_summary": str(
                parsed.get(
                    "tribunal_summary",
                    "",
                )
            ).strip(),
            "latency_ms": latency_ms,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "known_response_cost": response_cost,
        }

        self.store.event(
            run_id,
            "tribunal_complete",
            "claims_to_verdicts",
            tribunal,
            generation,
        )

        return tribunal

    async def _synthesize(
        self,
        run_id: str,
        problem: str,
        claims: Sequence[core.Claim],
        tribunals: Sequence[
            dict[str, Any]
        ],
        gateway: ResilientGateway,
    ) -> dict[str, Any]:
        synthesis_model = self.models[-1]

        system_prompt = """
You are the final synthesis instance of SAVANT Chimera.

You receive a problem, atomic claims, and tribunal outputs.

You are not authority.
Do not conceal unresolved conflicts.
Do not convert model agreement into truth.
Prefer surviving evidence-backed claims.
Preserve rejected claims as negative knowledge.
Preserve unresolved claims as unresolved.
Do not fabricate citations or validation.

Keep the answer and lists concise enough to guarantee a complete
JSON response.

Return exactly one complete JSON object and nothing else:

{
  "answer": "best current synthesis",
  "supported_claim_ids": ["claim id"],
  "rejected_claim_ids": ["claim id"],
  "unresolved_claim_ids": ["claim id"],
  "unknowns": ["material unknown"],
  "next_tests": ["minimum discriminating test"],
  "confidence": 0.0,
  "authority_effect": "none"
}
""".strip()

        user_prompt = core.canonical_json(
            {
                "problem": problem,
                "claims": self._claims_for_prompt(
                    claims
                ),
                "tribunals": list(
                    tribunals
                ),
            }
        )

        (
            parsed,
            _raw,
            latency_ms,
            prompt_tokens,
            completion_tokens,
            response_cost,
        ) = await self._structured_call(
            run_id=run_id,
            gateway=gateway,
            model=synthesis_model,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            phase="synthesis",
            generation=len(tribunals) + 1,
        )

        parsed[
            "authority_effect"
        ] = "none"

        parsed[
            "model"
        ] = synthesis_model

        parsed[
            "latency_ms"
        ] = latency_ms

        parsed[
            "prompt_tokens"
        ] = prompt_tokens

        parsed[
            "completion_tokens"
        ] = completion_tokens

        parsed[
            "known_response_cost"
        ] = response_cost

        self.store.event(
            run_id,
            "synthesis_complete",
            "verdicts_to_projection",
            parsed,
            len(tribunals) + 1,
        )

        return parsed

    async def run(
        self,
        problem: str,
    ) -> dict[str, Any]:
        problem = problem.strip()

        if not problem:
            raise ValueError(
                "problem cannot be empty"
            )

        instances = self._make_instances()

        configuration = {
            "schema": core.schema_version,
            "problem": problem,
            "models": self.models,
            "roles": [
                asdict(instance)
                for instance in instances
            ],
            "max_parallel": self.max_parallel,
            "max_calls": self.max_calls,
            "timeout_seconds": self.timeout_seconds,
            "max_tokens": self.max_tokens,
            "conflict_threshold": self.conflict_threshold,
            "temperature": self.temperature,
            "resilience": {
                "transient_retries": env_int(
                    "SAVANT_CHIMERA_TRANSIENT_RETRIES",
                    default_transient_retries,
                ),
                "structured_retries": env_int(
                    "SAVANT_CHIMERA_STRUCTURED_RETRIES",
                    default_structured_retries,
                ),
                "provider_pacing": True,
            },
        }

        run_fingerprint = core.fingerprint(
            configuration
        )

        run_id = (
            f"chimera_{core.uuid.uuid4().hex}"
        )

        self.store.create_run(
            run_id,
            run_fingerprint,
            problem,
            self.models,
        )

        self.store.event(
            run_id,
            "run_started",
            "problem_to_cognitive_topology",
            {
                "fingerprint": run_fingerprint,
                "instances": [
                    asdict(instance)
                    for instance in instances
                ],
                "authority_effect": (
                    core.authority_effect
                ),
                "resilient_gateway": True,
            },
        )

        budget = core.RunBudget(
            max_calls=self.max_calls
        )

        gateway = self._gateway(
            budget
        )

        semaphore = asyncio.Semaphore(
            self.max_parallel
        )

        try:
            with self.traces.span(
                "chimera.run",
                {
                    "savant.chimera.run_id": run_id,
                    "savant.authority_effect": (
                        core.authority_effect
                    ),
                },
            ):
                tasks = [
                    self._run_instance(
                        run_id,
                        problem,
                        instance,
                        gateway,
                        semaphore,
                    )
                    for instance in instances
                ]

                blind_results = await asyncio.gather(
                    *tasks
                )

                successful = [
                    result
                    for result in blind_results
                    if (
                        result.error is None
                        and result.claims
                    )
                ]

                if not successful:
                    raise RuntimeError(
                        "all blind cognitive instances failed "
                        "or returned no claims"
                    )

                all_claims = [
                    claim
                    for result in successful
                    for claim in result.claims
                ]

                graph_metrics = (
                    self._derive_claim_edges(
                        run_id,
                        all_claims,
                    )
                )

                self.store.event(
                    run_id,
                    "claim_graph_projected",
                    "claims_to_conflict_topology",
                    graph_metrics,
                    1,
                )

                tribunals = []

                tribunal_one = await self._tribunal(
                    run_id,
                    problem,
                    all_claims,
                    gateway,
                    generation=1,
                )

                tribunals.append(
                    tribunal_one
                )

                unresolved_count = sum(
                    1
                    for verdict in tribunal_one.get(
                        "verdicts",
                        [],
                    )
                    if verdict.get(
                        "status"
                    )
                    == "unresolved"
                )

                verdict_count = max(
                    len(
                        tribunal_one.get(
                            "verdicts",
                            [],
                        )
                    ),
                    1,
                )

                unresolved_ratio = (
                    unresolved_count
                    / verdict_count
                )

                escalation_required = (
                    graph_metrics[
                        "conflict_ratio"
                    ]
                    >= self.conflict_threshold
                    or unresolved_ratio >= 0.35
                )

                if (
                    escalation_required
                    and budget.calls
                    < budget.max_calls
                    and len(self.models) > 1
                ):
                    self.store.event(
                        run_id,
                        "escalation_triggered",
                        "epistemic_pressure_to_new_generation",
                        {
                            "conflict_ratio": (
                                graph_metrics[
                                    "conflict_ratio"
                                ]
                            ),
                            "unresolved_ratio": (
                                unresolved_ratio
                            ),
                        },
                        2,
                    )

                    tribunal_two = await self._tribunal(
                        run_id,
                        problem,
                        all_claims,
                        gateway,
                        generation=2,
                    )

                    tribunals.append(
                        tribunal_two
                    )

                synthesis = await self._synthesize(
                    run_id,
                    problem,
                    all_claims,
                    tribunals,
                    gateway,
                )

                result = {
                    "schema": core.schema_version,
                    "run_id": run_id,
                    "fingerprint": run_fingerprint,
                    "authority_effect": (
                        core.authority_effect
                    ),
                    "answer": synthesis.get(
                        "answer",
                        "",
                    ),
                    "confidence": synthesis.get(
                        "confidence"
                    ),
                    "supported_claim_ids": synthesis.get(
                        "supported_claim_ids",
                        [],
                    ),
                    "rejected_claim_ids": synthesis.get(
                        "rejected_claim_ids",
                        [],
                    ),
                    "unresolved_claim_ids": synthesis.get(
                        "unresolved_claim_ids",
                        [],
                    ),
                    "unknowns": synthesis.get(
                        "unknowns",
                        [],
                    ),
                    "next_tests": synthesis.get(
                        "next_tests",
                        [],
                    ),
                    "graph_metrics": graph_metrics,
                    "blind_instances": [
                        {
                            "instance": asdict(
                                result.instance
                            ),
                            "claim_ids": [
                                claim.claim_id
                                for claim
                                in result.claims
                            ],
                            "summary": (
                                result.summary
                            ),
                            "unknowns": (
                                result.unknowns
                            ),
                            "error": result.error,
                            "latency_ms": (
                                result.latency_ms
                            ),
                        }
                        for result
                        in blind_results
                    ],
                    "tribunals": tribunals,
                    "budget": {
                        "calls": budget.calls,
                        "max_calls": (
                            budget.max_calls
                        ),
                        "prompt_tokens": (
                            budget.prompt_tokens
                        ),
                        "completion_tokens": (
                            budget.completion_tokens
                        ),
                        "known_cost": (
                            budget.known_cost
                        ),
                    },
                    "resilience": {
                        "provider_pacing": True,
                        "structured_response_recovery": True,
                        "transient_provider_recovery": True,
                        "raw_structured_responses_persisted": True,
                        "capability_representation_preserved": True,
                    },
                }

                self.store.finish_run(
                    run_id,
                    result,
                )

                return result

        except Exception as exc:
            self.store.fail_run(
                run_id,
                f"{type(exc).__name__}: {exc}",
            )
            raise


def main() -> int:
    parser = core.build_parser()
    args = parser.parse_args()

    models = core.selected_models(
        args.models
    )

    if (
        args.command in {
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

    chimera = ResilientChimera(
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

        result["resilience"] = {
            "provider_pacing": True,
            "transient_provider_recovery": True,
            "structured_response_recovery": True,
            "raw_structured_responses_persisted": True,
            "capability_representation_preserved": True,
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
