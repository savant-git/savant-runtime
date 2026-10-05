export type ObservatoryKind =
  | "authority"
  | "lineage"
  | "dependency"
  | "relationship"
  | "timeline"
  | "repository"
  | "memory"
  | "ontology"
  | "fields"
  | "graph"


export type ObservatorySpec = {
  id: ObservatoryKind
  name: string
  instrument: string
  description: string
  verb: string
  sources: string[]
  lenses: string[]
  primaryKeys: string[]
  accent: string
}


export const observatorySpecs:
  Record<ObservatoryKind, ObservatorySpec> = {

  authority: {
    id: "authority",
    name: "authority chamber",
    instrument: "precedence resolver",
    description:
      "Interrogate governing sources, state, conflicts, provenance, supersession, registries and authority-bearing evidence without promoting projections into authority.",
    verb: "resolve",
    sources: [
      "/api/observatory/authority",
      "/api/authority/map",
      "/api/authority/contracts",
      "/api/authority/slots",
      "/api/authority/palaver",
      "/api/dashboard/state"
    ],
    lenses: [
      "governing",
      "conflict",
      "provenance",
      "supersession",
      "state",
      "all"
    ],
    primaryKeys: [
      "authority",
      "status",
      "state",
      "source",
      "provenance",
      "supersedes",
      "accepted",
      "canonical"
    ],
    accent: "gold"
  },

  lineage: {
    id: "lineage",
    name: "lineage loom",
    instrument: "ancestry reconstruction",
    description:
      "Reconstruct origin, ancestry, inheritance, mutation, supersession and recovery paths from lineage-bearing runtime projections.",
    verb: "trace",
    sources: [
      "/api/observatory/lineage",
      "/api/timeline",
      "/api/graph"
    ],
    lenses: [
      "origin",
      "ancestor",
      "mutation",
      "supersession",
      "recovery",
      "all"
    ],
    primaryKeys: [
      "lineage",
      "parent",
      "ancestor",
      "origin",
      "supersedes",
      "superseded_by",
      "history",
      "path"
    ],
    accent: "cyan"
  },

  dependency: {
    id: "dependency",
    name: "pressure map",
    instrument: "impact propagation",
    description:
      "Expose upstream requirements, downstream dependents, concentration, critical paths and structural pressure before implementation changes.",
    verb: "propagate",
    sources: [
      "/api/graph",
      "/api/tree",
      "/api/authority/relationships"
    ],
    lenses: [
      "upstream",
      "downstream",
      "critical",
      "shared",
      "isolated",
      "all"
    ],
    primaryKeys: [
      "dependency",
      "dependencies",
      "dependent",
      "dependents",
      "requires",
      "imports",
      "edges",
      "target"
    ],
    accent: "coral"
  },

  relationship: {
    id: "relationship",
    name: "resonance matrix",
    instrument: "relation interrogation",
    description:
      "Inspect typed semantic and structural connections while keeping relation data distinct from governing authority.",
    verb: "correlate",
    sources: [
      "/api/authority/relationships",
      "/api/graph"
    ],
    lenses: [
      "direct",
      "typed",
      "cross-domain",
      "reciprocal",
      "orphan",
      "all"
    ],
    primaryKeys: [
      "relationship",
      "relation",
      "source",
      "target",
      "type",
      "edge",
      "from",
      "to"
    ],
    accent: "violet"
  },

  timeline: {
    id: "timeline",
    name: "temporal strata",
    instrument: "state archaeology",
    description:
      "Traverse temporal layers, mutations and supersessions as ordered strata rather than a flat event list.",
    verb: "excavate",
    sources: [
      "/api/timeline",
      "/api/observatory/lineage"
    ],
    lenses: [
      "latest",
      "mutation",
      "supersession",
      "recovery",
      "historical",
      "all"
    ],
    primaryKeys: [
      "timestamp",
      "time",
      "date",
      "created",
      "updated",
      "mtime",
      "history",
      "event"
    ],
    accent: "amber"
  },

  repository: {
    id: "repository",
    name: "code terrain",
    instrument: "implementation cartography",
    description:
      "Navigate current implementation terrain, files, modules and build surfaces without confusing filesystem presence with authority.",
    verb: "survey",
    sources: [
      "/api/repository/files",
      "/api/tree"
    ],
    lenses: [
      "runtime",
      "frontend",
      "backend",
      "registry",
      "canon",
      "all"
    ],
    primaryKeys: [
      "path",
      "file",
      "name",
      "module",
      "size",
      "bytes",
      "mtime",
      "type"
    ],
    accent: "green"
  },

  memory: {
    id: "memory",
    name: "memory reservoir",
    instrument: "context retrieval",
    description:
      "Inspect stored and retrievable context, memory artifacts and durable context surfaces without representing retrieval as new authority.",
    verb: "retrieve",
    sources: [
      "/api/memory/files"
    ],
    lenses: [
      "active",
      "durable",
      "recent",
      "latent",
      "source",
      "all"
    ],
    primaryKeys: [
      "memory",
      "context",
      "path",
      "source",
      "updated",
      "created",
      "content",
      "title"
    ],
    accent: "blue"
  },

  ontology: {
    id: "ontology",
    name: "ontology atlas",
    instrument: "composition navigation",
    description:
      "Navigate Savant composition, identity placement, edifice and typed structural containment as addressable terrain.",
    verb: "locate",
    sources: [
      "/api/tree",
      "/api/graph",
      "/api/authority/slots"
    ],
    lenses: [
      "exile",
      "prodigal",
      "segue",
      "instance",
      "template",
      "all"
    ],
    primaryKeys: [
      "type",
      "kind",
      "class",
      "parent",
      "children",
      "path",
      "ontology",
      "identity"
    ],
    accent: "cyan"
  },

  fields: {
    id: "fields",
    name: "field weather",
    instrument: "structural climate",
    description:
      "Read structural-fields output as a derived climate: concentration, pressure, gradients and anomalous zones across the runtime.",
    verb: "measure",
    sources: [
      "/api/observatory/fields"
    ],
    lenses: [
      "pressure",
      "concentration",
      "gradient",
      "anomaly",
      "stable",
      "all"
    ],
    primaryKeys: [
      "field",
      "pressure",
      "density",
      "weight",
      "score",
      "concentration",
      "gradient",
      "strength"
    ],
    accent: "cyan"
  },

  graph: {
    id: "graph",
    name: "convergence lens",
    instrument: "relational projection",
    description:
      "A secondary compatibility view for runtime graph data. It emphasizes convergence, hubs and disconnected structures without restoring graph topology as the primary Palaver paradigm.",
    verb: "converge",
    sources: [
      "/api/graph"
    ],
    lenses: [
      "hub",
      "bridge",
      "isolated",
      "convergent",
      "divergent",
      "all"
    ],
    primaryKeys: [
      "node",
      "nodes",
      "edge",
      "edges",
      "source",
      "target",
      "id",
      "type"
    ],
    accent: "blue"
  }
}
