import {
  useMemo,
  useState,
} from "react";

import {
  Bot,
  ChevronDown,
  Gauge,
  RotateCcw,
  Sparkles,
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

const ITERATIONS = [
  2, 3, 5, 8, 13, 21,
];

const INTERVALS = [
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
  const [open, setOpen] =
    useState(false);
  const [iterations, setIterations] =
    useState(5);
  const [intervalMs, setIntervalMs] =
    useState(0);
  const [personaId, setPersonaId] =
    useState(defaultPersonaId);
  const [selection, setSelection] =
    useState<"final" | "auto">("final");
  const [preserveLineage, setPreserveLineage] =
    useState(true);
  const [staged, setStaged] =
    useState(false);

  const request = useMemo<UrgeRequest>(
    () => ({
      messageId,
      iterations,
      intervalMs,
      personaId,
      selection,
      preserveLineage,
    }),
    [
      messageId,
      iterations,
      intervalMs,
      personaId,
      selection,
      preserveLineage,
    ],
  );

  function reset() {
    setIterations(5);
    setIntervalMs(0);
    setPersonaId(defaultPersonaId);
    setSelection("final");
    setPreserveLineage(true);
    setStaged(false);
  }

  return (
    <div className="urge-control">
      <button
        type="button"
        className={
          open
            ? "urge-trigger active"
            : "urge-trigger"
        }
        onClick={() => setOpen(value => !value)}
        title="Urge iteration"
        aria-expanded={open}
      >
        <Sparkles size={14} />
        <span>urge</span>
        <ChevronDown size={12} />
      </button>

      {open && (
        <div
          className="urge-popover"
          role="dialog"
          aria-label="Urge iteration configuration"
        >
          <header className="urge-popover-header">
            <div>
              <strong>urge</strong>
              <span>iterative response refinement</span>
            </div>
            <button
              type="button"
              onClick={() => setOpen(false)}
              title="Close Urge"
            >
              <X size={14} />
            </button>
          </header>

          <div className="urge-state">
            <span className="urge-state-dot dormant" />
            <span>runtime dormant</span>
            <strong>0/{iterations}</strong>
          </div>

          <label className="urge-field">
            <span>
              <Gauge size={13} />
              iterations
            </span>
            <select
              value={iterations}
              onChange={event =>
                setIterations(
                  Number(event.target.value),
                )
              }
            >
              {ITERATIONS.map(value => (
                <option key={value} value={value}>
                  {value}
                </option>
              ))}
            </select>
          </label>

          <label className="urge-field">
            <span>
              <Timer size={13} />
              interval
            </span>
            <select
              value={intervalMs}
              onChange={event =>
                setIntervalMs(
                  Number(event.target.value),
                )
              }
            >
              {INTERVALS.map(([value, label]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </select>
          </label>

          <label className="urge-field">
            <span>
              <Bot size={13} />
              persona
            </span>
            <select
              value={personaId}
              onChange={event =>
                setPersonaId(event.target.value)
              }
            >
              {personas.map(persona => {
                const id =
                  persona.persona_id
                  || "orobouros";
                return (
                  <option key={id} value={id}>
                    {persona.display_name || id}
                  </option>
                );
              })}
            </select>
          </label>

          <div className="urge-selection">
            <button
              type="button"
              className={
                selection === "final"
                  ? "active"
                  : ""
              }
              onClick={() => setSelection("final")}
              title="Use the final iteration"
            >
              final
            </button>
            <button
              type="button"
              className={
                selection === "auto"
                  ? "active urge-auto"
                  : "urge-auto"
              }
              onClick={() => setSelection("auto")}
              title="Auto-select strongest iteration"
              aria-label="Auto-select strongest iteration"
            >
              a
            </button>
          </div>

          <label className="urge-check">
            <input
              type="checkbox"
              checked={preserveLineage}
              onChange={event =>
                setPreserveLineage(
                  event.target.checked,
                )
              }
            />
            <span>preserve iteration lineage</span>
          </label>

          <div className="urge-summary">
            <span>
              only the selected result enters chat
            </span>
            <span>
              intermediate iterations remain transient
            </span>
          </div>

          {staged && (
            <div className="urge-dormant-note">
              configuration staged. urge execution is
              not connected yet.
            </div>
          )}

          <footer className="urge-popover-footer">
            <button
              type="button"
              onClick={reset}
              title="Reset Urge settings"
            >
              <RotateCcw size={13} />
              reset
            </button>
            <button
              type="button"
              className="urge-run"
              onClick={() => {
                void request;
                setStaged(true);
              }}
              title="Stage configuration. Urge runtime is not connected."
            >
              <Sparkles size={13} />
              stage
            </button>
          </footer>
        </div>
      )}
    </div>
  );
}
