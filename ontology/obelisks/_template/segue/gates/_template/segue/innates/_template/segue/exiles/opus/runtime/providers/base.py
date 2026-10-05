from __future__ import annotations

from typing import Any, Dict


class ProviderError(RuntimeError):
    pass


def require_text(request: Dict[str, Any]) -> str:
    text = str(request.get("text") or "").strip()
    if not text:
        raise ProviderError("voice request missing text")
    return text


def voice_prompt(request: Dict[str, Any]) -> str:
    text = require_text(request)
    persona = request.get("persona") or {}
    voice = request.get("voice") or {}
    accent = request.get("accent") or {}
    emotion = request.get("emotion") or {}
    language = request.get("language") or {}

    return f"""
Persona:
- ID: {persona.get("persona_id")}
- Display name: {persona.get("display_name")}
- Description: {persona.get("description")}

Voice:
- Accent: {voice.get("accent") or accent.get("accent")}
- Region: {voice.get("region") or accent.get("region")}
- Era: {voice.get("era")}
- Cadence: {voice.get("cadence")}
- Vocabulary style: {voice.get("vocabulary_style")}
- Formality: {voice.get("formality")}
- Language: {language.get("language", "English")}
- Emotion: {emotion.get("label", "neutral")}
- Historical basis: {voice.get("historical_basis")}
- Safety note: {voice.get("safety_note")}

Speak the following text in this voice style.
Do not claim exact recreation of a real person.
Do not claim to be a historical figure.
Do not impersonate a living person.
Apply style subtly, not as caricature.

{text}
""".strip()
