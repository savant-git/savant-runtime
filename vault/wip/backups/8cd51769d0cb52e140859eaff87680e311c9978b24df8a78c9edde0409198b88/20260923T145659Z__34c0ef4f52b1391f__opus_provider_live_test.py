from __future__ import annotations

import importlib
import json
import sys
import time
import traceback
from typing import Any, Callable


ROOT = "/root/savant-runtime"

if ROOT not in sys.path:
    sys.path.insert(
        0,
        ROOT,
    )


PROVIDER_PACKAGE = (
    "ontology.obelisks._template.segue.gates._template."
    "segue.innates._template.segue.exiles.opus.runtime.providers"
)


def provider_module(
    name: str,
) -> Any:
    return importlib.import_module(
        f"{PROVIDER_PACKAGE}.{name}"
    )


anthropic_text = provider_module(
    "anthropic_text"
)
openai_text = provider_module(
    "openai_text"
)
deepseek_text = provider_module(
    "deepseek_text"
)
groq_text = provider_module(
    "groq_text"
)
fireworks_text = provider_module(
    "fireworks_text"
)
venice_uncensored_text = provider_module(
    "venice_uncensored_text"
)
elevenlabs_tts = provider_module(
    "elevenlabs_tts"
)
openai_tts = provider_module(
    "openai_tts"
)


# Use Savant's existing environment loader rather than parsing,
# printing, or otherwise exposing the environment file here.
openai_tts.load_environment()


TEXT_REQUEST = {
    "message": (
        "Reply with exactly: "
        "savant-provider-live"
    ),
    "system": (
        "This is a minimal Savant provider connectivity probe. "
        "Follow the requested response exactly."
    ),
    "max_tokens": 32,
}


TTS_REQUEST = {
    "text": "Savant provider live.",
}


def clean_error(
    exc: BaseException,
) -> str:
    value = (
        f"{type(exc).__name__}: {exc}"
    )

    # Never emit multiline provider payloads or large remote bodies.
    value = " ".join(
        value.split()
    )

    if len(value) > 240:
        value = (
            value[:237]
            + "..."
        )

    return value


def text_preview(
    value: Any,
) -> str:
    text = " ".join(
        str(
            value
            or ""
        ).split()
    )

    if len(text) > 80:
        return (
            text[:77]
            + "..."
        )

    return text


def run_probe(
    *,
    name: str,
    available: Callable[[], bool],
    execute: Callable[
        [dict[str, Any], dict[str, Any]],
        dict[str, Any],
    ],
    request: dict[str, Any],
    provider: dict[str, Any],
    audio: bool = False,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "provider": name,
        "configured": False,
        "status": "not-run",
        "model": "",
        "latency_seconds": 0.0,
        "response": "",
    }

    try:
        result["configured"] = bool(
            available()
        )
    except Exception as exc:
        result["status"] = "availability-error"
        result["response"] = clean_error(
            exc
        )
        return result

    if not result["configured"]:
        result["status"] = "not-configured"
        result["response"] = (
            "provider reports required credential/configuration unavailable"
        )
        return result

    started = time.monotonic()

    try:
        response = execute(
            dict(request),
            dict(provider),
        )

        elapsed = (
            time.monotonic()
            - started
        )

        result["latency_seconds"] = round(
            elapsed,
            3,
        )

        if not isinstance(
            response,
            dict,
        ):
            result["status"] = "invalid-response"
            result["response"] = (
                f"returned {type(response).__name__}"
            )
            return result

        result["model"] = str(
            response.get(
                "model",
                "",
            )
            or ""
        )

        if audio:
            payload = response.get(
                "audio"
            )

            if isinstance(
                payload,
                (
                    bytes,
                    bytearray,
                ),
            ) and payload:
                result["status"] = "ok"
                result["response"] = (
                    f"{len(payload):,} audio bytes"
                )
            else:
                result["status"] = "invalid-response"
                result["response"] = (
                    "no audio bytes returned"
                )

            return result

        returned_text = text_preview(
            response.get(
                "text",
                "",
            )
        )

        if response.get(
            "ok"
        ) and returned_text:
            result["status"] = "ok"
            result["response"] = returned_text
        else:
            result["status"] = "invalid-response"
            result["response"] = (
                returned_text
                or "no text returned"
            )

        return result

    except Exception as exc:
        result["latency_seconds"] = round(
            time.monotonic()
            - started,
            3,
        )
        result["status"] = "failed"
        result["response"] = clean_error(
            exc
        )
        return result


def print_result(
    result: dict[str, Any],
) -> None:
    provider = str(
        result["provider"]
    )

    status = str(
        result["status"]
    )

    model = str(
        result["model"]
        or "-"
    )

    latency = (
        f"{result['latency_seconds']:.3f}s"
    )

    response = str(
        result["response"]
        or "-"
    )

    print(
        f"{provider:<16} "
        f"{status:<18} "
        f"{latency:<10} "
        f"{model}"
    )

    print(
        f"{'':<16} "
        f"{response}"
    )


