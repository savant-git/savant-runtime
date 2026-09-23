import {
  useMemo,
  useState,
} from "react";

import {
  Activity,
  ArrowRight,
  BrainCircuit,
  Check,
  ChevronRight,
  CircleDot,
  GitBranch,
  Layers3,
  Play,
  RefreshCcw,
  ShieldCheck,
  Sparkles,
  Target,
  Workflow,
} from "lucide-react";


type Capability = {
  id: string;
  group: string;
  status: string;
};


type UrgeConfig = {
  exile_id: string;
  name: string;
  designation: string;
  capabilities: Capability[];
  accent: {
    primary: string;
    secondary: string;
    signal: string;
  };
};


type Candidate = {
  id: string;
  name: string;
  mechanism: string;
  score: number;
  clicheRisk: number;
  divergence: number;
  lineage: string[];
};


const demoCandidates: Candidate[] = [
  {
    id: "candidate:threshold",
    name: "threshold",
    mechanism:
      "identity emerges from a controlled interruption at the exact point a system changes state",
    score: 0.94,
    clicheRisk: 0.08,
    divergence: 0.91,
    lineage: [
      "primitive-recomposition",
      "underscore-vessel",
      "adversarial-synthesis",
    ],
  },
  {
    id: "candidate:counterform",
    name: "counterform",
    mechanism:
      "the absent region performs the primary semantic event while the visible geometry acts as its support",
    score: 0.91,
    clicheRisk: 0.06,
    divergence: 0.95,
    lineage: [
      "negative-space",
      "underscore-vessel",
      "revision-pressure",
    ],
  },
  {
    id: "candidate:phase",
    name: "phase",
    mechanism:
      "one stable construction sustains two coherent readings without changing geometry",
    score: 0.89,
    clicheRisk: 0.1,
    divergence: 0.88,
    lineage: [
      "semantic-paradox",
      "underscore-vessel",
      "adversarial-synthesis",
    ],
  },
];


const criteria = [
  [
    "conceptual fit",
    96,
  ],
  [
    "distinctiveness",
    94,
  ],
  [
    "anti-cliche",
    92,
  ],
  [
    "semantic density",
    89,
  ],
  [
    "surprising coherence",
    91,
  ],
  [
    "legibility",
    87,
  ],
  [
    "scalability",
    93,
  ],
  [
    "silhouette",
    90,
  ],
  [
    "reproduction",
    95,
  ],
  [
    "memorability",
    91,
  ],
  [
    "system extension",
    88,
  ],
  [
    "negative space",
    94,
  ],
] as const;


function Meter({
  value,
}: {
  value: number;
}) {
  return (
    <span
      className="urge-meter"
      aria-label={`${value}%`}
    >
      <span
        style={{
          width: `${value}%`,
        }}
      />
    </span>
  );
}


