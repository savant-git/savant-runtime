import React, {
  useEffect,
  useMemo,
  useRef,
  useState
} from "react";

import {
  createRoot
} from "react-dom/client";

import {
  ENVOY_VOICES,
  applyEnvoyVoice
} from "./envoyVoices.js";


const SpeechRecognition =
  window.SpeechRecognition ||
  window.webkitSpeechRecognition ||
  null;


const WAKE_PHRASES = [
  "wake up palaver",
  "hey palaver",
  "palaver awaken",
  "palaver online"
];


const MAX_ATTACHMENT_BYTES = 52_428_800;
const MAX_ATTACHMENT_MIB = 50;


function normalizeSpeech(text) {
  return String(
    text || ""
  )
    .toLowerCase()
    .replace(
      /[^\w\s]/g,
      ""
    )
    .replace(
      /\s+/g,
      " "
    )
    .trim();
}


function hasWakePhrase(text) {
  const clean =
    normalizeSpeech(
      text
    );

  return WAKE_PHRASES.some(
    phrase =>
      clean.includes(
        phrase
      )
  );
}


function stripWakePhrase(text) {
  let clean =
    normalizeSpeech(
      text
    );

  for (
    const phrase
    of WAKE_PHRASES
  ) {
    clean =
      clean.replace(
        phrase,
        ""
      );
  }

  return clean.trim();
}


function formatBytes(bytes) {
  const value =
    Number(
      bytes || 0
    );

  if (
    !Number.isFinite(
      value
    ) ||
    value <= 0
  ) {
    return "0 B";
  }

  const units = [
    "B",
    "KiB",
    "MiB",
    "GiB"
  ];

  let size = value;
  let unit = 0;

  while (
    size >= 1024 &&
    unit <
      units.length - 1
  ) {
    size /= 1024;
    unit += 1;
  }

  const digits =
    unit === 0
      ? 0
      : size >= 10
        ? 1
        : 2;

  return (
    size.toFixed(
      digits
    ) +
    " " +
    units[unit]
  );
}


function attachmentKey(
  file
) {
  return [
    file.name,
    file.size,
    file.lastModified
  ].join(
    ":"
  );
}


function speak(
  text,
  personaId
) {
  if (
    !window.speechSynthesis
  ) {
    return;
  }

  window.speechSynthesis.cancel();

  const utterance =
    new SpeechSynthesisUtterance(
      text
    );

  applyEnvoyVoice(
    utterance,
    personaId
  );

  window.speechSynthesis.speak(
    utterance
  );
}


async function uploadAttachment(
  file
) {
  if (
    file.size >
    MAX_ATTACHMENT_BYTES
  ) {
    throw new Error(
      `${file.name} exceeds the ${MAX_ATTACHMENT_MIB} MiB attachment limit`
    );
  }

  const response =
    await fetch(
      "/api/attachment/upload",
      {
        method: "POST",
        headers: {
          "Content-Type":
            file.type ||
            "application/octet-stream",
          "X-Palaver-Filename":
            encodeURIComponent(
              file.name
            ),
          "X-Palaver-Content-Type":
            file.type ||
            "application/octet-stream"
        },
        body: file
      }
    );

  const data =
    await response
      .json()
      .catch(
        () => null
      );

  if (
    !response.ok ||
    !data?.ok
  ) {
    throw new Error(
      data?.error ||
      `attachment upload failed with HTTP ${response.status}`
    );
  }

  return data.attachment;
}


function projectAttachments(
  attachments
) {
  return attachments.map(
    attachment => ({
      attachment_id:
        attachment.attachment_id,
      filename:
        attachment.filename,
      content_type:
        attachment.content_type,
      size_bytes:
        attachment.size_bytes,
      sha256:
        attachment.sha256,
      source:
        attachment.source
    })
  );
}


function attachmentContext(
  attachments
) {
  if (
    attachments.length === 0
  ) {
    return "";
  }

  return [
    "Palaver attachment references:",
    JSON.stringify(
      projectAttachments(
        attachments
      ),
      null,
      2
    )
  ].join(
    "\n"
  );
}


