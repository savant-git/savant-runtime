import {
  useCallback,
  useEffect,
  useMemo,
  useState,
  type ComponentType,
  type CSSProperties,
  type ReactNode,
} from "react";

import {
  Background,
  BackgroundVariant,
  Controls,
  MiniMap,
  ReactFlow,
  ReactFlowProvider,
  useReactFlow,
  type Edge,
  type Node,
} from "@xyflow/react";

import {
  useQuery,
} from "@tanstack/react-query";

import {
  AnimatePresence,
  motion,
} from "motion/react";

import {
  Activity,
  Boxes,
  Braces,
  CheckCircle2,
  ChevronRight,
  Command,
  Cpu,
  Download,
  Focus,
  Gauge,
  Grid3X3,
  HeartPulse,
  History,
  Layers3,
  Maximize2,
  Network,
  PanelLeft,
  RefreshCcw,
  Search,
  Settings,
  ShieldCheck,
  Sparkles,
  X,
} from "lucide-react";

import {
  z,
} from "zod";

import {
  create,
} from "zustand";

import {
  persist,
} from "zustand/middleware";

import {
  UrgeWorkbench,
} from "./UrgeWorkbench";

import "@xyflow/react/dist/style.css";


const PANEL_IDS = [
  "overview",
  "capabilities",
  "pipeline",
  "graph",
  "health",
  "validation",
  "activity",
  "provenance",
  "settings",
] as const;

type PanelId =
  typeof PANEL_IDS[number];


const PrioritySchema =
  z.object({
    id: z.enum([
      "mandatory",
      "salient",
      "arbitrary",
    ]),
    label: z.string(),
    description: z.string(),
  });


const CapabilitySchema =
  z.object({
    id: z.string(),
    group: z.string(),
    status: z.string(),
  });


const StatusSchema =
  z.object({
    id: z.string(),
    status: z.string(),
  });


const InstanceSchema =
  z.object({
    schema: z.string(),
    instance_id: z.string(),
    exile_id: z.string(),
    name: z.string(),
    designation: z.string(),
    sigil: z.string(),
    status: z.string(),

    authority: z.object({
      state: z.string(),
      confidence: z.number(),
      source: z.string(),
    }),

    accent: z.object({
      primary: z.string(),
      secondary: z.string(),
      signal: z.string(),
    }),

    purposes:
      z.array(
        z.string(),
      ).length(3),

    priority_modes:
      z.array(
        PrioritySchema,
      ).length(3),

    pipeline:
      z.array(
        z.string(),
      ).length(18),

    panels:
      z.array(
        z.enum(
          PANEL_IDS,
        ),
      ).length(9),

    capabilities:
      z.array(
        CapabilitySchema,
      ).min(3),

    health:
      z.array(
        StatusSchema,
      ).length(9),

    validation:
      z.array(
        StatusSchema,
      ).length(9),

    enhancements:
      z.array(
        z.string(),
      ).min(20),

    projection:
      z.object({
        authoritative: z.boolean(),
        rebuildable: z.boolean(),
        authority_source: z.string(),
        capability_source:
          z.string().nullable(),
        reserved_capability_slots:
          z.boolean(),
      }).optional(),

    projection_digest:
      z.string().optional(),
  });


type InstanceConfig =
  z.infer<
    typeof InstanceSchema
  >;


type Density =
  "comfortable"
  | "compact";


type SplyceState = {
  panel: PanelId;
  priority: string;
  commandOpen: boolean;
  focusMode: boolean;
  reducedMotion: boolean;
  telemetry: boolean;
  density: Density;
  search: string;
  selectedStage: number;
  selectedCapability:
    string | null;

  setPanel:
    (panel: PanelId) => void;

  setPriority:
    (priority: string) => void;

  setCommandOpen:
    (open: boolean) => void;

  setFocusMode:
    (value: boolean) => void;

  setReducedMotion:
    (value: boolean) => void;

  setTelemetry:
    (value: boolean) => void;

  setDensity:
    (density: Density) => void;

  setSearch:
    (value: string) => void;

  setSelectedStage:
    (value: number) => void;

  setSelectedCapability:
    (value: string | null) => void;
};


