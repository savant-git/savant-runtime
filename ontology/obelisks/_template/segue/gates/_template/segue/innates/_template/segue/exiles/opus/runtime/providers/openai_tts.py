from __future__ import annotations

import json
import urllib.request
from typing import Any, Dict

from environment import get, load_environment
from providers.base import ProviderError, voice_prompt


def available() -> bool:
    load_environment()
    return bool(
        get("OPENAI_API_KEY")
    )


def synthesize(
    request: Dict[str, Any],
    provider: Dict[str, Any],
) -> Dict[str, Any]:
    load_environment()

    api_key = get(
        "OPENAI_API_KEY"
    )

    if not api_key:
        raise ProviderError(
            "OPENAI_API_KEY missing"
        )

    voice = request.get(
        "voice"
    ) or {}

    model_env = str(
        voice.get(
            "model_env"
        )
        or ""
    )

    voice_env = str(
        voice.get(
            "voice_env"
        )
        or ""
    )

    model = (
        get(model_env)
        if model_env
        else None
    ) or voice.get(
        "model_default"
    ) or provider.get(
        "model_default"
    ) or "gpt-4o-mini-tts"

    voice_name = (
        get(voice_env)
        if voice_env
        else None
    ) or voice.get(
        "voice_default"
    ) or provider.get(
        "voice_default"
    ) or "alloy"

    payload = {
        "model": model,
        "voice": voice_name,
        "input": voice_prompt(
            request
        ),
        "format": "mp3",
    }

    req = urllib.request.Request(
        "https://api.openai.com/v1/audio/speech",
        data=json.dumps(
            payload
        ).encode(
            "utf-8"
        ),
        headers={
            "Content-Type": (
                "application/json"
            ),
            "Authorization": (
                f"Bearer {api_key}"
            ),
        },
        method="POST",
    )

    with urllib.request.urlopen(
        req,
        timeout=int(
            provider.get(
                "timeout_seconds",
                60,
            )
        ),
    ) as res:
        audio = res.read()

    return {
        "ok": True,
        "provider": "openai_tts",
        "model": model,
        "voice": voice_name,
        "mime_type": "audio/mpeg",
        "audio": audio,
    }
