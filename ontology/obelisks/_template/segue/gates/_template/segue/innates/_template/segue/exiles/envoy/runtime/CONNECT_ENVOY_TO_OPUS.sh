#!/usr/bin/env bash
set -euo pipefail

ROOT="/root/savant-runtime"
EXILES_ROOT="$ROOT/ontology/obelisks/_template/segue/gates/_template/segue/innates/_template/segue/exiles"

ENVOY="$EXILES_ROOT/envoy"
OPUS="$EXILES_ROOT/opus"
PALAVER="$EXILES_ROOT/palaver"

mkdir -p \
  "$ENVOY/runtime" \
  "$ENVOY/api" \
  "$ENVOY/graph" \
  "$ENVOY/lineage" \
  "$ENVOY/authority" \
  "$ENVOY/registry/contracts" \
  "$OPUS/runtime" \
  "$OPUS/registry/providers" \
  "$OPUS/registry/routes" \
  "$OPUS/api" \
  "$OPUS/graph" \
  "$PALAVER/graph"

cat > "$ENVOY/registry/contracts/opus_voice_orchestration_contract.json" <<'JSON'
{
  "id": "opus_voice_orchestration_contract",
  "type": "runtime_contract",
  "status": "active",
  "provider": "opus",
  "consumer": "envoy",
  "purpose": "Envoy resolves persona and voice intent; Opus orchestrates provider/model/API execution.",
  "flow": [
    "envoy.resolve_persona",
    "envoy.resolve_voice_profile",
    "opus.select_provider",
    "opus.execute_provider",
    "envoy.attach_voice_metadata"
  ],
  "rule": "Envoy owns persona and voice identity. Opus owns external API orchestration."
}
JSON

cat > "$OPUS/registry/routes/voice_tts_route.json" <<'JSON'
{
  "id": "voice_tts_route",
  "type": "api_orchestration_route",
  "status": "active",
  "owner": "opus",
  "domain": "voice_tts",
  "default_provider": "openai_tts",
  "fallback_order": [
    "openai_tts",
    "elevenlabs_tts"
  ],
  "required_env_any": [
    "OPENAI_API_KEY",
    "ELEVENLABS_API_KEY",
    "ELEVENLABS_SERVER_KEY"
  ],
  "notes": "Opus selects provider. Envoy supplies persona voice profile."
}
JSON

cat > "$OPUS/registry/providers/openai_tts.json" <<'JSON'
{
  "id": "openai_tts",
  "type": "tts_provider",
  "status": "active",
  "owner": "opus",
  "env_key": "OPENAI_API_KEY",
  "model_default": "gpt-4o-mini-tts",
  "voice_default": "alloy",
  "capabilities": [
    "text_to_speech",
    "mp3_output"
  ]
}
JSON

cat > "$OPUS/registry/providers/elevenlabs_tts.json" <<'JSON'
{
  "id": "elevenlabs_tts",
  "type": "tts_provider",
  "status": "available",
  "owner": "opus",
  "env_key_priority": [
    "ELEVENLABS_SERVER_KEY",
    "ELEVENLABS_API_KEY"
  ],
  "model_default": "eleven_multilingual_v2",
  "capabilities": [
    "text_to_speech",
    "streaming_tts",
    "voice_library",
    "voice_settings"
  ]
}
JSON

cat > "$OPUS/runtime/voice_orchestrator.py" <<'PY'
from __future__ import annotations

import json
import os
import urllib.request
from pathlib import Path
from typing import Any, Dict, Optional


OPUS_ROOT = Path(__file__).resolve().parents[1]
ROUTES = OPUS_ROOT / "registry" / "routes"
PROVIDERS = OPUS_ROOT / "registry" / "providers"


def read_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


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
PY

cat > "$ENVOY/runtime/opus_bridge.py" <<'PY'
from __future__ import annotations

import base64
import sys
from pathlib import Path
from typing import Any, Dict, Optional


ROOT = Path("/root/savant-runtime")
OPUS_RUNTIME = ROOT / "ontology/obelisks/_template/segue/gates/_template/segue/innates/_template/segue/exiles/opus/runtime"

if str(OPUS_RUNTIME) not in sys.path:
    sys.path.insert(0, str(OPUS_RUNTIME))

from voice_orchestrator import synthesize as opus_synthesize


def synthesize_with_opus(text: str, voice_profile: Dict[str, Any]) -> Dict[str, Any]:
    result = opus_synthesize(text, voice_profile)

    return {
        "provider": result["provider"],
        "mime_type": result["mime_type"],
        "audio_base64": base64.b64encode(result["audio"]).decode("ascii")
    }
PY

cat > "$ENVOY/graph/opus_connection.json" <<'JSON'
{
  "source": "exile:envoy",
  "target": "exile:opus",
  "relation": "delegates_api_orchestration_to",
  "authority": "runtime_patch",
  "description": "Envoy owns persona and voice identity. Opus owns external provider orchestration."
}
JSON

cat > "$OPUS/graph/envoy_connection.json" <<'JSON'
{
  "source": "exile:opus",
  "target": "exile:envoy",
  "relation": "orchestrates_external_voice_api_for",
  "authority": "runtime_patch",
  "description": "Opus selects and executes TTS providers for Envoy voice requests."
}
JSON

python3 - <<'PY'
from pathlib import Path

p = Path("/root/savant-runtime/ontology/obelisks/_template/segue/gates/_template/segue/innates/_template/segue/exiles/envoy/runtime/voice_engine.py")
s = p.read_text()

if "from opus_bridge import synthesize_with_opus" not in s:
    s = s.replace(
        "from typing import Any, Dict, Optional\n",
        "from typing import Any, Dict, Optional\n\nfrom opus_bridge import synthesize_with_opus\n",
    )

old = '''def synthesize(text: str, persona_id: Optional[str] = None) -> bytes:
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
'''

new = '''def synthesize(text: str, persona_id: Optional[str] = None) -> Dict[str, Any]:
    voice = resolve_voice(persona_id)
    return synthesize_with_opus(text, voice)


def synthesize_base64(text: str, persona_id: Optional[str] = None) -> Dict[str, Any]:
    voice = resolve_voice(persona_id)
    out = synthesize(text, persona_id)

    return {
        "persona_id": voice["persona"].get("persona_id"),
        "display_name": voice["persona"].get("display_name"),
        "voice": voice,
        "provider": out.get("provider"),
        "mime_type": out.get("mime_type", "audio/mpeg"),
        "audio_base64": out.get("audio_base64")
    }
'''

if old in s:
    s = s.replace(old, new)

p.write_text(s)
PY

echo "[OK] Envoy connected to Opus for API orchestration."
echo
echo "Run:"
echo "systemctl restart palaver-voice-backend.service"
