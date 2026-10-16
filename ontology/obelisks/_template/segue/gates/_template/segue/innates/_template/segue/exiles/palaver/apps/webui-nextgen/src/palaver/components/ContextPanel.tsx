import {
  Bot,
  CircleDot,
  Database,
  GitBranch,
  ShieldCheck,
  TerminalSquare
} from "lucide-react"

import {
  useWorkspaceStore
} from "../state/workspace-store"


const context:
  Record<string, string[]> = {
    chat: [
      "conversation · palaver",
      "persona · envoy",
      "execution · opus",
      "task · niche",
      "mutation · coda",
      "context · scrybe"
    ],

    terminal: [
      "surface · palaver",
      "authority · human",
      "shell · ubuntu",
      "mutation · coda",
      "transport · localhost",
      "execution · pty"
    ],

    authority: [
      "source chain",
      "trust level",
      "conflict state",
      "verification status"
    ],

    lineage: [
      "origin",
      "mutation",
      "inheritance",
      "supersession"
    ],

    dependency: [
      "critical path",
      "fault line",
      "collapse risk",
      "stability"
    ],

    relationship: [
      "strength",
      "resonance",
      "bridge",
      "echo"
    ],

    timeline: [
      "birth",
      "change",
      "recovery",
      "extinction"
    ],

    repository: [
      "source",
      "module gravity",
      "orphan risk",
      "build surface"
    ],

    memory: [
      "active",
      "latent",
      "dormant",
      "retrieval"
    ],

    ontology: [
      "domain",
      "cluster",
      "migration",
      "succession"
    ],

    fields: [
      "pressure",
      "distribution",
      "concentration",
      "change"
    ],

    graph: [
      "legacy relation view",
      "nodes",
      "edges",
      "projection"
    ]
  }


const icons = [
  Bot,
  ShieldCheck,
  GitBranch,
  Database,
  TerminalSquare,
  CircleDot
]


export default function ContextPanel() {
  const {
    active,
    density,
    focusMode
  } = useWorkspaceStore()

  const rows =
    context[active] || []

  return (
    <aside className="context-panel workstation-context">
      <div className="context-heading">
        <p>
          context field
        </p>

        <h2>
          {active}
        </h2>
      </div>

      <div className="context-stack">
        {rows.map(
          (row, index) => {
            const Icon =
              icons[
                index
                % icons.length
              ]

            return (
              <div
                className="context-row"
                key={row}
              >
                <div className="context-row-title">
                  <Icon size={12} />

                  <span>
                    {row}
                  </span>
                </div>

                <i />
              </div>
            )
          }
        )}
      </div>

      <div className="context-runtime">
        <div>
          <span>
            density
          </span>
          <b>
            {density}
          </b>
        </div>

        <div>
          <span>
            focus
          </span>
          <b>
            {focusMode
              ? "on"
              : "off"}
          </b>
        </div>

        <div>
          <span>
            authority
          </span>
          <b>
            projected
          </b>
        </div>
      </div>
    </aside>
  )
}
