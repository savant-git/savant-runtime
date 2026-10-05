import {
  Blocks,
  BrainCircuit,
  Camera,
  Check,
  Clipboard,
  FileSearch,
  Globe2,
  Image,
  Library,
  Mic,
  Paperclip,
  Search,
  Sparkles,
  SquareTerminal,
  WandSparkles
} from "lucide-react"

import {
  useMemo,
  useState
} from "react"


export type PalaverChatTool =
  | "files"
  | "image"
  | "camera"
  | "clipboard"
  | "create-image"
  | "plugins"
  | "web-search"
  | "deep-research"
  | "study"
  | "terminal"
  | "memory"
  | "source-search"
  | "voice"


export type CapabilityState =
  | "available"
  | "unavailable"
  | "installable"
  | "connecting"
  | "connected"
  | "permission-required"
  | "degraded"


export type PalaverCapability = {
  state:
    CapabilityState

  detail?:
    string
}


export type PalaverCapabilities = {
  createImage:
    PalaverCapability

  plugins:
    PalaverCapability

  web:
    PalaverCapability

  voice:
    PalaverCapability
}


type Props = {
  onTool: (
    tool:
      PalaverChatTool
  ) => void

  capabilities:
    PalaverCapabilities

  recentTools?:
    PalaverChatTool[]
}


type ToolDefinition = {
  id:
    PalaverChatTool

  group:
    "add"
    | "capabilities"
    | "workspace"

  label:
    string

  description:
    string

  icon:
    any

  capability?:
    keyof PalaverCapabilities

  keywords:
    string[]
}


const tools:
  ToolDefinition[] = [
    {
      id:
        "files",

      group:
        "add",

      label:
        "add files",

      description:
        "documents, text, code and local material",

      icon:
        Paperclip,

      keywords: [
        "file",
        "upload",
        "document",
        "attach"
      ]
    },

    {
      id:
        "image",

      group:
        "add",

      label:
        "add image",

      description:
        "choose an image from this device",

      icon:
        Image,

      keywords: [
        "image",
        "picture",
        "photo",
        "attach"
      ]
    },

    {
      id:
        "camera",

      group:
        "add",

      label:
        "take photo",

      description:
        "capture material directly from the camera",

      icon:
        Camera,

      keywords: [
        "camera",
        "photo",
        "capture"
      ]
    },

    {
      id:
        "clipboard",

      group:
        "add",

      label:
        "clipboard",

      description:
        "bring clipboard text in as attached context",

      icon:
        Clipboard,

      keywords: [
        "clipboard",
        "paste",
        "text"
      ]
    },

    {
      id:
        "create-image",

      group:
        "capabilities",

      label:
        "create image",

      description:
        "generate visual material from conversation",

      icon:
        WandSparkles,

      capability:
        "createImage",

      keywords: [
        "create",
        "generate",
        "image",
        "visual"
      ]
    },

    {
      id:
        "plugins",

      group:
        "capabilities",

      label:
        "plugins",

      description:
        "use installed Palaver-compatible capabilities",

      icon:
        Blocks,

      capability:
        "plugins",

      keywords: [
        "plugin",
        "app",
        "integration",
        "tool"
      ]
    },

    {
      id:
        "web-search",

      group:
        "capabilities",

      label:
        "web search",

      description:
        "retrieve current public-web information",

      icon:
        Globe2,

      capability:
        "web",

      keywords: [
        "web",
        "internet",
        "search",
        "current"
      ]
    },

    {
      id:
        "deep-research",

      group:
        "capabilities",

      label:
        "deep research",

      description:
        "extended source-grounded research workflow",

      icon:
        FileSearch,

      capability:
        "web",

      keywords: [
        "research",
        "sources",
        "deep",
        "web"
      ]
    },

    {
      id:
        "voice",

      group:
        "capabilities",

      label:
        "voice",

      description:
        "converse through an established voice runtime",

      icon:
        Mic,

      capability:
        "voice",

      keywords: [
        "voice",
        "audio",
        "speak",
        "microphone"
      ]
    },

    {
      id:
        "study",

      group:
        "workspace",

      label:
        "study",

      description:
        "switch Palaver into interactive teaching behavior",

      icon:
        Library,

      keywords: [
        "study",
        "learn",
        "teach"
      ]
    },

    {
      id:
        "terminal",

      group:
        "workspace",

      label:
        "terminal",

      description:
        "open the human command-authority terminal",

      icon:
        SquareTerminal,

      keywords: [
        "terminal",
        "shell",
        "ubuntu",
        "command"
      ]
    },

    {
      id:
        "memory",

      group:
        "workspace",

      label:
        "memory",

      description:
        "inspect and control Palaver context",

      icon:
        BrainCircuit,

      keywords: [
        "memory",
        "context",
        "scrybe"
      ]
    },

    {
      id:
        "source-search",

      group:
        "workspace",

      label:
        "source search",

      description:
        "search readable Savant source material",

      icon:
        Search,

      keywords: [
        "source",
        "search",
        "files",
        "repository"
      ]
    }
  ]


