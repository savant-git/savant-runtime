import {
  BookOpen,
  BrainCircuit,
  Braces,
  ChevronDown,
  ChevronRight,
  ClipboardList,
  File,
  Link2,
  MessageSquareText,
  Search,
  Server,
  SquareTerminal
} from "lucide-react"

import {
  useEffect,
  useMemo,
  useState
} from "react"

import {
  FileIndexEntry,
  repositoryEntries
} from "../lib/file-contract"

import {
  PalaverModule,
  useWorkspaceStore
} from "../state/workspace-store"


type Module = {
  id: PalaverModule
  label: string
  description: string
  icon: any
}


const modules:
  Module[] = [
    {
      id:
        "chat",

      label:
        "Palaver",

      description:
        "Talk, develop and solve problems",

      icon:
        MessageSquareText
    },

    {
      id:
        "terminal",

      label:
        "Terminal",

      description:
        "Run Ubuntu commands",

      icon:
        SquareTerminal
    },

    {
      id:
        "memory",

      label:
        "Memory",

      description:
        (
          "Find, understand and "
          + "control context"
        ),

      icon:
        BrainCircuit
    },

    {
      id:
        "kindred",

      label:
        "Kindred",

      description:
        (
          "Understand relationships, "
          + "ownership and impact"
        ),

      icon:
        Link2
    },

    {
      id:
        "source",

      label:
        "Files",

      description:
        (
          "Browse and inspect "
          + "readable source"
        ),

      icon:
        Braces
    },

    {
      id:
        "search",

      label:
        "Search",

      description:
        "Search across Palaver",

      icon:
        Search
    },

    {
      id:
        "work",

      label:
        "Work",

      description:
        (
          "See current tasks "
          + "and next actions"
        ),

      icon:
        ClipboardList
    },

    {
      id:
        "system",

      label:
        "System",

      description:
        "Check Palaver services",

      icon:
        Server
    },

    {
      id:
        "guide",

      label:
        "Help",

      description:
        "Learn Palaver",

      icon:
        BookOpen
    }
  ]


export default function ObservatoryRail() {
  const {
    active,
    setActive,
    openSource,
    setCommandOpen
  } = useWorkspaceStore()

  const [
    files,
    setFiles
  ] = useState<
    FileIndexEntry[]
  >([])

  const [
    filesOpen,
    setFilesOpen
  ] = useState(false)

  const [
    query,
    setQuery
  ] = useState("")


  useEffect(
    () => {
      let alive =
        true

      async function load() {
        try {
          const response =
            await fetch(
              "/api/repository/files",
              {
                cache:
                  "no-store"
              }
            )

          const text =
            await response.text()

          if (!alive) {
            return
          }

          let payload:
            unknown = {}

          try {
            payload =
              text
                ? JSON.parse(
                    text
                  )
                : {}
          } catch {
            payload = {}
          }

          setFiles(
            repositoryEntries(
              payload
            )
          )
        } catch {
          if (alive) {
            setFiles(
              []
            )
          }
        }
      }

      load()

      return () => {
        alive =
          false
      }
    },
    []
  )


  const visibleFiles =
    useMemo(
      () => {
        const terms =
          query
            .trim()
            .toLowerCase()
            .split(
              /\s+/
            )
            .filter(
              Boolean
            )

        const filtered =
          terms.length
          === 0
            ? files
            : files.filter(
                entry => {
                  const haystack =
                    (
                      `${entry.name} `
                      + entry.path
                    )
                      .toLowerCase()

                  return terms
                    .every(
                      term =>
                        haystack
                          .includes(
                            term
                          )
                    )
                }
              )

        return filtered
          .slice(
            0,
            500
          )
      },
      [
        files,
        query
      ]
    )


  return (
    <aside
      className={
        "rail workstation-rail"
      }
    >
      <div
        className="palaver-mark"
      >
        P
      </div>

      <button
        type="button"
        className="command-trigger"
        onClick={
          () =>
            setCommandOpen(
              true
            )
        }
      >
        command
      </button>

      <nav
        className="rail-nav"
      >
        <div
          className="rail-group"
        >
          <span
            className="rail-label"
          >
            palaver
          </span>

          {modules.map(
            module => {
              const Icon =
                module.icon

              return (
                <button
                  type="button"
                  key={
                    module.id
                  }
                  className={
                    active
                    === module.id
                      ? (
                        "rail-item "
                        + "active"
                      )
                      : "rail-item"
                  }
                  onClick={
                    () =>
                      setActive(
                        module.id
                      )
                  }
                  title={
                    module.description
                  }
                >
                  <Icon
                    size={16}
                  />

                  <span>
                    {module.label}
                  </span>
                </button>
              )
            }
          )}
        </div>

        <div
          className={
            "rail-file-section"
          }
        >
          <button
            type="button"
            className={
              "rail-files-heading"
            }
            onClick={
              () =>
                setFilesOpen(
                  value =>
                    !value
                )
            }
          >
            {filesOpen
              ? (
                <ChevronDown
                  size={12}
                />
              )
              : (
                <ChevronRight
                  size={12}
                />
              )}

            <span>
              all files
            </span>

            <b>
              {files.length}
            </b>
          </button>

          {filesOpen && (
            <>
              <label
                className={
                  "rail-file-search"
                }
              >
                <Search
                  size={11}
                />

                <input
                  value={query}
                  onChange={
                    event =>
                      setQuery(
                        event
                          .target
                          .value
                      )
                  }
                  placeholder={
                    "Find file"
                  }
                />
              </label>

              <div
                className={
                  "rail-file-list"
                }
              >
                {visibleFiles.map(
                  entry => (
                    <button
                      type="button"
                      key={
                        entry.path
                      }
                      onClick={
                        () =>
                          openSource(
                            entry.path
                          )
                      }
                      title={
                        entry.path
                      }
                    >
                      <File
                        size={11}
                      />

                      <span>
                        {entry.name}
                      </span>
                    </button>
                  )
                )}
              </div>
            </>
          )}
        </div>
      </nav>
    </aside>
  )
}