function Metric({
  label,
  value,
}: {
  label: string;
  value: string;
}) {
  return (
    <div className="urge-metric">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}


export function UrgeWorkbench({
  config,
}: {
  config: UrgeConfig;
}) {
  const [
    selected,
    setSelected,
  ] = useState(
    demoCandidates[0].id,
  );

  const [
    mode,
    setMode,
  ] = useState<
    "job" | "logo"
  >("logo");

  const [
    running,
    setRunning,
  ] = useState(false);

  const [
    objective,
    setObjective,
  ] = useState(
    "Create an identity whose distinction comes from a proprietary structural mechanism rather than fashionable styling.",
  );

  const candidate =
    useMemo(
      () =>
        demoCandidates.find(
          (item) =>
            item.id
            === selected,
        )
        ?? demoCandidates[0],
      [selected],
    );

  const urgeCapabilities =
    useMemo(
      () =>
        config.capabilities
          .filter(
            (item) =>
              item.group
              === "runtime-projection"
              || item.group
              === "integration-slot",
          )
          .slice(
            0,
            8,
          ),
      [config.capabilities],
    );

  return (
    <section
      className="urge-workbench"
      aria-label="Urge iteration workbench"
    >
      <header className="urge-hero">
        <div>
          <div className="urge-kicker">
            <RefreshCcw size={13} />
            exile / urge
          </div>

          <h1>
            iteration
            <span>
              without amnesia
            </span>
          </h1>

          <p>
            Generate divergence,
            preserve useful branches,
            apply revision pressure,
            and converge without
            flattening the strange
            ideas that deserved to
            survive.
          </p>
        </div>

        <div className="urge-runtime-state">
          <span>
            <CircleDot size={12} />
            runtime
          </span>

          <strong>
            ready
          </strong>

          <small>
            renderer reserved
          </small>
        </div>
      </header>

      <div className="urge-modebar">
        <div>
          <button
            type="button"
            data-active={
              mode === "job"
            }
            onClick={() =>
              setMode("job")
            }
          >
            <Workflow size={14} />
            arbitrary job
          </button>

          <button
            type="button"
            data-active={
              mode === "logo"
            }
            onClick={() =>
              setMode("logo")
            }
          >
            <Sparkles size={14} />
            logo intelligence
          </button>
        </div>

        <div className="urge-owner-chain">
          <span>
            opus
            <small>
              orchestration
            </small>
          </span>

          <ChevronRight size={13} />

          <span>
            underscore
            <small>
              discrimination
            </small>
          </span>

          <ChevronRight size={13} />

          <span>
            urge
            <small>
              iteration
            </small>
          </span>
        </div>
      </div>

      <div className="urge-grid">
        <section className="urge-objective">
          <div className="urge-section-title">
            <Target size={15} />

            <div>
              <small>
                objective
              </small>

              <strong>
                pressure source
              </strong>
            </div>
          </div>

          <textarea
            value={objective}
            onChange={(event) =>
              setObjective(
                event.target.value,
              )
            }
            spellCheck={false}
          />

          <div className="urge-objective-meta">
            <span>
              mode
              <strong>
                {mode}
              </strong>
            </span>

            <span>
              authority
              <strong>
                projection only
              </strong>
            </span>
          </div>

          <button
            className="urge-run"
            type="button"
            disabled={
              !objective.trim()
            }
            onClick={() => {
              setRunning(true);

              window.setTimeout(
                () =>
                  setRunning(
                    false,
                  ),
                700,
              );
            }}
          >
            {
              running
                ? (
                  <Activity
                    size={15}
                  />
                )
                : (
                  <Play
                    size={15}
                  />
                )
            }

            {
              running
                ? "projecting"
                : "iterate"
            }

            <ArrowRight
              size={14}
            />
          </button>
        </section>

        <section className="urge-stage">
          <div className="urge-section-title">
            <BrainCircuit size={15} />

            <div>
              <small>
                candidate stage
              </small>

              <strong>
                {
                  candidate.name
                }
              </strong>
            </div>

            <span className="urge-score">
              {
                Math.round(
                  candidate.score
                  * 100,
                )
              }
            </span>
          </div>

          <div className="urge-mark-field">
            <div className="urge-mark">
              <span />
              <span />
              <span />
            </div>

            <div className="urge-mechanism">
              <small>
                mechanism
              </small>

              <p>
                {
                  candidate.mechanism
                }
              </p>
            </div>
          </div>

          <div className="urge-stage-metrics">
            <Metric
              label="divergence"
              value={
                candidate.divergence
                  .toFixed(2)
              }
            />

            <Metric
              label="cliche risk"
              value={
                candidate.clicheRisk
                  .toFixed(2)
              }
            />

            <Metric
              label="lineage"
              value={
                String(
                  candidate.lineage
                    .length,
                )
              }
            />
          </div>
        </section>

        <section className="urge-pressure">
          <div className="urge-section-title">
            <Activity size={15} />

            <div>
              <small>
                revision pressure
              </small>

              <strong>
                criterion field
              </strong>
            </div>
          </div>

          <div className="urge-criteria">
            {
              criteria.map(
                ([
                  label,
                  value,
                ]) => (
                  <div
                    key={label}
                  >
                    <span>
                      {label}
                    </span>

                    <Meter
                      value={value}
                    />

                    <strong>
                      {value}
                    </strong>
                  </div>
                ),
              )
            }
          </div>
        </section>

        <section className="urge-frontier">
          <div className="urge-section-title">
            <GitBranch size={15} />

            <div>
              <small>
                underscore vessel
              </small>

              <strong>
                divergent frontier
              </strong>
            </div>
          </div>

          <div className="urge-candidates">
            {
              demoCandidates.map(
                (item) => (
                  <button
                    key={item.id}
                    type="button"
                    data-active={
                      selected
                      === item.id
                    }
                    onClick={() =>
                      setSelected(
                        item.id,
                      )
                    }
                  >
                    <span>
                      {
                        item.name
                      }
                    </span>

                    <strong>
                      {
                        Math.round(
                          item.score
                          * 100,
                        )
                      }
                    </strong>

                    <small>
                      divergence{" "}
                      {
                        item.divergence
                          .toFixed(2)
                      }
                    </small>
                  </button>
                ),
              )
            }
          </div>

          <div className="urge-lineage">
            {
              candidate.lineage.map(
                (
                  item,
                  index,
                ) => (
                  <span
                    key={item}
                  >
                    <i>
                      {index + 1}
                    </i>

                    {item}

                    {
                      index
                      < candidate
                        .lineage
                        .length
                        - 1
                        ? (
                          <ChevronRight
                            size={12}
                          />
                        )
                        : null
                    }
                  </span>
                ),
              )
            }
          </div>
        </section>

        <section className="urge-capability-strip">
          <div className="urge-section-title">
            <Layers3 size={15} />

            <div>
              <small>
                composition
              </small>

              <strong>
                active substrate
              </strong>
            </div>
          </div>

          <div>
            {
              urgeCapabilities.map(
                (item) => (
                  <span
                    key={item.id}
                  >
                    <Check
                      size={11}
                    />

                    {
                      item.id
                        .replace(
                          /^[^:]+:/,
                          "",
                        )
                    }
                  </span>
                ),
              )
            }
          </div>
        </section>

        <section className="urge-renderer-slot">
          <div className="urge-section-title">
            <ShieldCheck size={15} />

            <div>
              <small>
                vector projection
              </small>

              <strong>
                savant svg renderer
              </strong>
            </div>
          </div>

          <div className="urge-reserved">
            <span />

            <div>
              <strong>
                integration slot
              </strong>

              <p>
                Reserved typed boundary.
                Urge does not own or
                duplicate renderer
                substance.
              </p>
            </div>
          </div>
        </section>
      </div>
    </section>
  );
}