const useSplyce =
  create<SplyceState>()(
    persist(
      set => ({
        panel:
          "overview",

        priority:
          "salient",

        commandOpen:
          false,

        focusMode:
          false,

        reducedMotion:
          false,

        telemetry:
          true,

        density:
          "comfortable",

        search:
          "",

        selectedStage:
          0,

        selectedCapability:
          null,

        setPanel:
          panel =>
            set({
              panel,
            }),

        setPriority:
          priority =>
            set({
              priority,
            }),

        setCommandOpen:
          commandOpen =>
            set({
              commandOpen,
            }),

        setFocusMode:
          focusMode =>
            set({
              focusMode,
            }),

        setReducedMotion:
          reducedMotion =>
            set({
              reducedMotion,
            }),

        setTelemetry:
          telemetry =>
            set({
              telemetry,
            }),

        setDensity:
          density =>
            set({
              density,
            }),

        setSearch:
          search =>
            set({
              search,
            }),

        setSelectedStage:
          selectedStage =>
            set({
              selectedStage,
            }),

        setSelectedCapability:
          selectedCapability =>
            set({
              selectedCapability,
            }),
      }),
      {
        name:
          "savant-splyce-state",

        partialize:
          state => ({
            panel:
              state.panel,
            priority:
              state.priority,
            focusMode:
              state.focusMode,
            reducedMotion:
              state.reducedMotion,
            telemetry:
              state.telemetry,
            density:
              state.density,
          }),
      },
    ),
  );


const PANEL_ICONS:
Record<
  PanelId,
  ComponentType<{
    size?: number;
  }>
> = {
  overview:
    Grid3X3,
  capabilities:
    Boxes,
  pipeline:
    Layers3,
  graph:
    Network,
  health:
    HeartPulse,
  validation:
    ShieldCheck,
  activity:
    Activity,
  provenance:
    History,
  settings:
    Settings,
};


const SPLYCE_ENHANCEMENTS = [
  "deterministic instance overlays",
  "runtime schema validation",
  "authority-visible identity projection",

  "persistent developer workspace state",
  "cross-renderer state substrate",
  "selector-based reactive state",

  "stale-aware runtime synchronization",
  "background instance refresh",
  "request deduplication and caching",

  "interactive dependency topology",
  "keyboard-accessible graph navigation",
  "zoom pan fit and minimap controls",

  "recoverable interface boundaries",
  "component-level failure isolation",
  "explicit recovery surface",

  "nine-panel control grammar",
  "eighteen-stage pipeline inspection",
  "three-mode priority control",

  "capability search and filtering",
  "capability focus inspection",
  "reserved-capability visibility",

  "authority provenance inspector",
  "projection digest visibility",
  "non-authoritative projection signaling",

  "focus-mode workspace",
  "persistent density preferences",
  "reduced-motion enforcement",

  "command palette navigation",
  "numeric panel shortcuts",
  "developer hotkey grammar",

  "live interface telemetry",
  "runtime refresh control",
  "configuration export",

  "responsive topology workspace",
  "semantic health matrix",
  "semantic validation matrix",
] as const;


function statusTone(
  status: string,
): string {
  const value =
    status.toLowerCase();

  if (
    [
      "healthy",
      "ready",
      "passed",
      "accepted",
      "active",
    ].includes(
      value,
    )
  ) {
    return "positive";
  }

  if (
    [
      "provisional",
      "observed",
      "pending",
      "degraded",
    ].includes(
      value,
    )
  ) {
    return "warning";
  }

  if (
    [
      "failed",
      "blocked",
      "rejected",
      "error",
    ].includes(
      value,
    )
  ) {
    return "negative";
  }

  return "neutral";
}


async function fetchInstance():
Promise<InstanceConfig> {
  const response =
    await fetch(
      "/exile-ui.instance.json",
      {
        cache:
          "no-store",

        headers: {
          Accept:
            "application/json",
        },
      },
    );

  if (!response.ok) {
    throw new Error(
      "Splyce instance load failed: "
      + response.status,
    );
  }

  return InstanceSchema.parse(
    await response.json(),
  );
}


function StatusChip({
  status,
}: {
  status: string;
}) {
  return (
    <span
      className={
        "sp-status sp-status--"
        + statusTone(
          status,
        )
      }
    >
      <i />
      {status}
    </span>
  );
}


function Panel({
  eyebrow,
  title,
  action,
  children,
}: {
  eyebrow: string;
  title: string;
  action?: ReactNode;
  children: ReactNode;
}) {
  return (
    <motion.section
      className="sp-panel"
      initial={{
        opacity: 0,
        y: 10,
      }}
      animate={{
        opacity: 1,
        y: 0,
      }}
      transition={{
        duration: 0.28,
      }}
    >
      <header
        className=
          "sp-panel__header"
      >
        <div>
          <span
            className=
              "sp-eyebrow"
          >
            {eyebrow}
          </span>

          <h2>
            {title}
          </h2>
        </div>

        {action}
      </header>

      <div
        className=
          "sp-panel__body"
      >
        {children}
      </div>
    </motion.section>
  );
}


function Metric({
  value,
  label,
}: {
  value:
    string | number;
  label: string;
}) {
  return (
    <div
      className=
        "sp-metric"
    >
      <strong>
        {value}
      </strong>

      <span>
        {label}
      </span>
    </div>
  );
}