def main() -> int:
    timeout = 30

    probes = (
        {
            "name": "fireworks",
            "available": fireworks_text.available,
            "execute": fireworks_text.infer,
            "request": TEXT_REQUEST,
            "provider": {
                "env_key": "FIREWORKS_API_KEY",
                "model_env": "SAVANT_FIREWORKS_MODEL",
                "model_default": (
                    "accounts/fireworks/models/deepseek-v4-pro"
                ),
                "timeout_seconds": timeout,
            },
        },
        {
            "name": "openai",
            "available": openai_text.available,
            "execute": openai_text.infer,
            "request": TEXT_REQUEST,
            "provider": {
                "env_key": "OPENAI_API_KEY",
                "model_env": "SAVANT_MODEL",
                "model_default": "gpt-5",
                "timeout_seconds": timeout,
            },
        },
        {
            "name": "anthropic",
            "available": anthropic_text.available,
            "execute": anthropic_text.infer,
            "request": TEXT_REQUEST,
            "provider": {
                "env_key": "ANTHROPIC_API_KEY",
                "model_env": "SAVANT_ANTHROPIC_MODEL",
                "model_default": (
                    "claude-sonnet-4-20250514"
                ),
                "max_tokens": 32,
                "timeout_seconds": timeout,
            },
        },
        {
            "name": "deepseek",
            "available": deepseek_text.available,
            "execute": deepseek_text.infer,
            "request": TEXT_REQUEST,
            "provider": {
                "env_key": "DEEPSEEK_API_KEY",
                "model_env": "SAVANT_DEEPSEEK_MODEL",
                "model_default": "deepseek-v4-pro",
                "timeout_seconds": timeout,
            },
        },
        {
            "name": "groq",
            "available": groq_text.available,
            "execute": groq_text.infer,
            "request": TEXT_REQUEST,
            "provider": {
                "env_key": "GROQ_API_KEY",
                "model_env": "SAVANT_GROQ_MODEL",
                "model_default": "openai/gpt-oss-120b",
                "timeout_seconds": timeout,
            },
        },
        {
            "name": "venice",
            "available": venice_uncensored_text.available,
            "execute": venice_uncensored_text.infer,
            "request": TEXT_REQUEST,
            "provider": {
                "env_key": "VENICE_API_KEY",
                "timeout_seconds": timeout,
            },
        },
        {
            "name": "elevenlabs",
            "available": elevenlabs_tts.available,
            "execute": elevenlabs_tts.synthesize,
            "request": TTS_REQUEST,
            "provider": {
                "model_default": "eleven_multilingual_v2",
                "timeout_seconds": timeout,
            },
            "audio": True,
        },
        {
            "name": "openai-tts",
            "available": openai_tts.available,
            "execute": openai_tts.synthesize,
            "request": TTS_REQUEST,
            "provider": {
                "model_default": "gpt-4o-mini-tts",
                "voice_default": "alloy",
                "timeout_seconds": timeout,
            },
            "audio": True,
        },
    )

    print()
    print(
        "savant // opus provider live verification"
    )
    print(
        "=" * 72
    )
    print(
        f"{'provider':<16} "
        f"{'status':<18} "
        f"{'latency':<10} "
        f"model"
    )
    print(
        "-" * 72
    )

    results: list[
        dict[str, Any]
    ] = []

    for probe in probes:
        result = run_probe(
            name=probe["name"],
            available=probe["available"],
            execute=probe["execute"],
            request=probe["request"],
            provider=probe["provider"],
            audio=bool(
                probe.get(
                    "audio",
                    False,
                )
            ),
        )

        results.append(
            result
        )

        print_result(
            result
        )

        print(
            "-" * 72
        )

    successful = [
        result
        for result in results
        if result["status"] == "ok"
    ]

    failed = [
        result
        for result in results
        if result["status"] != "ok"
    ]

    print()
    print(
        "summary"
    )
    print(
        f"working: "
        f"{len(successful)}/"
        f"{len(results)}"
    )

    if successful:
        print(
            "live: "
            + ", ".join(
                str(
                    result["provider"]
                )
                for result
                in successful
            )
        )

    if failed:
        print(
            "not proven: "
            + ", ".join(
                (
                    f"{result['provider']}"
                    f"({result['status']})"
                )
                for result
                in failed
            )
        )

    print()

    # This is a diagnostic probe. A provider failure is represented
    # in the result matrix rather than aborting later provider tests.
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(
            main()
        )
    except KeyboardInterrupt:
        print(
            "\nprovider verification interrupted",
            file=sys.stderr,
        )
        raise SystemExit(
            130
        )
    except Exception:
        traceback.print_exc()
        raise SystemExit(
            1
        )
