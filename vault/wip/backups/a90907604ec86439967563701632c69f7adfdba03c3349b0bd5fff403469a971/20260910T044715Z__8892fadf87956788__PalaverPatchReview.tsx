import {
  AnimatePresence,
  motion,
  useReducedMotion,
} from "framer-motion"
import {
  Check,
  ChevronRight,
  Code2,
  FileDiff,
  LoaderCircle,
  ShieldCheck,
  X,
  XCircle,
} from "lucide-react"
import {
  useCallback,
  useEffect,
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
  | "creating"
  | "pending"
  | "applying"
  | "rejecting"
  | "applied"
  | "rejected"
  | "error"

type DiffPayload = {
  path?: string
  diff?: string
}

type PatchPayload = Record<string, unknown>

type ApiResult<T> = {
  ok?: boolean
  diff?: T
  patch?: T
  error?: string
  answer?: string
  trace?: string
}

const apiBase = (
  import.meta.env.VITE_PALAVER_API_BASE || ""
).replace(/\/$/, "")

async function postJson<T>(
  path: string,
  body: Record<string, unknown>,
): Promise<ApiResult<T>> {
  const response = await fetch(
    `${apiBase}${path}`,
    {
      method: "POST",
      headers: {
        "Content-Type":
          "application/json",
      },
      body: JSON.stringify(body),
    },
  )

  const payload =
    (await response.json()) as
      ApiResult<T>

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

  return payload
}

function patchIdFrom(
  patch: unknown,
): string {
  if (
    !patch ||
    typeof patch !== "object" ||
    Array.isArray(patch)
  ) {
    return ""
  }

  const record =
    patch as Record<
      string,
      unknown
    >

  const candidates = [
    record.patch_id,
    record.id,
    record.review_id,
  ]

  for (const candidate of candidates) {
    if (
      typeof candidate ===
        "string" &&
      candidate.trim()
    ) {
      return candidate.trim()
    }
  }

  return ""
}

function prettyPatch(
  patch: unknown,
): string {
  try {
    return JSON.stringify(
      patch,
      null,
      2,
    )
  } catch {
    return String(patch)
  }
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

  const [patch, setPatch] =
    useState<PatchPayload | null>(
      null,
    )

  const [patchId, setPatchId] =
    useState("")

  const [state, setState] =
    useState<ReviewState>("idle")

  const [error, setError] =
    useState("")

  const busy =
    state === "diffing" ||
    state === "creating" ||
    state === "applying" ||
    state === "rejecting"

  const canPreview =
    Boolean(path.trim()) &&
    !busy

  const canCreate =
    Boolean(path.trim()) &&
    Boolean(diff) &&
    !busy &&
    state !== "pending" &&
    state !== "applied"

  const canResolve =
    state === "pending" &&
    Boolean(patchId) &&
    !busy

  const statusLabel =
    useMemo(() => {
      switch (state) {
        case "diffing":
          return "building diff"
        case "creating":
          return "creating review"
        case "pending":
          return "awaiting decision"
        case "applying":
          return "applying approved patch"
        case "rejecting":
          return "rejecting patch"
        case "applied":
          return "applied"
        case "rejected":
          return "rejected"
        case "error":
          return "action failed"
        default:
          return "review first"
      }
    }, [state])

  const resetReview =
    useCallback(() => {
      setDiff("")
      setPatch(null)
      setPatchId("")
      setState("idle")
      setError("")
    }, [])

  const close =
    useCallback(() => {
      if (busy) {
        return
      }

      setOpen(false)
    }, [busy])

  const preview =
    useCallback(async () => {
      if (!path.trim()) {
        return
      }

      setState("diffing")
      setError("")
      setPatch(null)
      setPatchId("")

      try {
        const result =
          await postJson<DiffPayload>(
            "/api/file/diff",
            {
              path: path.trim(),
              content,
            },
          )

        const nextDiff =
          result.diff?.diff || ""

        setDiff(nextDiff)

        setState("idle")
      } catch (caught) {
        setState("error")
        setError(
          caught instanceof Error
            ? caught.message
            : String(caught),
        )
      }
    }, [content, path])

  const createReview =
    useCallback(async () => {
      if (
        !path.trim() ||
        !diff
      ) {
        return
      }

      setState("creating")
      setError("")

      try {
        const result =
          await postJson<PatchPayload>(
            "/api/patch-review/create",
            {
              path: path.trim(),
              content,
            },
          )

        const created =
          result.patch || {}

        const createdId =
          patchIdFrom(created)

        if (!createdId) {
          throw new Error(
            "patch review was created without an identifiable patch id",
          )
        }

        setPatch(created)
        setPatchId(createdId)
        setState("pending")
      } catch (caught) {
        setState("error")
        setError(
          caught instanceof Error
            ? caught.message
            : String(caught),
        )
      }
    }, [
      content,
      diff,
      path,
    ])

  const apply =
    useCallback(async () => {
      if (!patchId) {
        return
      }

      setState("applying")
      setError("")

      try {
        const result =
          await postJson<PatchPayload>(
            "/api/patch-review/apply",
            {
              patch_id: patchId,
            },
          )

        setPatch(
          result.patch || {},
        )

        setState("applied")
      } catch (caught) {
        setState("error")
        setError(
          caught instanceof Error
            ? caught.message
            : String(caught),
        )
      }
    }, [patchId])

  const reject =
    useCallback(async () => {
      if (!patchId) {
        return
      }

      setState("rejecting")
      setError("")

      try {
        const result =
          await postJson<PatchPayload>(
            "/api/patch-review/reject",
            {
              patch_id: patchId,
            },
          )

        setPatch(
          result.patch || {},
        )

        setState("rejected")
      } catch (caught) {
        setState("error")
        setError(
          caught instanceof Error
            ? caught.message
            : String(caught),
        )
      }
    }, [patchId])

  useEffect(() => {
    const onKeyDown = (
      event:
        globalThis.KeyboardEvent,
    ) => {
      if (
        (event.metaKey ||
          event.ctrlKey) &&
        event.shiftKey &&
        event.key.toLowerCase() ===
          "p"
      ) {
        event.preventDefault()

        setOpen(
          (current) => !current,
        )

        return
      }

      if (
        event.key === "Escape" &&
        open
      ) {
        close()
      }
    }

    window.addEventListener(
      "keydown",
      onKeyDown,
    )

    return () => {
      window.removeEventListener(
        "keydown",
        onKeyDown,
      )
    }
  }, [close, open])

  const onSubmit = (
    event: FormEvent,
  ) => {
    event.preventDefault()
    preview()
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
      preview()
    }
  }

  return (
    <>
      <button
        type="button"
        className="palaver-patch-launcher"
        aria-label="Open patch review"
        title="Patch review · Ctrl/⌘ Shift P"
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
              onClick={close}
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
                    review first
                  </span>

                  <h2>
                    patch
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

                    {statusLabel}
                  </span>

                  <button
                    type="button"
                    aria-label="Close patch review"
                    disabled={busy}
                    onClick={close}
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
                    placeholder="relative path inside savant-runtime"
                    spellCheck={false}
                    autoCapitalize="none"
                    autoCorrect="off"
                    disabled={
                      state ===
                        "pending" ||
                      state ===
                        "applying" ||
                      state ===
                        "applied"
                    }
                    onChange={(event) => {
                      setPath(
                        event.target
                          .value,
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
                    disabled={
                      state ===
                        "pending" ||
                      state ===
                        "applying" ||
                      state ===
                        "applied"
                    }
                    onKeyDown={
                      onEditorKeyDown
                    }
                    onChange={(event) => {
                      setContent(
                        event.target
                          .value,
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
                      !canPreview
                    }
                  >
                    <FileDiff size={15} />
                    preview diff
                  </button>

                  <span>
                    no write occurs during preview
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

                    {diff && (
                      <span>
                        reviewed before proposal
                      </span>
                    )}
                  </header>

                  <pre>
                    {diff ||
                      "No diff generated yet."}
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

                {patch && (
                  <details className="palaver-patch-receipt">
                    <summary>
                      review record
                    </summary>

                    <pre>
                      {prettyPatch(
                        patch,
                      )}
                    </pre>
                  </details>
                )}

                <footer className="palaver-patch-actions">
                  {state !==
                    "pending" &&
                    state !==
                      "applied" &&
                    state !==
                      "rejected" && (
                      <button
                        type="button"
                        className="palaver-patch-create"
                        disabled={
                          !canCreate
                        }
                        onClick={
                          createReview
                        }
                      >
                        <ShieldCheck
                          size={16}
                        />
                        create review
                        <ChevronRight
                          size={15}
                        />
                      </button>
                    )}

                  {state ===
                    "pending" && (
                    <>
                      <button
                        type="button"
                        className="palaver-patch-reject"
                        disabled={
                          !canResolve
                        }
                        onClick={
                          reject
                        }
                      >
                        <XCircle
                          size={16}
                        />
                        reject
                      </button>

                      <button
                        type="button"
                        className="palaver-patch-apply"
                        disabled={
                          !canResolve
                        }
                        onClick={
                          apply
                        }
                      >
                        <Check
                          size={16}
                        />
                        apply reviewed patch
                      </button>
                    </>
                  )}

                  {(state ===
                    "applied" ||
                    state ===
                      "rejected") && (
                    <button
                      type="button"
                      className="palaver-patch-primary"
                      onClick={() => {
                        setPath("")
                        setContent("")
                        resetReview()
                      }}
                    >
                      new review
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