function Overview({
  config,
}: {
  config:
    InstanceConfig;
}) {
  const {
    priority,
    setPriority,
  } = useSplyce();

  return (
    <div
      className=
        "sp-grid sp-grid--overview"
    >
      <Panel
        eyebrow="Identity"
        title={config.name}
      >
        <div
          className=
            "sp-identity"
        >
          <div
            className=
              "sp-sigil"
          >
            {config.sigil}
          </div>

          <div>
            <strong>
              {
                config.designation
              }
            </strong>

            <p>
              {
                config.purposes.join(
                  " · ",
                )
              }
            </p>
          </div>
        </div>
      </Panel>

      <Panel
        eyebrow="Authority"
        title="Authority envelope"
      >
        <StatusChip
          status={
            config.authority.state
          }
        />

        <div
          className=
            "sp-confidence"
        >
          <span>
            confidence
          </span>

          <strong>
            {
              Math.round(
                config.authority
                  .confidence
                * 100,
              )
            }
            %
          </strong>

          <div>
            <motion.i
              initial={{
                scaleX: 0,
              }}
              animate={{
                scaleX:
                  config.authority
                    .confidence,
              }}
            />
          </div>
        </div>

        <code>
          {
            config.authority.source
          }
        </code>
      </Panel>

      <Panel
        eyebrow="Scyon"
        title="Operational surface"
      >
        <div
          className=
            "sp-metrics"
        >
          <Metric
            value={
              config.capabilities
                .length
            }
            label="capabilities"
          />

          <Metric
            value="18"
            label="stages"
          />

          <Metric
            value="9"
            label="panels"
          />
        </div>
      </Panel>

      <Panel
        eyebrow="Priority"
        title="Expansion mode"
      >
        <div
          className=
            "sp-priority"
        >
          {
            config.priority_modes
              .map(
                mode => (
                  <button
                    key={mode.id}
                    type="button"
                    data-active={
                      priority
                      === mode.id
                    }
                    onClick={() =>
                      setPriority(
                        mode.id,
                      )
                    }
                  >
                    <strong>
                      {
                        mode.label
                      }
                    </strong>

                    <span>
                      {
                        mode.description
                      }
                    </span>
                  </button>
                ),
              )
          }
        </div>
      </Panel>

      <Panel
        eyebrow="Assurance"
        title="Health projection"
      >
        <div
          className=
            "sp-metrics"
        >
          <Metric
            value={
              config.health
                .filter(
                  item =>
                    statusTone(
                      item.status,
                    )
                    === "positive",
                ).length
            }
            label="healthy"
          />

          <Metric
            value="9"
            label="dimensions"
          />

          <Metric
            value={
              config.validation
                .filter(
                  item =>
                    statusTone(
                      item.status,
                    )
                    === "positive",
                ).length
            }
            label="validated"
          />
        </div>
      </Panel>

      <Panel
        eyebrow="Splyce"
        title="Living interface substrate"
      >
        <div
          className=
            "sp-organism"
        >
          <i />
          <i />
          <i />
          <b />
        </div>
      </Panel>
    </div>
  );
}


function Capabilities({
  config,
}: {
  config:
    InstanceConfig;
}) {
  const {
    search,
    setSearch,
    selectedCapability,
    setSelectedCapability,
  } = useSplyce();

  const groups =
    useMemo(
      () =>
        [
          ...new Set(
            config.capabilities
              .map(
                item =>
                  item.group,
              ),
          ),
        ].sort(),
      [config.capabilities],
    );

  const [
    group,
    setGroup,
  ] = useState(
    "all",
  );

  const filtered =
    config.capabilities.filter(
      item => {
        const groupMatch =
          group === "all"
          || item.group === group;

        const query =
          search
            .trim()
            .toLowerCase();

        const searchMatch =
          !query
          || item.id
            .toLowerCase()
            .includes(query)
          || item.group
            .toLowerCase()
            .includes(query);

        return (
          groupMatch
          && searchMatch
        );
      },
    );

  return (
    <Panel
      eyebrow=
        "Capability registry"
      title=
        "Operational capabilities"
      action={
        <span
          className=
            "sp-count"
        >
          {filtered.length}
          /
          {
            config.capabilities
              .length
          }
        </span>
      }
    >
      <div
        className=
          "sp-searchbar"
      >
        <Search
          size={15}
        />

        <input
          value={search}
          onChange={
            event =>
              setSearch(
                event.target.value,
              )
          }
          placeholder=
            "Search capabilities"
        />
      </div>

      <div
        className=
          "sp-filter"
      >
        <button
          type="button"
          data-active={
            group === "all"
          }
          onClick={() =>
            setGroup(
              "all",
            )
          }
        >
          all
        </button>

        {
          groups.map(
            value => (
              <button
                key={value}
                type="button"
                data-active={
                  group === value
                }
                onClick={() =>
                  setGroup(
                    value,
                  )
                }
              >
                {value}
              </button>
            ),
          )
        }
      </div>

      <div
        className=
          "sp-capabilities"
      >
        {
          filtered.map(
            (
              capability,
              index,
            ) => (
              <button
                type="button"
                key={
                  capability.id
                }
                data-active={
                  selectedCapability
                  === capability.id
                }
                onClick={() =>
                  setSelectedCapability(
                    selectedCapability
                    === capability.id
                      ? null
                      : capability.id,
                  )
                }
              >
                <span>
                  {
                    String(
                      index + 1,
                    ).padStart(
                      2,
                      "0",
                    )
                  }
                </span>

                <Boxes
                  size={17}
                />

                <strong>
                  {
                    capability.id
                  }
                </strong>

                <small>
                  {
                    capability.group
                  }
                </small>

                <StatusChip
                  status={
                    capability.status
                  }
                />
              </button>
            ),
          )
        }
      </div>
    </Panel>
  );
}


