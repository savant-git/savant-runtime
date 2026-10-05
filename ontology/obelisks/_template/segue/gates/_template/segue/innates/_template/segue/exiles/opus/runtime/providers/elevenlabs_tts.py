from __future__ import annotations

import json
import urllib.request
from typing import Any, Dict

from environment import first, get, load_environment
from providers.base import ProviderError, voice_prompt


def api_key() -> str:
    load_environment()

    _, value = first(
        "ELEVENLABS_SERVER_KEY",
        "ELEVENLABS_API_KEY",
    )

    return value or ""


def available() -> bool:
    return bool(
        api_key()
    )


def synthesize(
    request: Dict[str, Any],
    provider: Dict[str, Any],
) -> Dict[str, Any]:
    load_environment()

    key = api_key()

    if not key:
        raise ProviderError(
            "ELEVENLABS_SERVER_KEY or "
            "ELEVENLABS_API_KEY missing"
        )

    voice = request.get(
        "voice"
    ) or {}

    voice_id = (
        voice.get(
            "elevenlabs_voice_id"
        )
        or get(
            "ELEVENLABS_DEFAULT_VOICE_ID"
        )
    )

    if not voice_id:
        raise ProviderError(
            "ELEVENLABS_DEFAULT_VOICE_ID "
            "or voice.elevenlabs_voice_id missing"
        )

    model = (
        voice.get(
            "elevenlabs_model"
        )
        or provider.get(
            "model_default"
        )
        or "eleven_multilingual_v2"
    )

    payload = {
        "text": voice_prompt(
            request
        ),
        "model_id": model,
        "voice_settings": {
            "stability": float(
                voice.get(
                    "stability",
                    0.5,
                )
            ),
            "similarity_boost": float(
                voice.get(
                    "similarity_boost",
                    0.75,
                )
            ),
            "style": float(
                voice.get(
                    "style",
                    0.25,
                )
            ),
            "use_speaker_boost": True,
        },
    }

    req = urllib.request.Request(
        (
            "https://api.elevenlabs.io/v1/"
            f"text-to-speech/{voice_id}"
        ),
        data=json.dumps(
            payload
        ).encode(
            "utf-8"
        ),
        headers={
            "Content-Type": (
                "application/json"
            ),
            "xi-api-key": key,
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
        "provider": "elevenlabs_tts",
        "model": model,
        "voice": voice_id,
        "mime_type": "audio/mpeg",
        "audio": audio,
    }
