import {
  useEffect,
  useMemo,
  useState
} from "react"

import {
  BrainCircuit,
  Braces,
  ClipboardList,
  FileCode2,
  Link2,
  MessageSquareText,
  Search,
  X
} from "lucide-react"

import {
  repositoryEntries
} from "../lib/file-contract"

import {
  useWorkspaceStore
} from "../state/workspace-store"


type ResultType =
  | "file"
  | "memory"
  | "relationship"
  | "work"


type Result = {
  id: string
  type: ResultType
  title: string
  subtitle: string
  preview: string
  path?: string
  raw: unknown
}


function stringify(
  value: unknown
) {
  if (
    typeof value
    === "string"
  ) {
    return value
  }

  try {
    return JSON.stringify(
      value
    )
  } catch {
    return String(value)
  }
}


function flattenObjects(
  value: unknown,
  output:
    Record<string, unknown>[] = [],
  depth = 0
) {
  if (
    depth > 8
  ) {
    return output
  }

  if (
    Array.isArray(value)
  ) {
    value.forEach(
      item =>
        flattenObjects(
          item,
          output,
          depth + 1
        )
    )

    return output
  }

  if (
    value
    && typeof value
    === "object"
  ) {
    const record =
      value as
        Record<string, unknown>

    output.push(record)

    Object.values(record)
      .forEach(
        item => {
          if (
            item
            && typeof item
            === "object"
          ) {
            flattenObjects(
              item,
              output,
              depth + 1
            )
          }
        }
      )
  }

  return output
}


function first(
  record:
    Record<string, unknown>,
  keys: string[]
) {
  for (
    const key
    of keys
  ) {
    if (
      typeof record[key]
      === "string"
      && String(
        record[key]
      ).trim()
    ) {
      return String(
        record[key]
      ).trim()
    }
  }

  return ""
}


