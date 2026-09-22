import {
  AnimatePresence,
  motion,
  useReducedMotion,
} from "framer-motion"
import {
  ArrowLeft,
  GitBranch,
  MessageCircle,
  X,
} from "lucide-react"
import { useMemo } from "react"
import type {
  PalaverMessageRecord,
} from "./PalaverMessage"

export type ConversationBranch = {
  id: string
  sourceMessageId: string
  label: string
  createdAt: number
  messages: PalaverMessageRecord[]
}

type Props = {
  open: boolean
  branches: ConversationBranch[]
  activeBranchId: string | null
  onClose: () => void
  onSelect: (
    branchId: string | null,
  ) => void
}

export default function PalaverBranches({
  open,
  branches,
  activeBranchId,
  onClose,
  onSelect,
}: Props) {
  const reducedMotion =
    useReducedMotion()

  const ordered = useMemo(
    () =>
      [...branches].sort(
        (left, right) =>
          right.createdAt -
          left.createdAt,
      ),
    [branches],
  )

  return (
    <AnimatePresence>
      {open && (
        <>
          <motion.button
            className="palaver-branch-backdrop"
            aria-label="Close conversation paths"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
          />

          <motion.aside
            className="palaver-branches"
            initial={
              reducedMotion
                ? false
                : {
                    opacity: 0,
                    x: -45,
                  }
            }
            animate={{
              opacity: 1,
              x: 0,
            }}
            exit={{
              opacity: 0,
              x: -30,
            }}
            transition={{
              type: "spring",
              stiffness: 320,
              damping: 34,
            }}
          >
            <header>
              <div>
                <GitBranch size={16} />
                <span>
                  conversation paths
                </span>
              </div>

              <button
                type="button"
                aria-label="Close conversation paths"
                onClick={onClose}
              >
                <X size={17} />
              </button>
            </header>

            <div className="palaver-branch-list">
              <button
                type="button"
                className={
                  activeBranchId === null
                    ? "active"
                    : ""
                }
                onClick={() =>
                  onSelect(null)
                }
              >
                <span className="palaver-branch-icon">
                  <MessageCircle
                    size={16}
                  />
                </span>

                <span>
                  <strong>
                    main conversation
                  </strong>
                  <small>
                    original path
                  </small>
                </span>

                <ArrowLeft size={14} />
              </button>

              {ordered.map(
                (
                  branch,
                  index,
                ) => (
                  <button
                    type="button"
                    key={branch.id}
                    className={
                      activeBranchId ===
                      branch.id
                        ? "active"
                        : ""
                    }
                    onClick={() =>
                      onSelect(
                        branch.id,
                      )
                    }
                  >
                    <span className="palaver-branch-index">
                      {String(
                        index + 1,
                      ).padStart(
                        2,
                        "0",
                      )}
                    </span>

                    <span>
                      <strong>
                        {branch.label}
                      </strong>

                      <small>
                        {
                          branch
                            .messages
                            .length
                        }{" "}
                        messages
                      </small>
                    </span>

                    <GitBranch
                      size={14}
                    />
                  </button>
                ),
              )}

              {!ordered.length && (
                <div className="palaver-branch-empty">
                  Branch from any
                  message to explore
                  another direction
                  without losing the
                  current conversation.
                </div>
              )}
            </div>
          </motion.aside>
        </>
      )}
    </AnimatePresence>
  )
}
