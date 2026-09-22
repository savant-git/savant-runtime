import {
  AnimatePresence,
  motion,
  useReducedMotion,
} from "framer-motion"
import {
  Check,
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

type PatchRecord = {
  id?: string
  path?: string
  before?: string
  after?: string
  diff?: string
  expected_digest?: string | null
  mutation_owner?: string
  requester?: string
  status?: string
  applied?: boolean
  rejected?: boolean
  mutation?: unknown
  [key: string]: unknown
}

type ApiResponse = {
  ok?: boolean
  diff?: DiffPayload
  patch?: PatchRecord
  error?: string
  answer?: string
  trace?: string
}

const apiBase = (
  import.meta.env.VITE_PALAVER_API_BASE || ""
).replace(/\/$/, "")

async function postJson(
  route: string,
  body: Record<string, unknown>,
): Promise<ApiResponse> {
  const response = await fetch(
    `${apiBase}${route}`,
    {
      method: "POST",
      headers: {
        "Content-Type":
          "application/json",
      },
      body: JSON.stringify(body),
    },
  )

  let payload:
    ApiResponse

  try {
    payload =
      (await response.json()) as
        ApiResponse
  } catch {
    throw new Error(
      `${response.status} ${response.statusText}`,
    )
  }

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

function normalizePath(
  value: string,
): string {
  return value.trim()
}

function patchId(
  patch: PatchRecord | null,
): string {
  const value =
    patch?.id

  return typeof value === "string"
    ? value.trim()
    : ""
}

function pretty(
  value: unknown,
): string {
  try {
    return JSON.stringify(
      value,
      null,
      2,
    )
  } catch {
    return String(value)
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

  const [resolvedPath, setResolvedPath] =
    useState("")

  const [patch, setPatch] =
    useState<PatchRecord | null>(
      null,
    )

  const [state, setState] =
    useState<ReviewState>(
      "idle",
    )

  const [error, setError] =
    useState("")

  const normalizedPath =
    useMemo(
      () => normalizePath(path),
      [path],
    )

  const currentPatchId =
    useMemo(
      () => patchId(patch),
      [patch],
    )

  const busy =
    state === "diffing" ||
    state === "creating" ||
    state === "applying" ||
    state === "rejecting"

  const canEdit =
    !busy &&
    state !== "pending" &&
    state !== "applied"

  const canPreview =
    Boolean(normalizedPath) &&
    canEdit

  const canCreate =
    state === "reviewed" &&
    Boolean(diff || content) &&
    Boolean(normalizedPath) &&
    !busy

  const canResolve =
    state === "pending" &&
    Boolean(currentPatchId) &&
    !busy

  const resetReview =
    useCallback(() => {
      setDiff("")
      setResolvedPath("")
      setPatch(null)
      setState("idle")
      setError("")
    }, [])

  const preview =
    useCallback(async () => {
      if (!canPreview) {
        return
      }

      setState("diffing")
      setError("")
      setPatch(null)

      try {
        const payload =
          await postJson(
            "/api/file/diff",
            {
              path: normalizedPath,
              content,
            },
          )

        if (
          !payload.diff ||
          typeof payload.diff !==
            "object"
        ) {
          throw new Error(
            "diff response did not contain a diff payload",
          )
        }

        setResolvedPath(
          typeof payload.diff.path ===
            "string"
            ? payload.diff.path
            : normalizedPath,
        )

        setDiff(
          typeof payload.diff.diff ===
            "string"
            ? payload.diff.diff
            : "",
        )

        setState("reviewed")
      } catch (caught) {
        setState("error")

        setError(
          caught instanceof Error
            ? caught.message
            : String(caught),
        )
      }
    }, [
      canPreview,
      content,
      normalizedPath,
    ])

  const createReview =
    useCallback(async () => {
      if (!canCreate) {
        return
      }

      setState("creating")
      setError("")

      try {
        const payload =
          await postJson(
            "/api/patch-review/create",
            {
              path:
                resolvedPath ||
                normalizedPath,
              content,
            },
          )

        if (
          !payload.patch ||
          typeof payload.patch !==
            "object"
        ) {
          throw new Error(
            "patch review response did not contain a patch record",
          )
        }

        const id =
          patchId(
            payload.patch,
          )

        if (!id) {
          throw new Error(
            "patch review response did not contain an id",
          )
        }

        setPatch(
          payload.patch,
        )

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
      canCreate,
      content,
      normalizedPath,
      resolvedPath,
    ])

  const applyReview =
    useCallback(async () => {
      if (!canResolve) {
        return
      }

      setState("applying")
      setError("")

      try {
        const payload =
          await postJson(
            "/api/patch-review/apply",
            {
              patch_id:
                currentPatchId,
            },
          )

        if (
          !payload.patch ||
          typeof payload.patch !==
            "object"
        ) {
          throw new Error(
            "apply response did not contain a patch record",
          )
        }

        setPatch(
          payload.patch,
        )

        if (
          payload.patch.status ===
            "missing" ||
          payload.patch.applied ===
            false
        ) {
          throw new Error(
            "pending patch could not be applied",
          )
        }

        setState("applied")
      } catch (caught) {
        setState("error")

        setError(
          caught instanceof Error
            ? caught.message
            : String(caught),
        )
      }
    }, [
      canResolve,
      currentPatchId,
    ])

  const rejectReview =
    useCallback(async () => {
      if (!canResolve) {
        return
      }

      setState("rejecting")
      setError("")

      try {
        const payload =
          await postJson(
            "/api/patch-review/reject",
            {
              patch_id:
                currentPatchId,
            },
          )

        if (
          !payload.patch ||
          typeof payload.patch !==
            "object"
        ) {
          throw new Error(
            "reject response did not contain a patch record",
          )
        }

        setPatch(
          payload.patch,
        )

        if (
          payload.patch.status ===
            "missing" ||
          payload.patch.rejected ===
            false
        ) {
          throw new Error(
            "pending patch could not be rejected",
          )
        }

        setState("rejected")
      } catch (caught) {
        setState("error")

        setError(
          caught instanceof Error
            ? caught.message
            : String(caught),
        )
      }
    }, [
      canResolve,
      currentPatchId,
    ])

  const startNew =
    useCallback(() => {
      setPath("")
      setContent("")
      resetReview()
    }, [resetReview])

  const onSubmit = (
    event: FormEvent,
  ) => {
    event.preventDefault()
    void preview()
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
      void preview()
    }
  }

  const status =
    useMemo(() => {
      switch (state) {
        case "diffing":
          return "building diff"
        case "reviewed":
          return "diff reviewed"
        case "creating":
          return "creating review"
        case "pending":
          return "awaiting decision"
        case "applying":
          return "applying through coda"
        case "rejecting":
          return "rejecting"
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
                    palaver review
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

                    {status}
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
                    disabled={!canEdit}
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
                    disabled={!canEdit}
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
                      !canPreview
                    }
                  >
                    {state ===
                    "diffing" ? (
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
                    apply remains impossible until a review record exists
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

                    {resolvedPath && (
                      <span>
                        {resolvedPath}
                      </span>
                    )}
                  </header>

                  <pre>
                    {state ===
                      "diffing"
                      ? "Generating server-side diff…"
                      : diff ||
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
                      patch record
                    </summary>

                    <pre>
                      {pretty(
                        patch,
                      )}
                    </pre>
                  </details>
                )}

                <footer className="palaver-patch-actions">
                  {state ===
                    "reviewed" && (
                    <button
                      type="button"
                      className="palaver-patch-create"
                      disabled={
                        !canCreate
                      }
                      onClick={() =>
                        void createReview()
                      }
                    >
                      <ShieldCheck
                        size={16}
                      />
                      create patch review
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
                        onClick={() =>
                          void rejectReview()
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
                        onClick={() =>
                          void applyReview()
                        }
                      >
                        <Check
                          size={16}
                        />
                        apply through coda
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
                      onClick={
                        startNew
                      }
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
