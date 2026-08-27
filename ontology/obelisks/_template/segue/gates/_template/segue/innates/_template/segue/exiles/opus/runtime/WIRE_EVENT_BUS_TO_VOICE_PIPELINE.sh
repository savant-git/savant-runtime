#!/usr/bin/env bash
set -euo pipefail

ROOT="/root/savant-runtime"
EXILES_ROOT="$ROOT/ontology/obelisks/_template/segue/gates/_template/segue/innates/_template/segue/exiles"

OPUS="$EXILES_ROOT/opus"
ENVOY="$EXILES_ROOT/envoy"

python3 - <<'PY'
from pathlib import Path

router = Path("/root/savant-runtime/ontology/obelisks/_template/segue/gates/_template/segue/innates/_template/segue/exiles/opus/runtime/router.py")
s = router.read_text()

if "from event_bus.bus import publish" not in s:
    s = s.replace(
        "from typing import Any, Dict, List\n",
        "from typing import Any, Dict, List\n\nfrom event_bus.bus import publish\n",
        1
    )

old = '''def execute_voice_request(request: Dict[str, Any]) -> Dict[str, Any]:
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
'''

new = '''def execute_voice_request(request: Dict[str, Any]) -> Dict[str, Any]:
    publish(
        type="api.request",
        source="exile:opus",
        payload={
            "route": "voice_tts_route",
            "request_owner": request.get("owner", "envoy"),
            "text_chars": len(str(request.get("text") or ""))
        }
    )

    p = select_provider("voice_tts_route")
    route_data = route("voice_tts_route")
    policy_data = policy(route_data.get("policy_ref", "voice_tts_policy"))

    publish(
        type="provider.selected",
        source="exile:opus",
        payload={
            "route": "voice_tts_route",
            "provider": p["id"],
            "policy": policy_data.get("id")
        }
    )

    p["timeout_seconds"] = policy_data.get("timeout_seconds", 60)

    mod = load_provider_module(p["id"])

    try:
        result = mod.synthesize(request, p)
    except Exception as e:
        publish(
            type="provider.failed",
            source="exile:opus",
            payload={
                "route": "voice_tts_route",
                "provider": p["id"],
                "error": str(e)
            }
        )
        raise

    result["lineage"] = {
        "owner": "opus",
        "route": "voice_tts_route",
        "provider": p["id"],
        "policy": policy_data.get("id"),
        "fallback_order": route_data.get("fallback_order", []),
        "request_owner": request.get("owner", "envoy")
    }

    publish(
        type="api.response",
        source="exile:opus",
        payload={
            "route": "voice_tts_route",
            "provider": p["id"],
            "mime_type": result.get("mime_type"),
            "audio_bytes": len(result.get("audio", b""))
        }
    )

    return result
'''

if old in s:
    s = s.replace(old, new)

router.write_text(s)
PY

python3 - <<'PY'
from pathlib import Path

voice = Path("/root/savant-runtime/ontology/obelisks/_template/segue/gates/_template/segue/innates/_template/segue/exiles/envoy/runtime/voice_engine.py")
s = voice.read_text()

if "from event_bus.bus import publish" not in s:
    s = s.replace(
        "from typing import Any, Dict, Optional\n",
        "from typing import Any, Dict, Optional\n\nfrom event_bus.bus import publish\n",
        1
    )

old = '''def synthesize(text: str, persona_id: Optional[str] = None) -> Dict[str, Any]:
    if synthesize_voice_request is None:
        raise RuntimeError(OPUS_IMPORT_ERROR or "Opus voice pipeline unavailable")

    request = build_voice_request(text, persona_id)
    return synthesize_voice_request(request)
'''

new = '''def synthesize(text: str, persona_id: Optional[str] = None) -> Dict[str, Any]:
    if synthesize_voice_request is None:
        raise RuntimeError(OPUS_IMPORT_ERROR or "Opus voice pipeline unavailable")

    request = build_voice_request(text, persona_id)

    publish(
        type="speech.started",
        source="exile:envoy",
        payload={
            "persona_id": persona_id or "palaver_default",
            "text_chars": len(text)
        }
    )

    try:
        out = synthesize_voice_request(request)
    except Exception as e:
        publish(
            type="speech.failed",
            source="exile:envoy",
            payload={
                "persona_id": persona_id or "palaver_default",
                "error": str(e)
            }
        )
        raise

    publish(
        type="speech.finished",
        source="exile:envoy",
        payload={
            "persona_id": persona_id or "palaver_default",
            "provider": out.get("provider"),
            "mime_type": out.get("mime_type")
        }
    )

    return out
'''

if old in s:
    s = s.replace(old, new)

voice.write_text(s)
PY

echo "[OK] Event bus wired into Envoy voice and Opus provider pipeline."

systemctl restart palaver-voice-backend.service

sleep 3

echo
echo "=== ENVOY HEALTH ==="
curl -s http://127.0.0.1:8787/api/envoy/health
echo

echo
echo "=== EVENT LOG PATH ==="
echo "$OPUS/observatory/events/runtime_events.jsonl"
