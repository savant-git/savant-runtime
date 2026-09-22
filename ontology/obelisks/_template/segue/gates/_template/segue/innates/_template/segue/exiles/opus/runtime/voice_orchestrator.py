from __future__ import annotations

import json
import os
import urllib.request
from pathlib import Path
from typing import Any, Dict, Optional
from .json_io import read_json


OPUS_ROOT = Path(__file__).resolve().parents[1]
ROUTES = OPUS_ROOT / "registry" / "routes"
PROVIDERS = OPUS_ROOT / "registry" / "providers"


def env_present(key: Optional[str]) -> bool:
    return bool(key and os.getenv(key))


def resolve_provider(route_id: str = "voice_tts_route") -> Dict[str, Any]:
    route = read_json(ROUTES / f"{route_id}.json")
    fallback = route.get("fallback_order") or [route.get("default_provider")]

    for provider_id in fallback:
        if not provider_id:
            continue

        provider = read_json(PROVIDERS / f"{provider_id}.json")

        env_key = provider.get("env_key")
        env_key_priority = provider.get("env_key_priority") or []

        if env_present(env_key):
            provider["selected_env_key"] = env_key
            return provider

        for key in env_key_priority:
            if env_present(key):
                provider["selected_env_key"] = key
                return provider

    raise RuntimeError("No available TTS provider credentials found for Opus voice route.")


def build_voice_prompt(text: str, voice_profile: Dict[str, Any]) -> str:
    persona = voice_profile.get("persona", {})

    return f"""
Persona:
- ID: {persona.get("persona_id")}
- Display name: {persona.get("display_name")}
- Description: {persona.get("description")}

Voice profile:
- Accent: {voice_profile.get("accent")}
- Region: {voice_profile.get("region")}
- Era: {voice_profile.get("era")}
- Cadence: {voice_profile.get("cadence")}
- Vocabulary style: {voice_profile.get("vocabulary_style")}
- Formality: {voice_profile.get("formality")}
- Historical basis: {voice_profile.get("historical_basis")}
- Safety note: {voice_profile.get("safety_note")}

Speak the following text in this voice style.
Do not claim exact recreation of a real person.
Do not claim to be a historical figure.
Do not impersonate a living person.

{text}
""".strip()


def synthesize_openai(text: str, voice_profile: Dict[str, Any], provider: Dict[str, Any]) -> bytes:
    api_key = os.getenv(provider["selected_env_key"])

    model = (
        os.getenv(voice_profile.get("model_env") or "")
        or voice_profile.get("model_default")
        or provider.get("model_default")
        or "gpt-4o-mini-tts"
    )

    voice = (
        os.getenv(voice_profile.get("voice_env") or "")
        or voice_profile.get("voice_default")
        or provider.get("voice_default")
        or "alloy"
    )

    payload = {
        "model": model,
        "voice": voice,
        "input": build_voice_prompt(text, voice_profile),
        "format": "mp3"
    }

    req = urllib.request.Request(
        "https://api.openai.com/v1/audio/speech",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        },
        method="POST"
    )

    with urllib.request.urlopen(req, timeout=60) as res:
        return res.read()


def synthesize_elevenlabs(text: str, voice_profile: Dict[str, Any], provider: Dict[str, Any]) -> bytes:
    api_key = os.getenv(provider["selected_env_key"])

    voice_id = (
        voice_profile.get("elevenlabs_voice_id")
        or os.getenv("ELEVENLABS_DEFAULT_VOICE_ID", "")
    )

    if not voice_id:
        raise RuntimeError("ELEVENLABS_DEFAULT_VOICE_ID or voice_profile.elevenlabs_voice_id is required.")

    model = voice_profile.get("elevenlabs_model") or provider.get("model_default") or "eleven_multilingual_v2"

    payload = {
        "text": build_voice_prompt(text, voice_profile),
        "model_id": model,
        "voice_settings": {
            "stability": float(voice_profile.get("stability", 0.5)),
            "similarity_boost": float(voice_profile.get("similarity_boost", 0.75)),
            "style": float(voice_profile.get("style", 0.25)),
            "use_speaker_boost": True
        }
    }

    req = urllib.request.Request(
        f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "xi-api-key": api_key
        },
        method="POST"
    )

    with urllib.request.urlopen(req, timeout=60) as res:
        return res.read()


def synthesize(text: str, voice_profile: Dict[str, Any]) -> Dict[str, Any]:
    provider = resolve_provider("voice_tts_route")
    provider_id = provider["id"]

    if provider_id == "openai_tts":
        audio = synthesize_openai(text, voice_profile, provider)
    elif provider_id == "elevenlabs_tts":
        audio = synthesize_elevenlabs(text, voice_profile, provider)
    else:
        raise RuntimeError(f"Unsupported Opus TTS provider: {provider_id}")

    return {
        "provider": provider_id,
        "audio": audio,
        "mime_type": "audio/mpeg"
    }
