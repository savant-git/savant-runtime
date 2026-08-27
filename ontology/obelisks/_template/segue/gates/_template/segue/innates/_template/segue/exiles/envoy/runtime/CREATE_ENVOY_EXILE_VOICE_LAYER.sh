#!/usr/bin/env bash
set -euo pipefail

ROOT="/root/savant-runtime"
EXILES_ROOT="$ROOT/ontology/obelisks/_template/segue/gates/_template/segue/innates/_template/segue/exiles"
ENVOY="$EXILES_ROOT/envoy"

mkdir -p \
  "$ENVOY/runtime" \
  "$ENVOY/registry/personas" \
  "$ENVOY/registry/voices/historical" \
  "$ENVOY/registry/voices/synthetic" \
  "$ENVOY/registry/accents" \
  "$ENVOY/registry/eras" \
  "$ENVOY/registry/pronunciation" \
  "$ENVOY/canon"

cat > "$ENVOY/README.md" <<'MD'
# ENVOY EXILE

Envoy owns persona management, identity presentation, voice selection,
persona-specific speech style, and historical/persona voice approximation.

Palaver does not own voice identity.

Palaver requests a persona voice from Envoy.

Envoy resolves:

persona
  ↓
voice profile
  ↓
provider
  ↓
model
  ↓
audio response
MD

cat > "$ENVOY/canon/envoy_voice_registry.md" <<'MD'
# ENVOY VOICE REGISTRY
# STATUS: CANON
# AUTHORITY: USER DIRECTIVE
# DOMAIN: ENVOY
# RELATIONSHIP: PALAVER USES ENVOY VOICES

Every Envoy persona must have a unique voice profile.

Historical figures must use research-informed approximation only.

Historical voice profiles must be derived from:

- time period
- birthplace
- region
- class background
- education
- documented language
- accent/dialect evidence
- surviving writing style
- public descriptions of speech where available
- period vocabulary
- rhetorical habits

No profile may claim exact recreation unless licensed direct voice data exists.
MD

cat > "$ENVOY/registry/personas/palaver_default.json" <<'JSON'
{
  "persona_id": "palaver_default",
  "display_name": "Palaver Default",
  "exile": "envoy",
  "voice_ref": "synthetic/palaver_default",
  "description": "Default synthetic Palaver control-plane voice."
}
JSON

cat > "$ENVOY/registry/personas/historical_research_mode.json" <<'JSON'
{
  "persona_id": "historical_research_mode",
  "display_name": "Historical Research Mode",
  "exile": "envoy",
  "voice_ref": "historical/research_mode",
  "description": "Generic research-informed historical approximation mode."
}
JSON

cat > "$ENVOY/registry/voices/synthetic/palaver_default.json" <<'JSON'
{
  "voice_id": "synthetic/palaver_default",
  "provider": "openai",
  "model_env": "OPENAI_TTS_MODEL",
  "model_default": "gpt-4o-mini-tts",
  "voice_env": "OPENAI_TTS_VOICE",
  "voice_default": "alloy",
  "accent": "neutral American English",
  "region": "contemporary networked runtime",
  "era": "modern",
  "cadence": "measured, direct, crisp",
  "vocabulary_style": "technical but plain",
  "formality": "high",
  "rate": 1.0,
  "pitch": 1.0,
  "temperature": 0.3,
  "historical_basis": "Native synthetic Palaver voice. Not based on a real person.",
  "safety_note": "Synthetic assistant voice."
}
JSON

cat > "$ENVOY/registry/voices/historical/research_mode.json" <<'JSON'
{
  "voice_id": "historical/research_mode",
  "provider": "openai",
  "model_env": "OPENAI_TTS_MODEL",
  "model_default": "gpt-4o-mini-tts",
  "voice_env": null,
  "voice_default": "onyx",
  "accent": "research-derived historical approximation",
  "region": "persona-specific",
  "era": "persona-specific",
  "cadence": "period-informed and rhetorically controlled",
  "vocabulary_style": "period-informed",
  "formality": "contextual",
  "rate": 0.92,
  "pitch": 0.95,
  "temperature": 0.45,
  "historical_basis": "Derived from documented time period, birthplace, class background, education, regional accent, surviving writing style, and public descriptions where available.",
  "safety_note": "Approximation only. Does not claim exact recreation of an actual human voice."
}
JSON

