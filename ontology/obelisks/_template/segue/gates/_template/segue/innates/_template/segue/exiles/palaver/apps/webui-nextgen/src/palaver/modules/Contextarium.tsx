import {
  useEffect,
  useMemo,
  useState
} from "react"

import {
  AnimatePresence,
  motion
} from "framer-motion"

import {
  Boxes,
  ChevronRight,
  CircleDot,
  Database,
  FileText,
  Filter,
  GitBranch,
  Layers3,
  MessageSquareText,
  Network,
  Orbit,
  Search,
  Sparkles,
  X
} from "lucide-react"

import {
  useWorkspaceStore
} from "../state/workspace-store"


type MemoryItem = {
  id: string
  path: string
  source: string
  title: string
  text: string
  tokens: string[]
  depth: number
  raw: unknown
}


type Link = {
  left: string
  right: string
  score: number
  terms: string[]
}


type Mode =
  | "organize"
  | "connections"
  | "inspect"
  | "chat-context"


function hash(
  input: string
) {
  let value = 2166136261

  for (
    let index = 0;
    index < input.length;
    index += 1
  ) {
    value ^=
      input.charCodeAt(index)

    value =
      Math.imul(
        value,
        16777619
      )
  }

  return (
    value >>> 0
  ).toString(16)
}


function words(
  text: string
) {
  const stop =
    new Set([
      "the",
      "and",
      "that",
      "this",
      "with",
      "from",
      "for",
      "into",
      "are",
      "was",
      "were",
      "has",
      "have",
      "not",
      "but",
      "its",
      "their",
      "then",
      "than",
      "when",
      "where",
      "which",
      "what",
      "all",
      "can"
    ])

  return [
    ...new Set(
      text
        .toLowerCase()
        .match(
          /[a-z0-9_./:-]{4,}/g
        )
        ?.filter(
          token =>
            !stop.has(token)
        )
        ?? []
    )
  ].slice(
    0,
    160
  )
}


function label(
  value: unknown,
  fallback: string
) {
  if (
    value
    && typeof value
    === "object"
    && !Array.isArray(value)
  ) {
    const record =
      value as
        Record<string, unknown>

    for (
      const key
      of [
        "title",
        "name",
        "id",
        "path",
        "subject"
      ]
    ) {
      if (
        typeof record[key]
        === "string"
      ) {
        return String(
          record[key]
        )
      }
    }
  }

  return fallback
}


function flatten(
  source: string,
  value: unknown,
  path = "$",
  depth = 0,
  result: MemoryItem[] = []
) {
  if (depth > 10) {
    return result
  }

  let text = ""

  try {
    text =
      typeof value
      === "string"
        ? value
        : JSON.stringify(value)
  } catch {
    text =
      String(value)
  }

  if (
    text.length > 12
  ) {
    result.push({
      id:
        hash(
          `${source}:${path}:${text}`
        ),

      path,
      source,

      title:
        label(
          value,
          path.split(".").at(-1)
          ?? path
        ),

      text:
        text.slice(
          0,
          24000
        ),

      tokens:
        words(text),

      depth,
      raw: value
    })
  }

  if (
    Array.isArray(value)
  ) {
    value.forEach(
      (
        item,
        index
      ) =>
        flatten(
          source,
          item,
          `${path}[${index}]`,
          depth + 1,
          result
        )
    )
  } else if (
    value
    && typeof value
    === "object"
  ) {
    Object.entries(value)
      .forEach(
        ([
          key,
          item
        ]) => {
          if (
            item
            && typeof item
            === "object"
          ) {
            flatten(
              source,
              item,
              `${path}.${key}`,
              depth + 1,
              result
            )
          }
        }
      )
  }

  return result
}


