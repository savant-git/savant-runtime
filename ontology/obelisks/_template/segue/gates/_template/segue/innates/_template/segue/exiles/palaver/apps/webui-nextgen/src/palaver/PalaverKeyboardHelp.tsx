import {
  AnimatePresence,
  motion,
  useReducedMotion,
} from "framer-motion"
import {
  Command,
  CornerDownLeft,
  GitBranch,
  HelpCircle,
  Keyboard,
  MessageCircle,
  Search,
  X,
} from "lucide-react"
import {
  useCallback,
  useEffect,
  useState,
} from "react"

type Shortcut = {
  keys: string[]
  label: string
  icon: typeof Command
}

const shortcuts: Shortcut[] = [
  {
    keys: ["⌘ / ctrl", "k"],
    label: "open command palette",
    icon: Command,
  },
  {
    keys: ["⌘ / ctrl", "l"],
    label: "focus conversation composer",
    icon: MessageCircle,
  },
  {
    keys: ["⌘ / ctrl", "f"],
    label: "find a message",
    icon: Search,
  },
  {
    keys: ["⌘ / ctrl", "b"],
    label: "open conversation paths",
    icon: GitBranch,
  },
  {
    keys: ["⌘ / ctrl", "↑ / ↓"],
    label: "move between messages",
    icon: Keyboard,
  },
  {
    keys: ["enter"],
    label: "send message",
    icon: CornerDownLeft,
  },
  {
    keys: ["shift", "enter"],
    label: "insert a new line",
    icon: CornerDownLeft,
  },
  {
    keys: ["esc"],
    label: "close the active temporary surface",
    icon: X,
  },
]

export default function PalaverKeyboardHelp() {
  const reducedMotion = useReducedMotion()
  const [open, setOpen] = useState(false)

  const close = useCallback(() => {
    setOpen(false)
  }, [])

  useEffect(() => {
    const onKeyDown = (
      event: globalThis.KeyboardEvent,
    ) => {
      const target =
        event.target as HTMLElement | null

      const typing =
        target?.tagName === "INPUT" ||
        target?.tagName === "TEXTAREA" ||
        target?.isContentEditable

      if (
        event.key === "?" &&
        !typing &&
        !event.metaKey &&
        !event.ctrlKey &&
        !event.altKey
      ) {
        event.preventDefault()
        setOpen((current) => !current)
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

  return (
    <>
      <button
        type="button"
        className="palaver-help-launcher"
        aria-label="Open keyboard help"
        title="Keyboard help · ?"
        onClick={() => setOpen(true)}
      >
        <HelpCircle size={17} />
      </button>

      <AnimatePresence>
        {open && (
          <>
            <motion.button
              type="button"
              className="palaver-help-backdrop"
              aria-label="Close keyboard help"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={close}
            />

            <motion.section
              className="palaver-help"
              role="dialog"
              aria-modal="true"
              aria-labelledby="palaver-help-title"
              initial={
                reducedMotion
                  ? false
                  : {
                      opacity: 0,
                      y: 18,
                      scale: 0.98,
                    }
              }
              animate={{
                opacity: 1,
                y: 0,
                scale: 1,
              }}
              exit={{
                opacity: 0,
                y: 12,
                scale: 0.99,
              }}
            >
              <header className="palaver-help-head">
                <div>
                  <span>
                    <Keyboard size={14} />
                    navigation
                  </span>

                  <h2 id="palaver-help-title">
                    keyboard
                  </h2>
                </div>

                <button
                  type="button"
                  aria-label="Close keyboard help"
                  onClick={close}
                >
                  <X size={18} />
                </button>
              </header>

              <div className="palaver-help-grid">
                {shortcuts.map(
                  ({
                    keys,
                    label,
                    icon: Icon,
                  }) => (
                    <div
                      key={`${keys.join("-")}:${label}`}
                      className="palaver-help-row"
                    >
                      <Icon
                        size={15}
                        aria-hidden="true"
                      />

                      <span>
                        {label}
                      </span>

                      <div className="palaver-help-keys">
                        {keys.map((key) => (
                          <kbd key={key}>
                            {key}
                          </kbd>
                        ))}
                      </div>
                    </div>
                  ),
                )}
              </div>

              <footer className="palaver-help-foot">
                <span>
                  press
                  <kbd>?</kbd>
                  anywhere outside an editor
                </span>
              </footer>
            </motion.section>
          </>
        )}
      </AnimatePresence>
    </>
  )
}