cat > "$ENVOY/runtime/voice_engine.py" <<'PY'
from __future__ import annotations

import base64
import json
import os
import urllib.request
from pathlib import Path
from typing import Any, Dict, Optional


ENVOY_ROOT = Path(__file__).resolve().parents[1]
PERSONAS = ENVOY_ROOT / "registry" / "personas"
VOICES = ENVOY_ROOT / "registry" / "voices"


def read_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def persona_path(persona_id: str) -> Path:
    return PERSONAS / f"{persona_id}.json"


def resolve_persona(persona_id: Optional[str]) -> Dict[str, Any]:
    pid = persona_id or "palaver_default"
    path = persona_path(pid)

    if not path.exists():
        path = persona_path("palaver_default")

    return read_json(path)


def resolve_voice(persona_id: Optional[str]) -> Dict[str, Any]:
    persona = resolve_persona(persona_id)
    voice_ref = persona.get("voice_ref", "synthetic/palaver_default")
    path = VOICES / f"{voice_ref}.json"

    if not path.exists():
        path = VOICES / "synthetic" / "palaver_default.json"

    voice = read_json(path)
    voice["persona"] = persona
    return voice


def list_personas() -> list[Dict[str, Any]]:
    rows = []
    for path in sorted(PERSONAS.glob("*.json")):
        rows.append(read_json(path))
    return rows


def env_or_default(env_name: Optional[str], default: str) -> str:
    if env_name:
        return os.getenv(env_name, default)
    return default


def build_voice_prompt(text: str, voice: Dict[str, Any]) -> str:
    persona = voice.get("persona", {})

    return f"""
Persona:
- ID: {persona.get("persona_id")}
- Display name: {persona.get("display_name")}
- Description: {persona.get("description")}

Voice profile:
- Accent: {voice.get("accent")}
- Region: {voice.get("region")}
- Era: {voice.get("era")}
- Cadence: {voice.get("cadence")}
- Vocabulary style: {voice.get("vocabulary_style")}
- Formality: {voice.get("formality")}
- Historical basis: {voice.get("historical_basis")}
- Safety note: {voice.get("safety_note")}

Speak the following text in this voice style.
Do not claim exact recreation of a real person.
Do not claim to be a historical figure.
Do not impersonate a living person.

{text}
""".strip()


def synthesize_openai(text: str, voice: Dict[str, Any]) -> bytes:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is missing")

    model = env_or_default(voice.get("model_env"), voice.get("model_default", "gpt-4o-mini-tts"))
    voice_name = env_or_default(voice.get("voice_env"), voice.get("voice_default", "alloy"))

    payload = {
        "model": model,
        "voice": voice_name,
        "input": build_voice_prompt(text, voice),
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


def synthesize(text: str, persona_id: Optional[str] = None) -> bytes:
    voice = resolve_voice(persona_id)
    provider = voice.get("provider")

    if provider == "openai":
        return synthesize_openai(text, voice)

    raise RuntimeError(f"Unsupported voice provider: {provider}")


def synthesize_base64(text: str, persona_id: Optional[str] = None) -> Dict[str, Any]:
    voice = resolve_voice(persona_id)
    audio = synthesize(text, persona_id)

    return {
        "persona_id": voice["persona"].get("persona_id"),
        "display_name": voice["persona"].get("display_name"),
        "voice": voice,
        "mime_type": "audio/mpeg",
        "audio_base64": base64.b64encode(audio).decode("ascii")
    }
PY

touch "$ENVOY/runtime/__init__.py"

echo "[OK] Envoy exile voice layer created:"
echo "$ENVOY"
find "$ENVOY" -maxdepth 4 -type f | sort