function Pipeline({
  config,
}: {
  config:
    InstanceConfig;
}) {
  const {
    selectedStage,
    setSelectedStage,
  } = useSplyce();

  return (
    <Panel
      eyebrow=
        "Universal grammar"
      title=
        "18-stage execution pipeline"
      action={
        <span
          className=
            "sp-count"
        >
          6 × 3
        </span>
      }
    >
      <div
        className=
          "sp-pipeline"
      >
        {
          Array.from(
            {
              length: 6,
            },
            (
              _,
              phase,
            ) => (
              <section
                key={phase}
              >
                <header>
                  <span>
                    phase
                  </span>

                  <strong>
                    {
                      String(
                        phase + 1,
                      ).padStart(
                        2,
                        "0",
                      )
                    }
                  </strong>
                </header>

                {
                  config.pipeline
                    .slice(
                      phase * 3,
                      phase * 3 + 3,
                    )
                    .map(
                      (
                        stage,
                        offset,
                      ) => {
                        const index =
                          phase * 3
                          + offset;

                        return (
                          <button
                            key={
                              stage
                            }
                            type="button"
                            data-active={
                              index
                              ===
                              selectedStage
                            }
                            onClick={() =>
                              setSelectedStage(
                                index,
                              )
                            }
                          >
                            <span>
                              {
                                String(
                                  index + 1,
                                ).padStart(
                                  2,
                                  "0",
                                )
                              }
                            </span>

                            <strong>
                              {
                                stage
                                  .replaceAll(
                                    "_",
                                    " ",
                                  )
                              }
                            </strong>

                            <ChevronRight
                              size={13}
                            />
                          </button>
                        );
                      },
                    )
                }
              </section>
            ),
          )
        }
      </div>

      <div
        className=
          "sp-stage"
      >
        <span
          className=
            "sp-eyebrow"
        >
          Selected stage
        </span>

        <strong>
          {
            String(
              selectedStage + 1,
            ).padStart(
              2,
              "0",
            )
          }
          {" / "}
          {
            config.pipeline[
              selectedStage
            ].replaceAll(
              "_",
              " ",
            )
          }
        </strong>
      </div>
    </Panel>
  );
}


function topology(
  config:
    InstanceConfig,
): {
  nodes: Node[];
  edges: Edge[];
} {
  const nodes:
    Node[] = [
      {
        id:
          config.exile_id,

        position: {
          x: 0,
          y: 0,
        },

        data: {
          label:
            config.name,
        },

        type:
          "input",
      },
    ];

  const edges:
    Edge[] = [];

  config.purposes.forEach(
    (
      purpose,
      index,
    ) => {
      const id =
        "purpose:"
        + String(
          index + 1,
        );

      nodes.push({
        id,
        position: {
          x: 280,
          y:
            index * 140
            - 140,
        },
        data: {
          label:
            purpose,
        },
      });

      edges.push({
        id:
          config.exile_id
          + "->"
          + id,
        source:
          config.exile_id,
        target:
          id,
        animated:
          true,
      });
    },
  );

  config.capabilities.forEach(
    (
      capability,
      index,
    ) => {
      const purposeIndex =
        index % 3;

      const purposeId =
        "purpose:"
        + String(
          purposeIndex + 1,
        );

      const id =
        "capability:"
        + capability.id;

      nodes.push({
        id,
        position: {
          x:
            620
            + Math.floor(
              index / 9,
            ) * 250,

          y:
            (index % 9)
            * 76
            - 300,
        },
        data: {
          label:
            capability.id,
        },
      });

      edges.push({
        id:
          purposeId
          + "->"
          + id,
        source:
          purposeId,
        target:
          id,
      });
    },
  );

  return {
    nodes,
    edges,
  };
}


