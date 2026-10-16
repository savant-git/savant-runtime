#!/usr/bin/env bash
set -euo pipefail

ROOT="/root/savant-runtime"
APP="$ROOT/webui_ultra"

if [ ! -d "$APP" ]; then
  echo "[ERROR] Missing app: $APP"
  exit 1
fi

cd "$APP"

cat > package.json <<'JSON'
{
  "name": "palaver-voice-ui",
  "version": "1.0.0",
  "private": true,
  "type": "module",
  "scripts": {
    "dev": "vite --host 0.0.0.0",
    "start": "vite --host 0.0.0.0",
    "build": "vite build",
    "preview": "vite preview --host 0.0.0.0"
  },
  "dependencies": {
    "@vitejs/plugin-react": "latest",
    "vite": "latest",
    "react": "latest",
    "react-dom": "latest"
  },
  "devDependencies": {}
}
JSON

mkdir -p src

cat > index.html <<'HTML'
<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Palaver Voice</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.jsx"></script>
  </body>
</html>
HTML

cat > src/main.jsx <<'JSX'
import React, { useEffect, useRef, useState } from "react";
import { createRoot } from "react-dom/client";

const SpeechRecognition =
  window.SpeechRecognition ||
  window.webkitSpeechRecognition ||
  null;

const WAKE_PHRASE = "fuck you palaver";

function normalizeSpeech(text) {
  return String(text || "")
    .toLowerCase()
    .replace(/[^\w\s]/g, "")
    .replace(/\s+/g, " ")
    .trim();
}

function hasWakePhrase(text) {
  return normalizeSpeech(text).includes(WAKE_PHRASE);
}

function stripWakePhrase(text) {
  const clean = normalizeSpeech(text);
  return clean.replace(WAKE_PHRASE, "").trim();
}

function speak(text) {
  if (!window.speechSynthesis) return;

  window.speechSynthesis.cancel();

  const utterance = new SpeechSynthesisUtterance(text);
  const voices = window.speechSynthesis.getVoices?.() || [];
  const voice =
    voices.find(v => /en-US|en_GB|en/i.test(v.lang)) ||
    voices[0] ||
    null;

  if (voice) utterance.voice = voice;

  utterance.rate = 0.92;
  utterance.pitch = 0.82;
  utterance.volume = 1;

  window.speechSynthesis.speak(utterance);
}

async function askPalaver(text) {
  const endpoints = [
    "/api/palaver",
    "/palaver",
    "/api/chat",
    "/api/message",
    "/message"
  ];

  for (const endpoint of endpoints) {
    try {
      const res = await fetch(endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          text,
          message: text,
          prompt: text,
          source: "palaver_voice",
          mode: "voice"
        })
      });

      if (!res.ok) continue;

      const data = await res.json().catch(() => null);

      if (data) {
        const answer =
          data.reply ||
          data.response ||
          data.answer ||
          data.text ||
          data.message ||
          data.output ||
          data.result;

        if (typeof answer === "string" && answer.trim()) {
          return answer.trim();
        }
      }

      const raw = await res.text().catch(() => "");
      if (raw.trim()) return raw.trim();
    } catch (_) {}
  }

  return "Palaver is awake. Backend response endpoint is not connected yet.";
}

