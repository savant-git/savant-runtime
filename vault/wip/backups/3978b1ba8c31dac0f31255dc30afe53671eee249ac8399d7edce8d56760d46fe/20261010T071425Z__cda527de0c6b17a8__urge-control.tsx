import {
  useEffect,
  useId,
  useLayoutEffect,
  useMemo,
  useRef,
  useState,
} from "react";

import { createPortal } from "react-dom";

import {
  Bot,
  ChevronDown,
  Gauge,
  RotateCcw,
  Orbit,
  Timer,
  X,
} from "lucide-react";

export type UrgePersona = {
  persona_id?: string;
  display_name?: string;
};

export type UrgeRequest = {
  messageId: string;
  iterations: number;
  intervalMs: number;
  personaId: string;
  selection: "final" | "auto";
  preserveLineage: boolean;
};

type Props = {
  messageId: string;
  personas: UrgePersona[];
  defaultPersonaId: string;
};

const iterationsAvailable = [2, 3, 5, 8, 13, 21];

const intervalsAvailable = [
  [0, "continuous"],
  [250, "250 ms"],
  [500, "500 ms"],
  [1000, "1 sec"],
  [2500, "2.5 sec"],
] as const;

export default function UrgeControl({
  messageId,
  personas,
  defaultPersonaId,
}: Props) {
  const dialogId = useId();
  const triggerRef = useRef<HTMLButtonElement>(null);
  const panelRef = useRef<HTMLDivElement>(null);
  const [open, setOpen] = useState(false);
  const [iterations, setIterations] = useState(5);
  const [intervalMs, setIntervalMs] = useState(0);
  const [personaId, setPersonaId] = useState(defaultPersonaId);
  const [selection, setSelection] =
    useState<"final" | "auto">("final");
  const [preserveLineage, setPreserveLineage] = useState(true);
  const [staged, setStaged] = useState(false);

  const personaOptions = useMemo(() => {
    const unique = new Map<string, UrgePersona>();
    for (const persona of personas) {
      const id = persona.persona_id || "orobouros";
      unique.set(id, persona);
    }
    if (!unique.size) {
      unique.set("orobouros", {
        persona_id: "orobouros",
        display_name: "orobouros",
      });
    }
    return Array.from(unique, ([id, persona]) => ({
      id,
      label: persona.display_name || id,
    }));
  }, [personas]);

  const request = useMemo<UrgeRequest>(() => ({
    messageId,
    iterations,
    intervalMs,
    personaId,
    selection,
    preserveLineage,
  }), [
    messageId,
    iterations,
    intervalMs,
    personaId,
    selection,
    preserveLineage,
  ]);

  function close() {
    setOpen(false);
    triggerRef.current?.focus({ preventScroll: true });
  }

  function reset() {
    setIterations(5);
    setIntervalMs(0);
    setPersonaId(defaultPersonaId);
    setSelection("final");
    setPreserveLineage(true);
    setStaged(false);
  }

  useEffect(() => {
    setStaged(false);
  }, [request]);

  useLayoutEffect(() => {
    if (!open) return;

    const panel = panelRef.current;
    if (!panel) return;

    function position() {
      const element = panelRef.current;
      const trigger = triggerRef.current;
      if (!element || !trigger) return;

      const viewport = window.visualViewport;
      const left = viewport?.offsetLeft ?? 0;
      const top = viewport?.offsetTop ?? 0;
      const width = viewport?.width ?? window.innerWidth;
      const height = viewport?.height ?? window.innerHeight;
      const margin = 12;
      const availableWidth = Math.max(1, width - margin * 2);
      const panelWidth = Math.min(300, availableWidth);
      const availableHeight = Math.max(1, height - margin * 2);

      element.style.setProperty("position", "fixed", "important");
      element.style.setProperty("width", `${panelWidth}px`, "important");
      element.style.setProperty(
        "max-height", `${availableHeight}px`, "important",
      );
      element.style.setProperty("overflow-y", "auto", "important");
      element.style.setProperty("bottom", "auto", "important");
      element.style.setProperty("right", "auto", "important");
      element.style.setProperty("transform", "none", "important");
      element.style.setProperty("z-index", "2147483000", "important");

      const anchor = trigger.getBoundingClientRect();
      const panelHeight = element.getBoundingClientRect().height;

      const x = Math.max(
        left + margin,
        Math.min(anchor.right - panelWidth, left + width - panelWidth - margin),
      );

      const below = anchor.bottom + 8;
      const above = anchor.top - panelHeight - 8;
      const preferredY =
        below + panelHeight <= top + height - margin ? below : above;

      const y = Math.max(
        top + margin,
        Math.min(preferredY, top + height - panelHeight - margin),
      );

      element.style.setProperty("left", `${x}px`, "important");
      element.style.setProperty("top", `${y}px`, "important");
    }

    position();

    panel.querySelector<HTMLButtonElement>("button")?.focus({
      preventScroll: true,
    });

    const observer = new ResizeObserver(position);
    observer.observe(panel);

    window.addEventListener("resize", position);
    window.addEventListener("scroll", position, true);
    window.visualViewport?.addEventListener("resize", position);
    window.visualViewport?.addEventListener("scroll", position);

    return () => {
      observer.disconnect();
      window.removeEventListener("resize", position);
      window.removeEventListener("scroll", position, true);
      window.visualViewport?.removeEventListener("resize", position);
      window.visualViewport?.removeEventListener("scroll", position);
    };
  }, [open]);

  useEffect(() => {
    if (!open) return;

    function outside(event: PointerEvent) {
      const target = event.target;
      if (!(target instanceof Node)) return;
      if (panelRef.current?.contains(target)) return;
      if (triggerRef.current?.contains(target)) return;
      setOpen(false);
    }

    function keyboard(event: KeyboardEvent) {
      if (event.key === "Escape") {
        event.preventDefault();
        setOpen(false);
        triggerRef.current?.focus({ preventScroll: true });
      }
    }

    document.addEventListener("pointerdown", outside);
    document.addEventListener("keydown", keyboard);

    return () => {
      document.removeEventListener("pointerdown", outside);
      document.removeEventListener("keydown", keyboard);
    };
  }, [open]);

  return (
    <div className="urge-control">
      <button
        ref={triggerRef}
        type="button"
        className={open ? "urge-trigger active" : "urge-trigger"}
        onClick={() => setOpen(value => !value)}
        title="Configure response refinement; execution is dormant"
        aria-label="Configure urge response refinement"
        aria-haspopup="dialog"
        aria-controls={open ? dialogId : undefined}
        aria-expanded={open}
      >
        <Orbit size={14} />
        <span>urge</span>
        <ChevronDown size={11} />
      </button>

      {open && createPortal(
        <div className="palaver-only">
          <div
            ref={panelRef}
            id={dialogId}
            className="urge-popover"
            role="dialog"
            aria-label="urge iteration configuration"
            data-message-id={messageId}
            style={{
              position: "fixed",
              width: 300,
              padding: 12,
              boxSizing: "border-box",
              background: "#171b1f",
              color: "#e6e1d6",
              border: "1px solid #655337",
              borderRadius: 8,
              boxShadow: "0 18px 60px #000a",
              zIndex: 2147483000,
            }}
          >
            <header className="urge-popover-header">
              <div>
                <strong>urge</strong>
                <span>response refinement</span>
              </div>
              <button type="button" onClick={close} title="Close urge">
                <X size={14} />
              </button>
            </header>

            <div className="urge-state">
              <span className="urge-state-dot dormant" />
              <span>runtime dormant</span>
              <strong aria-label={`zero of ${iterations} iterations run`}>
                0/{iterations}
              </strong>
            </div>

            <label className="urge-field">
              <span><Gauge size={13} />iterations</span>
              <select
                value={iterations}
                onChange={event => setIterations(Number(event.target.value))}
              >
                {iterationsAvailable.map(value => (
                  <option key={value} value={value}>{value}</option>
                ))}
              </select>
            </label>

            <label className="urge-field">
              <span><Timer size={13} />interval</span>
              <select
                value={intervalMs}
                onChange={event => setIntervalMs(Number(event.target.value))}
              >
                {intervalsAvailable.map(([value, label]) => (
                  <option key={value} value={value}>{label}</option>
                ))}
              </select>
            </label>

            <label className="urge-field">
              <span><Bot size={13} />persona</span>
              <select
                value={personaId}
                onChange={event => setPersonaId(event.target.value)}
              >
                {personaOptions.map(persona => (
                  <option key={persona.id} value={persona.id}>
                    {persona.label}
                  </option>
                ))}
              </select>
            </label>

            <div className="urge-selection">
              <button
                type="button"
                className={selection === "final" ? "active" : ""}
                aria-pressed={selection === "final"}
                onClick={() => setSelection("final")}
                title="Select the final iteration when execution is implemented"
              >
                final
              </button>
              <button
                type="button"
                className={selection === "auto" ? "active urge-auto" : "urge-auto"}
                aria-pressed={selection === "auto"}
                aria-label="Automatically select the strongest iteration"
                onClick={() => setSelection("auto")}
                title="Let the AI select its strongest result when execution is implemented"
              >
                a
              </button>
            </div>

            <label className="urge-check">
              <input
                type="checkbox"
                checked={preserveLineage}
                onChange={event => setPreserveLineage(event.target.checked)}
              />
              <span>preserve iteration lineage</span>
            </label>

            <div className="urge-summary">
              <span>selected result enters chat</span>
              <span>intermediate results remain outside chat</span>
            </div>

            <div className="urge-dormant-note" role="status" aria-live="polite">
              {staged
                ? "configuration staged locally. execution is not connected."
                : "configuration only. no iterations will run."}
            </div>

            <footer className="urge-popover-footer">
              <button type="button" onClick={reset} title="Reset urge settings">
                <RotateCcw size={13} />reset
              </button>
              <button
                type="button"
                className="urge-run"
                onClick={() => setStaged(true)}
                title="Stage locally without executing or changing chat"
              >
                <Orbit size={13} />stage
              </button>
            </footer>
          </div>
        </div>,
        document.body,
      )}
    </div>
  );
}
