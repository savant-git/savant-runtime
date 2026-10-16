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
  ShieldCheck,
  X,
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

type LocalReviewState =
  | "idle"
  | "reviewed"

function normalizePath(
  value: string,
): string {
  return value.trim()
}

function reviewText(
  path: string,
  content: string,
): string {
  return [
    "palaver local patch proposal",
    "",
    `path: ${path}`,
    "",
    "proposed complete content:",
    "",
    content,
  ].join("\n")
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

  const [state, setState] =
    useState<LocalReviewState>(
      "idle",
    )

  const [copied, setCopied] =
    useState(false)

  const normalizedPath =
    useMemo(
      () => normalizePath(path),
      [path],
    )

  const proposal =
    useMemo(
      () =>
        normalizedPath
          ? reviewText(
              normalizedPath,
              content,
            )
          : "",
      [
        content,
        normalizedPath,
      ],
    )

  const resetReview =
    useCallback(() => {
      setState("idle")
      setCopied(false)
    }, [])

  const review =
    useCallback(() => {
      if (!normalizedPath) {
        return
      }

      setState("reviewed")
      setCopied(false)
    }, [normalizedPath])

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
    review()
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
      review()
    }
  }

  return (
    <>
      <button
        type="button"
        className="palaver-patch-launcher"
        aria-label="Open patch proposal"
        title="Patch proposal"
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
              aria-label="Close patch proposal"
              initial={{
                opacity: 0,
              }}
              animate={{
                opacity: 1,
              }}
              exit={{
                opacity: 0,
              }}
              onClick={() =>
                setOpen(false)
              }
            />

            <motion.section
              className="palaver-patch-review"
              role="dialog"
              aria-modal="true"
              aria-label="Patch proposal"
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
                    local only
                  </span>

                  <h2>
                    patch proposal
                  </h2>
                </div>

                <div className="palaver-patch-head-actions">
                  <span className="palaver-patch-status">
                    no runtime mutation
                  </span>

                  <button
                    type="button"
                    aria-label="Close patch proposal"
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
                      !normalizedPath
                    }
                  >
                    <FileDiff size={15} />
                    review proposal
                  </button>

                  <span>
                    this surface does not call write or patch endpoints
                  </span>
                </div>

                <div className="palaver-patch-diff">
                  <header>
                    <div>
                      <Code2 size={14} />
                      <strong>
                        proposal
                      </strong>
                    </div>

                    <span>
                      disposable browser state
                    </span>
                  </header>

                  <pre>
                    {state ===
                    "reviewed"
                      ? proposal
                      : "No proposal reviewed yet."}
                  </pre>
                </div>

                <footer className="palaver-patch-actions">
                  {state ===
                    "reviewed" && (
                    <button
                      type="button"
                      className="palaver-patch-create"
                      onClick={
                        copyProposal
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
                        : "copy proposal"}
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