function FitButton() {
  const reactFlow =
    useReactFlow();

  return (
    <button
      className=
        "sp-flow-action"
      type="button"
      onClick={() =>
        reactFlow.fitView({
          duration: 500,
          padding: 0.18,
        })
      }
    >
      <Maximize2
        size={14}
      />

      fit
    </button>
  );
}


function Graph({
  config,
}: {
  config:
    InstanceConfig;
}) {
  const graph =
    useMemo(
      () =>
        topology(
          config,
        ),
      [config],
    );

  return (
    <Panel
      eyebrow="Graph"
      title="Interactive topology"
      action={
        <span
          className=
            "sp-count"
        >
          {
            graph.nodes.length
          }
          {" nodes"}
        </span>
      }
    >
      <div
        className=
          "sp-flow"
      >
        <ReactFlow
          nodes={graph.nodes}
          edges={graph.edges}
          fitView
          nodesDraggable
          nodesConnectable={
            false
          }
          elementsSelectable
          minZoom={0.15}
          maxZoom={2.5}
        >
          <Background
            variant={
              BackgroundVariant.Dots
            }
            gap={22}
            size={1}
          />

          <Controls
            showInteractive={
              false
            }
          />

          <MiniMap
            pannable
            zoomable
          />

          <FitButton />
        </ReactFlow>
      </div>
    </Panel>
  );
}


function Matrix({
  title,
  eyebrow,
  values,
}: {
  title: string;
  eyebrow: string;
  values:
    Array<{
      id: string;
      status: string;
    }>;
}) {
  return (
    <Panel
      eyebrow={eyebrow}
      title={title}
      action={
        <span
          className=
            "sp-count"
        >
          9
        </span>
      }
    >
      <div
        className=
          "sp-matrix"
      >
        {
          values.map(
            (
              item,
              index,
            ) => (
              <article
                key={item.id}
              >
                <span>
                  {
                    String(
                      index + 1,
                    ).padStart(
                      2,
                      "0",
                    )
                  }
                </span>

                <CheckCircle2
                  size={17}
                />

                <strong>
                  {
                    item.id
                      .replaceAll(
                        "_",
                        " ",
                      )
                  }
                </strong>

                <StatusChip
                  status={
                    item.status
                  }
                />
              </article>
            ),
          )
        }
      </div>
    </Panel>
  );
}


function ActivityPanel({
  config,
}: {
  config:
    InstanceConfig;
}) {
  const events = [
    "splyce.instantiated",
    "instance.loaded",
    "authority.projected",
    "capabilities.projected",
    "pipeline.bound",
    "health.projected",
    "validation.projected",
    "topology.derived",
    "interface.ready",
  ];

  return (
    <Panel
      eyebrow="Observatory"
      title="Living activity"
      action={
        <span
          className=
            "sp-count"
        >
          9
        </span>
      }
    >
      <div
        className=
          "sp-events"
      >
        {
          events.map(
            (
              event,
              index,
            ) => (
              <div
                key={event}
              >
                <span>
                  {
                    String(
                      index + 1,
                    ).padStart(
                      2,
                      "0",
                    )
                  }
                </span>

                <Activity
                  size={14}
                />

                <strong>
                  {event}
                </strong>

                <small>
                  {
                    config.exile_id
                  }
                </small>
              </div>
            ),
          )
        }
      </div>
    </Panel>
  );
}


function Provenance({
  config,
}: {
  config:
    InstanceConfig;
}) {
  const download =
    useCallback(
      () => {
        const blob =
          new Blob(
            [
              JSON.stringify(
                config,
                null,
                2,
              ),
            ],
            {
              type:
                "application/json",
            },
          );

        const url =
          URL.createObjectURL(
            blob,
          );

        const anchor =
          document.createElement(
            "a",
          );

        anchor.href =
          url;

        anchor.download =
          config.exile_id
            .replace(
              ":",
              "-",
            )
          + ".splyce.json";

        anchor.click();

        URL.revokeObjectURL(
          url,
        );
      },
      [config],
    );

  return (
    <Panel
      eyebrow="Provenance"
      title="Projection envelope"
      action={
        <button
          type="button"
          className=
            "sp-inline-action"
          onClick={download}
        >
          <Download
            size={14}
          />

          export
        </button>
      }
    >
      <dl
        className=
          "sp-definition"
      >
        <div>
          <dt>
            instance
          </dt>
          <dd>
            {
              config.instance_id
            }
          </dd>
        </div>

        <div>
          <dt>
            exile
          </dt>
          <dd>
            {
              config.exile_id
            }
          </dd>
        </div>

        <div>
          <dt>
            schema
          </dt>
          <dd>
            {
              config.schema
            }
          </dd>
        </div>

        <div>
          <dt>
            authority
          </dt>
          <dd>
            {
              config.authority.state
            }
          </dd>
        </div>

        <div>
          <dt>
            authority source
          </dt>
          <dd>
            {
              config.authority.source
            }
          </dd>
        </div>

        <div>
          <dt>
            authoritative UI
          </dt>
          <dd>
            {
              config.projection
                ?.authoritative
                ? "yes"
                : "no"
            }
          </dd>
        </div>

        <div>
          <dt>
            rebuildable
          </dt>
          <dd>
            {
              config.projection
                ?.rebuildable
                ? "yes"
                : "unknown"
            }
          </dd>
        </div>

        <div>
          <dt>
            projection digest
          </dt>
          <dd>
            {
              config
                .projection_digest
              ?? "unavailable"
            }
          </dd>
        </div>

        <div>
          <dt>
            capability source
          </dt>
          <dd>
            {
              config.projection
                ?.capability_source
              ?? "reserved projection"
            }
          </dd>
        </div>
      </dl>
    </Panel>
  );
}


