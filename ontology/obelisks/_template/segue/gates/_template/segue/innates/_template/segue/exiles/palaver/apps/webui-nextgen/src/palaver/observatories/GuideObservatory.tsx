import {
  BookOpen,
  Boxes,
  Clock,
  Database,
  GitBranch,
  Keyboard,
  MemoryStick,
  MessageSquareText,
  Network,
  Radar,
  Search,
  Shield,
  SquareTerminal,
  Workflow
} from "lucide-react"


const sections = [
  {
    icon: MessageSquareText,
    title: "palaver",
    signal: "conversation",
    body:
      "Use Palaver for conversation, development, implementation reasoning, current-work questions, error analysis, and coordination across Savant owners.",
    actions: [
      "ctrl/⌘ + / opens chat",
      "ctrl/⌘ + enter sends",
      "assistant code can be staged into terminal",
      "staging never auto-executes"
    ]
  },
  {
    icon: SquareTerminal,
    title: "terminal",
    signal: "human execution",
    body:
      "A real Ubuntu PTY. Human command authority remains with the operator. Select terminal output and send it directly into Palaver for analysis.",
    actions: [
      "ctrl/⌘ + ` opens terminal",
      "chat icon sends selected output to Palaver",
      "+ creates a new PTY session",
      "fullscreen isolates the shell"
    ]
  },
  {
    icon: Workflow,
    title: "chat + terminal",
    signal: "development mode",
    body:
      "Use the vertical split when discussing and executing work together. The divider is resizable and neither pane transfers execution authority to AI.",
    actions: [
      "ctrl/⌘ + shift + t toggles split",
      "drag divider to resize",
      "stage commands from chat",
      "review before pressing enter"
    ]
  },
  {
    icon: Shield,
    title: "authority",
    signal: "governing meaning",
    body:
      "Inspect source chains, trust state, conflicts, provenance, supersession, and whether something is proposed, accepted, canonical, or merely projected.",
    actions: [
      "use before authority-sensitive changes",
      "distinguish projection from authority",
      "inspect conflicts before reconciliation"
    ]
  },
  {
    icon: GitBranch,
    title: "lineage",
    signal: "origin and mutation",
    body:
      "Trace where an element came from, how it changed, what it inherited, what superseded it, and how it can be replayed or recovered.",
    actions: [
      "inspect origin",
      "inspect mutation",
      "inspect supersession",
      "inspect recovery path"
    ]
  },
  {
    icon: Network,
    title: "dependency",
    signal: "structural impact",
    body:
      "Inspect what depends on an element, what it depends upon, critical paths, fault lines, and possible breakage before structural changes.",
    actions: [
      "use before shared-interface changes",
      "identify critical dependents",
      "identify stability risks"
    ]
  },
  {
    icon: Boxes,
    title: "relations",
    signal: "semantic connection",
    body:
      "Inspect structural and semantic relationships without treating a graph visualization as authority.",
    actions: [
      "instance → owner",
      "task → implementation",
      "concept → canon",
      "file → dependent"
    ]
  },
  {
    icon: Clock,
    title: "timeline",
    signal: "temporal history",
    body:
      "Inspect introduction, mutation, supersession, restoration, replay, and other time-ordered states.",
    actions: [
      "find when something appeared",
      "compare historical states",
      "trace supersession"
    ]
  },
  {
    icon: Database,
    title: "repository",
    signal: "implementation terrain",
    body:
      "Inspect implementation files, modules, build surfaces, source topology, and repository structure. Filesystem presence alone does not establish authority.",
    actions: [
      "locate implementation",
      "inspect active source",
      "inspect module relationships"
    ]
  },
  {
    icon: MemoryStick,
    title: "memory",
    signal: "context ecology",
    body:
      "Inspect active, latent, dormant, and retrievable context associated with Scrybe and related memory projections.",
    actions: [
      "inspect active context",
      "locate durable memory",
      "inspect retrieval paths"
    ]
  },
  {
    icon: Search,
    title: "ontology",
    signal: "system geography",
    body:
      "Inspect where a concept belongs in Savant composition and how lower primitives compose into higher structures.",
    actions: [
      "locate ownership",
      "inspect edifice",
      "inspect composition",
      "inspect specialization"
    ]
  },
  {
    icon: Radar,
    title: "fields",
    signal: "structural pressure",
    body:
      "Inspect derived concentrations, distributions, pressures, and cross-system effects. Field output is a projection, not authority.",
    actions: [
      "inspect concentration",
      "inspect pressure",
      "inspect distribution"
    ]
  },
  {
    icon: Network,
    title: "graph",
    signal: "legacy projection",
    body:
      "Retained only as a secondary relational projection. Prefer Authority, Lineage, Dependency, Relations, and Ontology for normal work.",
    actions: [
      "do not treat topology as authority",
      "do not make graph UI the primary workflow"
    ]
  }
]


export default function GuideObservatory() {
  return (
    <section className="guide-observatory">
      <header className="guide-header">
        <div className="guide-title">
          <BookOpen size={18} />

          <div>
            <p>
              interface manual
            </p>

            <h1>
              palaver
            </h1>
          </div>
        </div>

        <div className="guide-shortcuts">
          <span>
            <Keyboard size={12} />
            ctrl/⌘ k · command
          </span>

          <span>
            ctrl/⌘ / · chat
          </span>

          <span>
            ctrl/⌘ ` · terminal
          </span>
        </div>
      </header>

      <div className="guide-grid">
        {sections.map(
          section => {
            const Icon =
              section.icon

            return (
              <article
                className="guide-card"
                key={section.title}
              >
                <header>
                  <div className="guide-card-icon">
                    <Icon size={16} />
                  </div>

                  <div>
                    <span>
                      {section.signal}
                    </span>

                    <h2>
                      {section.title}
                    </h2>
                  </div>
                </header>

                <p>
                  {section.body}
                </p>

                <div className="guide-actions">
                  {section.actions.map(
                    action => (
                      <div key={action}>
                        <i />
                        <span>
                          {action}
                        </span>
                      </div>
                    )
                  )}
                </div>
              </article>
            )
          }
        )}
      </div>
    </section>
  )
}