const capabilityLabels:
  Record<
    CapabilityState,
    string
  > = {
    available:
      "available",

    unavailable:
      "not connected",

    installable:
      "installable",

    connecting:
      "connecting",

    connected:
      "connected",

    "permission-required":
      "permission required",

    degraded:
      "degraded"
  }


function executable(
  state:
    CapabilityState
) {
  return (
    state === "available"
    || state === "connected"
  )
}


function sectionLabel(
  value:
    ToolDefinition["group"]
) {
  switch (
    value
  ) {
    case "add":
      return "add"

    case "capabilities":
      return "capabilities"

    case "workspace":
      return "workspace"
  }
}


export default function ChatToolMenu({
  onTool,
  capabilities,
  recentTools = []
}: Props) {
  const [
    query,
    setQuery
  ] = useState("")

  const normalized =
    query
      .trim()
      .toLowerCase()


  const visible =
    useMemo(
      () => {
        if (
          !normalized
        ) {
          return tools
        }

        return tools.filter(
          tool =>
            [
              tool.label,
              tool.description,
              ...tool.keywords
            ]
              .join(" ")
              .toLowerCase()
              .includes(
                normalized
              )
        )
      },
      [
        normalized
      ]
    )


  const ordered =
    useMemo(
      () => {
        if (
          normalized
          || recentTools.length
          === 0
        ) {
          return visible
        }

        const recent =
          new Map(
            recentTools.map(
              (
                id,
                index
              ) => [
                id,
                index
              ]
            )
          )

        return [
          ...visible
        ].sort(
          (
            a,
            b
          ) => {
            const ar =
              recent.get(
                a.id
              )

            const br =
              recent.get(
                b.id
              )

            if (
              ar !== undefined
              && br !== undefined
            ) {
              return ar - br
            }

            if (
              ar !== undefined
            ) {
              return -1
            }

            if (
              br !== undefined
            ) {
              return 1
            }

            return 0
          }
        )
      },
      [
        visible,
        recentTools,
        normalized
      ]
    )


  return (
    <div
      className={
        "palaver-tool-menu"
      }
      role="menu"
      aria-label={
        "Palaver tools"
      }
    >
      <label
        className={
          "palaver-tool-search"
        }
      >
        <Search
          size={14}
        />

        <input
          value={
            query
          }
          onChange={
            event =>
              setQuery(
                event
                  .target
                  .value
              )
          }
          placeholder={
            "Find a capability"
          }
          aria-label={
            "Find a Palaver capability"
          }
          autoFocus
        />
      </label>

      {(
        [
          "add",
          "capabilities",
          "workspace"
        ] as const
      ).map(
        group => {
          const entries =
            ordered.filter(
              tool =>
                tool.group
                === group
            )

          if (
            entries.length
            === 0
          ) {
            return null
          }

          return (
            <section
              key={
                group
              }
              className={
                "palaver-tool-group"
              }
            >
              <header>
                {sectionLabel(
                  group
                )}
              </header>

              {entries.map(
                tool => {
                  const Icon =
                    tool.icon

                  const capability =
                    tool.capability
                      ? capabilities[
                          tool.capability
                        ]
                      : null

                  const canRun =
                    capability
                      ? executable(
                          capability.state
                        )
                      : true

                  return (
                    <button
                      type="button"
                      role="menuitem"
                      key={
                        tool.id
                      }
                      className={
                        canRun
                          ? (
                            "palaver-tool-item"
                          )
                          : (
                            "palaver-tool-item "
                            + "capability-dormant"
                          )
                      }
                      onClick={
                        () =>
                          onTool(
                            tool.id
                          )
                      }
                      data-capability-state={
                        capability
                          ?.state
                        ?? "available"
                      }
                    >
                      <span
                        className={
                          "palaver-tool-icon"
                        }
                      >
                        <Icon
                          size={17}
                        />
                      </span>

                      <span
                        className={
                          "palaver-tool-copy"
                        }
                      >
                        <strong>
                          {tool.label}
                        </strong>

                        <small>
                          {tool.description}
                        </small>
                      </span>

                      {capability
                      && (
                        <span
                          className={
                            (
                              "palaver-capability-state "
                              + `state-${capability.state}`
                            )
                          }
                        >
                          {canRun
                            && (
                              <Check
                                size={10}
                              />
                            )}

                          {capabilityLabels[
                            capability.state
                          ]}
                        </span>
                      )}
                    </button>
                  )
                }
              )}
            </section>
          )
        }
      )}

      {visible.length
      === 0
      && (
        <div
          className={
            "palaver-tool-empty"
          }
        >
          <Sparkles
            size={15}
          />

          <span>
            no matching capability
          </span>
        </div>
      )}
    </div>
  )
}