async function askPalaver(
  text,
  personaId,
  attachments = []
) {
  const endpoints = [
    "/api/palaver",
    "/palaver",
    "/api/chat",
    "/api/message",
    "/message"
  ];

  const projected =
    projectAttachments(
      attachments
    );

  const context =
    attachmentContext(
      attachments
    );

  for (
    const endpoint
    of endpoints
  ) {
    try {
      const res =
        await fetch(
          endpoint,
          {
            method: "POST",
            headers: {
              "Content-Type":
                "application/json"
            },
            body:
              JSON.stringify(
                {
                  text,
                  message: text,
                  prompt: text,
                  persona_id:
                    personaId,
                  context,
                  attachments:
                    projected
                }
              )
          }
        );

      if (
        !res.ok
      ) {
        continue;
      }

      const data =
        await res
          .json()
          .catch(
            () => null
          );

      if (
        data
      ) {
        return (
          data.reply ||
          data.response ||
          data.answer ||
          data.text ||
          data.message ||
          data.output ||
          data.result ||
          JSON.stringify(
            data
          )
        );
      }

      const raw =
        await res
          .text()
          .catch(
            () => ""
          );

      if (
        raw.trim()
      ) {
        return raw.trim();
      }

    } catch (_) {
    }
  }

  return (
    "Palaver is awake. " +
    "Backend response endpoint is not connected yet."
  );
}