export default function SearchModule() {
  const {
    setActive,
    setComposerDraft,
    openSource,
    setLastActivity
  } = useWorkspaceStore()

  const [
    query,
    setQuery
  ] = useState("")

  const [
    files,
    setFiles
  ] = useState<Result[]>([])

  const [
    memory,
    setMemory
  ] = useState<Result[]>([])

  const [
    relationships,
    setRelationships
  ] = useState<Result[]>([])

  const [
    work,
    setWork
  ] = useState<Result[]>([])

  const [
    scope,
    setScope
  ] = useState<
    "all"
    | ResultType
  >("all")


  useEffect(() => {
    async function loadBase() {
      try {
        const [
          filesResponse,
          relationshipsResponse,
          workResponse
        ] =
          await Promise.all([
            fetch(
              "/api/repository/files",
              {
                cache:
                  "no-store"
              }
            ),

            fetch(
              "/api/authority/relationships",
              {
                cache:
                  "no-store"
              }
            ),

            fetch(
              "/api/dashboard/state",
              {
                cache:
                  "no-store"
              }
            )
          ])

        const filesPayload =
          await filesResponse.json()

        setFiles(
          repositoryEntries(
            filesPayload
          )
            .map(
              entry => ({
                id:
                  `file:${entry.path}`,

                type:
                  "file" as const,

                title:
                  entry.name,

                subtitle:
                  entry.path,

                preview:
                  "Readable source file",

                path:
                  entry.path,

                raw:
                  entry
              })
            )
        )


        const relationText =
          await relationshipsResponse.text()

        let relationPayload:
          unknown =
            relationText

        try {
          relationPayload =
            JSON.parse(
              relationText
            )
        } catch {
          relationPayload =
            relationText
        }

        const relationRows =
          flattenObjects(
            relationPayload
          )

        setRelationships(
          relationRows
            .map(
              (
                record,
                index
              ) => {
                const source =
                  first(
                    record,
                    [
                      "source",
                      "from",
                      "parent",
                      "owner"
                    ]
                  )

                const target =
                  first(
                    record,
                    [
                      "target",
                      "to",
                      "child",
                      "dependent"
                    ]
                  )

                const type =
                  first(
                    record,
                    [
                      "type",
                      "relation",
                      "relationship"
                    ]
                  )
                  || "relationship"

                if (
                  !source
                  || !target
                ) {
                  return null
                }

                return {
                  id:
                    `relationship:${index}:${source}:${target}`,

                  type:
                    "relationship" as const,

                  title:
                    `${source} → ${target}`,

                  subtitle:
                    type,

                  preview:
                    stringify(
                      record
                    ).slice(
                      0,
                      260
                    ),

                  raw:
                    record
                }
              }
            )
            .filter(
              (
                item
              ): item is Result =>
                item !== null
            )
        )


        const workPayload =
          await workResponse.json()

        setWork(
          flattenObjects(
            workPayload
          )
            .map(
              (
                record,
                index
              ) => {
                const title =
                  first(
                    record,
                    [
                      "title",
                      "task",
                      "name",
                      "id"
                    ]
                  )

                if (!title) {
                  return null
                }

                return {
                  id:
                    `work:${index}:${title}`,

                  type:
                    "work" as const,

                  title,

                  subtitle:
                    first(
                      record,
                      [
                        "status",
                        "state",
                        "priority",
                        "owner"
                      ]
                    )
                    || "work",

                  preview:
                    stringify(
                      record
                    ).slice(
                      0,
                      260
                    ),

                  raw:
                    record
                }
              }
            )
            .filter(
              (
                item
              ): item is Result =>
                item !== null
            )
        )
      } catch {
        // Individual scopes can still be searched.
      }
    }

    loadBase()
  }, [])


  useEffect(() => {
    const term =
      query.trim()

    if (
      term.length < 2
    ) {
      setMemory([])
      return
    }

    const controller =
      new AbortController()

    const timeout =
      window.setTimeout(
        async () => {
          try {
            const response =
              await fetch(
                `/api/memory/search?q=${encodeURIComponent(term)}`,
                {
                  cache:
                    "no-store",

                  signal:
                    controller.signal
                }
              )

            const payload =
              await response.json()

            const rows =
              Array.isArray(
                payload.results
              )
                ? payload.results
                : []

            setMemory(
              rows.map(
                (
                  row: any,
                  index: number
                ) => ({
                  id:
                    `memory:${index}:${row.path ?? ""}`,

                  type:
                    "memory" as const,

                  title:
                    String(
                      row.path
                      ?? "memory"
                    )
                      .split("/")
                      .pop()
                    || "memory",

                  subtitle:
                    String(
                      row.path
                      ?? ""
                    ),

                  preview:
                    String(
                      row.preview
                      ?? ""
                    ),

                  path:
                    typeof row.path
                    === "string"
                      ? row.path
                      : undefined,

                  raw:
                    row
                })
              )
            )
          } catch {
            if (
              !controller
                .signal
                .aborted
            ) {
              setMemory([])
            }
          }
        },
        220
      )

    return () => {
      window.clearTimeout(
        timeout
      )

      controller.abort()
    }
  }, [
    query
  ])


  const results =
    useMemo(
      () => {
        const term =
          query
            .trim()
            .toLowerCase()

        if (
          term.length < 2
        ) {
          return []
        }

        const all = [
          ...files,
          ...memory,
          ...relationships,
          ...work
        ]

        return all
          .filter(
            result =>
              (
                scope === "all"
                || result.type
                === scope
              )
              && [
                result.title,
                result.subtitle,
                result.preview
              ]
                .join(" ")
                .toLowerCase()
                .includes(term)
          )
          .slice(
            0,
            300
          )
      },
      [
        files,
        memory,
        relationships,
        work,
        query,
        scope
      ]
    )


  function open(
    result: Result
  ) {
    if (
      result.type
      === "file"
      && result.path
    ) {
      openSource(
        result.path
      )

      return
    }

    if (
      result.type
      === "memory"
    ) {
      setActive(
        "memory"
      )

      return
    }

    if (
      result.type
      === "relationship"
    ) {
      setActive(
        "kindred"
      )

      return
    }

    if (
      result.type
      === "work"
    ) {
      setActive(
        "work"
      )
    }
  }


  function ask(
    result: Result
  ) {
    setComposerDraft(
      [
        "Help me understand this Palaver search result.",
        `type: ${result.type}`,
        `title: ${result.title}`,
        `source: ${result.subtitle}`,
        "",
        stringify(
          result.raw
        )
      ].join("\n")
    )

    setActive(
      "chat"
    )

    setLastActivity(
      `search result attached to palaver`
    )
  }


  function icon(
    type: ResultType
  ) {
    switch (type) {
      case "file":
        return (
          <Braces
            size={15}
          />
        )

      case "memory":
        return (
          <BrainCircuit
            size={15}
          />
        )

      case "relationship":
        return (
          <Link2
            size={15}
          />
        )

      case "work":
        return (
          <ClipboardList
            size={15}
          />
        )
    }
  }


  return (
    <section className="universal-search">
      <header>
        <span>
          find anything palaver can currently see
        </span>

        <h1>
          search
        </h1>

        <p>
          Search readable files, memory, work and Kindred relationships from one place.
        </p>
      </header>


      <div className="universal-search-box">
        <Search
          size={18}
        />

        <input
          autoFocus
          value={query}
          onChange={
            event =>
              setQuery(
                event.target.value
              )
          }
          placeholder="Search Savant files, memory, work or relationships…"
        />

        {query && (
          <button
            type="button"
            onClick={() =>
              setQuery("")
            }
          >
            <X
              size={15}
            />
          </button>
        )}
      </div>


      <nav className="search-scopes">
        {[
          [
            "all",
            "Everything"
          ],
          [
            "file",
            "Files"
          ],
          [
            "memory",
            "Memory"
          ],
          [
            "relationship",
            "Kindred"
          ],
          [
            "work",
            "Work"
          ]
        ].map(
          ([
            value,
            label
          ]) => (
            <button
              type="button"
              key={value}
              className={
                scope === value
                  ? "active"
                  : ""
              }
              onClick={() =>
                setScope(
                  value as
                    "all"
                    | ResultType
                )
              }
            >
              {label}
            </button>
          )
        )}
      </nav>


      <div className="search-results">
        {query.trim().length < 2
          ? (
            <div className="search-empty">
              <Search
                size={28}
              />

              Type at least two characters.
            </div>
          )
          : results.length === 0
            ? (
              <div className="search-empty">
                Nothing matching this search is currently exposed.
              </div>
            )
            : results.map(
                result => (
                  <article
                    key={
                      result.id
                    }
                  >
                    <button
                      type="button"
                      className="search-result-main"
                      onClick={() =>
                        open(result)
                      }
                    >
                      <div className="search-result-icon">
                        {icon(
                          result.type
                        )}
                      </div>

                      <div>
                        <span>
                          {result.type}
                        </span>

                        <strong>
                          {result.title}
                        </strong>

                        <small>
                          {result.subtitle}
                        </small>

                        {result.preview && (
                          <p>
                            {result.preview}
                          </p>
                        )}
                      </div>
                    </button>

                    <button
                      type="button"
                      className="search-ask"
                      onClick={() =>
                        ask(result)
                      }
                      title="Ask Palaver about this"
                    >
                      <MessageSquareText
                        size={14}
                      />
                    </button>
                  </article>
                )
              )}
      </div>
    </section>
  )
}
