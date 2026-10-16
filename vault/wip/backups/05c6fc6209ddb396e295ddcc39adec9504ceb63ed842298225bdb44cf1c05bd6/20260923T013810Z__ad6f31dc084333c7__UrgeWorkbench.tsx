import {
  useMemo,
  useRef,
  useState,
} from "react";

import {
  Activity,
  AlertTriangle,
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


type UnknownRecord = Record<
  string,
  unknown
>;


type Candidate = {
  id: string;
  name: string;
  mechanism: string;
  score: number;
  clicheRisk: number;
  divergence: number;
  lineage: string[];
  source: UnknownRecord;
};


type WorkbenchProjection = {
  schema?: string;
  owner?: string;
  authority_effect?: string;
  projection_only?: boolean;
  status?: UnknownRecord;
  candidate_stage?: UnknownRecord;
  pressure?: UnknownRecord;
  creative_frontier?: UnknownRecord;
  logo?: UnknownRecord;
  renderer?: UnknownRecord;
  lineage?: UnknownRecord;
  metrics?: UnknownRecord;
  ownership?: UnknownRecord;
  boundaries?: UnknownRecord;
  digest?: string;
};


type ExecutionResult = {
  schema?: string;
  owner?: string;
  capability?: string;
  request?: UnknownRecord;
  creative?: UnknownRecord;
  logo?: UnknownRecord | null;
  renderer?: UnknownRecord;
  workbench?: WorkbenchProjection;
  boundaries?: UnknownRecord;
};


type ExecutionEnvelope = {
  schema?: string;
  owner?: string;
  ok?: boolean;
  capability?: string;
  result?: ExecutionResult;
  error?: string;
  detail?: string;
  authority_effect?: string;
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
    source: {},
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
    source: {},
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
    source: {},
  },
];


const criteria = [
  ["conceptual fit", 96],
  ["distinctiveness", 94],
  ["anti-cliche", 92],
  ["semantic density", 89],
  ["surprising coherence", 91],
  ["legibility", 87],
  ["scalability", 93],
  ["silhouette", 90],
  ["reproduction", 95],
  ["memorability", 91],
  ["system extension", 88],
  ["negative space", 94],
] as const;


function record(
  value: unknown,
): UnknownRecord | null {
  if (
    value !== null
    && typeof value === "object"
    && !Array.isArray(value)
  ) {
    return value as UnknownRecord;
  }

  return null;
}


function records(
  value: unknown,
): UnknownRecord[] {
  if (!Array.isArray(value)) {
    return [];
  }

  return value
    .map(record)
    .filter(
      (
        item,
      ): item is UnknownRecord =>
        item !== null,
    );
}


function strings(
  value: unknown,
): string[] {
  if (!Array.isArray(value)) {
    return [];
  }

  return value
    .map((item) =>
      String(item).trim(),
    )
    .filter(Boolean);
}


function firstString(
  source: UnknownRecord,
  keys: string[],
  fallback: string,
): string {
  for (const key of keys) {
    const value = source[key];

    if (
      typeof value === "string"
      && value.trim()
    ) {
      return value.trim();
    }
  }

  return fallback;
}


function firstNumber(
  source: UnknownRecord,
  keys: string[],
  fallback: number,
): number {
  for (const key of keys) {
    const value = source[key];

    if (
      typeof value === "number"
      && Number.isFinite(value)
    ) {
      return value;
    }
  }

  return fallback;
}


function normalizedUnit(
  value: number,
): number {
  if (!Number.isFinite(value)) {
    return 0;
  }

  if (value > 1 && value <= 100) {
    return value / 100;
  }

  return Math.max(
    0,
    Math.min(
      1,
      value,
    ),
  );
}