function App() {
  const [
    personaId,
    setPersonaId
  ] =
    useState(
      "palaver_default"
    );

  const [
    armed,
    setArmed
  ] =
    useState(
      false
    );

  const [
    heard,
    setHeard
  ] =
    useState(
      ""
    );

  const [
    reply,
    setReply
  ] =
    useState(
      ""
    );

  const [
    status,
    setStatus
  ] =
    useState(
      "idle"
    );

  const [
    attachments,
    setAttachments
  ] =
    useState(
      []
    );

  const [
    uploading,
    setUploading
  ] =
    useState(
      false
    );

  const [
    attachmentError,
    setAttachmentError
  ] =
    useState(
      ""
    );

  const [
    dragActive,
    setDragActive
  ] =
    useState(
      false
    );

  const recognitionRef =
    useRef(
      null
    );

  const fileInputRef =
    useRef(
      null
    );


  const totalAttachmentBytes =
    useMemo(
      () =>
        attachments.reduce(
          (
            total,
            attachment
          ) =>
            total +
            Number(
              attachment.size_bytes ||
              0
            ),
          0
        ),
      [
        attachments
      ]
    );


  async function ingestFiles(
    fileList
  ) {
    const incoming =
      Array.from(
        fileList || []
      );

    if (
      incoming.length === 0
    ) {
      return;
    }

    setAttachmentError(
      ""
    );

    const accepted = [];

    const existingKeys =
      new Set(
        attachments.map(
          attachment =>
            [
              attachment.filename,
              attachment.size_bytes
            ].join(
              ":"
            )
        )
      );

    for (
      const file
      of incoming
    ) {
      if (
        file.size >
        MAX_ATTACHMENT_BYTES
      ) {
        setAttachmentError(
          `${file.name} is ${formatBytes(file.size)}; maximum is ${MAX_ATTACHMENT_MIB} MiB per attachment.`
        );

        continue;
      }

      const key =
        [
          file.name,
          file.size
        ].join(
          ":"
        );

      if (
        existingKeys.has(
          key
        )
      ) {
        continue;
      }

      accepted.push(
        file
      );

      existingKeys.add(
        key
      );
    }

    if (
      accepted.length === 0
    ) {
      return;
    }

    setUploading(
      true
    );

    setStatus(
      "uploading attachments"
    );

    try {
      const uploaded =
        [];

      for (
        const file
        of accepted
      ) {
        const record =
          await uploadAttachment(
            file
          );

        uploaded.push(
          record
        );
      }

      setAttachments(
        current => [
          ...current,
          ...uploaded
        ]
      );

      setStatus(
        `${uploaded.length} attachment${uploaded.length === 1 ? "" : "s"} ready`
      );

    } catch (
      error
    ) {
      setAttachmentError(
        String(
          error?.message ||
          error
        )
      );

      setStatus(
        "attachment error"
      );

    } finally {
      setUploading(
        false
      );

      if (
        fileInputRef.current
      ) {
        fileInputRef.current.value =
          "";
      }
    }
  }


  function removeAttachment(
    attachmentId
  ) {
    setAttachments(
      current =>
        current.filter(
          attachment =>
            attachment.attachment_id !==
            attachmentId
        )
    );
  }


  async function handleSpeech(
    text
  ) {
    setHeard(
      text
    );

    if (
      !hasWakePhrase(
        text
      )
    ) {
      setStatus(
        "waiting for wake phrase"
      );

      return;
    }

    const command =
      stripWakePhrase(
        text
      );

    setArmed(
      true
    );

    setStatus(
      "wake phrase detected"
    );

    const prompt =
      command ||
      "Palaver, acknowledge voice activation.";

    const answer =
      await askPalaver(
        prompt,
        personaId,
        attachments
      );

    setReply(
      answer
    );

    speak(
      answer,
      personaId
    );

    setStatus(
      "answered"
    );
  }


  function start() {
    if (
      !SpeechRecognition
    ) {
      setStatus(
        "speech recognition unavailable"
      );

      return;
    }

    const rec =
      new SpeechRecognition();

    rec.lang =
      "en-US";

    rec.interimResults =
      true;

    rec.continuous =
      true;

    rec.onstart =
      () =>
        setStatus(
          "listening"
        );

    rec.onresult =
      event => {
        let text =
          "";

        for (
          let i =
            event.resultIndex;
          i <
            event.results.length;
          i++
        ) {
          text +=
            event.results[i][0]
              .transcript +
            " ";
        }

        setHeard(
          text.trim()
        );

        for (
          let i =
            event.resultIndex;
          i <
            event.results.length;
          i++
        ) {
          if (
            event.results[i]
              .isFinal
          ) {
            handleSpeech(
              event.results[i][0]
                .transcript
            );
          }
        }
      };

    rec.onerror =
      event =>
        setStatus(
          "voice error: " +
          event.error
        );

    rec.onend =
      () => {
        if (
          recognitionRef.current
        ) {
          try {
            rec.start();
          } catch (_) {
          }
        }
      };

    recognitionRef.current =
      rec;

    rec.start();
  }


  function stop() {
    const rec =
      recognitionRef.current;

    recognitionRef.current =
      null;

    rec?.stop?.();

    setStatus(
      "stopped"
    );
  }


  useEffect(
    () => {
      window.PALAVER_PERSONA =
        personaId;

      window
        .speechSynthesis
        ?.getVoices
        ?.();
    },
    [
      personaId
    ]
  );


  useEffect(
    () => {
      return () => {
        recognitionRef.current
          ?.stop
          ?.();

        window
          .speechSynthesis
          ?.cancel
          ?.();
      };
    },
    []
  );


  const selectedVoice =
    ENVOY_VOICES[
      personaId
    ] ||
    ENVOY_VOICES
      .palaver_default;


  return (
    <main>
      <section>
        <div className="kicker">
          PALAVER VOICE / ENVOY VOICE REGISTRY
        </div>

        <h1>
          Palaver Voice Interface
        </h1>

        <p className="phrase">
          Say: “wake up palaver” or “hey palaver”
        </p>

        <label>
          Envoy Persona Voice
        </label>

        <select
          value={
            personaId
          }
          onChange={
            event =>
              setPersonaId(
                event.target.value
              )
          }
        >
          {Object.values(
            ENVOY_VOICES
          ).map(
            voice => (
              <option
                key={
                  voice.persona_id
                }
                value={
                  voice.persona_id
                }
              >
                {
                  voice.display_name
                }
              </option>
            )
          )}
        </select>

        <div className="voiceProfile">
          <strong>
            {
              selectedVoice.display_name
            }
          </strong>

          <span>
            {
              selectedVoice.accent
            }
          </span>

          <span>
            {
              selectedVoice.cadence
            }
          </span>

          <span>
            {
              selectedVoice.safety_note
            }
          </span>
        </div>

        <label>
          Attachments
        </label>

        <div
          className={
            "attachmentZone" +
            (
              dragActive
                ? " active"
                : ""
            )
          }
          onDragEnter={
            event => {
              event.preventDefault();
              setDragActive(
                true
              );
            }
          }
          onDragOver={
            event => {
              event.preventDefault();
              setDragActive(
                true
              );
            }
          }
          onDragLeave={
            event => {
              event.preventDefault();

              if (
                event.currentTarget ===
                event.target
              ) {
                setDragActive(
                  false
                );
              }
            }
          }
          onDrop={
            event => {
              event.preventDefault();

              setDragActive(
                false
              );

              ingestFiles(
                event.dataTransfer
                  .files
              );
            }
          }
          onClick={
            () =>
              fileInputRef
                .current
                ?.click()
          }
        >
          <input
            ref={
              fileInputRef
            }
            className="hiddenFileInput"
            type="file"
            multiple
            onChange={
              event =>
                ingestFiles(
                  event.target.files
                )
            }
          />

          <div className="attachmentMark">
            +
          </div>

          <div>
            <strong>
              Drop files here or choose attachments
            </strong>

            <span>
              Up to {MAX_ATTACHMENT_MIB} MiB per file
            </span>
          </div>
        </div>

        {attachmentError && (
          <div className="attachmentError">
            {
              attachmentError
            }
          </div>
        )}

        {attachments.length > 0 && (
          <div className="attachmentList">
            {attachments.map(
              attachment => (
                <div
                  className="attachment"
                  key={
                    attachment.attachment_id
                  }
                >
                  <div className="attachmentIdentity">
                    <strong>
                      {
                        attachment.filename
                      }
                    </strong>

                    <span>
                      {
                        attachment.content_type ||
                        "application/octet-stream"
                      }
                    </span>
                  </div>

                  <div className="attachmentMeta">
                    <span>
                      {
                        formatBytes(
                          attachment.size_bytes
                        )
                      }
                    </span>

                    <span className="attachmentReady">
                      stored
                    </span>

                    <button
                      type="button"
                      className="attachmentRemove"
                      onClick={
                        event => {
                          event.stopPropagation();

                          removeAttachment(
                            attachment.attachment_id
                          );
                        }
                      }
                      aria-label={
                        `Remove ${attachment.filename}`
                      }
                    >
                      ×
                    </button>
                  </div>
                </div>
              )
            )}

            <div className="attachmentSummary">
              <span>
                {attachments.length} attached
              </span>

              <span>
                {
                  formatBytes(
                    totalAttachmentBytes
                  )
                }
              </span>
            </div>
          </div>
        )}

        <div className="buttons">
          <button
            onClick={
              start
            }
            disabled={
              uploading
            }
          >
            Start Listening
          </button>

          <button
            onClick={
              stop
            }
          >
            Stop
          </button>

          <button
            onClick={
              () =>
                speak(
                  reply ||
                  "Palaver voice is active.",
                  personaId
                )
            }
          >
            Test Voice
          </button>
        </div>

        <div className="grid">
          <div>
            <label>
              Status
            </label>

            <pre>
              {
                uploading
                  ? "uploading"
                  : status
              }
            </pre>
          </div>

          <div>
            <label>
              Armed
            </label>

            <pre>
              {
                armed
                  ? "yes"
                  : "no"
              }
            </pre>
          </div>

          <div>
            <label>
              Heard
            </label>

            <pre>
              {
                heard ||
                "nothing yet"
              }
            </pre>
          </div>

          <div>
            <label>
              Reply
            </label>

            <pre>
              {
                reply ||
                "no reply yet"
              }
            </pre>
          </div>
        </div>
      </section>

      <style>{`
        * {
          box-sizing: border-box;
        }

        body {
          margin: 0;
          background: #05070d;
          color: #f5f7ff;
          font-family:
            Inter,
            ui-sans-serif,
            system-ui,
            -apple-system,
            BlinkMacSystemFont,
            "Segoe UI",
            sans-serif;
        }

        main {
          min-height: 100vh;
          display: grid;
          place-items: center;
          padding: 24px;
          background:
            radial-gradient(
              circle at 20% 0%,
              rgba(91, 141, 239, 0.22),
              transparent 36%
            ),
            radial-gradient(
              circle at 80% 10%,
              rgba(177, 92, 255, 0.18),
              transparent 34%
            ),
            linear-gradient(
              135deg,
              #05070d,
              #090c14 48%,
              #020308
            );
        }

        section {
          width: min(
            1040px,
            100%
          );
          border:
            1px solid
            rgba(
              255,
              255,
              255,
              0.14
            );
          border-radius: 28px;
          padding:
            clamp(
              24px,
              5vw,
              56px
            );
          background:
            rgba(
              8,
              11,
              20,
              0.78
            );
          box-shadow:
            0 30px 120px
            rgba(
              0,
              0,
              0,
              0.6
            );
          backdrop-filter:
            blur(
              18px
            );
        }

        .kicker {
          color: #8fb4ff;
          letter-spacing:
            0.24em;
          font-size: 12px;
          font-weight: 800;
          margin-bottom: 16px;
        }

        h1 {
          font-size:
            clamp(
              40px,
              7vw,
              88px
            );
          line-height: 0.92;
          letter-spacing:
            -0.07em;
          margin:
            0 0 18px;
        }

        .phrase {
          font-size:
            clamp(
              18px,
              2.6vw,
              30px
            );
          color: #d8e2ff;
          margin:
            0 0 28px;
        }

        label {
          display: block;
          color: #9eb9ff;
          font-size: 12px;
          font-weight: 900;
          letter-spacing:
            0.18em;
          text-transform:
            uppercase;
          margin:
            18px 0 8px;
        }

        select {
          width: 100%;
          border-radius: 16px;
          border:
            1px solid
            rgba(
              255,
              255,
              255,
              0.14
            );
          background:
            rgba(
              255,
              255,
              255,
              0.08
            );
          color: white;
          padding:
            14px 16px;
          font-size: 16px;
          outline: none;
        }

        option {
          color: black;
        }

        .voiceProfile {
          display: grid;
          gap: 6px;
          margin:
            14px 0 24px;
          padding: 16px;
          border-radius: 18px;
          background:
            rgba(
              255,
              255,
              255,
              0.055
            );
          border:
            1px solid
            rgba(
              255,
              255,
              255,
              0.11
            );
          color:
            rgba(
              245,
              247,
              255,
              0.8
            );
        }

        .voiceProfile strong {
          color: white;
          font-size: 18px;
        }

        .attachmentZone {
          min-height: 128px;
          display: flex;
          align-items: center;
          gap: 18px;
          padding: 20px;
          border-radius: 22px;
          cursor: pointer;
          border:
            1px dashed
            rgba(
              143,
              180,
              255,
              0.42
            );
          background:
            linear-gradient(
              135deg,
              rgba(
                77,
                124,
                255,
                0.08
              ),
              rgba(
                157,
                92,
                255,
                0.05
              )
            );
          transition:
            transform 160ms ease,
            border-color 160ms ease,
            background 160ms ease;
        }

        .attachmentZone:hover,
        .attachmentZone.active {
          transform:
            translateY(
              -1px
            );
          border-color:
            rgba(
              143,
              180,
              255,
              0.92
            );
          background:
            linear-gradient(
              135deg,
              rgba(
                77,
                124,
                255,
                0.16
              ),
              rgba(
                157,
                92,
                255,
                0.1
              )
            );
        }

        .hiddenFileInput {
          display: none;
        }

        .attachmentMark {
          width: 54px;
          height: 54px;
          flex:
            0 0 auto;
          display: grid;
          place-items: center;
          border-radius: 18px;
          font-size: 30px;
          font-weight: 300;
          color: white;
          background:
            linear-gradient(
              135deg,
              #4d7cff,
              #9d5cff
            );
          box-shadow:
            0 12px 40px
            rgba(
              89,
              103,
              255,
              0.25
            );
        }

        .attachmentZone strong,
        .attachmentZone span {
          display: block;
        }

        .attachmentZone strong {
          font-size: 16px;
          margin-bottom: 5px;
        }

        .attachmentZone span {
          color:
            rgba(
              245,
              247,
              255,
              0.58
            );
          font-size: 13px;
        }

        .attachmentError {
          margin-top: 10px;
          padding:
            11px 13px;
          border-radius: 14px;
          color: #ffd7e7;
          border:
            1px solid
            rgba(
              255,
              90,
              149,
              0.3
            );
          background:
            rgba(
              255,
              44,
              112,
              0.09
            );
          font-size: 13px;
        }

        .attachmentList {
          display: grid;
          gap: 8px;
          margin-top: 10px;
        }

        .attachment {
          display: flex;
          align-items: center;
          justify-content:
            space-between;
          gap: 16px;
          padding:
            11px 13px;
          border-radius: 16px;
          border:
            1px solid
            rgba(
              255,
              255,
              255,
              0.1
            );
          background:
            rgba(
              255,
              255,
              255,
              0.045
            );
        }

        .attachmentIdentity {
          min-width: 0;
        }

        .attachmentIdentity strong,
        .attachmentIdentity span {
          display: block;
        }

        .attachmentIdentity strong {
          overflow: hidden;
          text-overflow:
            ellipsis;
          white-space:
            nowrap;
          font-size: 14px;
        }

        .attachmentIdentity span {
          color:
            rgba(
              245,
              247,
              255,
              0.46
            );
          font-size: 11px;
          margin-top: 3px;
        }

        .attachmentMeta {
          flex:
            0 0 auto;
          display: flex;
          align-items: center;
          gap: 10px;
          color:
            rgba(
              245,
              247,
              255,
              0.65
            );
          font-size: 12px;
        }

        .attachmentReady {
          color: #a6ffcb;
        }

        .attachmentRemove {
          width: 30px;
          height: 30px;
          padding: 0;
          display: grid;
          place-items: center;
          border-radius: 999px;
          background:
            rgba(
              255,
              255,
              255,
              0.07
            );
        }

        .attachmentSummary {
          display: flex;
          justify-content:
            space-between;
          color:
            rgba(
              245,
              247,
              255,
              0.48
            );
          padding:
            4px 3px;
          font-size: 11px;
        }

        .buttons {
          display: flex;
          flex-wrap: wrap;
          gap: 12px;
          margin:
            28px 0;
        }

        button {
          border: 0;
          border-radius: 999px;
          padding:
            14px 20px;
          color: white;
          font-weight: 900;
          cursor: pointer;
          background:
            linear-gradient(
              135deg,
              #4d7cff,
              #9d5cff
            );
        }

        button:disabled {
          opacity: 0.48;
          cursor:
            not-allowed;
        }

        .grid {
          display: grid;
          grid-template-columns:
            repeat(
              2,
              minmax(
                0,
                1fr
              )
            );
          gap: 14px;
        }

        pre {
          white-space:
            pre-wrap;
          min-height: 72px;
          margin: 0;
          padding: 16px;
          border-radius: 18px;
          color:
            rgba(
              245,
              247,
              255,
              0.86
            );
          background:
            rgba(
              255,
              255,
              255,
              0.06
            );
          border:
            1px solid
            rgba(
              255,
              255,
              255,
              0.11
            );
          font: inherit;
          line-height: 1.5;
        }

        @media (
          max-width: 720px
        ) {
          .grid {
            grid-template-columns:
              1fr;
          }

          .buttons > button {
            width: 100%;
          }

          .attachment {
            align-items:
              flex-start;
          }

          .attachmentMeta {
            flex-wrap: wrap;
            justify-content:
              flex-end;
          }
        }

        @media (
          prefers-reduced-motion:
          reduce
        ) {
          *,
          *::before,
          *::after {
            scroll-behavior:
              auto !important;
            transition-duration:
              0.001ms !important;
            animation-duration:
              0.001ms !important;
            animation-iteration-count:
              1 !important;
          }
        }
      `}</style>
    </main>
  );
}


createRoot(
  document.getElementById(
    "root"
  )
).render(
  <App />
);
