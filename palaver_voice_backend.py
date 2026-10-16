#!/usr/bin/env python3
import os
import sys, json, re, difflib, urllib.request
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

    model = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
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

    return corrected, f"Palaver understood: {corrected}. No AI API responded. Last API error: {last}"

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


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8787)
