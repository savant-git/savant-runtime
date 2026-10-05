import {
  AnimatePresence,
  motion,
  useReducedMotion,
} from "framer-motion"
import {
  ArrowDown,
  ArrowUp,
  CircleDot,
  GitBranch,
  MessageCircle,
  Search,
  X,
} from "lucide-react"
import {
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react"
import type {
  PalaverMessageRecord,
} from "./PalaverMessage"

type Props = {
  open: boolean
  messages: PalaverMessageRecord[]
  activeMessageId: string | null
  branchCount: number
  onClose: () => void
  onSelect: (messageId: string) => void
  onPrevious: () => void
  onNext: () => void
  onOpenBranches: () => void
}

function label(
  message: PalaverMessageRecord,
) {
  const compact =
    message.body
      .replace(/\s+/g, " ")
      .trim()

  if (compact.length <= 78) {
    return compact
  }

  return `${compact.slice(0, 75)}…`
}

export default function PalaverFocusRail({
  open,
  messages,
  activeMessageId,
  branchCount,
  onClose,
  onSelect,
  onPrevious,
  onNext,
  onOpenBranches,
}: Props) {
  const reducedMotion =
    useReducedMotion()

  const [query, setQuery] =
    useState("")

  const inputRef =
    useRef<HTMLInputElement>(
      null,
    )

  useEffect(() => {
    if (!open) {
      setQuery("")
      return
    }

    requestAnimationFrame(
      () =>
        inputRef.current?.focus(),
    )
  }, [open])

  const visible =
    useMemo(() => {
      const normalized =
        query
          .trim()
          .toLowerCase()

      if (!normalized) {
        return messages
      }

      return messages.filter(
        (message) =>
          message.body
            .toLowerCase()
            .includes(
              normalized,
            ),
      )
    }, [
      messages,
      query,
    ])

  return (
    <AnimatePresence>
      {open && (
        <>
          <motion.button
            className="palaver-focus-backdrop"
            aria-label="Close message navigator"
            initial={{
              opacity: 0,
            }}
            animate={{
              opacity: 1,
            }}
            exit={{
              opacity: 0,
            }}
            onClick={
              onClose
            }
          />

          <motion.aside
            className="palaver-focus-rail"
            initial={
              reducedMotion
                ? false
                : {
                    opacity: 0,
                    x: 34,
                    scale:
                      0.985,
                  }
            }
            animate={{
              opacity: 1,
              x: 0,
              scale: 1,
            }}
            exit={{
              opacity: 0,
              x: 24,
              scale:
                0.99,
            }}
            transition={{
              type: "spring",
              stiffness:
                330,
              damping: 34,
            }}
          >
            <header className="palaver-focus-head">
              <div>
                <CircleDot
                  size={15}
                />

                <span>
                  message navigator
                </span>
              </div>

              <button
                type="button"
                aria-label="Close message navigator"
                onClick={
                  onClose
                }
              >
                <X
                  size={17}
                />
              </button>
            </header>

            <div className="palaver-focus-search">
              <Search
                size={15}
              />

              <input
                ref={
                  inputRef
                }
                value={query}
                placeholder="find in conversation"
                onChange={(
                  event,
                ) =>
                  setQuery(
                    event.target
                      .value,
                  )
                }
              />

              <span>
                {
                  visible.length
                }
              </span>
            </div>

            <div className="palaver-focus-list">
              {visible.map(
                (
                  message,
                  index,
                ) => {
                  const active =
                    message.id ===
                    activeMessageId

                  return (
                    <button
                      type="button"
                      key={
                        message.id
                      }
                      className={
                        active
                          ? "active"
                          : ""
                      }
                      onClick={() =>
                        onSelect(
                          message.id,
                        )
                      }
                    >
                      <span className="palaver-focus-index">
                        {String(
                          index +
                            1,
                        ).padStart(
                          2,
                          "0",
                        )}
                      </span>

                      <span>
                        <strong>
                          {message.role ===
                          "assistant"
                            ? "palaver"
                            : "you"}
                        </strong>

                        <small>
                          {label(
                            message,
                          )}
                        </small>
                      </span>

                      <MessageCircle
                        size={14}
                      />
                    </button>
                  )
                },
              )}

              {!visible.length && (
                <div className="palaver-focus-empty">
                  No messages match.
                </div>
              )}
            </div>

            <footer className="palaver-focus-foot">
              <div>
                <button
                  type="button"
                  onClick={
                    onPrevious
                  }
                  aria-label="Previous message"
                >
                  <ArrowUp
                    size={15}
                  />
                </button>

                <button
                  type="button"
                  onClick={
                    onNext
                  }
                  aria-label="Next message"
                >
                  <ArrowDown
                    size={15}
                  />
                </button>
              </div>

              <button
                type="button"
                className="palaver-focus-branch"
                onClick={
                  onOpenBranches
                }
              >
                <GitBranch
                  size={15}
                />

                <span>
                  paths
                </span>

                <strong>
                  {branchCount}
                </strong>
              </button>
            </footer>
          </motion.aside>
        </>
      )}
    </AnimatePresence>
  )
}