function SettingsPanel() {
  const {
    focusMode,
    setFocusMode,
    reducedMotion,
    setReducedMotion,
    telemetry,
    setTelemetry,
    density,
    setDensity,
  } = useSplyce();

  return (
    <Panel
      eyebrow="Splyce"
      title=
        "Developer environment"
      action={
        <span
          className=
            "sp-count"
        >
          36
        </span>
      }
    >
      <div
        className=
          "sp-settings"
      >
        <button
          type="button"
          data-active={
            focusMode
          }
          onClick={() =>
            setFocusMode(
              !focusMode,
            )
          }
        >
          <Focus
            size={17}
          />
          focus mode
        </button>

        <button
          type="button"
          data-active={
            reducedMotion
          }
          onClick={() =>
            setReducedMotion(
              !reducedMotion,
            )
          }
        >
          <Sparkles
            size={17}
          />
          reduced motion
        </button>

        <button
          type="button"
          data-active={
            telemetry
          }
          onClick={() =>
            setTelemetry(
              !telemetry,
            )
          }
        >
          <Gauge
            size={17}
          />
          telemetry
        </button>

        <button
          type="button"
          data-active={
            density
            === "compact"
          }
          onClick={() =>
            setDensity(
              density
              === "compact"
                ? "comfortable"
                : "compact",
            )
          }
        >
          <PanelLeft
            size={17}
          />
          compact density
        </button>

        <button
          type="button"
          onClick={() => {
            useSplyce
              .persist
              .clearStorage();

            window.location.reload();
          }}
        >
          <RefreshCcw
            size={17}
          />
          reset persistence
        </button>
      </div>

      <div
        className=
          "sp-enhancements"
      >
        {
          SPLYCE_ENHANCEMENTS
            .map(
              (
                item,
                index,
              ) => (
                <span
                  key={item}
                >
                  {
                    String(
                      index + 1,
                    ).padStart(
                      2,
                      "0",
                    )
                  }
                  {" "}
                  {item}
                </span>
              ),
            )
        }
      </div>
    </Panel>
  );
}


function CommandPalette({
  config,
}: {
  config:
    InstanceConfig;
}) {
  const {
    commandOpen,
    setCommandOpen,
    setPanel,
  } = useSplyce();

  const [
    query,
    setQuery,
  ] = useState(
    "",
  );

  if (!commandOpen) {
    return null;
  }

  const commands =
    config.panels
      .map(
        panel => ({
          id: panel,
          label:
            "Open "
            + panel,
        }),
      )
      .filter(
        command =>
          command.label
            .toLowerCase()
            .includes(
              query
                .toLowerCase(),
            ),
      );

  return (
    <motion.div
      className=
        "sp-command-backdrop"
      initial={{
        opacity: 0,
      }}
      animate={{
        opacity: 1,
      }}
      onMouseDown={() =>
        setCommandOpen(
          false,
        )
      }
    >
      <motion.div
        className=
          "sp-command"
        initial={{
          y: -14,
          scale: 0.98,
        }}
        animate={{
          y: 0,
          scale: 1,
        }}
        onMouseDown={
          event =>
            event
              .stopPropagation()
        }
      >
        <header>
          <Command
            size={17}
          />

          <input
            autoFocus
            value={query}
            onChange={
              event =>
                setQuery(
                  event.target.value,
                )
            }
            placeholder=
              "Splyce command…"
          />

          <button
            type="button"
            onClick={() =>
              setCommandOpen(
                false,
              )
            }
          >
            <X
              size={15}
            />
          </button>
        </header>

        <div>
          {
            commands.map(
              (
                command,
                index,
              ) => (
                <button
                  key={
                    command.id
                  }
                  type="button"
                  onClick={() => {
                    setPanel(
                      command.id,
                    );

                    setCommandOpen(
                      false,
                    );
                  }}
                >
                  <span>
                    {
                      index + 1
                    }
                  </span>

                  <strong>
                    {
                      command.label
                    }
                  </strong>

                  <ChevronRight
                    size={14}
                  />
                </button>
              ),
            )
          }
        </div>
      </motion.div>
    </motion.div>
  );
}


