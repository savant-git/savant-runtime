import {
  AnimatePresence,
  motion,
  useReducedMotion,
} from "framer-motion"
import {
  Check,
  ClipboardCopy,
  Code2,
  FileDiff,
  LoaderCircle,
  ShieldCheck,
  X,
  XCircle,
} from "lucide-react"
import {
  useCallback,
  useMemo,
  useState,
} from "react"
import type {
  FormEvent,
  KeyboardEvent,
} from "react"

type ReviewState =
  | "idle"
  | "diffing"
  | "reviewed"
  | "error"

type DiffPayload = {
  path?: string
  diff?: string
}

type DiffResponse = {
  ok?: boolean
  diff?: DiffPayload
  error?: string
  answer?: string
  trace?: string
}

const apiBase = (
  import.meta.env.VITE_PALAVER_API_BASE || ""
).replace(/\/$/, "")

function normalizePath(
  value: string,
): string {
  return value.trim()
}

function localProposal(
  path: string,
  content: string,
  diff: string,
): string {
  return [
    "palaver reviewed patch proposal",
    "",
    `path: ${path}`,
    "",
    "diff:",
    diff || "(no changes)",
    "",
    "proposed complete content:",
    "",
    content,
  ].join("\n")
}

async function requestDiff(
  path: string,
  content: string,
): Promise<DiffPayload> {
  const response = await fetch(
    `${apiBase}/api/file/diff`,
    {
      method: "POST",
      headers: {
        "Content-Type":
          "application/json",
      },
      body: JSON.stringify({
        path,
        content,
      }),
    },
  )

  const payload =
    (await response.json()) as
      DiffResponse

  if (
    !response.ok ||
    payload.ok === false
  ) {
    throw new Error(
      payload.error ||
        payload.answer ||
        payload.trace ||
        `${response.status} ${response.statusText}`,
    )
  }

  if (
    !payload.diff ||
    typeof payload.diff !==
      "object"
  ) {
    throw new Error(
      "palaver diff response did not contain a diff payload",
    )
  }

  return payload.diff
}

