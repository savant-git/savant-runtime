import { useEffect, useId, useMemo, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { Bot, Gauge, Orbit, RotateCcw, Timer, X } from "lucide-react";

export type UrgePersona = { persona_id?: string; display_name?: string };
export type UrgeRequest = {
  messageId: string; iterations: number; intervalMs: number;
  personaId: string; selection: "final" | "auto"; preserveLineage: boolean;
};
type Props = {
  messageId: string; personas: UrgePersona[]; defaultPersonaId: string;
};
export default function UrgeControl({ messageId, personas, defaultPersonaId }: Props) {
  const id = useId();
  const trigger = useRef<HTMLButtonElement>(null);
  const panel = useRef<HTMLDivElement>(null);
  const [open, setOpen] = useState(false);
  const [iterations, setIterations] = useState(5);
  const [intervalMs, setIntervalMs] = useState(0);
  const [personaId, setPersonaId] = useState(defaultPersonaId);
  const [selection, setSelection] = useState<"final" | "auto">("final");
  const [preserveLineage, setPreserveLineage] = useState(true);
  const [staged, setStaged] = useState(false);
  const request = useMemo<UrgeRequest>(() => ({
    messageId, iterations, intervalMs, personaId, selection, preserveLineage,
  }), [messageId, iterations, intervalMs, personaId, selection, preserveLineage]);
  useEffect(() => { setStaged(false); }, [request]);
  function close() { setOpen(false); trigger.current?.focus({ preventScroll: true }); }
  function reset() {
    setIterations(5); setIntervalMs(0); setPersonaId(defaultPersonaId);
    setSelection("final"); setPreserveLineage(true); setStaged(false);
  }
  useEffect(() => {
    if (!open) return;
    panel.current?.querySelector<HTMLButtonElement>("button")?.focus({ preventScroll: true });
    function outside(event: PointerEvent) {
      if (event.target instanceof Node
        && !panel.current?.contains(event.target)
        && !trigger.current?.contains(event.target)) setOpen(false);
    }
    function keyboard(event: KeyboardEvent) {
      if (event.key === "Escape") { event.preventDefault(); close(); }
    }
    document.addEventListener("pointerdown", outside);
    document.addEventListener("keydown", keyboard);
    return () => {
      document.removeEventListener("pointerdown", outside);
      document.removeEventListener("keydown", keyboard);
    };
  }, [open]);
  const options = personas.length ? personas : [
    { persona_id: "orobouros", display_name: "orobouros" },
  ];
  return <div className="urge-control">
    <button ref={trigger} type="button" className="urge-trigger"
      title="Configure urge; execution remains dormant"
      aria-label="Configure urge" aria-expanded={open}
      aria-haspopup="dialog" aria-controls={open ? id : undefined}
      onClick={() => setOpen(value => !value)}>
      <Orbit size={14} /><span>urge</span>
    </button>
    {open && createPortal(
      <div className="palaver-urge-layer">
        <div ref={panel} id={id} role="dialog" aria-label="urge configuration"
          className="palaver-urge-panel" data-message-id={messageId}>
          <header><strong>urge</strong><span>runtime dormant · 0/{iterations}</span>
            <button type="button" title="Close urge" onClick={close}><X size={14} /></button>
          </header>
          <label><span><Gauge size={13} />iterations</span>
            <select value={iterations} onChange={event => setIterations(Number(event.target.value))}>
              {[2, 3, 5, 8, 13, 21].map(value => <option key={value}>{value}</option>)}
            </select></label>
          <label><span><Timer size={13} />interval</span>
            <select value={intervalMs} onChange={event => setIntervalMs(Number(event.target.value))}>
              {[[0,"continuous"],[250,"250 ms"],[500,"500 ms"],[1000,"1 sec"],[2500,"2.5 sec"]].map(([value,label]) =>
                <option key={value} value={value}>{label}</option>)}
            </select></label>
          <label><span><Bot size={13} />persona</span>
            <select value={personaId} onChange={event => setPersonaId(event.target.value)}>
              {options.map(persona => <option key={persona.persona_id || "orobouros"}
                value={persona.persona_id || "orobouros"}>{persona.display_name || persona.persona_id || "orobouros"}</option>)}
            </select></label>
          <div className="palaver-urge-selection">
            <button type="button" aria-pressed={selection === "final"} title="Select final iteration"
              onClick={() => setSelection("final")}>final</button>
            <button type="button" aria-pressed={selection === "auto"} title="AI selects its strongest iteration"
              onClick={() => setSelection("auto")}>a</button>
          </div>
          <label><input type="checkbox" checked={preserveLineage}
            onChange={event => setPreserveLineage(event.target.checked)} />
            preserve iteration lineage</label>
          <p role="status">{staged ? "staged locally; execution is not connected." : "only the selected result enters chat when execution is implemented."}</p>
          <footer>
            <button type="button" title="Reset configuration" onClick={reset}><RotateCcw size={13} />reset</button>
            <button type="button" title="Stage without running iterations"
              onClick={() => setStaged(true)}><Orbit size={13} />stage</button>
          </footer>
        </div>
      </div>, document.body)}
  </div>;
}