function candidateFromRecord(
  source: UnknownRecord,
  index: number,
): Candidate {
  const assessment =
    record(
      source.assessment,
    ) ?? {};

  const scores =
    record(
      source.scores,
    ) ?? {};

  const id = firstString(
    source,
    [
      "id",
      "candidate_id",
      "identity",
    ],
    `candidate:live:${index + 1}`,
  );

  const name = firstString(
    source,
    [
      "name",
      "title",
      "label",
      "lens",
    ],
    `candidate ${index + 1}`,
  );

  const mechanism = firstString(
    source,
    [
      "mechanism",
      "concept",
      "text",
      "description",
      "proposal",
      "content",
    ],
    "Projected candidate. Inspect its source projection for additional structure.",
  );

  const score = normalizedUnit(
    firstNumber(
      source,
      [
        "score",
        "fitness",
        "quality",
        "survivability",
      ],
      firstNumber(
        scores,
        [
          "score",
          "fitness",
          "quality",
          "survivability",
        ],
        0,
      ),
    ),
  );

  const clicheRisk =
    normalizedUnit(
      firstNumber(
        source,
        [
          "cliche_risk",
          "clicheRisk",
          "cliche_similarity",
        ],
        firstNumber(
          assessment,
          [
            "cliche_risk",
            "cliche_similarity",
          ],
          0,
        ),
      ),
    );

  const divergence =
    normalizedUnit(
      firstNumber(
        source,
        [
          "divergence",
          "novelty",
          "distinctiveness",
        ],
        firstNumber(
          scores,
          [
            "divergence",
            "novelty",
            "distinctiveness",
          ],
          0,
        ),
      ),
    );

  const directLineage =
    strings(
      source.lineage,
    );

  const lineage =
    directLineage.length
      ? directLineage
      : [
          "opus-orchestration",
          "underscore-discrimination",
          "urge-iteration",
        ];

  return {
    id,
    name,
    mechanism,
    score,
    clicheRisk,
    divergence,
    lineage,
    source,
  };
}