export default function PalaverPatchReview() {
  const reducedMotion =
    useReducedMotion()

  const [open, setOpen] =
    useState(false)

  const [path, setPath] =
    useState("")

  const [content, setContent] =
    useState("")

  const [diff, setDiff] =
    useState("")

  const [resolvedPath, setResolvedPath] =
    useState("")

  const [state, setState] =
    useState<ReviewState>(
      "idle",
    )

  const [error, setError] =
    useState("")

  const [copied, setCopied] =
    useState(false)

  const normalizedPath =
    useMemo(
      () => normalizePath(path),
      [path],
    )

  const busy =
    state === "diffing"

  const proposal =
    useMemo(
      () =>
        state === "reviewed"
          ? localProposal(
              resolvedPath ||
                normalizedPath,
              content,
              diff,
            )
          : "",
      [
        content,
        diff,
        normalizedPath,
        resolvedPath,
        state,
      ],
    )

  const resetReview =
    useCallback(() => {
      setDiff("")
      setResolvedPath("")
      setState("idle")
      setError("")
      setCopied(false)
    }, [])

  const review =
    useCallback(async () => {
      if (
        !normalizedPath ||
        busy
      ) {
        return
      }

      setState("diffing")
      setError("")
      setCopied(false)

      try {
        const result =
          await requestDiff(
            normalizedPath,
            content,
          )

        setResolvedPath(
          typeof result.path ===
            "string"
            ? result.path
            : normalizedPath,
        )

        setDiff(
          typeof result.diff ===
            "string"
            ? result.diff
            : "",
        )

        setState("reviewed")
      } catch (caught) {
        setDiff("")
        setResolvedPath("")
        setState("error")

        setError(
          caught instanceof Error
            ? caught.message
            : String(caught),
        )
      }
    }, [
      busy,
      content,
      normalizedPath,
    ])

  const copyProposal =
    useCallback(async () => {
      if (!proposal) {
        return
      }

      try {
        await navigator.clipboard.writeText(
          proposal,
        )

        setCopied(true)

        window.setTimeout(
          () => {
            setCopied(false)
          },
          1400,
        )
      } catch {
        setCopied(false)
      }
    }, [proposal])

  const onSubmit = (
    event: FormEvent,
  ) => {
    event.preventDefault()
    void review()
  }

  const onEditorKeyDown = (
    event:
      KeyboardEvent<HTMLTextAreaElement>,
  ) => {
    if (
      (event.metaKey ||
        event.ctrlKey) &&
      event.key === "Enter"
    ) {
      event.preventDefault()
      void review()
    }
  }

  return (
    <>
      <button
        type="button"
        className="palaver-patch-launcher"
        aria-label="Open patch review"
        title="Patch review"
        onClick={() =>
          setOpen(true)
        }
      >
        <FileDiff size={17} />
      </button>

      <AnimatePresence>
        {open && (
          <>
            <motion.button
              type="button"
              className="palaver-patch-backdrop"
              aria-label="Close patch review"
              initial={{
                opacity: 0,
              }}
              animate={{
                opacity: 1,
              }}
              exit={{
                opacity: 0,
              }}
              onClick={() => {
                if (!busy) {
                  setOpen(false)
                }
              }}
            />

            <motion.section
              className="palaver-patch-review"
              role="dialog"
              aria-modal="true"
              aria-label="Patch review"
              initial={
                reducedMotion
                  ? false
                  : {
                      opacity: 0,
                      y: 24,
                      scale: 0.985,
                    }
              }
              animate={{
                opacity: 1,
                y: 0,
                scale: 1,
              }}
              exit={{
                opacity: 0,
                y: 18,
                scale: 0.99,
              }}
            >
              <header className="palaver-patch-head">
                <div className="palaver-patch-title">
                  <span>
                    <ShieldCheck
                      size={15}
                    />
                    server diff
                  </span>

                  <h2>
                    patch review
                  </h2>
                </div>

                <div className="palaver-patch-head-actions">
                  <span
                    className={`palaver-patch-status state-${state}`}
                  >
                    {busy && (
                      <LoaderCircle
                        size={12}
                        className="spin"
                      />
                    )}

                    {state ===
                      "diffing" &&
                      "building diff"}

                    {state ===
                      "reviewed" &&
                      "reviewed"}

                    {state ===
                      "error" &&
                      "diff failed"}

                    {state ===
                      "idle" &&
                      "no mutation"}
                  </span>

                  <button
                    type="button"
                    aria-label="Close patch review"
                    disabled={busy}
                    onClick={() =>
                      setOpen(false)
                    }
                  >
                    <X size={18} />
                  </button>
                </div>
              </header>

              <form
                className="palaver-patch-body"
                onSubmit={onSubmit}
              >
                <label className="palaver-patch-field">
                  <span>
                    runtime path
                  </span>

                  <input
                    value={path}
                    placeholder="path inside savant-runtime"
                    spellCheck={false}
                    autoCapitalize="none"
                    autoCorrect="off"
                    disabled={busy}
                    onChange={(event) => {
                      setPath(
                        event.target.value,
                      )
                      resetReview()
                    }}
                  />
                </label>

                <label className="palaver-patch-field palaver-patch-content">
                  <span>
                    proposed complete content
                  </span>

                  <textarea
                    value={content}
                    placeholder="Paste the proposed complete file content here."
                    spellCheck={false}
                    disabled={busy}
                    onKeyDown={
                      onEditorKeyDown
                    }
                    onChange={(event) => {
                      setContent(
                        event.target.value,
                      )
                      resetReview()
                    }}
                  />
                </label>

                <div className="palaver-patch-toolbar">
                  <button
                    type="submit"
                    className="palaver-patch-primary"
                    disabled={
                      !normalizedPath ||
                      busy
                    }
                  >
                    {busy ? (
                      <LoaderCircle
                        size={15}
                        className="spin"
                      />
                    ) : (
                      <FileDiff
                        size={15}
                      />
                    )}

                    preview diff
                  </button>

                  <span>
                    diff only, no write endpoint invoked
                  </span>
                </div>

                <div className="palaver-patch-diff">
                  <header>
                    <div>
                      <Code2 size={14} />
                      <strong>
                        deterministic diff
                      </strong>
                    </div>

                    {state ===
                      "reviewed" && (
                      <span>
                        {resolvedPath ||
                          normalizedPath}
                      </span>
                    )}
                  </header>

                  <pre>
                    {state ===
                    "reviewed"
                      ? diff ||
                        "No changes."
                      : state ===
                          "diffing"
                        ? "Generating server-side diff…"
                        : "No diff generated yet."}
                  </pre>
                </div>

                {error && (
                  <div
                    className="palaver-patch-error"
                    role="alert"
                  >
                    <XCircle
                      size={15}
                    />

                    <span>
                      {error}
                    </span>
                  </div>
                )}

                <footer className="palaver-patch-actions">
                  {state ===
                    "reviewed" && (
                    <button
                      type="button"
                      className="palaver-patch-create"
                      onClick={() =>
                        void copyProposal()
                      }
                    >
                      {copied ? (
                        <Check
                          size={16}
                        />
                      ) : (
                        <ClipboardCopy
                          size={16}
                        />
                      )}

                      {copied
                        ? "copied"
                        : "copy reviewed proposal"}
                    </button>
                  )}
                </footer>
              </form>
            </motion.section>
          </>
        )}
      </AnimatePresence>
    </>
  )
}