function SplyceWorkspace({
  config,
  refreshing,
  refresh,
}: {
  config:
    InstanceConfig;
  refreshing:
    boolean;
  refresh:
    () => void;
}) {
  const {
    panel,
    setPanel,
    commandOpen,
    setCommandOpen,
    focusMode,
    reducedMotion,
    telemetry,
    density,
  } = useSplyce();

  const [
    clock,
    setClock,
  ] = useState(
    new Date(),
  );

  useEffect(
    () => {
      const timer =
        window.setInterval(
          () =>
            setClock(
              new Date(),
            ),
          1000,
        );

      return () =>
        window.clearInterval(
          timer,
        );
    },
    [],
  );

  useEffect(
    () => {
      document
        .documentElement
        .toggleAttribute(
          "data-splyce-focus",
          focusMode,
        );

      document
        .documentElement
        .toggleAttribute(
          "data-splyce-reduced-motion",
          reducedMotion,
        );

      document
        .documentElement
        .toggleAttribute(
          "data-splyce-telemetry",
          telemetry,
        );

      document
        .documentElement
        .setAttribute(
          "data-splyce-density",
          density,
        );
    },
    [
      focusMode,
      reducedMotion,
      telemetry,
      density,
    ],
  );

  useEffect(
    () => {
      const keydown =
        (
          event:
            KeyboardEvent,
        ) => {
          if (
            (
              event.metaKey
              || event.ctrlKey
            )
            && event.key
              .toLowerCase()
              === "k"
          ) {
            event.preventDefault();

            setCommandOpen(
              !commandOpen,
            );

            return;
          }

          if (
            event.key
            === "Escape"
          ) {
            setCommandOpen(
              false,
            );

            return;
          }

          const numeric =
            Number(
              event.key,
            );

          if (
            numeric >= 1
            && numeric <= 9
            && !event.metaKey
            && !event.ctrlKey
            && !event.altKey
          ) {
            const next =
              config.panels[
                numeric - 1
              ];

            if (next) {
              setPanel(
                next,
              );
            }
          }
        };

      window.addEventListener(
        "keydown",
        keydown,
      );

      return () =>
        window.removeEventListener(
          "keydown",
          keydown,
        );
    },
    [
      commandOpen,
      config.panels,
      setCommandOpen,
      setPanel,
    ],
  );

  let content:
    ReactNode;

  switch (panel) {
    case "overview":
      content =
        config.exile_id
        === "exile:urge"
          ? (
            <UrgeWorkbench
              config={config}
            />
          )
          : (
            <Overview
              config={config}
            />
          );
      break;

    case "capabilities":
      content =
        <Capabilities
          config={config}
        />;
      break;

    case "pipeline":
      content =
        <Pipeline
          config={config}
        />;
      break;

    case "graph":
      content =
        <Graph
          config={config}
        />;
      break;

    case "health":
      content =
        <Matrix
          eyebrow=
            "Introspection"
          title=
            "Health matrix"
          values={
            config.health
          }
        />;
      break;

    case "validation":
      content =
        <Matrix
          eyebrow="Assurance"
          title=
            "Validation matrix"
          values={
            config.validation
          }
        />;
      break;

    case "activity":
      content =
        <ActivityPanel
          config={config}
        />;
      break;

    case "provenance":
      content =
        <Provenance
          config={config}
        />;
      break;

    case "settings":
      content =
        <SettingsPanel />;
      break;

    default:
      content = null;
  }

  return (
    <div
      className="splyce"
      style={
        {
          "--sp-accent":
            config.accent.primary,
          "--sp-secondary":
            config.accent.secondary,
          "--sp-signal":
            config.accent.signal,
        } as CSSProperties
      }
    >
      <div
        className=
          "sp-atmosphere"
      >
        <div />
        <div />
        <div />
      </div>

      <aside
        className=
          "sp-dock"
      >
        <div
          className=
            "sp-mark"
        >
          <strong>
            S
          </strong>

          <span>
            PLYCE
          </span>
        </div>

        <nav>
          {
            config.panels.map(
              (
                item,
                index,
              ) => {
                const Icon =
                  PANEL_ICONS[
                    item
                  ]
                  ?? Braces;

                return (
                  <button
                    key={item}
                    type="button"
                    data-active={
                      panel === item
                    }
                    title={
                      String(
                        index + 1,
                      )
                      + ": "
                      + item
                    }
                    onClick={() =>
                      setPanel(
                        item,
                      )
                    }
                  >
                    <Icon
                      size={17}
                    />

                    <span>
                      {
                        index + 1
                      }
                    </span>
                  </button>
                );
              },
            )
          }
        </nav>

        <button
          className=
            "sp-command-button"
          type="button"
          onClick={() =>
            setCommandOpen(
              true,
            )
          }
        >
          <Command
            size={17}
          />

          <span>
            K
          </span>
        </button>
      </aside>

      <main
        className=
          "sp-main"
      >
        <header
          className=
            "sp-top"
        >
          <div>
            <span
              className=
                "sp-eyebrow"
            >
              SPLYCE /
              {" "}
              {
                config.exile_id
              }
            </span>

            <div
              className=
                "sp-title"
            >
              <h1>
                {
                  config.name
                }
              </h1>

              <span>
                /
              </span>

              <p>
                {
                  config.designation
                }
              </p>
            </div>
          </div>

          <div
            className=
              "sp-top__tools"
          >
            <StatusChip
              status={
                config.status
              }
            />

            <button
              type="button"
              onClick={refresh}
              disabled={
                refreshing
              }
            >
              <RefreshCcw
                size={14}
                className={
                  refreshing
                    ? "sp-spin"
                    : ""
                }
              />

              sync
            </button>

            <div>
              <Cpu
                size={14}
              />

              SCYON
            </div>

            <time>
              {
                clock
                  .toLocaleTimeString(
                    [],
                    {
                      hour12:
                        false,
                    },
                  )
              }
            </time>
          </div>
        </header>

        <div
          className=
            "sp-context"
        >
          <span>
            <strong>
              {
                config.capabilities
                  .length
              }
            </strong>
            capabilities
          </span>

          <span>
            <strong>
              18
            </strong>
            stages
          </span>

          <span>
            <strong>
              09
            </strong>
            panels
          </span>

          <span>
            <strong>
              36
            </strong>
            enhancements
          </span>

          <button
            type="button"
            onClick={() =>
              setCommandOpen(
                true,
              )
            }
          >
            <Search
              size={13}
            />

            command

            <kbd>
              ⌘K
            </kbd>
          </button>
        </div>

        <AnimatePresence
          mode="wait"
        >
          <motion.div
            key={panel}
            className=
              "sp-workspace"
            initial={{
              opacity: 0,
              filter:
                "blur(5px)",
              y: 6,
            }}
            animate={{
              opacity: 1,
              filter:
                "blur(0)",
              y: 0,
            }}
            exit={{
              opacity: 0,
              y: -4,
            }}
            transition={{
              duration:
                reducedMotion
                  ? 0
                  : 0.22,
            }}
          >
            {content}
          </motion.div>
        </AnimatePresence>
      </main>

      {
        telemetry && (
          <>
            <div
              className=
                "sp-telemetry sp-telemetry--left"
            >
              SAVANT /
              SPLYCE /
              LIVING UI
            </div>

            <div
              className=
                "sp-telemetry sp-telemetry--right"
            >
              {
                config.instance_id
              }
            </div>
          </>
        )
      }

      <CommandPalette
        config={config}
      />
    </div>
  );
}


