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
    ]
