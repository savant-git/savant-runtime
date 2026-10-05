#!/usr/bin/env bash
set -euo pipefail

ROOT="/root/savant-runtime"
EXILES_ROOT="$ROOT/ontology/obelisks/_template/segue/gates/_template/segue/innates/_template/segue/exiles"

OPUS="$EXILES_ROOT/opus"
ENVOY="$EXILES_ROOT/envoy"
PALAVER="$EXILES_ROOT/palaver"

mkdir -p \
  "$OPUS/runtime" \
  "$OPUS/runtime/providers" \
  "$OPUS/registry/routes" \
  "$OPUS/registry/providers" \
  "$OPUS/registry/policies" \
  "$OPUS/canon" \
  "$OPUS/authority" \
  "$OPUS/lineage" \
  "$OPUS/graph" \
  "$OPUS/observatory" \
  "$ENVOY/registry/contracts" \
  "$ENVOY/graph" \
  "$PALAVER/graph"

cat > "$OPUS/canon/voice_orchestration_pipeline.md" <<'MD'
# OPUS VOICE ORCHESTRATION PIPELINE
# STATUS: CANON
# AUTHORITY: USER DIRECTIVE
# OWNER: OPUS
# CONSUMER: ENVOY
# CALLER: PALAVER

Opus owns API orchestration.

Envoy owns persona identity, voice characteristics, accent, language,
pronunciation, speaking style, and presentation intent.

Palaver owns conversation and dialogue.

Runtime flow:

Palaver
  -> Envoy
  -> Opus
  -> External API Provider
  -> Opus
  -> Envoy
  -> Palaver

Rules:

- Envoy must not hardcode provider execution.
- Envoy emits provider-agnostic voice requests.
- Opus resolves credentials, provider, model, cost policy, latency policy,
  retry policy, and fallback policy.
- Opus returns audio plus provider lineage.
- Envoy attaches persona and voice metadata.
- Palaver consumes final response/audio.
MD

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
  "policy_ref": "voice_tts_policy",
  "required_env_any": [
    "OPENAI_API_KEY",
    "ELEVENLABS_SERVER_KEY",
    "ELEVENLABS_API_KEY"
  ]
}
JSON

cat > "$OPUS/registry/policies/voice_tts_policy.json" <<'JSON'
{
  "id": "voice_tts_policy",
  "type": "orchestration_policy",
  "status": "active",
  "owner": "opus",
  "domain": "voice_tts",
  "latency_priority": "medium",
  "cost_priority": "medium",
  "quality_priority": "high",
  "retry_attempts": 2,
  "timeout_seconds": 60,
  "cache_enabled": true,
  "lineage_required": true,
  "fallback_required": true
}
JSON

cat > "$OPUS/runtime/providers/base.py" <<'PY'
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
PY

cat > "$OPUS/runtime/providers/openai_tts.py" <<'PY'
from __future__ import annotations

import json
import os
import urllib.request
from typing import Any, Dict

from providers.base import ProviderError, voice_prompt


def available() -> bool:
    return bool(os.getenv("OPENAI_API_KEY"))


def synthesize(request: Dict[str, Any], provider: Dict[str, Any]) -> Dict[str, Any]:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ProviderError("OPENAI_API_KEY missing")

    voice = request.get("voice") or {}

    model = (
        os.getenv(str(voice.get("model_env") or ""))
        or voice.get("model_default")
        or provider.get("model_default")
        or "gpt-4o-mini-tts"
    )

    voice_name = (
        os.getenv(str(voice.get("voice_env") or ""))
        or voice.get("voice_default")
        or provider.get("voice_default")
        or "alloy"
    )

    payload = {
        "model": model,
        "voice": voice_name,
        "input": voice_prompt(request),
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

    with urllib.request.urlopen(req, timeout=int(provider.get("timeout_seconds", 60))) as res:
        audio = res.read()

    return {
        "ok": True,
        "provider": "openai_tts",
        "model": model,
        "voice": voice_name,
        "mime_type": "audio/mpeg",
        "audio": audio
    }
PY

cat > "$OPUS/runtime/providers/elevenlabs_tts.py" <<'PY'
from __future__ import annotations

import json
import os
import urllib.request
from typing import Any, Dict

from providers.base import ProviderError, voice_prompt


def api_key() -> str:
    return (
        os.getenv("ELEVENLABS_SERVER_KEY")
        or os.getenv("ELEVENLABS_API_KEY")
        or ""
    )


def available() -> bool:
    return bool(api_key())


def synthesize(request: Dict[str, Any], provider: Dict[str, Any]) -> Dict[str, Any]:
    key = api_key()
    if not key:
        raise ProviderError("ELEVENLABS_SERVER_KEY or ELEVENLABS_API_KEY missing")

    voice = request.get("voice") or {}
    voice_id = voice.get("elevenlabs_voice_id") or os.getenv("ELEVENLABS_DEFAULT_VOICE_ID")

    if not voice_id:
        raise ProviderError("ELEVENLABS_DEFAULT_VOICE_ID or voice.elevenlabs_voice_id missing")

    model = voice.get("elevenlabs_model") or provider.get("model_default") or "eleven_multilingual_v2"

    payload = {
        "text": voice_prompt(request),
        "model_id": model,
        "voice_settings": {
            "stability": float(voice.get("stability", 0.5)),
            "similarity_boost": float(voice.get("similarity_boost", 0.75)),
            "style": float(voice.get("style", 0.25)),
            "use_speaker_boost": True
        }
    }

    req = urllib.request.Request(
        f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "xi-api-key": key
        },
        method="POST"
    )

    with urllib.request.urlopen(req, timeout=int(provider.get("timeout_seconds", 60))) as res:
        audio = res.read()

    return {
        "ok": True,
        "provider": "elevenlabs_tts",
        "model": model,
        "voice": voice_id,
        "mime_type": "audio/mpeg",
        "audio": audio
    }
