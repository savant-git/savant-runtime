import {useEffect,useId,useMemo,useRef,useState} from "react"
import type {RefObject} from "react"
import {createPortal} from "react-dom"
import {Activity,ArrowLeft,ArrowRight,Bot,Check,ChevronDown,CircleHelp,Clock3,GitBranch,Layers3,Orbit,Pause,Play,RotateCcw,ScanEye,Sparkles,X} from "../components/savant-glyphs"
import type {UrgeControlProps,UrgeExtendedRequest,UrgePersonaMode} from "./urge-types"
import {limits,modeDescriptions,modeLabels,clampNumber,personaIdentity,personaName} from "./urge-configuration"
import type {PanelTab} from "./urge-configuration"
import "./urge-control.css"
export default function UrgeDialog({
  messageId,
  personas,
  defaultPersonaId,open,setOpen,trigger,dialogId,
}: UrgeControlProps & {dialogId:string;open:boolean;setOpen:(value:boolean)=>void;trigger:RefObject<HTMLButtonElement|null>}) {
  const id = dialogId;
  const panel = useRef<HTMLDivElement>(null);

  const options = useMemo(() => {
    const source = personas.length
      ? personas
      : [{
          persona_id: "orobouros",
          display_name: "orobouros",
        }];

    const seen = new Set<string>();

    return source.filter(persona => {
      const identity = personaIdentity(persona);
      if (seen.has(identity)) return false;
      seen.add(identity);
      return true;
    });
  }, [personas]);

  const initialPersona = options.some(
    persona => personaIdentity(persona) === defaultPersonaId,
  )
    ? defaultPersonaId
    : personaIdentity(options[0]);

  const [iterations, setIterations] = useState(5);
  const [iterationText, setIterationText] = useState("5");
  const [intervalMs, setIntervalMs] = useState(0);
  const [intervalText, setIntervalText] = useState("0");
  const [personaIds, setPersonaIds] = useState<string[]>([
    initialPersona,
  ]);
  const [personaMenu, setPersonaMenu] = useState(false);
  const [personaMode, setPersonaMode] =
    useState<UrgePersonaMode>("adaptive");
  const [selection, setSelection] =
    useState<"final" | "auto">("final");
  const [preserveLineage, setPreserveLineage] = useState(true);
  const [staged, setStaged] = useState(false);
  const [tab, setTab] = useState<PanelTab>("session");

  const request = useMemo<UrgeExtendedRequest>(() => ({
    messageId,
    iterations,
    intervalMs,
    personaId: personaIds[0] || initialPersona,
    personaIds,
    personaMode,
    selection,
    preserveLineage,
  }), [
    messageId,
    iterations,
    intervalMs,
    personaIds,
    personaMode,
    selection,
    preserveLineage,
    initialPersona,
  ]);

  useEffect(() => {
    setStaged(false);
  }, [request]);

  useEffect(() => {
    setPersonaIds(current => {
      const available = new Set(options.map(personaIdentity));
      const filtered = current.filter(identity =>
        available.has(identity)
      ).slice(0, limits.personas);

      return filtered.length
        ? filtered
        : [initialPersona];
    });
  }, [options, initialPersona]);

  function setIterationValue(value: number) {
    const normalized = clampNumber(
      String(value),
      limits.iterations.min,
      limits.iterations.max,
      5,
    );
    setIterations(normalized);
    setIterationText(String(normalized));
  }

  function setIntervalValue(value: number) {
    const normalized = clampNumber(
      String(value),
      limits.intervalMs.min,
      limits.intervalMs.max,
      0,
    );
    setIntervalMs(normalized);
    setIntervalText(String(normalized));
  }

  function commitIterations() {
    setIterationValue(clampNumber(
      iterationText,
      limits.iterations.min,
      limits.iterations.max,
      iterations,
    ));
  }

  function commitInterval() {
    setIntervalValue(clampNumber(
      intervalText,
      limits.intervalMs.min,
      limits.intervalMs.max,
      intervalMs,
    ));
  }

  function togglePersona(identity: string) {
    setPersonaIds(current => {
      if (current.includes(identity)) {
        return current.length > 1
          ? current.filter(item => item !== identity)
          : current;
      }

      if (current.length >= limits.personas) return current;

      return [...current, identity];
    });
  }

  function reset() {
    setIterationValue(5);
    setIntervalValue(0);
    setPersonaIds([initialPersona]);
    setPersonaMode("adaptive");
    setSelection("final");
    setPreserveLineage(true);
    setPersonaMenu(false);
    setTab("session");
    setStaged(false);
  }

  function close() {
    setOpen(false);
    setPersonaMenu(false);
    trigger.current?.focus({ preventScroll: true });
  }

  useEffect(() => {
    if (!open) return;

    const first = panel.current?.querySelector<HTMLButtonElement>(
      "button",
    );
    first?.focus({ preventScroll: true });

    function outside(event: PointerEvent) {
      if (
        event.target instanceof Node &&
        !panel.current?.contains(event.target) &&
        !trigger.current?.contains(event.target)
      ) {
        setOpen(false);
        setPersonaMenu(false);
      }
    }

    function keyboard(event: KeyboardEvent) {
      if (event.key === "Escape") {
        event.preventDefault();
        close();
      }
    }

    document.addEventListener("pointerdown", outside);
    document.addEventListener("keydown", keyboard);

    return () => {
      document.removeEventListener("pointerdown", outside);
      document.removeEventListener("keydown", keyboard);
    };
  }, [open]);

  const selectedNames = personaIds.map(identity => {
    const persona = options.find(
      item => personaIdentity(item) === identity,
    );
    return persona ? personaName(persona) : identity;
  });

  return open ? createPortal(
        <div className="palaver-urge-layer">


          <div
            ref={panel}
            id={id}
            role="dialog"
            aria-modal="false"
            aria-label="urge iteration controls"
            className="palaver-urge-panel urge-next"
            data-message-id={messageId}
          >
            <header className="urge-head">
              <div className="urge-brand">
                <Orbit size={24} />
                <div>
                  <strong>urge</strong>
                  <small>Response evolution</small>
                </div>
              </div>

              <div className="urge-status">
                EXECUTION DORMANT
              </div>

              <button
                type="button"
                className="urge-icon"
                title="Close"
                aria-label="Close urge"
                onClick={close}
              >
                <X size={16} />
              </button>
            </header>

            <div className="urge-body">
              <div className="urge-section">
                <p className="urge-kicker">
                  01 / Evolution parameters
                </p>

                <div className="urge-numbers">
                  <div>
                    <label
                      className="urge-label"
                      htmlFor={`${id}-iterations`}
                    >
                      <span>Iterations</span>
                      <CircleHelp
                        size={13}
                        aria-label="Number of refinement cycles"
                      />
                    </label>

                    <div className="urge-number">
                      <Activity size={16} />
                      <input
                        id={`${id}-iterations`}
                        type="number"
                        min={limits.iterations.min}
                        max={limits.iterations.max}
                        step="1"
                        value={iterationText}
                        onChange={event => {
                          setIterationText(event.target.value);
                          const value = Number(event.target.value);
                          if (
                            event.target.value.trim() &&
                            Number.isFinite(value)
                          ) {
                            setIterations(clampNumber(
                              event.target.value,
                              limits.iterations.min,
                              limits.iterations.max,
                              iterations,
                            ));
                          }
                        }}
                        onBlur={commitIterations}
                        onKeyDown={event => {
                          if (event.key === "Enter") {
                            commitIterations();
                            event.currentTarget.blur();
                          }
                        }}
                      />
                      <span className="urge-unit">cycles</span>
                    </div>

                    <div className="urge-presets">
                      {[3, 5, 8, 13, 21].map(value => (
                        <button
                          key={value}
                          type="button"
                          aria-pressed={iterations === value}
                          onClick={() => setIterationValue(value)}
                        >
                          {value}
                        </button>
                      ))}
                    </div>
                  </div>

                  <div>
                    <label
                      className="urge-label"
                      htmlFor={`${id}-interval`}
                    >
                      <span>Interval</span>
                      <Clock3
                        size={13}
                        aria-label="Delay between iterations"
                      />
                    </label>

                    <div className="urge-number">
                      <Clock3 size={16} />
                      <input
                        id={`${id}-interval`}
                        type="number"
                        min={limits.intervalMs.min}
                        max={limits.intervalMs.max}
                        step="1"
                        value={intervalText}
                        onChange={event => {
                          setIntervalText(event.target.value);
                          const value = Number(event.target.value);
                          if (
                            event.target.value.trim() &&
                            Number.isFinite(value)
                          ) {
                            setIntervalMs(clampNumber(
                              event.target.value,
                              limits.intervalMs.min,
                              limits.intervalMs.max,
                              intervalMs,
                            ));
                          }
                        }}
                        onBlur={commitInterval}
                        onKeyDown={event => {
                          if (event.key === "Enter") {
                            commitInterval();
                            event.currentTarget.blur();
                          }
                        }}
                      />
                      <span className="urge-unit">ms</span>
                    </div>

                    <div className="urge-presets">
                      {[
                        [0, "live"],
                        [250, "250"],
                        [500, "500"],
                        [1000, "1s"],
                        [2500, "2.5s"],
                      ].map(([value, label]) => (
                        <button
                          key={value}
                          type="button"
                          aria-pressed={intervalMs === value}
                          onClick={() => setIntervalValue(
                            Number(value),
                          )}
                        >
                          {label}
                        </button>
                      ))}
                    </div>
                  </div>
                </div>

                <p className="urge-explain">
                  Values outside the supported range are clamped.
                  Current interface bounds: 1–21 iterations,
                  0–2500 ms.
                </p>
              </div>

              <div className="urge-section">
                <p className="urge-kicker">
                  02 / Persona intelligence
                </p>

                <div className="urge-label">
                  <span>Choose up to three personas</span>
                  <span>{personaIds.length}/3</span>
                </div>

                <div className="urge-persona-row">
                  <button
                    type="button"
                    className="urge-persona-button"
                    aria-label="Choose personas"
                    aria-expanded={personaMenu}
                    aria-controls={`${id}-persona-menu`}
                    onClick={() => setPersonaMenu(value => !value)}
                  >
                    p
                  </button>

                  {selectedNames.map((name, index) => (
                    <span
                      key={personaIds[index]}
                      className="urge-persona-chip"
                    >
                      {name}
                    </span>
                  ))}

                  <button
                    type="button"
                    className="urge-icon"
                    aria-label="Toggle persona list"
                    onClick={() => setPersonaMenu(value => !value)}
                  >
                    <ChevronDown size={14} />
                  </button>
                </div>

                {personaMenu && (
                  <div
                    className="urge-menu"
                    id={`${id}-persona-menu`}
                    aria-label="Available personas"
                  >
                    {options.map(persona => {
                      const identity = personaIdentity(persona);
                      const selected = personaIds.includes(identity);
                      const disabled = !selected &&
                        personaIds.length >= limits.personas;

                      return (
                        <button
                          key={identity}
                          type="button"
                          aria-pressed={selected}
                          disabled={disabled}
                          onClick={() => togglePersona(identity)}
                        >
                          <span>{personaName(persona)}</span>
                          {selected && <Check size={14} />}
                        </button>
                      );
                    })}
                  </div>
                )}

                <div
                  className="urge-mode-grid"
                  role="group"
                  aria-label="Persona collaboration mode"
                >
                  <button
                    type="button"
                    aria-pressed={personaMode === "adaptive"}
                    onClick={() => setPersonaMode("adaptive")}
                  >
                    <Bot size={17} />
                    Adaptive
                  </button>

                  <button
                    type="button"
                    aria-pressed={personaMode === "consolidated"}
                    onClick={() => setPersonaMode("consolidated")}
                  >
                    <Layers3 size={17} />
                    Consolidate
                  </button>

                  <button
                    type="button"
                    aria-pressed={personaMode === "deliberative"}
                    onClick={() => setPersonaMode("deliberative")}
                  >
                    <GitBranch size={17} />
                    Deliberate
                  </button>
                </div>

                <p className="urge-explain">
                  {modeDescriptions[personaMode]}
                </p>
              </div>

              <div className="urge-section">
                <p className="urge-kicker">
                  03 / Result selection
                </p>

                <div
                  className="urge-selection"
                  role="group"
                  aria-label="Final result selection"
                >
                  <button
                    type="button"
                    aria-pressed={selection === "final"}
                    onClick={() => setSelection("final")}
                  >
                    Use last iteration
                  </button>

                  <button
                    type="button"
                    className="urge-auto"
                    aria-pressed={selection === "auto"}
                    title="AI chooses the strongest iteration"
                    aria-label="AI selects strongest result"
                    onClick={() => setSelection("auto")}
                  >
                    a
                  </button>
                </div>

                <p className="urge-explain">
                  {selection === "auto"
                    ? "AI selection is requested, but no evaluation has run."
                    : "The final completed iteration is the requested result."}
                </p>

                <label className="urge-check">
                  <input
                    type="checkbox"
                    checked={preserveLineage}
                    onChange={event =>
                      setPreserveLineage(event.target.checked)
                    }
                  />
                  Preserve iteration lineage
                </label>
              </div>

              <div className="urge-tabs" role="tablist">
                <button
                  type="button"
                  role="tab"
                  aria-selected={tab === "session"}
                  aria-controls={`${id}-session`}
                  onClick={() => setTab("session")}
                >
                  <ScanEye size={13} /> Live evolution
                </button>

                <button
                  type="button"
                  role="tab"
                  aria-selected={tab === "future"}
                  aria-controls={`${id}-future`}
                  onClick={() => setTab("future")}
                >
                  <Sparkles size={13} /> Carbon futures
                </button>
              </div>

              {tab === "session" ? (
                <section
                  id={`${id}-session`}
                  role="tabpanel"
                  className="urge-section"
                >
                  <div className="urge-live" aria-live="polite">
                    <div className="urge-live-title">
                      <Activity size={15} />
                      Latest iteration
                    </div>
                    <p>
                      No iteration has executed. When Urge is
                      connected, this window will display the
                      newest completed result and its evidence.
                    </p>
                  </div>

                  <div
                    className="urge-timeline"
                    aria-label="Iteration timeline"
                  >
                    {Array.from(
                      { length: iterations },
                      (_, index) => (
                        <span key={index}>{index + 1}</span>
                      ),
                    )}
                  </div>

                  <div className="urge-transport">
                    <button
                      type="button"
                      disabled
                      title="Requires a running session"
                    >
                      <Pause size={14} />
                      Pause
                    </button>
                    <button
                      type="button"
                      disabled
                      title="Requires a persisted iteration history"
                    >
                      <ArrowLeft size={14} />
                      Rewind
                    </button>
                    <button
                      type="button"
                      disabled
                      title="Requires a paused session"
                    >
                      <Play size={14} />
                      Resume
                    </button>
                  </div>

                  <p className="urge-explain">
                    Rewind will require an explicit confirmation.
                    Superseded results must remain recoverable
                    as history rather than being silently destroyed.
                  </p>
                </section>
              ) : (
                <section
                  id={`${id}-future`}
                  role="tabpanel"
                  className="urge-section urge-future"
                >
                  <h3>Explore before committing</h3>
                  <p>
                    Carbon can compare hypothetical outcomes
                    from different personas, intervals, and
                    iteration counts without modifying the
                    active Urge session.
                  </p>
                  <p>
                    Predictions must be labeled hypothetical
                    and distinguished from observed results.
                  </p>
                  <button
                    type="button"
                    disabled
                    title="Carbon execution is not connected"
                  >
                    <ArrowRight size={14} />
                    Project alternative futures
                  </button>
                </section>
              )}

              <footer className="urge-footer">
                <a href="/urge-demo.html" target="_blank" rel="noopener noreferrer" title="Open the standalone simulation; it does not execute chat iterations">urge demo</a>
                <button
                  type="button"
                  onClick={reset}
                  title="Reset configuration"
                >
                  <RotateCcw size={13} /> Reset
                </button>

                <div>
                  <span className="urge-help">
                    <CircleHelp size={12} />
                    {staged
                      ? "Staged locally"
                      : "Configuration only"}
                  </span>
                </div>

                <button
                  type="button"
                  className="urge-primary"
                  onClick={() => {
                    commitIterations();
                    commitInterval();
                    setStaged(true);
                  }}
                  title="Stage configuration without executing"
                >
                  <Orbit size={13} /> Stage
                </button>
              </footer>
            </div>
          </div>
        </div>,
        document.body,
      ) : null;
}