function App() {
  const [armed, setArmed] = useState(false);
  const [heard, setHeard] = useState("");
  const [reply, setReply] = useState("");
  const [status, setStatus] = useState("idle");
  const recognitionRef = useRef(null);

  async function handleSpeech(text) {
    setHeard(text);

    if (!hasWakePhrase(text)) {
      setStatus("waiting for wake phrase");
      return;
    }

    const command = stripWakePhrase(text);

    setArmed(true);
    setStatus("wake phrase detected");

    const prompt = command || "Palaver, acknowledge voice activation.";
    const answer = await askPalaver(prompt);

    setReply(answer);
    speak(answer);

    setStatus("answered");
  }

  function start() {
    if (!SpeechRecognition) {
      setStatus("speech recognition unavailable");
      return;
    }

    const rec = new SpeechRecognition();
    rec.lang = "en-US";
    rec.interimResults = true;
    rec.continuous = true;

    rec.onstart = () => setStatus("listening for: fuck you palaver");

    rec.onresult = event => {
      let text = "";

      for (let i = event.resultIndex; i < event.results.length; i++) {
        text += event.results[i][0].transcript + " ";
      }

      setHeard(text.trim());

      for (let i = event.resultIndex; i < event.results.length; i++) {
        if (event.results[i].isFinal) {
          handleSpeech(event.results[i][0].transcript);
        }
      }
    };

    rec.onerror = event => {
      setStatus("voice error: " + event.error);
    };

    rec.onend = () => {
      if (recognitionRef.current) {
        try {
          rec.start();
        } catch (_) {}
      }
    };

    recognitionRef.current = rec;
    rec.start();
  }

  function stop() {
    const rec = recognitionRef.current;
    recognitionRef.current = null;
    rec?.stop?.();
    setStatus("stopped");
  }

  useEffect(() => {
    window.speechSynthesis?.getVoices?.();
    return () => {
      recognitionRef.current?.stop?.();
      window.speechSynthesis?.cancel?.();
    };
  }, []);

  return (
    <main>
      <section>
        <div className="kicker">PALAVER VOICE</div>
        <h1>Wake phrase enabled.</h1>
        <p className="phrase">Say: “fuck you palaver”</p>

        <div className="buttons">
          <button onClick={start}>Start Listening</button>
          <button onClick={stop}>Stop</button>
          <button onClick={() => speak(reply || "Palaver voice is active.")}>
            Test Voice
          </button>
        </div>

        <div className="grid">
          <div>
            <label>Status</label>
            <pre>{status}</pre>
          </div>

          <div>
            <label>Armed</label>
            <pre>{armed ? "yes" : "no"}</pre>
          </div>

          <div>
            <label>Heard</label>
            <pre>{heard || "nothing yet"}</pre>
          </div>

          <div>
            <label>Reply</label>
            <pre>{reply || "no reply yet"}</pre>
          </div>
        </div>
      </section>

      <style>{`
        * { box-sizing: border-box; }

        body {
          margin: 0;
          background: #05070d;
          color: #f5f7ff;
          font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
        }

        main {
          min-height: 100vh;
          display: grid;
          place-items: center;
          padding: 24px;
          background:
            radial-gradient(circle at 20% 0%, rgba(91, 141, 239, 0.22), transparent 36%),
            radial-gradient(circle at 80% 10%, rgba(177, 92, 255, 0.18), transparent 34%),
            linear-gradient(135deg, #05070d, #090c14 48%, #020308);
        }

        section {
          width: min(980px, 100%);
          border: 1px solid rgba(255,255,255,0.14);
          border-radius: 28px;
          padding: clamp(24px, 5vw, 56px);
          background: rgba(8, 11, 20, 0.78);
          box-shadow: 0 30px 120px rgba(0,0,0,0.6);
          backdrop-filter: blur(18px);
        }

        .kicker {
          color: #8fb4ff;
          letter-spacing: 0.24em;
          font-size: 12px;
          font-weight: 800;
          margin-bottom: 16px;
        }

        h1 {
          font-size: clamp(42px, 8vw, 96px);
          line-height: 0.9;
          letter-spacing: -0.07em;
          margin: 0 0 18px;
        }

        .phrase {
          font-size: clamp(20px, 3vw, 34px);
          color: #d8e2ff;
          margin: 0 0 28px;
        }

        .buttons {
          display: flex;
          flex-wrap: wrap;
          gap: 12px;
          margin-bottom: 28px;
        }

        button {
          border: 0;
          border-radius: 999px;
          padding: 14px 20px;
          color: white;
          font-weight: 900;
          cursor: pointer;
          background: linear-gradient(135deg, #4d7cff, #9d5cff);
        }

        .grid {
          display: grid;
          grid-template-columns: repeat(2, minmax(0, 1fr));
          gap: 14px;
        }

        label {
          display: block;
          color: #9eb9ff;
          font-size: 12px;
          font-weight: 900;
          letter-spacing: 0.18em;
          text-transform: uppercase;
          margin-bottom: 8px;
        }

        pre {
          white-space: pre-wrap;
          min-height: 72px;
          margin: 0;
          padding: 16px;
          border-radius: 18px;
          color: rgba(245,247,255,0.86);
          background: rgba(255,255,255,0.06);
          border: 1px solid rgba(255,255,255,0.11);
          font: inherit;
          line-height: 1.5;
        }

        @media (max-width: 720px) {
          .grid { grid-template-columns: 1fr; }
          button { width: 100%; }
        }
      `}</style>
    </main>
  );
}

createRoot(document.getElementById("root")).render(<App />);
JSX

npm install

echo
echo "[OK] Patched webui_ultra."
echo
echo "Run:"
echo "cd /root/savant-runtime/webui_ultra"
echo "npm run dev -- --host 0.0.0.0"