export function Splyce() {
  const query =
    useQuery({
      queryKey: [
        "splyce",
        "active-instance",
      ],

      queryFn:
        fetchInstance,

      staleTime:
        5000,

      refetchInterval:
        15000,

      refetchOnWindowFocus:
        true,

      retry:
        2,
    });

  if (query.isPending) {
    return (
      <div
        className=
          "sp-boot"
      >
        <div
          className=
            "sp-boot__core"
        />

        <strong>
          SPLYCE
        </strong>

        <span>
          substantiating interface
        </span>
      </div>
    );
  }

  if (query.isError) {
    return (
      <div
        className=
          "sp-failure"
      >
        <ShieldCheck
          size={30}
        />

        <strong>
          Splyce failed closed.
        </strong>

        <p>
          {
            query.error
              instanceof Error
              ? query.error.message
              : "Unknown instance error"
          }
        </p>

        <button
          type="button"
          onClick={() =>
            query.refetch()
          }
        >
          <RefreshCcw
            size={14}
          />

          retry
        </button>
      </div>
    );
  }

  return (
    <ReactFlowProvider>
      <SplyceWorkspace
        config={query.data}
        refreshing={
          query.isFetching
        }
        refresh={() => {
          void query.refetch();
        }}
      />
    </ReactFlowProvider>
  );
}
