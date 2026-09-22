import {
  Command
} from "cmdk"

import {
  BookOpen,
  BrainCircuit,
  Braces,
  ClipboardList,
  Columns2,
  Focus,
  Gauge,
  Link2,
  MessageSquareText,
  PanelLeft,
  PanelRight,
  RotateCcw,
  Search,
  Server,
  SquareTerminal
} from "lucide-react"

import {
  PalaverModule,
  WorkspacePreset,
  useWorkspaceStore
} from "../state/workspace-store"


type Entry = {
  id:
    PalaverModule

  label:
    string

  description:
    string

  icon:
    any
}


const tools:
  Entry[] = [
    {
      id:
        "chat",

      label:
        "Chat with Palaver",

      description:
        "Conversation workspace",

      icon:
        MessageSquareText
    },

    {
      id:
        "terminal",

      label:
        "Open Terminal",

      description:
        "Ubuntu execution surface",

      icon:
        SquareTerminal
    },

    {
      id:
        "memory",

      label:
        "Browse Memory",

      description:
        "Scrybe context projection",

      icon:
        BrainCircuit
    },

    {
      id:
        "kindred",

      label:
        "Explore Kindred",

      description:
        (
          "Relationships, ownership "
          + "and impact"
        ),

      icon:
        Link2
    },

    {
      id:
        "source",

      label:
        "Browse Files",

      description:
        "Source inspection surface",

      icon:
        Braces
    },

    {
      id:
        "search",

      label:
        "Search Everything",

      description:
        "Palaver search surface",

      icon:
        Search
    },

    {
      id:
        "work",

      label:
        "See Current Work",

      description:
        "Niche task projection",

      icon:
        ClipboardList
    },

    {
      id:
        "system",

      label:
        "Check System",

      description:
        "Runtime observability",

      icon:
        Server
    },

    {
      id:
        "guide",

      label:
        "Help",

      description:
        "Palaver guide",

      icon:
        BookOpen
    }
  ]


const presets:
  {
    id:
      WorkspacePreset

    label:
      string

    detail:
      string
  }[] = [
    {
      id:
        "conversation",

      label:
        "Conversation",

      detail:
        "Balanced Palaver workspace"
    },

    {
      id:
        "inference",

      label:
        "Inference",

      detail:
        "System and provider inspection"
    },

    {
      id:
        "context",

      label:
        "Context",

      detail:
        "Memory-centered inspection"
    },

    {
      id:
        "review",

      label:
        "Review",

      detail:
        "Source and mutation review"
    },

    {
      id:
        "inspection",

      label:
        "Deep Inspection",

      detail:
        "Relationship analysis"
    },

    {
      id:
        "focus",

      label:
        "Focus",

      detail:
        "Conversation without side rails"
    }
  ]


export default function CommandCenter() {
  const {
    commandOpen,
    setCommandOpen,
    setActive,
    toggleFocus,
    cycleDensity,
    toggleChatTerminalSplit,
    toggleLeftPanel,
    toggleRightPanel,
    applyWorkspacePreset,
    restoreWorkspace
  } = useWorkspaceStore()


  if (
    !commandOpen
  ) {
    return null
  }


  function close() {
    setCommandOpen(
      false
    )
  }


  function open(
    value:
      PalaverModule
  ) {
    setActive(
      value
    )

    close()
  }


  function preset(
    value:
      WorkspacePreset
  ) {
    applyWorkspacePreset(
      value
    )

    close()
  }


  return (
    <div
      className="command-backdrop"
      onClick={
        close
      }
    >
      <Command
        className={
          "command-center "
          + "savant-command-center"
        }
        onClick={
          event =>
            event
              .stopPropagation()
        }
      >
        <div
          className="command-kicker"
        >
          <span>
            palaver command
          </span>

          <b>
            operational index
          </b>
        </div>

        <Command.Input
          autoFocus
          placeholder={
            (
              "Open tools, switch "
              + "workspace, change layout…"
            )
          }
        />

        <Command.List>
          <Command.Empty>
            Nothing found.
          </Command.Empty>

          <Command.Group
            heading="tools"
          >
            {tools.map(
              entry => {
                const Icon =
                  entry.icon

                return (
                  <Command.Item
                    key={
                      entry.id
                    }
                    value={
                      (
                        entry.label
                        + " "
                        + entry.description
                      )
                    }
                    onSelect={
                      () =>
                        open(
                          entry.id
                        )
                    }
                  >
                    <Icon
                      size={15}
                    />

                    <div>
                      <strong>
                        {entry.label}
                      </strong>

                      <small>
                        {entry.description}
                      </small>
                    </div>
                  </Command.Item>
                )
              }
            )}
          </Command.Group>

          <Command.Group
            heading="workspaces"
          >
            {presets.map(
              entry => (
                <Command.Item
                  key={
                    entry.id
                  }
                  value={
                    (
                      entry.label
                      + " "
                      + entry.detail
                    )
                  }
                  onSelect={
                    () =>
                      preset(
                        entry.id
                      )
                  }
                >
                  <Columns2
                    size={15}
                  />

                  <div>
                    <strong>
                      {entry.label}
                    </strong>

                    <small>
                      {entry.detail}
                    </small>
                  </div>
                </Command.Item>
              )
            )}
          </Command.Group>

          <Command.Group
            heading="layout"
          >
            <Command.Item
              onSelect={
                () => {
                  toggleChatTerminalSplit()
                  close()
                }
              }
            >
              <Columns2
                size={15}
              />

              <div>
                <strong>
                  Chat + Terminal Split
                </strong>

                <small>
                  Dual operational surface
                </small>
              </div>
            </Command.Item>

            <Command.Item
              onSelect={
                () => {
                  toggleLeftPanel()
                  close()
                }
              }
            >
              <PanelLeft
                size={15}
              />

              <div>
                <strong>
                  Toggle Tool Rail
                </strong>

                <small>
                  Show or hide navigation
                </small>
              </div>
            </Command.Item>

            <Command.Item
              onSelect={
                () => {
                  toggleRightPanel()
                  close()
                }
              }
            >
              <PanelRight
                size={15}
              />

              <div>
                <strong>
                  Toggle Inspector
                </strong>

                <small>
                  Show or hide context
                </small>
              </div>
            </Command.Item>

            <Command.Item
              onSelect={
                () => {
                  toggleFocus()
                  close()
                }
              }
            >
              <Focus
                size={15}
              />

              <div>
                <strong>
                  Toggle Focus Mode
                </strong>

                <small>
                  Suppress peripheral chrome
                </small>
              </div>
            </Command.Item>

            <Command.Item
              onSelect={
                () => {
                  cycleDensity()
                  close()
                }
              }
            >
              <Gauge
                size={15}
              />

              <div>
                <strong>
                  Cycle Density
                </strong>

                <small>
                  Comfortable / compact / expert
                </small>
              </div>
            </Command.Item>

            <Command.Item
              onSelect={
                () => {
                  restoreWorkspace()
                  close()
                }
              }
            >
              <RotateCcw
                size={15}
              />

              <div>
                <strong>
                  Restore Workspace
                </strong>

                <small>
                  Reset local layout state
                </small>
              </div>
            </Command.Item>
          </Command.Group>
        </Command.List>

        <footer
          className="command-footer"
        >
          <span>
            ↑↓ move
          </span>

          <span>
            enter open
          </span>

          <span>
            esc close
          </span>

          <span>
            ctrl/⌘ k
          </span>
        </footer>
      </Command>
    </div>
  )
}