function similarity(
  a: MemoryItem,
  b: MemoryItem
): Link | null {
  const left =
    new Set(a.tokens)

  const shared =
    b.tokens.filter(
      token =>
        left.has(token)
    )

  if (
    shared.length < 2
  ) {
    return null
  }

  const denominator =
    Math.max(
      Math.min(
        a.tokens.length,
        b.tokens.length
      ),
      1
    )

  const score =
    shared.length
    / denominator

  if (
    score < .08
  ) {
    return null
  }

  return {
    left:
      a.id,

    right:
      b.id,

    score,

    terms:
      shared.slice(
        0,
        12
      )
  }
}


function isMemoryItem(
  value:
    MemoryItem | undefined
): value is MemoryItem {
  return value !== undefined
}


export default function Contextarium() {
  const {
    setActive,
    setComposerDraft,
    setLastActivity
  } = useWorkspaceStore()

  const [
    items,
    setItems
  ] = useState<
    MemoryItem[]
  >([])

  const [
    loading,
    setLoading
  ] = useState(true)

  const [
    query,
    setQuery
  ] = useState("")

  const [
    mode,
    setMode
  ] = useState<Mode>(
    "organize"
  )

  const [
    selected,
    setSelected
  ] = useState<
    string | null
  >(null)

  const [
    capsule,
    setCapsule
  ] = useState<
    string[]
  >([])


  useEffect(() => {
    let alive = true

    async function load() {
      setLoading(true)

      const endpoints = [
        "/api/memory/files",
        "/api/tree",
        "/api/authority/relationships"
      ]

      const loaded:
        MemoryItem[] = []

      for (
        const endpoint
        of endpoints
      ) {
        try {
          const response =
            await fetch(
              endpoint,
              {
                cache:
                  "no-store"
              }
            )

          const text =
            await response.text()

          let value:
            unknown = text

          try {
            value =
              JSON.parse(text)
          } catch {
            value =
              text
          }

          if (
            response.ok
          ) {
            flatten(
              endpoint,
              value,
              "$",
              0,
              loaded
            )
          }
        } catch {
          // Individual memory sources
          // may be temporarily unavailable.
        }
      }

      if (!alive) {
        return
      }

      const unique =
        new Map<
          string,
          MemoryItem
        >()

      loaded.forEach(
        item =>
          unique.set(
            item.id,
            item
          )
      )

      setItems([
        ...unique.values()
      ])

      setLoading(false)

      setLastActivity(
        "memory organized"
      )
    }

    load()

    return () => {
      alive = false
    }
  }, [
    setLastActivity
  ])


  const links =
    useMemo(
      () => {
        const ranked =
          items
            .filter(
              item =>
                item.tokens.length
                >= 2
            )
            .slice(
              0,
              180
            )

        const result:
          Link[] = []

        for (
          let left = 0;
          left < ranked.length;
          left += 1
        ) {
          for (
            let right =
              left + 1;
            right < ranked.length;
            right += 1
          ) {
            const link =
              similarity(
                ranked[left],
                ranked[right]
              )

            if (link) {
              result.push(link)
            }
          }
        }

        return result
          .sort(
            (a, b) =>
              b.score
              - a.score
          )
          .slice(
            0,
            400
          )
      },
      [items]
    )


  const filtered =
    useMemo(
      () => {
        const terms =
          words(query)

        if (
          terms.length === 0
        ) {
          return items
        }

        return items.filter(
          item => {
            const haystack =
              [
                item.title,
                item.path,
                item.source,
                item.text
              ]
                .join(" ")
                .toLowerCase()

            return terms.every(
              term =>
                haystack.includes(
                  term
                )
            )
          }
        )
      },
      [
        items,
        query
      ]
    )


  const selectedItem =
    items.find(
      item =>
        item.id
        === selected
    )
    ?? null


  const neighborhood =
    useMemo(
      () => {
        if (!selected) {
          return []
        }

        return links
          .filter(
            link =>
              link.left
              === selected
              || link.right
              === selected
          )
          .map(
            link => {
              const target =
                link.left
                === selected
                  ? link.right
                  : link.left

              return {
                link,

                item:
                  items.find(
                    candidate =>
                      candidate.id
                      === target
                  )
              }
            }
          )
          .filter(
            (
              entry
            ): entry is {
              link: Link
              item: MemoryItem
            } =>
              entry.item
              !== undefined
          )
      },
      [
        items,
        links,
        selected
      ]
    )


  function toggleContext(
    id: string
  ) {
    setCapsule(
      current =>
        current.includes(id)
          ? current.filter(
              item =>
                item !== id
            )
          : [
              ...current,
              id
            ].slice(
              -20
            )
    )
  }


  function useContextInChat() {
    const selectedItems:
      MemoryItem[] =
        capsule
          .map(
            id =>
              items.find(
                item =>
                  item.id
                  === id
              )
          )
          .filter(
            isMemoryItem
          )

    if (
      selectedItems.length
      === 0
    ) {
      return
    }

    const packet =
      selectedItems
        .map(
          (
            item,
            index
          ) =>
            [
              `context ${index + 1}`,
              `source: ${item.source}`,
              `path: ${item.path}`,
              `title: ${item.title}`,
              item.text.slice(
                0,
                5000
              )
            ].join("\n")
        )
        .join(
          "\n\n---\n\n"
        )

    setComposerDraft(
      [
        "Use the following selected memory as working context.",
        "Preserve provenance and authority distinctions.",
        "",
        packet
      ].join("\n")
    )

    setActive("chat")

    setLastActivity(
      "selected memory sent to palaver"
    )
  }


  return (
    <section className="contextarium">
      <header className="contextarium-header">
        <div className="contextarium-brand">
          <div className="contextarium-core">
            <Orbit size={21} />
            <i />
            <b />
          </div>

          <div>
            <span>
              persistent context organizer
            </span>

            <h1>
              memory
            </h1>

            <p>
              Everything Palaver remembers, organized so you can find it, understand how it connects, and choose exactly what context to use.
            </p>
          </div>
        </div>


        <div className="contextarium-metrics">
          <div>
            <b>
              {items.length}
            </b>

            <span>
              memories
            </span>
          </div>

          <div>
            <b>
              {links.length}
            </b>

            <span>
              connections
            </span>
          </div>

          <div>
            <b>
              {capsule.length}
            </b>

            <span>
              selected
            </span>
          </div>
        </div>
      </header>


      <div className="contextarium-controls">
        <label>
          <Search size={14} />

          <input
            value={query}
            onChange={
              event =>
                setQuery(
                  event.target.value
                )
            }
            placeholder="Search everything Palaver remembers…"
          />

          {query && (
            <button
              type="button"
              onClick={() =>
                setQuery("")
              }
              title="Clear search"
            >
              <X size={13} />
            </button>
          )}
        </label>


        <nav>
          <button
            type="button"
            className={
              mode === "organize"
                ? "active"
                : ""
            }
            onClick={() =>
              setMode(
                "organize"
              )
            }
            title="Browse memory grouped by source and edifice"
          >
            <GitBranch
              size={13}
            />

            organize
          </button>


          <button
            type="button"
            className={
              mode === "connections"
                ? "active"
                : ""
            }
            onClick={() =>
              setMode(
                "connections"
              )
            }
            title="See memories that appear related"
          >
            <Network
              size={13}
            />

            connections
          </button>


          <button
            type="button"
            className={
              mode === "inspect"
                ? "active"
                : ""
            }
            onClick={() =>
              setMode(
                "inspect"
              )
            }
            title="Inspect one memory and everything connected to it"
          >
            <CircleDot
              size={13}
            />

            inspect
          </button>


          <button
            type="button"
            className={
              mode
              === "chat-context"
                ? "active"
                : ""
            }
            onClick={() =>
              setMode(
                "chat-context"
              )
            }
            title="Choose exactly what memory Palaver should use"
          >
            <Boxes
              size={13}
            />

            use in chat
          </button>
        </nav>
      </div>


      <main className="contextarium-stage">
        <section className="memory-stream">
          <header>
            <span>
              {loading
                ? "loading memory"
                : `${filtered.length} memories`}
            </span>

            <Filter
              size={13}
            />
          </header>


          <div>
            <AnimatePresence
              initial={false}
            >
              {filtered
                .slice(
                  0,
                  600
                )
                .map(
                  item => (
                    <motion.button
                      type="button"
                      key={item.id}
                      className={
                        [
                          "memory-cell",

                          selected
                          === item.id
                            ? "selected"
                            : "",

                          capsule.includes(
                            item.id
                          )
                            ? "captured"
                            : ""
                        ]
                          .filter(Boolean)
                          .join(" ")
                      }
                      onClick={() => {
                        setSelected(
                          item.id
                        )

                        setMode(
                          "inspect"
                        )
                      }}
                      initial={{
                        opacity: 0,
                        x: -5
                      }}
                      animate={{
                        opacity: 1,
                        x: 0
                      }}
                    >
                      <FileText
                        size={13}
                      />

                      <div>
                        <strong>
                          {item.title}
                        </strong>

                        <span>
                          {item.path}
                        </span>
                      </div>

                      <ChevronRight
                        size={12}
                      />
                    </motion.button>
                  )
                )}
            </AnimatePresence>
          </div>
        </section>


        <section className="contextarium-canvas">
          {mode === "organize" && (
            <div className="memory-forest">
              <header>
                <GitBranch
                  size={16}
                />

                <div>
                  <span>
                    organized memory
                  </span>

                  <h2>
                    grouped by source and edifice
                  </h2>
                </div>
              </header>


              <div className="forest-columns">
                {[
                  ...new Set(
                    filtered.map(
                      item =>
                        item.source
                    )
                  )
                ]
                  .slice(
                    0,
                    12
                  )
                  .map(
                    source => (
                      <article
                        key={source}
                      >
                        <header>
                          <Database
                            size={13}
                          />

                          <strong>
                            {source
                              .replace(
                                "/api/",
                                ""
                              )}
                          </strong>
                        </header>


                        {filtered
                          .filter(
                            item =>
                              item.source
                              === source
                          )
                          .slice(
                            0,
                            30
                          )
                          .map(
                            item => (
                              <button
                                type="button"
                                key={item.id}
                                style={{
                                  paddingLeft:
                                    `${8 + Math.min(
                                      item.depth,
                                      5
                                    ) * 8}px`
                                }}
                                onClick={() => {
                                  setSelected(
                                    item.id
                                  )

                                  setMode(
                                    "inspect"
                                  )
                                }}
                              >
                                <i />

                                <span>
                                  {item.title}
                                </span>
                              </button>
                            )
                          )}
                      </article>
                    )
                  )}
              </div>
            </div>
          )}


          {mode === "connections" && (
            <div className="memory-braid">
              <header>
                <Network
                  size={16}
                />

                <div>
                  <span>
                    connections
                  </span>

                  <h2>
                    memories that appear to be related
                  </h2>
                </div>
              </header>


              <div className="braid-lanes">
                {links
                  .slice(
                    0,
                    120
                  )
                  .map(
                    link => {
                      const left =
                        items.find(
                          item =>
                            item.id
                            === link.left
                        )

                      const right =
                        items.find(
                          item =>
                            item.id
                            === link.right
                        )

                      if (
                        !left
                        || !right
                      ) {
                        return null
                      }

                      return (
                        <button
                          type="button"
                          key={
                            `${link.left}:${link.right}`
                          }
                          className="braid-link"
                          onClick={() => {
                            setSelected(
                              left.id
                            )

                            setMode(
                              "inspect"
                            )
                          }}
                        >
                          <div>
                            <strong>
                              {left.title}
                            </strong>

                            <span>
                              {left.source}
                            </span>
                          </div>


                          <div className="braid-bridge">
                            <i
                              style={{
                                opacity:
                                  Math.min(
                                    .9,
                                    .2
                                    + link.score
                                  )
                              }}
                            />

                            <em>
                              {link.terms
                                .slice(
                                  0,
                                  3
                                )
                                .join(
                                  " · "
                                )}
                            </em>
                          </div>


                          <div>
                            <strong>
                              {right.title}
                            </strong>

                            <span>
                              {right.source}
                            </span>
                          </div>
                        </button>
                      )
                    }
                  )}


                {!loading
                  && links.length === 0
                  && (
                    <div className="contextarium-empty">
                      <Network
                        size={30}
                      />

                      No strong memory connections were derived from the currently loaded data.
                    </div>
                  )}
              </div>
            </div>
          )}


          {mode === "inspect" && (
            <div className="memory-focus">
              {selectedItem
                ? (
                  <>
                    <header>
                      <CircleDot
                        size={16}
                      />

                      <div>
                        <span>
                          selected memory
                        </span>

                        <h2>
                          {selectedItem.title}
                        </h2>
                      </div>


                      <button
                        type="button"
                        onClick={() =>
                          toggleContext(
                            selectedItem.id
                          )
                        }
                      >
                        <Sparkles
                          size={13}
                        />

                        {capsule.includes(
                          selectedItem.id
                        )
                          ? "remove from context"
                          : "add to context"}
                      </button>
                    </header>


                    <div className="focus-origin">
                      <span>
                        source

                        <b>
                          {selectedItem.source}
                        </b>
                      </span>

                      <span>
                        location

                        <b>
                          {selectedItem.path}
                        </b>
                      </span>
                    </div>


                    <pre>
                      {selectedItem.text}
                    </pre>


                    <section className="focus-neighborhood">
                      <header>
                        related memories
                      </header>


                      {neighborhood
                        .slice(
                          0,
                          20
                        )
                        .map(
                          entry => (
                            <button
                              type="button"
                              key={
                                entry.item.id
                              }
                              onClick={() =>
                                setSelected(
                                  entry.item.id
                                )
                              }
                            >
                              <span>
                                {entry.item.title}
                              </span>

                              <em>
                                {entry.link.terms
                                  .slice(
                                    0,
                                    4
                                  )
                                  .join(
                                    " · "
                                  )}
                              </em>

                              <b>
                                {Math.round(
                                  entry.link.score
                                  * 100
                                )}
                              </b>
                            </button>
                          )
                        )}


                      {neighborhood.length
                        === 0
                        && (
                          <div className="contextarium-empty small">
                            No strong related memories found.
                          </div>
                        )}
                    </section>
                  </>
                )
                : (
                  <div className="contextarium-empty">
                    <CircleDot
                      size={30}
                    />

                    Choose a memory from the list on the left.
                  </div>
                )}
            </div>
          )}


          {mode === "chat-context" && (
            <div className="memory-capsule">
              <header>
                <Boxes
                  size={16}
                />

                <div>
                  <span>
                    chat context
                  </span>

                  <h2>
                    memories Palaver should use for your next request
                  </h2>
                </div>


                <button
                  type="button"
                  disabled={
                    capsule.length
                    === 0
                  }
                  onClick={
                    useContextInChat
                  }
                >
                  <MessageSquareText
                    size={13}
                  />

                  use this context in chat
                </button>
              </header>


              <div>
                {capsule.map(
                  id => {
                    const item =
                      items.find(
                        candidate =>
                          candidate.id
                          === id
                      )

                    if (!item) {
                      return null
                    }

                    return (
                      <article
                        key={id}
                      >
                        <header>
                          <FileText
                            size={13}
                          />

                          <strong>
                            {item.title}
                          </strong>

                          <button
                            type="button"
                            onClick={() =>
                              toggleContext(
                                id
                              )
                            }
                            title="Remove from context"
                          >
                            <X
                              size={12}
                            />
                          </button>
                        </header>

                        <span>
                          {item.source}
                        </span>

                        <p>
                          {item.text.slice(
                            0,
                            340
                          )}
                        </p>
                      </article>
                    )
                  }
                )}


                {capsule.length
                  === 0
                  && (
                    <div className="contextarium-empty">
                      <Layers3
                        size={30}
                      />

                      Open a memory and choose “add to context.”
                    </div>
                  )}
              </div>
            </div>
          )}
        </section>
      </main>
    </section>
  )
}
