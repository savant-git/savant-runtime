import {
  useEffect
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
  const {
    active,
    density,
    focusMode,
    workspaceMode,
    lastActivity,
    setCommandOpen,
    toggleFocus,
    cycleDensity,
    toggleChatTerminalSplit,
    setActive
  } = useWorkspaceStore()

  useEffect(() => {
    const handler = (
      event: KeyboardEvent
    ) => {
      if (
        (
          event.metaKey
          || event.ctrlKey
        )
        && event.key.toLowerCase()
        === "k"
      ) {
        event.preventDefault()
        setCommandOpen(true)
      }

      if (
        (
          event.metaKey
          || event.ctrlKey
        )
        && event.key === "`"
      ) {
        event.preventDefault()
        setActive("terminal")
      }

      if (
        (
          event.metaKey
          || event.ctrlKey
        )
        && event.key === "/"
      ) {
        event.preventDefault()
        setActive("chat")
      }

      if (
        (
          event.metaKey
          || event.ctrlKey
        )
        && event.shiftKey
        && event.key.toLowerCase()
        === "t"
      ) {
        event.preventDefault()
        toggleChatTerminalSplit()
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
  }, [
    focusMode,
    setActive,
    setCommandOpen,
    toggleChatTerminalSplit,
    toggleFocus
  ])

  return (
    <main
      className={
        [
          "shell",
          "palaver-workstation",
          `density-${density}`,
          focusMode
            ? "focus-mode"
            : ""
        ]
          .filter(Boolean)
          .join(" ")
      }
    >
      <AmbientEnvironment />
      <CommandCenter />

      <div className="cinematic-grid" />
      <div className="cinematic-vignette" />

      <header className="workstation-topbar">
        <div className="topbar-brand">
          <div className="topbar-sigil">
            <Sparkles size={15} />
          </div>

          <div>
            <strong>
              palaver
            </strong>

            <span>
              cognitive workstation
            </span>
          </div>
        </div>

        <div className="topbar-location">
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

        <div className="topbar-actions">
          <button
            type="button"
            onClick={() =>
              setCommandOpen(true)
            }
            title="Command palette · Ctrl/⌘ K"
          >
            <Command size={14} />
            <span>
              command
            </span>
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
              toggleChatTerminalSplit
            }
            title="Vertical chat / terminal split · Ctrl/⌘ Shift T"
          >
            <Columns2 size={14} />
          </button>

          <button
            type="button"
            onClick={cycleDensity}
            title="Cycle density"
          >
            <Gauge size={14} />
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
            <Focus size={14} />
          </button>
        </div>
      </header>

      <section className="palaver-layout">
        <aside className="palaver-left">
          <ObservatoryRail />
        </aside>

        <section className="palaver-center">
          {workspaceMode
          === "chat-terminal-split"
            ? (
              <Group
                orientation="horizontal"
                className="chat-terminal-split"
              >
                <Panel
                  defaultSize={52}
                  minSize={25}
                >
                  <div className="split-pane">
                    <ChatObservatory />
                  </div>
                </Panel>

                <Separator
                  className="split-separator"
                />

                <Panel
                  defaultSize={48}
                  minSize={25}
                >
                  <div className="split-pane">
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
                    y: 12,
                    scale: .995,
                    filter: "blur(4px)"
                  }}
                  animate={{
                    opacity: 1,
                    y: 0,
                    scale: 1,
                    filter: "blur(0px)"
                  }}
                  exit={{
                    opacity: 0,
                    y: -8,
                    scale: .997,
                    filter: "blur(3px)"
                  }}
                  transition={{
                    duration: .24,
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

        <aside className="palaver-right">
          <ContextPanel />
        </aside>
      </section>

      <footer className="workstation-statusbar">
        <div>
          <span className="status-pulse" />
          <b>
            palaver
          </b>
          <span>
            localhost
          </span>
        </div>

        <div className="status-activity">
          {lastActivity}
        </div>

        <div>
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
        </div>
      </footer>
    </main>
  )
}
