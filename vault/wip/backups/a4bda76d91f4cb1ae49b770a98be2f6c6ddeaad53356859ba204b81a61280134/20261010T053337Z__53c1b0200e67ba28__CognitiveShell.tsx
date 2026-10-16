import { useEffect, useState } from "react";
import { Columns2, Rows2, MessageSquare, TerminalSquare, PanelTop, HelpCircle, Command, RotateCcw } from "lucide-react";
import { Group, Panel, Separator } from "react-resizable-panels";
import AmbientEnvironment from "../environment/AmbientEnvironment";
import CommandCenter from "../components/CommandCenter";
import ChatObservatory from "../observatories/ChatObservatory";
import TerminalObservatory from "../observatories/TerminalObservatory";
import SavantMark from "../brand/savant-mark";
import { useWorkspaceStore } from "../state/workspace-store";
import "./cognitive-shell2222.css";

type Surface = "chat" | "terminal" | "split";
type Axis = "horizontal" | "vertical";

export default function CognitiveShell() {
  const {
    density, focusMode, workspacePreset, statusbarVisible, lastActivity,
    setCommandOpen, toggleFocus, restoreWorkspace, setActive,
  } = useWorkspaceStore();
  const [surface, setSurface] = useState<Surface>("chat");
  const [axis, setAxis] = useState<Axis>("horizontal");
  const [help, setHelp] = useState(false);

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      const command = event.ctrlKey || event.metaKey;
      if (command && event.key.toLowerCase() === "k") {
        event.preventDefault();
        setCommandOpen(true);
      } else if (command && event.key === "`") {
        event.preventDefault();
        setSurface("terminal");
        setActive("terminal");
      } else if (command && event.key === "/") {
        event.preventDefault();
        setSurface("chat");
        setActive("chat");
      } else if (command && event.shiftKey && event.key.toLowerCase() === "t") {
        event.preventDefault();
        setSurface(current => current === "split" ? "chat" : "split");
      } else if (event.key === "Escape" && focusMode) {
        toggleFocus();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [setCommandOpen, setActive, focusMode, toggleFocus]);

  const changeSurface = (next: Surface) => {
    setSurface(next);
    if (next !== "split") setActive(next);
  };

  return (
    <main className={`shell palaver-workstation palaver-recast density-${density} preset-${workspacePreset}${focusMode ? " focus-mode" : ""}`}>
      <AmbientEnvironment />
      <CommandCenter />
      <div className="cinematic-grid" aria-hidden="true" />
      <div className="cinematic-vignette" aria-hidden="true" />
      <header className="workstation-topbar palaver-recast__header">
        <div className="topbar-brand palaver-recast__brand">
          <SavantMark mode="header" state="idle" label="savant" />
          <div className="palaver-recast__wordmark"><strong>palaver</strong><span>savant / cognitive instrument</span></div>
        </div>
        <div className="palaver-recast__controls" role="toolbar" aria-label="workspace controls">
          <button type="button" className={surface === "chat" ? "active" : ""} onClick={() => changeSurface("chat")} title="Chat only" aria-label="Chat only"><MessageSquare size={17} /></button>
          <button type="button" className={surface === "terminal" ? "active" : ""} onClick={() => changeSurface("terminal")} title="Terminal only" aria-label="Terminal only"><TerminalSquare size={17} /></button>
          <button type="button" className={surface === "split" ? "active" : ""} onClick={() => changeSurface("split")} title="Chat and terminal" aria-label="Chat and terminal"><PanelTop size={17} /></button>
          <button type="button" onClick={() => setAxis(current => current === "horizontal" ? "vertical" : "horizontal")} title={axis === "horizontal" ? "Switch to stacked panes" : "Switch to side-by-side panes"} aria-label="Change split direction">{axis === "horizontal" ? <Columns2 size={17} /> : <Rows2 size={17} />}</button>
          <button type="button" className={help ? "active" : ""} onClick={() => setHelp(value => !value)} title="Explain controls" aria-label="Toggle help mode" aria-pressed={help}><HelpCircle size={17} /></button>
          <button type="button" onClick={() => setCommandOpen(true)} title="Command center (Ctrl K)" aria-label="Command center"><Command size={17} /></button>
          <button type="button" onClick={restoreWorkspace} title="Restore saved workspace" aria-label="Restore workspace"><RotateCcw size={17} /></button>
        </div>
      </header>
      {help && <div className="palaver-recast__help" role="status">Chat: conversation only. Terminal: console only. Split: both panes. Direction: stack or place side by side. Command: open command center. Restore: restore workspace settings. Long-press controls to read their labels.</div>}
      <section className="palaver-layout palaver-recast__layout" aria-label="palaver workspace">
        <section className="palaver-center palaver-recast__center">
          {surface === "split" ? (
            <Group orientation={axis} className={`chat-terminal-split palaver-recast__split palaver-recast__split--${axis}`}>
              <Panel defaultSize={55} minSize={20}><div className="split-pane palaver-recast__pane"><ChatObservatory /></div></Panel>
              <Separator className="split-separator savant-resize-handle palaver-recast__separator" />
              <Panel defaultSize={45} minSize={20}><div className="split-pane palaver-recast__pane"><TerminalObservatory /></div></Panel>
            </Group>
          ) : (
            <div className="workspace-surface palaver-recast__surface" key={surface}>
              {surface === "chat" ? <ChatObservatory /> : <TerminalObservatory />}
            </div>
          )}
        </section>
      </section>
      {statusbarVisible && <footer className="workstation-statusbar palaver-recast__status"><span>● palaver / local</span><span>{lastActivity}</span><span>{surface} {surface === "split" ? `/ ${axis}` : ""}</span></footer>}
    </main>
  );
}
