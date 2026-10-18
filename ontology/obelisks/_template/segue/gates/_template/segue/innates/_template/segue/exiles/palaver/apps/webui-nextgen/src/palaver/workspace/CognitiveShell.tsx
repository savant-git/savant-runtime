import {useShallow} from "zustand/react/shallow"
import {
  useEffect,
  useState
} from "react"

import {
  AnimatePresence,
  motion
} from "framer-motion"

import {
  Command, Columns2, MessageSquareText,
  TerminalSquare, HelpCircle, RotateCcw, Search, BookOpen
} from "../components/savant-glyphs"


import {
  Group,
  Panel,
  Separator
} from "react-resizable-panels"

import {SavantArrivalAnchor} from "../brand/savant-arrival";
import "./palaver-instrument.css";
import "./palaver-navigation.css";
import "./palaver-industrial.css";

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

  const {active,
    density,
    focusMode,
    workspaceMode,
    workspacePreset,
    leftPanelVisible,
    rightPanelVisible,
    statusbarVisible,
    lastActivity,
    setWorkspaceMode,
    setCommandOpen,
    toggleFocus,
    cycleDensity,
    toggleChatTerminalSplit,
    toggleLeftPanel,
    toggleRightPanel,
    restoreWorkspace,
    applyWorkspacePreset,
    setActive
  } = useWorkspaceStore(useShallow(state=>({active:state.active,density:state.density,focusMode:state.focusMode,workspaceMode:state.workspaceMode,workspacePreset:state.workspacePreset,leftPanelVisible:state.leftPanelVisible,rightPanelVisible:state.rightPanelVisible,statusbarVisible:state.statusbarVisible,lastActivity:state.lastActivity,setWorkspaceMode:state.setWorkspaceMode,setCommandOpen:state.setCommandOpen,toggleFocus:state.toggleFocus,cycleDensity:state.cycleDensity,toggleChatTerminalSplit:state.toggleChatTerminalSplit,toggleLeftPanel:state.toggleLeftPanel,toggleRightPanel:state.toggleRightPanel,restoreWorkspace:state.restoreWorkspace,applyWorkspacePreset:state.applyWorkspacePreset,setActive:state.setActive})))


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


  useEffect(() => {
    const root = document.querySelector<HTMLElement>(".palaver-instrument");
    if (!root) return;
    let timer: number | undefined;
    let tooltip: HTMLDivElement | null = null;
    function dismiss() {
      window.clearTimeout(timer);
      tooltip?.remove();
      tooltip = null;
    }
    function explain(target: HTMLElement) {
      dismiss();
      const text = target.getAttribute("title")
        || target.getAttribute("aria-label")
        || target.textContent?.trim() || "control";
      tooltip = document.createElement("div");
      tooltip.className = "palaver-help-tooltip";
      tooltip.setAttribute("role", "status");
      tooltip.textContent = text;
      document.body.append(tooltip);
      const rect = target.getBoundingClientRect();
      tooltip.style.left = Math.max(8, Math.min(rect.left,
        window.innerWidth - tooltip.getBoundingClientRect().width - 8)) + "px";
      tooltip.style.top = Math.max(8, Math.min(rect.bottom + 8,
        window.innerHeight - tooltip.offsetHeight - 8)) + "px";
    }
    function pointer(event: PointerEvent) {
      dismiss();
      const target = event.target instanceof Element
        ? event.target.closest<HTMLElement>("button, select, textarea, input") : null;
      if (target) timer = window.setTimeout(() => explain(target), 550);
    }
    function release() { window.clearTimeout(timer); }
    function click(event: MouseEvent) {
      const target = event.target instanceof Element
        ? event.target.closest<HTMLElement>("button, select, textarea, input") : null;
      if (!target || target.dataset.palaverHelpToggle === "true") return;
      if (helpMode) {
        event.preventDefault();
        event.stopPropagation();
        explain(target);
      }
    }
    function key(event: KeyboardEvent) {
      if (event.key === "Escape") { dismiss(); setHelpMode(false); }
    }
    root.addEventListener("pointerdown", pointer);
    root.addEventListener("pointerup", release);
    root.addEventListener("pointercancel", dismiss);
    root.addEventListener("pointermove", dismiss);
    root.addEventListener("click", click, true);
    document.addEventListener("keydown", key);
    return () => {
      dismiss();
      root.removeEventListener("pointerdown", pointer);
      root.removeEventListener("pointerup", release);
      root.removeEventListener("pointercancel", dismiss);
      root.removeEventListener("pointermove", dismiss);
      root.removeEventListener("click", click, true);
      document.removeEventListener("keydown", key);
    };
  }, [helpMode]);

  return (
    <main
      className={
        [
          "shell",
          "palaver-workstation",
          "palaver-only",
          "palaver-instrument",
          "left-panel-hidden",
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
          <SavantArrivalAnchor />

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

        <div className="palaver-header-controls">
        <nav className="palaver-aperture-nav" aria-label="Knowledge navigation">
          {([
            { id: "source", label: "Sources", Icon: BookOpen },
            { id: "search", label: "Search", Icon: Search }
          ] as const).map(({ id, label, Icon }) => (
            <button
              key={id}
              type="button"
              className={active === id && workspaceMode === "single" ? "aperture-active" : ""}
              aria-current={active === id && workspaceMode === "single" ? "page" : undefined}
              aria-label={label}
              title={label}
              onClick={() => {
                setWorkspaceMode("single")
                setActive(id)
              }}
            >
              <span className="aperture-ring" aria-hidden="true" />
              <Icon size={16} />
              <span className="aperture-label">{label}</span>
            </button>
          ))}
        </nav>

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
            onClick={() => { setWorkspaceMode("single"); setActive("chat"); }}
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
            onClick={() => { setWorkspaceMode("single"); setActive("terminal"); }}
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
            data-palaver-help-toggle="true"
            aria-label="Interface help"
          >
            <HelpCircle
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
                  {ObservatoryRouter(active)}
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
