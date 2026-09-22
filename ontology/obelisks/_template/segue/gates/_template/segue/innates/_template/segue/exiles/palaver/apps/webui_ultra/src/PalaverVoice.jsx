import React, { useEffect, useMemo, useRef, useState } from "react";

const SpeechRecognition =
  window.SpeechRecognition ||
  window.webkitSpeechRecognition ||
  null;

function pickVoice() {
  const voices = window.speechSynthesis?.getVoices?.() || [];
  return (
    voices.find(v => /Google US English|Microsoft.*Aria|Samantha|Daniel|Natural/i.test(v.name)) ||
    voices.find(v => /en-US|en_GB|en/i.test(v.lang)) ||
    voices[0] ||
    null
  );
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

      if (!data) {
        const raw = await res.text().catch(() => "");
        if (raw.trim()) return raw.trim();
      }

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
    } catch (_) {}
  }

  return "Palaver voice interface is active, but no backend response endpoint answered this request.";
}

export default function PalaverVoice() {
  const [supported, setSupported] = useState(Boolean(SpeechRecognition));
  const [listening, setListening] = useState(false);
  const [thinking, setThinking] = useState(false);
  const [transcript, setTranscript] = useState("");
  const [reply, setReply] = useState("");
  const [log, setLog] = useState([]);
  const recognitionRef = useRef(null);

  const status = useMemo(() => {
    if (!supported) return "Speech recognition unavailable in this browser.";
    if (thinking) return "Palaver is processing.";
    if (listening) return "Listening.";
    return "Voice interface ready.";
  }, [supported, thinking, listening]);

  function speak(text) {
    if (!window.speechSynthesis) return;

    window.speechSynthesis.cancel();

    const utterance = new SpeechSynthesisUtterance(text);
    const voice = pickVoice();

    if (voice) utterance.voice = voice;

    utterance.rate = 0.92;
    utterance.pitch = 0.82;
    utterance.volume = 1;

    window.speechSynthesis.speak(utterance);
  }

  async function submit(text) {
    const clean = String(text || "").trim();
    if (!clean) return;

    setThinking(true);
    setTranscript(clean);

    const answer = await askPalaver(clean);

    setReply(answer);
    setLog(prev => [
      {
        at: new Date().toISOString(),
        user: clean,
        palaver: answer
      },
      ...prev
    ].slice(0, 25));

    speak(answer);
    setThinking(false);
  }

  function startListening() {
    if (!SpeechRecognition) {
      setSupported(false);
      return;
    }

    window.speechSynthesis?.cancel?.();

    const recognition = new SpeechRecognition();
    recognition.lang = "en-US";
    recognition.interimResults = true;
    recognition.continuous = false;

    recognition.onstart = () => {
      setListening(true);
      setTranscript("");
    };

    recognition.onresult = event => {
      let interim = "";
      let finalText = "";

      for (let i = event.resultIndex; i < event.results.length; i++) {
        const part = event.results[i][0].transcript;
        if (event.results[i].isFinal) finalText += part;
        else interim += part;
      }

      setTranscript(finalText || interim);

      if (finalText.trim()) {
        recognition.stop();
        submit(finalText);
      }
    };

    recognition.onerror = event => {
      setListening(false);
      setReply("Voice recognition error: " + event.error);
    };

    recognition.onend = () => {
      setListening(false);
    };

    recognitionRef.current = recognition;
    recognition.start();
  }

  function stopListening() {
    recognitionRef.current?.stop?.();
    setListening(false);
  }

  useEffect(() => {
    if (window.speechSynthesis) {
      window.speechSynthesis.getVoices();
      window.speechSynthesis.onvoiceschanged = () => {
        window.speechSynthesis.getVoices();
      };
    }

    return () => {
      recognitionRef.current?.stop?.();
      window.speechSynthesis?.cancel?.();
    };
  }, []);

  return (
    <div className="palaver-voice-root">
      <div className="palaver-voice-card">
        <div className="palaver-voice-kicker">PALAVER VOICE CONTROL PLANE</div>

        <h1>Speak to Palaver</h1>

        <p className="palaver-voice-status">{status}</p>

        <div className="palaver-voice-actions">
          <button
            className={listening ? "danger" : "primary"}
            onClick={listening ? stopListening : startListening}
            disabled={thinking}
          >
            {listening ? "Stop Listening" : "Start Voice"}
          </button>

          <button
            className="secondary"
            onClick={() => speak(reply || "Palaver audible voice is active.")}
          >
            Test Voice
          </button>

          <button
            className="secondary"
            onClick={() => {
              window.speechSynthesis?.cancel?.();
              stopListening();
            }}
          >
            Silence
          </button>
        </div>

        <label>Heard</label>
        <div className="palaver-voice-panel">
          {transcript || "No speech captured yet."}
        </div>

        <label>Palaver Response</label>
        <div className="palaver-voice-panel response">
          {reply || "No response yet."}
        </div>

        <form
          onSubmit={event => {
            event.preventDefault();
            const value = event.currentTarget.elements.manual.value;
            submit(value);
            event.currentTarget.reset();
          }}
        >
          <input
            name="manual"
            placeholder="Fallback: type a message to Palaver"
            autoComplete="off"
          />
          <button type="submit" disabled={thinking}>Send</button>
        </form>

        <div className="palaver-voice-log">
          {log.map((item, index) => (
            <div className="palaver-voice-log-item" key={index}>
              <strong>You:</strong> {item.user}
              <br />
              <strong>Palaver:</strong> {item.palaver}
            </div>
          ))}
        </div>
      </div>

      <style>{`
        .palaver-voice-root {
          min-height: 100vh;
          display: grid;
          place-items: center;
          background:
            radial-gradient(circle at 20% 10%, rgba(91, 141, 239, 0.20), transparent 34%),
            radial-gradient(circle at 80% 0%, rgba(177, 92, 255, 0.18), transparent 32%),
            linear-gradient(135deg, #05070d, #090c14 45%, #020308);
          color: #f4f7ff;
          font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
          padding: 24px;
        }

        .palaver-voice-card {
          width: min(940px, 100%);
          border: 1px solid rgba(255, 255, 255, 0.14);
          border-radius: 28px;
          padding: clamp(22px, 4vw, 48px);
          background: rgba(8, 11, 20, 0.78);
          box-shadow: 0 30px 100px rgba(0, 0, 0, 0.55);
          backdrop-filter: blur(18px);
        }

        .palaver-voice-kicker {
          color: #8fb4ff;
          letter-spacing: 0.24em;
          font-size: 12px;
          font-weight: 700;
          margin-bottom: 14px;
        }

        h1 {
          font-size: clamp(38px, 7vw, 84px);
          line-height: 0.92;
          margin: 0 0 18px;
          letter-spacing: -0.06em;
        }

        .palaver-voice-status {
          color: rgba(244, 247, 255, 0.76);
          font-size: 17px;
          margin-bottom: 26px;
        }

        .palaver-voice-actions {
          display: flex;
          flex-wrap: wrap;
          gap: 12px;
          margin-bottom: 26px;
        }

        button {
          border: 0;
          border-radius: 999px;
          padding: 13px 18px;
          color: white;
          font-weight: 800;
          cursor: pointer;
          background: rgba(255, 255, 255, 0.11);
        }

        button:disabled {
          opacity: 0.5;
          cursor: not-allowed;
        }

        button.primary {
          background: linear-gradient(135deg, #4d7cff, #9d5cff);
        }

        button.danger {
          background: linear-gradient(135deg, #ff355d, #ff8a3d);
        }

        button.secondary {
          border: 1px solid rgba(255, 255, 255, 0.16);
        }

        label {
          display: block;
          margin: 18px 0 8px;
          color: #9eb9ff;
          font-size: 12px;
          letter-spacing: 0.18em;
          font-weight: 800;
          text-transform: uppercase;
        }

        .palaver-voice-panel {
          min-height: 64px;
          border-radius: 18px;
          border: 1px solid rgba(255, 255, 255, 0.11);
          background: rgba(255, 255, 255, 0.055);
          padding: 16px;
          color: rgba(244, 247, 255, 0.86);
          line-height: 1.55;
        }

        .palaver-voice-panel.response {
          min-height: 110px;
        }

        form {
          display: flex;
          gap: 10px;
          margin-top: 22px;
        }

        input {
          flex: 1;
          min-width: 0;
          border-radius: 999px;
          border: 1px solid rgba(255, 255, 255, 0.13);
          background: rgba(255, 255, 255, 0.07);
          color: white;
          padding: 14px 18px;
          outline: none;
        }

        .palaver-voice-log {
          margin-top: 22px;
          display: grid;
          gap: 10px;
        }

        .palaver-voice-log-item {
          border-left: 3px solid rgba(143, 180, 255, 0.75);
          padding: 10px 14px;
          background: rgba(255, 255, 255, 0.045);
          border-radius: 12px;
          color: rgba(244, 247, 255, 0.75);
          font-size: 14px;
          line-height: 1.45;
        }

        @media (max-width: 640px) {
          form {
            flex-direction: column;
          }

          .palaver-voice-actions {
            flex-direction: column;
          }

          button {
            width: 100%;
          }
        }
      `}</style>
    </div>
  );
}
