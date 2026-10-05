#!/usr/bin/env bash
set -euo pipefail

ROOT="/root/savant-runtime"
APP="$ROOT/webui_ultra"
BACKEND="$ROOT/palaver_voice_backend.py"
LOG="$ROOT/palaver-voice-backend.log"

cd "$APP"

cat > vite.config.js <<'JS'
import { defineConfig } from "vite";

export default defineConfig({
  server: {
    host: "0.0.0.0",
    port: 5173,
    strictPort: true,
    allowedHosts: true,
    proxy: {
      "/api": "http://127.0.0.1:8787"
    }
  }
});
JS

cat > "$BACKEND" <<'PY'
#!/usr/bin/env python3
import os, json, re, difflib, urllib.request
from pathlib import Path
from flask import Flask, request, jsonify
from flask_cors import CORS

ROOT = Path("/root/savant-runtime")
ENV_PATHS = [Path("/root/.env"), ROOT / ".env"]

def load_env():
    for p in ENV_PATHS:
        if not p.exists():
            continue
        for line in p.read_text(errors="ignore").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

load_env()

app = Flask(__name__)
CORS(app)

LEXICON = sorted(set("""
savant palaver carbon cataxis coda envoy filament graffiti lore mobius modus
niche notary opus pact shatter underscore urge zero fortex prodigal exile innate
gate obelisk iota mote trait quirk ontology canon lineage provenance authority
runtime graph projection segue instance vault registry observatory topology
compiler search fabric verification simulation recursion mathematics adaptation
communication construction representation relationship knowledge truth work
constraints divergence evolution deconstruction orchestration
""".split()))

COMMON = {
    "palver": "palaver",
    "pallaver": "palaver",
    "palava": "palaver",
    "savaant": "savant",
    "savnt": "savant",
    "mobius": "mobius",
    "moebius": "mobius",
    "mobiux": "mobius",
    "catxis": "cataxis",
    "cataxus": "cataxis",
    "undrscore": "underscore",
    "under score": "underscore",
    "notery": "notary",
    "filiment": "filament",
    "grafitti": "graffiti",
    "graffitti": "graffiti",
}

def normalize_phrase(text):
    text = str(text or "").lower()
    text = re.sub(r"[^a-z0-9\s_-]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    for wrong, right in COMMON.items():
        text = text.replace(wrong, right)
    fixed = []
    for word in text.split():
        if word in LEXICON or len(word) <= 3:
            fixed.append(word)
            continue
        match = difflib.get_close_matches(word, LEXICON, n=1, cutoff=0.78)
        fixed.append(match[0] if match else word)
    return " ".join(fixed)

def gemini(prompt):
    key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or os.getenv("AI_STUDIO_API_KEY")
    if not key:
        return None

    model = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"

    payload = {
        "contents": [{
            "parts": [{
                "text": prompt
            }]
        }]
    }

    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
        method="POST"
    )

    with urllib.request.urlopen(req, timeout=45) as r:
        data = json.loads(r.read().decode())
    return data["candidates"][0]["content"]["parts"][0]["text"]

def openai(prompt):
    key = os.getenv("OPENAI_API_KEY")
    if not key:
        return None

    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    payload = {
        "model": model,
        "input": prompt
    }

    req = urllib.request.Request(
        "https://api.openai.com/v1/responses",
        data=json.dumps(payload).encode(),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {key}"
        },
        method="POST"
    )

    with urllib.request.urlopen(req, timeout=45) as r:
        data = json.loads(r.read().decode())

    if "output_text" in data:
        return data["output_text"]

    return json.dumps(data)[:2000]

def answer(original):
    corrected = normalize_phrase(original)

    prompt = f"""
You are Palaver, Savant's conversational control plane.

Responsibilities:
- understand the user's intent
- correct obvious speech recognition and spelling errors
- route conceptually to Savant domains when useful
- answer clearly and briefly
- do not pretend backend actions happened unless they actually did

Original transcript:
{original}

Corrected transcript:
{corrected}

Respond as Palaver.
""".strip()

    for engine in (gemini, openai):
        try:
            out = engine(prompt)
            if out:
                return corrected, out.strip()
        except Exception as e:
            last = str(e)

    return corrected, f"Palaver understood: {corrected}. No AI API responded. Check .env credentials."

@app.post("/api/palaver")
@app.post("/palaver")
@app.post("/api/chat")
@app.post("/api/message")
@app.post("/message")
def palaver():
    data = request.get_json(silent=True) or {}
    text = data.get("text") or data.get("message") or data.get("prompt") or ""
    corrected, reply = answer(text)
    return jsonify({
        "original": text,
        "corrected": corrected,
        "reply": reply,
        "response": reply,
        "answer": reply
    })

@app.get("/api/health")
def health():
    return jsonify({
        "ok": True,
        "gemini": bool(os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or os.getenv("AI_STUDIO_API_KEY")),
        "openai": bool(os.getenv("OPENAI_API_KEY"))
    })

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8787)
PY

python3 -m venv "$ROOT/.venv_voice"
"$ROOT/.venv_voice/bin/pip" install --upgrade pip flask flask-cors

fuser -k 8787/tcp 2>/dev/null || true
nohup "$ROOT/.venv_voice/bin/python" "$BACKEND" > "$LOG" 2>&1 &

sleep 2

echo "=== BACKEND HEALTH ==="
curl -s http://127.0.0.1:8787/api/health
echo

echo "=== BACKEND TEST ==="
curl -s -X POST http://127.0.0.1:8787/api/palaver \
  -H 'Content-Type: application/json' \
  -d '{"text":"hey palver what is mobus"}'
echo

echo "Backend running on 127.0.0.1:8787"
echo "Restart Vite after this."
