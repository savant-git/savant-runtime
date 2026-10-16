import {
  useEffect,
  useState
} from "react"

import {
  AnimatePresence,
  motion
} from "framer-motion"

import {
  Command,
  Focus,
  Gauge,
  Columns2,
  Rows3,
  MessageSquareText,
  TerminalSquare,
  HelpCircle,
  PanelLeftClose,
  PanelLeftOpen,
  PanelRightClose,
  PanelRightOpen,
  RotateCcw,
  Sparkles
} from "lucide-react"

import {
  Group,
  Panel,
  Separator
} from "react-resizable-panels"

import AmbientEnvironment
  from "../environment/AmbientEnvironment"

import CommandCenter
  from "../components/CommandCenter"

import ContextPanel
  from "../components/ContextPanel"

import ObservatoryRail
  from "../components/ObservatoryRail"

import ChatObservatory
  from "../observatories/ChatObservatory"

import TerminalObservatory
  from "../observatories/TerminalObservatory"

import {
  ObservatoryRouter
} from "../observatories"

import {
  useWorkspaceStore
} from "../state/workspace-store"


export default function CognitiveShell() {
  const [
    splitOrientation,
    setSplitOrientation,
  ] = useState<
    "horizontal" | "vertical"
  >(
    () =>
      (
        localStorage.getItem(
          "palaver.split-orientation",
        )
        === "vertical"
      )
        ? "vertical"
        : "horizontal",
  )

  const [
    helpMode,
    setHelpMode,
  ] = useState(
    false,
  )

  const {
    active,
    density,
    focusMode,
    workspaceMode,
    workspacePreset,
    leftPanelVisible,
    rightPanelVisible,
    statusbarVisible,
    lastActivity,
    setCommandOpen,
    toggleFocus,
    cycleDensity,
    toggleChatTerminalSplit,
    toggleLeftPanel,
    toggleRightPanel,
    restoreWorkspace,
    applyWorkspacePreset,
    setActive
  } = useWorkspaceStore()


  useEffect(
    () => {
      localStorage.setItem(
        "palaver.split-orientation",
        splitOrientation,
      )
    },
    [
      splitOrientation,
    ],
  )


  useEffect(
    () => {
      const handler = (
        event: KeyboardEvent
      ) => {
        const command =
          event.metaKey
          || event.ctrlKey

        if (
          command
          && event.key
            .toLowerCase()
            === "k"
        ) {
          event.preventDefault()
          setCommandOpen(true)
          return
        }

        if (
          command
          && event.key === "`"
        ) {
          event.preventDefault()
          setActive("terminal")
          return
        }

        if (
          command
          && event.key === "/"
        ) {
          event.preventDefault()
          setActive("chat")
          return
        }

        if (
          command
          && event.shiftKey
          && event.key
            .toLowerCase()
            === "t"
        ) {
          event.preventDefault()
          toggleChatTerminalSplit()
          return
        }

        if (
          command
          && event.shiftKey
          && event.key
            .toLowerCase()
            === "l"
        ) {
          event.preventDefault()
          toggleLeftPanel()
          return
        }

        if (
          command
          && event.shiftKey
          && event.key
            .toLowerCase()
            === "r"
        ) {
          event.preventDefault()
          toggleRightPanel()
          return
        }

        if (
          command
          && event.shiftKey
          && event.key === "1"
        ) {
          event.preventDefault()
          applyWorkspacePreset(
            "conversation"
          )
          return
        }

        if (
          command
          && event.shiftKey
          && event.key === "2"
        ) {
          event.preventDefault()
          applyWorkspacePreset(
            "context"
          )
          return
        }

        if (
          command
          && event.shiftKey
          && event.key === "3"
        ) {
          event.preventDefault()
          applyWorkspacePreset(
            "inspection"
          )
          return
        }

        if (
          event.key === "Escape"
          && focusMode
        ) {
          toggleFocus()
        }
      }

      window.addEventListener(
        "keydown",
        handler
      )

      return () =>
        window.removeEventListener(
          "keydown",
          handler
        )
    },
    [
      applyWorkspacePreset,
      focusMode,
      setActive,
      setCommandOpen,
      toggleChatTerminalSplit,
      toggleFocus,
      toggleLeftPanel,
      toggleRightPanel
    ]
  )


  return (
    <main
      className={
        [
          "shell",
          "palaver-workstation",
          "palaver-only",
          helpMode
            ? "help-mode"
            : "",
          "savant-spectrum",
          `density-${density}`,
          `preset-${workspacePreset}`,
          focusMode
            ? "focus-mode"
            : "",
          !leftPanelVisible
            ? "left-panel-hidden"
            : "",
          !rightPanelVisible
            ? "right-panel-hidden"
            : "",
          !statusbarVisible
            ? "statusbar-hidden"
            : ""
        ]
          .filter(Boolean)
          .join(" ")
      }
      onClickCapture={
        event => {
          if (!helpMode) {
            return
          }

          const eventTarget =
            event.target

          if (
            !(
              eventTarget
              instanceof HTMLElement
            )
          ) {
            return
          }

          const target =
            eventTarget.closest(
              "button, select, textarea, input, [role='button']",
            )

          if (!target) {
            return
          }

          event.preventDefault()
          event.stopPropagation()

          window.alert(
            target.getAttribute(
              "title",
            )
            || target.getAttribute(
              "aria-label",
            )
            || "This control does not yet have additional instructions.",
          )
        }
      }
    >
      <AmbientEnvironment />

      <CommandCenter />

      <div
        className="cinematic-grid"
      />

      <div
        className="cinematic-vignette"
      />

      <header
        className="workstation-topbar"
      >
        <div
          className="topbar-brand"
        >
          <motion.div
            className="topbar-sigil"
            whileHover={{
              rotateY: 12,
              rotateX: -8,
              scale: 1.04
            }}
            transition={{
              type: "spring",
              stiffness: 260,
              damping: 20
            }}
          >
            <Sparkles
              size={15}
            />
          </motion.div>

          <div>
            <strong>
              palaver
            </strong>

            <span>
              savant cognitive instrument
            </span>
          </div>
        </div>

        <div
          className="topbar-command-strip"
        >
          <button
            type="button"
            className="command-surface"
            onClick={
              () =>
                setCommandOpen(true)
            }
          >
            <Command
              size={13}
            />

            <span>
              command
            </span>

            <kbd>
              ctrl k
            </kbd>
          </button>

          <div
            className="topbar-location"
          >
            <span>
              surface
            </span>

            <b>
              {workspaceMode
              === "chat-terminal-split"
                ? "chat / terminal"
                : active}
            </b>
          </div>

          <div
            className="workspace-preset-chip"
          >
            <span>
              workspace
            </span>

            <strong>
              {workspacePreset}
            </strong>
          </div>
        </div>

        <div
          className="topbar-actions"
        >
          <button
            type="button"
            className={
              workspaceMode
              === "single"
              && active
              === "chat"
                ? "active"
                : ""
            }
            onClick={
              () =>
                setActive("chat")
            }
            title="Chat only"
            aria-label="Chat only"
          >
            <MessageSquareText
              size={14}
            />
          </button>

          <button
            type="button"
            className={
              workspaceMode
              === "single"
              && active
              === "terminal"
                ? "active"
                : ""
            }
            onClick={
              () =>
                setActive("terminal")
            }
            title="Terminal only"
            aria-label="Terminal only"
          >
            <TerminalSquare
              size={14}
            />
          </button>

          <button
            type="button"
            className={
              workspaceMode
              === "chat-terminal-split"
                ? "active"
                : ""
            }
            onClick={
              () => {
                if (
                  workspaceMode
                  !== "chat-terminal-split"
                ) {
                  toggleChatTerminalSplit()
                }
              }
            }
            title="Show chat and terminal"
            aria-label="Show chat and terminal"
          >
            <Columns2
              size={14}
            />
          </button>

          <button
            type="button"
            disabled={
              workspaceMode
              !== "chat-terminal-split"
            }
            onClick={
              () =>
                setSplitOrientation(
                  current =>
                    current
                    === "horizontal"
                      ? "vertical"
                      : "horizontal",
                )
            }
            title={
              splitOrientation
              === "horizontal"
                ? "Split top and bottom"
                : "Split side by side"
            }
            aria-label={
              "Change split orientation"
            }
          >
            {splitOrientation
            === "horizontal"
              ? (
                <Rows3
                  size={14}
                />
              )
              : (
                <Columns2
                  size={14}
                />
              )}
          </button>

          <button
            type="button"
            className={
              helpMode
                ? "active"
                : ""
            }
            onClick={
              () =>
                setHelpMode(
                  current =>
                    !current,
                )
            }
            title={
              helpMode
                ? "Exit interface help"
                : "Explain interface controls"
            }
            aria-label="Interface help"
          >
            <HelpCircle
              size={14}
            />
          </button>

          <button
            type="button"
            onClick={
              cycleDensity
            }
            title={
              "Cycle density · "
              + density
            }
          >
            <Gauge
              size={14}
            />

            <span
              className="topbar-action-label"
            >
              {density}
            </span>
          </button>

          <button
            type="button"
            className={
              focusMode
                ? "active"
                : ""
            }
            onClick={
              toggleFocus
            }
            title="Focus mode"
          >
            <Focus
              size={14}
            />
          </button>

          <button
            type="button"
            onClick={
              restoreWorkspace
            }
            title="Restore workspace"
          >
            <RotateCcw
              size={13}
            />
          </button>
        </div>
      </header>

      <section
        className="palaver-layout"
      >
        <section
          className="palaver-center"
        >
          {workspaceMode
          === "chat-terminal-split"
            ? (
              <Group
                orientation={
                  splitOrientation
                }
                className={
                  "chat-terminal-split "
                  + `split-${splitOrientation}`
                }
              >
                <Panel
                  defaultSize={52}
                  minSize={25}
                >
                  <div
                    className="split-pane"
                  >
                    <ChatObservatory />
                  </div>
                </Panel>

                <Separator
                  className={
                    "split-separator "
                    + "savant-resize-handle"
                  }
                />

                <Panel
                  defaultSize={48}
                  minSize={25}
                >
                  <div
                    className="split-pane"
                  >
                    <TerminalObservatory />
                  </div>
                </Panel>
              </Group>
            )
            : (
              <AnimatePresence
                mode="wait"
                initial={false}
              >
                <motion.div
                  key={active}
                  className="workspace-surface"
                  initial={{
                    opacity: 0,
                    y: 10,
                    scale: .997,
                    filter:
                      "blur(3px)"
                  }}
                  animate={{
                    opacity: 1,
                    y: 0,
                    scale: 1,
                    filter:
                      "blur(0px)"
                  }}
                  exit={{
                    opacity: 0,
                    y: -6,
                    scale: .998,
                    filter:
                      "blur(2px)"
                  }}
                  transition={{
                    duration: .2,
                    ease: [
                      .22,
                      1,
                      .36,
                      1
                    ]
                  }}
                >
                  {ObservatoryRouter(
                    active
                  )}
                </motion.div>
              </AnimatePresence>
            )}
        </section>
      </section>

      {statusbarVisible && (
        <footer
          className="workstation-statusbar"
        >
          <div
            className="status-identity"
          >
            <span
              className="status-pulse"
            />

            <b>
              palaver
            </b>

            <span>
              local
            </span>

            <i />

            <span>
              {workspacePreset}
            </span>
          </div>

          <div
            className="status-activity"
          >
            {lastActivity}
          </div>

          <div
            className="status-shortcuts"
          >
            <span>
              ctrl/⌘ /
            </span>

            <b>
              chat
            </b>

            <span>
              ctrl/⌘ `
            </span>

            <b>
              terminal
            </b>

            <span>
              ctrl/⌘ k
            </span>

            <b>
              command
            </b>
          </div>
        </footer>
      )}
    </main>
  )
}