PY

cat > "$OPUS/runtime/router.py" <<'PY'
from __future__ import annotations

import importlib
import json
from pathlib import Path
from typing import Any, Dict, List


OPUS_ROOT = Path(__file__).resolve().parents[1]
ROUTES = OPUS_ROOT / "registry" / "routes"
PROVIDERS = OPUS_ROOT / "registry" / "providers"
POLICIES = OPUS_ROOT / "registry" / "policies"


def read_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def route(route_id: str) -> Dict[str, Any]:
    return read_json(ROUTES / f"{route_id}.json")


def provider(provider_id: str) -> Dict[str, Any]:
    return read_json(PROVIDERS / f"{provider_id}.json")


def policy(policy_id: str) -> Dict[str, Any]:
    return read_json(POLICIES / f"{policy_id}.json")


def load_provider_module(provider_id: str):
    return importlib.import_module(f"providers.{provider_id}")


def select_provider(route_id: str = "voice_tts_route") -> Dict[str, Any]:
    r = route(route_id)
    fallback = r.get("fallback_order") or [r.get("default_provider")]

    for provider_id in fallback:
        if not provider_id:
            continue

        p = provider(provider_id)
        mod = load_provider_module(provider_id)

        if hasattr(mod, "available") and mod.available():
            p["selected"] = True
            p["route_id"] = route_id
            return p

    raise RuntimeError(f"No available provider for route: {route_id}")


def execute_voice_request(request: Dict[str, Any]) -> Dict[str, Any]:
    p = select_provider("voice_tts_route")
    route_data = route("voice_tts_route")
    policy_data = policy(route_data.get("policy_ref", "voice_tts_policy"))

    p["timeout_seconds"] = policy_data.get("timeout_seconds", 60)

    mod = load_provider_module(p["id"])
    result = mod.synthesize(request, p)

    result["lineage"] = {
        "owner": "opus",
        "route": "voice_tts_route",
        "provider": p["id"],
        "policy": policy_data.get("id"),
        "fallback_order": route_data.get("fallback_order", []),
        "request_owner": request.get("owner", "envoy")
    }

    return result
PY

cat > "$OPUS/runtime/voice_orchestration_pipeline.py" <<'PY'
from __future__ import annotations

import base64
from typing import Any, Dict

from router import execute_voice_request


def synthesize_voice_request(request: Dict[str, Any]) -> Dict[str, Any]:
    result = execute_voice_request(request)

    return {
        "ok": True,
        "provider": result.get("provider"),
        "model": result.get("model"),
        "voice": result.get("voice"),
        "mime_type": result.get("mime_type", "audio/mpeg"),
        "audio_base64": base64.b64encode(result["audio"]).decode("ascii"),
        "lineage": result.get("lineage", {})
    }
PY

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

cat > "$ENVOY/registry/contracts/opus_voice_request_contract.json" <<'JSON'
{
  "id": "opus_voice_request_contract",
  "type": "runtime_contract",
  "status": "active",
  "provider": "opus",
  "consumer": "envoy",
  "request_object": {
    "owner": "envoy",
    "text": "string",
    "persona": "object",
    "voice": "object",
    "accent": "object",
    "language": "object",
    "emotion": "object",
    "pronunciation": "object"
  },
  "rule": "Envoy emits voice intent. Opus executes external API orchestration."
}
JSON

cat > "$OPUS/graph/voice_orchestration_pipeline.json" <<'JSON'
{
  "id": "opus:voice_orchestration_pipeline",
  "type": "runtime_pipeline",
  "source": "exile:envoy",
  "target": "external:tts_providers",
  "owner": "exile:opus",
  "relation": "orchestrates_voice_api_execution",
  "authority": "runtime_patch"
}
JSON

cat > "$ENVOY/graph/opus_voice_pipeline.json" <<'JSON'
{
  "id": "envoy:opus_voice_pipeline",
  "type": "runtime_dependency",
  "source": "exile:envoy",
  "target": "exile:opus",
  "relation": "delegates_api_orchestration_to",
  "authority": "runtime_patch"
}
JSON

touch "$OPUS/runtime/__init__.py"
touch "$OPUS/runtime/providers/__init__.py"

echo "[OK] Opus voice orchestration pipeline installed."
find "$OPUS/runtime" "$OPUS/registry" "$OPUS/graph" -maxdepth 3 -type f | sort