function projectedCandidates(
  workbench: WorkbenchProjection | null,
): Candidate[] {
  if (!workbench) {
    return [];
  }

  const creativeFrontier =
    record(
      workbench.creative_frontier,
    );

  const finalFrontier =
    records(
      creativeFrontier?.final,
    );

  if (finalFrontier.length) {
    return finalFrontier.map(
      candidateFromRecord,
    );
  }

  const candidateStage =
    record(
      workbench.candidate_stage,
    );

  const output: UnknownRecord[] = [];

  const best =
    record(
      candidateStage?.best,
    );

  if (best) {
    output.push(best);
  }

  output.push(
    ...records(
      candidateStage?.alternates,
    ),
  );

  return output.map(
    candidateFromRecord,
  );
}


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

  const [
    logoName,
    setLogoName,
  ] = useState(
    config.name || "savant",
  );

  const [
    workbench,
    setWorkbench,
  ] = useState<
    WorkbenchProjection | null
  >(null);

  const [
    execution,
    setExecution,
  ] = useState<
    ExecutionResult | null
  >(null);

  const [
    error,
    setError,
  ] = useState<
    string | null
  >(null);

  const requestSequence =
    useRef(0);

  const liveCandidates =
    useMemo(
      () =>
        projectedCandidates(
          workbench,
        ),
      [workbench],
    );

  const candidates =
    liveCandidates.length
      ? liveCandidates
      : demoCandidates;

  const candidate =
    useMemo(
      () =>
        candidates.find(
          (item) =>
            item.id === selected,
        )
        ?? candidates[0],
      [
        candidates,
        selected,
      ],
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

  const renderer =
    record(
      workbench?.renderer,
    );

  const rendererState =
    firstString(
      renderer ?? {},
      [
        "state",
        "status",
      ],
      "reserved",
    );

  const projectionDigest =
    typeof workbench?.digest
      === "string"
      ? workbench.digest
      : null;

  const run = async () => {
    const cleanObjective =
      objective.trim();

    const cleanName =
      logoName.trim();

    if (!cleanObjective) {
      return;
    }

    if (
      mode === "logo"
      && !cleanName
    ) {
      setError(
        "Logo mode requires a name.",
      );
      return;
    }

    const sequence =
      requestSequence.current + 1;

    requestSequence.current =
      sequence;

    setRunning(true);
    setError(null);

    try {
      const response =
        await fetch(
          "/api/execution/dispatch",
          {
            method: "POST",
            headers: {
              Accept:
                "application/json",
              "Content-Type":
                "application/json",
            },
            body: JSON.stringify({
              capability:
                "exile:urge:iterate",
              payload: {
                objective:
                  cleanObjective,
                mode,
                name:
                  mode === "logo"
                    ? cleanName
                    : "",
                brief:
                  mode === "logo"
                    ? {
                        name:
                          cleanName,
                      }
                    : {},
                constraints: [],
                invariants: [],
                cliches: [],
                baselines: [],
                context: {
                  surface:
                    "splyce",
                  instance:
                    config.exile_id,
                },
                creative_policy: {},
              },
            }),
          },
        );

      const envelope =
        (await response.json())
          as ExecutionEnvelope;

      if (
        !response.ok
        || envelope.ok === false
      ) {
        const detail =
          envelope.detail
          || envelope.error
          || `execution failed with status ${response.status}`;

        throw new Error(
          detail,
        );
      }

      if (
        sequence
        !== requestSequence.current
      ) {
        return;
      }

      if (!envelope.result) {
        throw new Error(
          "execution returned no result",
        );
      }

      const nextWorkbench =
        envelope.result.workbench;

      if (!nextWorkbench) {
        throw new Error(
          "execution returned no workbench projection",
        );
      }

      setExecution(
        envelope.result,
      );

      setWorkbench(
        nextWorkbench,
      );

      const nextCandidates =
        projectedCandidates(
          nextWorkbench,
        );

      if (nextCandidates.length) {
        setSelected(
          nextCandidates[0].id,
        );
      }
    } catch (cause) {
      if (
        sequence
        !== requestSequence.current
      ) {
        return;
      }

      setError(
        cause instanceof Error
          ? cause.message
          : "execution failed",
      );
    } finally {
      if (
        sequence
        === requestSequence.current
      ) {
        setRunning(false);
      }
    }
  };

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
            {running
              ? "executing"
              : error
                ? "fault"
                : workbench
                  ? "projected"
                  : "ready"}
          </strong>

          <small>
            renderer {rendererState}
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

          {mode === "logo" ? (
            <input
              value={logoName}
              onChange={(event) =>
                setLogoName(
                  event.target.value,
                )
              }
              aria-label="Logo name"
              placeholder="identity name"
              spellCheck={false}
            />
          ) : null}

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

            {projectionDigest ? (
              <span>
                projection
                <strong>
                  {projectionDigest.slice(
                    0,
                    10,
                  )}
                </strong>
              </span>
            ) : null}
          </div>

          {error ? (
            <div
              role="alert"
              className="urge-error"
            >
              <AlertTriangle
                size={14}
              />
              {error}
            </div>
          ) : null}

          <button
            className="urge-run"
            type="button"
            disabled={
              running
              || !objective.trim()
              || (
                mode === "logo"
                && !logoName.trim()
              )
            }
            onClick={() => {
              void run();
            }}
          >
            {running ? (
              <Activity size={15} />
            ) : (
              <Play size={15} />
            )}

            {running
              ? "projecting"
              : workbench
                ? "iterate again"
                : "iterate"}

            <ArrowRight size={14} />
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
                {candidate.name}
              </strong>
            </div>

            <span className="urge-score">
              {Math.round(
                candidate.score
                * 100,
              )}
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
                {candidate.mechanism}
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
            {criteria.map(
              ([
                label,
                value,
              ]) => (
                <div key={label}>
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
            )}
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
            {candidates.map(
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
                    {item.name}
                  </span>

                  <strong>
                    {Math.round(
                      item.score
                      * 100,
                    )}
                  </strong>

                  <small>
                    divergence{" "}
                    {item.divergence
                      .toFixed(2)}
                  </small>
                </button>
              ),
            )}
          </div>

          <div className="urge-lineage">
            {candidate.lineage.map(
              (
                item,
                index,
              ) => (
                <span
                  key={`${item}:${index}`}
                >
                  <i>
                    {index + 1}
                  </i>

                  {item}

                  {index
                  < candidate.lineage
                    .length - 1 ? (
                    <ChevronRight
                      size={12}
                    />
                  ) : null}
                </span>
              ),
            )}
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
            {urgeCapabilities.map(
              (item) => (
                <span key={item.id}>
                  <Check size={11} />

                  {item.id.replace(
                    /^[^:]+:/,
                    "",
                  )}
                </span>
              ),
            )}
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
                {rendererState
                  === "reserved"
                  ? (
                    "Reserved typed boundary. "
                    + "Urge does not own or "
                    + "duplicate renderer "
                    + "substance."
                  )
                  : (
                    "Renderer projection state: "
                    + rendererState
                    + "."
                  )}
              </p>
            </div>
          </div>

          {execution?.capability ? (
            <div className="urge-objective-meta">
              <span>
                capability
                <strong>
                  {execution.capability}
                </strong>
              </span>
            </div>
          ) : null}
        </section>
      </div>
    </section>
  );
}
