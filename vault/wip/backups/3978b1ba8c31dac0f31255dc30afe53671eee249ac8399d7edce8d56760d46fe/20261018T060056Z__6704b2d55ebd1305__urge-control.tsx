
import {
  useEffect,
  useId,
  useMemo,
  useRef,
  useState,
} from "react";
import { createPortal } from "react-dom";
import {
  Activity,
  ArrowLeft,
  ArrowRight,
  Bot,
  Check,
  ChevronDown,
  CircleHelp,
  Clock3,
  GitBranch,
  Layers3,
  Orbit,
  Pause,
  Play,
  RotateCcw,
  ScanEye,
  Sparkles,
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

export type UrgePersonaMode =
  | "adaptive"
  | "consolidated"
  | "deliberative";

export type UrgeExtendedRequest = UrgeRequest & {
  personaIds: string[];
  personaMode: UrgePersonaMode;
};

type Props = {
  messageId: string;
  personas: UrgePersona[];
  defaultPersonaId: string;
};

type PanelTab = "session" | "future";

const limits = {
  iterations: { min: 1, max: 21 },
  intervalMs: { min: 0, max: 2500 },
  personas: 3,
} as const;

const modeDescriptions: Record<UrgePersonaMode, string> = {
  adaptive:
    "For each iteration, select the most suitable persona from your chosen set.",
  consolidated:
    "Combine shared traits once and resolve conflicting traits through evaluation.",
  deliberative:
    "Keep personas distinct. Each proposes a direction before a collective decision.",
};

const modeLabels: Record<UrgePersonaMode, string> = {
  adaptive: "Adaptive",
  consolidated: "Consolidate",
  deliberative: "Deliberate",
};

const styles = `
.palaver-urge-layer {
  position: fixed;
  inset: 0;
  z-index: 10000;
  pointer-events: none;
}
.palaver-urge-panel.urge-next {
  --urge-text: #e2eae8;
  --urge-muted: #a0b1b0;
  --urge-edge: #42605e;
  --urge-bright: #b4e0d4;
  --urge-copper: #bd9a73;
  pointer-events: auto;
  position: fixed;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: min(94vw, 540px);
  max-height: min(90dvh, 820px);
  overflow-y: auto;
  overscroll-behavior: contain;
  padding: 0;
  border: 1px solid #52716e;
  border-radius: 16px;
  background: linear-gradient(145deg,#223139,#101a21 65%,#17221f);
  color: var(--urge-text);
  box-shadow: 0 30px 100px #000d, inset 0 1px #e5fff017;
  font: 13px/1.5 "Space Grotesk","Segoe UI",system-ui,sans-serif;
}
.urge-next * { box-sizing: border-box; }
.urge-next button,
.urge-next input {
  font: inherit;
}
.urge-next button {
  cursor: pointer;
  border: 1px solid #45605e;
  border-radius: 8px;
  color: var(--urge-text);
  background: #1b2b31;
  min-height: 34px;
}
.urge-next button:disabled {
  cursor: not-allowed;
  opacity: .42;
}
.urge-next button:focus-visible,
.urge-next input:focus-visible {
  outline: 2px solid var(--urge-bright);
  outline-offset: 2px;
}
.urge-next button[aria-pressed="true"] {
  background: #31544d !important;
  border-color: #a4d6c7 !important;
  color: #f0fffa !important;
}
.urge-next .urge-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 18px 20px;
  border-bottom: 1px solid #405450;
}
.urge-next .urge-brand {
  display: flex;
  align-items: center;
  gap: 11px;
}
.urge-next .urge-brand strong {
  display: block;
  font-size: 19px;
  letter-spacing: -.05em;
}
.urge-next .urge-brand small,
.urge-next .urge-muted {
  color: var(--urge-muted);
  font-size: 11px;
}
.urge-next .urge-status {
  color: var(--urge-copper);
  font-size: 10px;
  letter-spacing: .06em;
}
.urge-next .urge-icon {
  display: inline-grid;
  place-items: center;
  width: 34px;
  height: 34px;
  padding: 0;
  flex: none;
}
.urge-next .urge-body { padding: 18px 20px 20px; }
.urge-next .urge-section {
  margin-bottom: 20px;
}
.urge-next .urge-label {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 8px;
  color: #c8d9d5;
  font-size: 12px;
}
.urge-next .urge-kicker {
  color: var(--urge-copper);
  font-size: 10px;
  text-transform: uppercase;
  letter-spacing: .13em;
  margin: 0 0 12px;
}
.urge-next .urge-numbers {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}
.urge-next .urge-number {
  display: flex;
  align-items: center;
  gap: 7px;
  border: 1px solid #405652;
  background: #101d22;
  border-radius: 10px;
  padding: 7px 10px;
}
.urge-next .urge-number input {
  min-width: 0;
  width: 100%;
  background: transparent;
  border: 0;
  outline: none;
  color: #effbf7;
  font-size: 19px;
  font-weight: 600;
  font-variant-numeric: tabular-nums;
}
.urge-next .urge-number input:focus-visible {
  outline: none;
}
.urge-next .urge-unit {
  color: var(--urge-muted);
  font-size: 10px;
  white-space: nowrap;
}
.urge-next .urge-presets {
  display: flex;
  gap: 5px;
  flex-wrap: wrap;
  margin-top: 8px;
}
.urge-next .urge-presets button {
  min-height: 26px;
  padding: 2px 9px;
  font-size: 10px;
}
.urge-next .urge-persona-row {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}
.urge-next .urge-persona-button {
  width: 36px;
  height: 36px;
  padding: 0;
  font-size: 20px;
  font-weight: 650;
  text-transform: lowercase;
}
.urge-next .urge-persona-chip {
  padding: 6px 9px;
  border: 1px solid #45605e;
  border-radius: 7px;
  font-size: 11px;
  color: #c8e4dc;
}
.urge-next .urge-menu {
  margin-top: 9px;
  padding: 8px;
  border: 1px solid #506963;
  border-radius: 10px;
  background: #111e23;
  max-height: 180px;
  overflow-y: auto;
}
.urge-next .urge-menu button {
  display: flex;
  width: 100%;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding: 8px 10px;
  margin: 2px 0;
  text-align: left;
}
.urge-next .urge-mode-grid {
  display: grid;
  grid-template-columns: repeat(3,minmax(0,1fr));
  gap: 7px;
  margin-top: 12px;
}
.urge-next .urge-mode-grid button {
  min-height: 58px;
  padding: 8px 5px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-direction: column;
  gap: 5px;
  font-size: 11px;
}
.urge-next .urge-explain {
  margin: 9px 0 0;
  color: var(--urge-muted);
  font-size: 11px;
  line-height: 1.55;
}
.urge-next .urge-selection {
  display: flex;
  gap: 8px;
}
.urge-next .urge-selection button {
  flex: 1;
  min-height: 39px;
}
.urge-next .urge-selection .urge-auto {
  flex: 0 0 46px;
  font-size: 18px;
  font-weight: 700;
}
.urge-next .urge-check {
  display: flex;
  align-items: center;
  gap: 9px;
  margin-top: 12px;
  cursor: pointer;
  font-size: 11px;
}
.urge-next .urge-check input {
  accent-color: #a2d4c6;
}
.urge-next .urge-tabs {
  display: flex;
  gap: 7px;
  margin: 14px 0;
  border-bottom: 1px solid #405450;
}
.urge-next .urge-tabs button {
  border: 0;
  border-bottom: 2px solid transparent;
  border-radius: 0;
  background: transparent;
  padding: 8px 12px;
}
.urge-next .urge-tabs button[aria-selected="true"] {
  border-bottom-color: #a4d6c7;
  color: #eafff7;
}
.urge-next .urge-live {
  min-height: 124px;
  padding: 14px;
  border: 1px solid #47605c;
  border-radius: 11px;
  background:
    radial-gradient(circle at 90% 10%,#6ba38d18,transparent 45%),
    #101b20;
}
.urge-next .urge-live-title {
  display: flex;
  align-items: center;
  gap: 7px;
  color: #d1e9e0;
  font-size: 12px;
  margin-bottom: 9px;
}
.urge-next .urge-live p {
  margin: 0;
  font-size: 12px;
  color: #9fb1b0;
}
.urge-next .urge-timeline {
  display: flex;
  gap: 5px;
  margin-top: 12px;
  overflow-x: auto;
}
.urge-next .urge-timeline span {
  display: grid;
  place-items: center;
  flex: 0 0 25px;
  height: 25px;
  border: 1px solid #425653;
  border-radius: 6px;
  color: #829995;
  font-size: 10px;
}
.urge-next .urge-transport {
  display: flex;
  gap: 8px;
  margin-top: 13px;
}
.urge-next .urge-transport button {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  flex: 1;
  padding: 8px;
  font-size: 11px;
}
.urge-next .urge-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  padding-top: 14px;
  border-top: 1px solid #405450;
}
.urge-next .urge-footer button {
  padding: 8px 12px;
}
.urge-next .urge-primary {
  background: #badfd3 !important;
  color: #10211d !important;
  border-color: #d6f2e8 !important;
  font-weight: 650 !important;
}
.urge-next .urge-help {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  color: var(--urge-muted);
  font-size: 10px;
}
.urge-next .urge-future {
  padding: 15px;
  border: 1px solid #4b625d;
  border-radius: 11px;
  background: #122027;
}
.urge-next .urge-future h3 {
  margin: 0 0 9px;
  font-size: 14px;
}
.urge-next .urge-future p {
  font-size: 11px;
  color: #a9bbb7;
  margin: 0 0 10px;
}
.urge-next .urge-future button {
  width: 100%;
  padding: 9px;
}
@media (max-width: 480px) {
  .palaver-urge-panel.urge-next {
    width: calc(100vw - 16px);
    max-height: calc(100dvh - 16px);
  }
  .urge-next .urge-head { padding: 12px 14px; }
  .urge-next .urge-body { padding: 14px; }
  .urge-next .urge-mode-grid button { font-size: 10px; }
}
@media (prefers-reduced-motion: reduce) {
  .urge-next *, .urge-next *::before {
    animation: none !important;
    transition: none !important;
  }
}
`;

function clampNumber(
  raw: string,
  min: number,
  max: number,
  fallback: number,
): number {
  const value = Number(raw);
  if (!raw.trim() || !Number.isFinite(value)) return fallback;
  return Math.max(min, Math.min(max, Math.trunc(value)));
}

function personaIdentity(
  persona: UrgePersona,
): string {
  return persona.persona_id || "orobouros";
}

function personaName(
  persona: UrgePersona,
): string {
  return persona.display_name || personaIdentity(persona);
}

export default function UrgeControl({
  messageId,
  personas,
  defaultPersonaId,
}: Props) {
  const id = useId();
  const trigger = useRef<HTMLButtonElement>(null);
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

  const [open, setOpen] = useState(false);
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

  return (
    <div className="urge-control">
      <button
        ref={trigger}
        type="button"
        className="urge-trigger"
        title="Configure urge iteration"
        aria-label="Configure urge"
        aria-expanded={open}
        aria-haspopup="dialog"
        aria-controls={open ? id : undefined}
        onClick={() => setOpen(value => !value)}
      >
        <Orbit size={14} />
        <span>urge</span>
      </button>

      {open && createPortal(
        <div className="palaver-urge-layer">
          <style>{styles}</style>

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
      )}
    </div>
  );
}
