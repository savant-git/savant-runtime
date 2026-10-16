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
  Paperclip,
  Search,
  Server,
  SquareTerminal
} from "lucide-react"

import {
  PalaverModule,
  useWorkspaceStore
} from "../state/workspace-store"


type Entry = {
  id: PalaverModule
  label: string
  icon: any
}


const tools:
  Entry[] = [
  {
    id:
      "chat",

    label:
      "Chat with Palaver",

    icon:
      MessageSquareText
  },

  {
    id:
      "terminal",

    label:
      "Open Terminal",

    icon:
      SquareTerminal
  },

  {
    id:
      "memory",

    label:
      "Browse Memory",

    icon:
      BrainCircuit
  },

  {
    id:
      "kindred",

    label:
      "Explore Kindred",

    icon:
      Link2
  },

  {
    id:
      "source",

    label:
      "Browse Files",

    icon:
      Braces
  },

  {
    id:
      "search",

    label:
      "Search Everything",

    icon:
      Search
  },

  {
    id:
      "uploads",

    label:
      "Upload Files",

    icon:
      Paperclip
  },

  {
    id:
      "work",

    label:
      "See Current Work",

    icon:
      ClipboardList
  },

  {
    id:
      "system",

    label:
      "Check System",

    icon:
      Server
  },

  {
    id:
      "guide",

    label:
      "Help",

    icon:
      BookOpen
  }
]


export default function CommandCenter() {
  const {
    commandOpen,
    setCommandOpen,
    setActive,
    toggleFocus,
    cycleDensity,
    toggleChatTerminalSplit
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
    setActive(value)
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
        className="command-center"
        onClick={
          event =>
            event
              .stopPropagation()
        }
      >
        <div className="command-kicker">
          palaver command
        </div>

        <Command.Input
          autoFocus
          placeholder="Open a tool or change the workspace…"
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
                    onSelect={() =>
                      open(
                        entry.id
                      )
                    }
                  >
                    <Icon
                      size={15}
                    />

                    {entry.label}
                  </Command.Item>
                )
              }
            )}
          </Command.Group>


          <Command.Group
            heading="layout"
          >
            <Command.Item
              onSelect={() => {
                toggleChatTerminalSplit()
                close()
              }}
            >
              <Columns2
                size={15}
              />

              Chat + Terminal Split
            </Command.Item>

            <Command.Item
              onSelect={() => {
                toggleFocus()
                close()
              }}
            >
              <Focus
                size={15}
              />

              Toggle Focus Mode
            </Command.Item>

            <Command.Item
              onSelect={() => {
                cycleDensity()
                close()
              }}
            >
              <Gauge
                size={15}
              />

              Change Interface Density
            </Command.Item>
          </Command.Group>
        </Command.List>


        <footer className="command-footer">
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
