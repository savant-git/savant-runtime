#!/usr/bin/env bash
set -euo pipefail

ROOT="/root/savant-runtime"
EXILES_ROOT="$ROOT/ontology/obelisks/_template/segue/gates/_template/segue/innates/_template/segue/exiles"

ENVOY="$EXILES_ROOT/envoy"
PALAVER="$EXILES_ROOT/palaver"
BACKEND="$ROOT/palaver_voice_backend.py"

mkdir -p \
  "$ENVOY/api" \
  "$ENVOY/graph" \
  "$ENVOY/lineage" \
  "$ENVOY/authority" \
  "$ENVOY/observatory" \
  "$PALAVER/registry/providers" \
  "$PALAVER/graph"

cat > "$PALAVER/registry/providers/envoy_voice_provider.json" <<'JSON'
{
  "id": "envoy_voice_provider",
  "type": "voice_provider",
  "status": "active",
  "owner": "envoy",
  "consumer": "palaver",
  "runtime_module": "envoy.runtime.voice_engine",
  "capabilities": [
    "list_personas",
    "resolve_persona",
    "resolve_voice",
    "synthesize",
    "synthesize_base64"
  ]
}
JSON

cat > "$ENVOY/api/palaver_voice_contract.json" <<'JSON'
{
  "id": "palaver_voice_contract",
  "type": "api_contract",
  "provider": "envoy",
  "consumer": "palaver",
  "endpoints": [
    {
      "method": "GET",
      "path": "/api/envoy/personas",
      "purpose": "List available Envoy personas."
    },
    {
      "method": "POST",
      "path": "/api/envoy/speech",
      "purpose": "Synthesize speech through Envoy."
    }
  ]
}
JSON

cat > "$ENVOY/graph/palaver_connection.json" <<'JSON'
{
  "source": "exile:palaver",
  "target": "exile:envoy",
  "relation": "uses_voice_provider",
  "direction": "palaver_to_envoy",
  "authority": "runtime_patch",
  "description": "Palaver delegates persona voice selection and speech synthesis to Envoy."
}
JSON

cat > "$PALAVER/graph/envoy_connection.json" <<'JSON'
{
  "source": "exile:palaver",
  "target": "exile:envoy",
  "relation": "delegates_voice_to",
  "authority": "runtime_patch",
  "description": "Palaver owns conversation but does not own voice identity."
}
JSON

cp "$BACKEND" "$BACKEND.before_envoy_connection_$(date -u +%Y%m%dT%H%M%SZ)" 2>/dev/null || true

python3 - <<'PY'
from pathlib import Path

backend = Path("/root/savant-runtime/palaver_voice_backend.py")
s = backend.read_text()

if "ENVOY_EXILE_ROOT" not in s:
    insert = '''
# === ENVOY VOICE BRIDGE ===
ENVOY_EXILE_ROOT = Path("/root/savant-runtime/ontology/obelisks/_template/segue/gates/_template/segue/innates/_template/segue/exiles/envoy")
ENVOY_RUNTIME = ENVOY_EXILE_ROOT / "runtime"

if str(ENVOY_RUNTIME) not in sys.path:
    sys.path.insert(0, str(ENVOY_RUNTIME))

try:
    from voice_engine import list_personas, synthesize_base64, resolve_voice
except Exception as e:
    list_personas = None
    synthesize_base64 = None
    resolve_voice = None
    ENVOY_IMPORT_ERROR = str(e)
else:
    ENVOY_IMPORT_ERROR = None
# === END ENVOY VOICE BRIDGE ===
'''
    if "import sys" not in s:
        s = s.replace("import os", "import os\nimport sys", 1)
    marker = "app = Flask(__name__)"
    s = s.replace(marker, insert + "\n" + marker, 1)

if '@app.get("/api/envoy/personas")' not in s:
    routes = r'''

@app.get("/api/envoy/personas")
def envoy_personas():
    if list_personas is None:
        return jsonify({"ok": False, "error": ENVOY_IMPORT_ERROR or "Envoy unavailable"}), 500
    return jsonify({"ok": True, "personas": list_personas()})


@app.post("/api/envoy/speech")
def envoy_speech():
    if synthesize_base64 is None:
        return jsonify({"ok": False, "error": ENVOY_IMPORT_ERROR or "Envoy unavailable"}), 500

    data = request.get_json(silent=True) or {}
    text = data.get("text") or data.get("message") or data.get("reply") or ""
    persona_id = data.get("persona_id") or data.get("persona") or "palaver_default"

    if not text.strip():
        return jsonify({"ok": False, "error": "missing text"}), 400

    try:
        out = synthesize_base64(text, persona_id)
        out["ok"] = True
        return jsonify(out)
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.get("/api/envoy/health")
def envoy_health():
    return jsonify({
        "ok": ENVOY_IMPORT_ERROR is None,
        "envoy_root": str(ENVOY_EXILE_ROOT),
        "envoy_runtime": str(ENVOY_RUNTIME),
        "import_error": ENVOY_IMPORT_ERROR
    })
'''
    s = s.replace('\nif __name__ == "__main__":', routes + '\n\nif __name__ == "__main__":', 1)

backend.write_text(s)
PY

echo "[OK] Envoy connected to Palaver backend."
echo
echo "Restart backend:"
echo "systemctl restart palaver-voice-backend.service"
echo
echo "Test:"
echo "curl -s http://127.0.0.1:8787/api/envoy/health"

echo
echo "[OK] Envoy to Palaver bridge script completed."
echo "Verify Palaver service health before enabling any dependent automation."
