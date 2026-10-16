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
  ArrowRight,
  Boxes,
  CircleDot,
  FileCode2,
  GitBranch,
  History,
  Link2,
  MessageSquareText,
  Network,
  Search,
  Shield,
  Sparkles,
  Target,
  Workflow,
  X
} from "lucide-react"

import {
  useWorkspaceStore
} from "../state/workspace-store"


type View =
  | "neighborhood"
  | "path"
  | "impact"
  | "composition"
  | "ownership"
  | "dependency"
  | "history"
  | "evidence"


type Relation = {
  id: string
  source: string
  target: string
  type: string
  evidence: string
  raw: unknown
}


type Entity = {
  id: string
  label: string
  relations: Relation[]
}


function hash(
  value: string
) {
  let output = 2166136261

  for (
    let index = 0;
    index < value.length;
    index += 1
  ) {
    output ^=
      value.charCodeAt(index)

    output =
      Math.imul(
        output,
        16777619
      )
  }

  return (
    output >>> 0
  ).toString(16)
}


function text(
  value: unknown
) {
  if (
    value === null
    || value === undefined
  ) {
    return ""
  }

  if (
    typeof value
    === "string"
    || typeof value
    === "number"
    || typeof value
    === "boolean"
  ) {
    return String(value)
  }

  try {
    return JSON.stringify(
      value
    )
  } catch {
    return String(value)
  }
}


function firstString(
  record:
    Record<string, unknown>,
  keys: string[]
) {
  for (
    const key
    of keys
  ) {
    const value =
      record[key]

    if (
      typeof value
      === "string"
      && value.trim()
    ) {
      return value.trim()
    }
  }

  return ""
}


function relationFromRecord(
  record:
    Record<string, unknown>,
  sourceName: string
): Relation | null {
  const source =
    firstString(
      record,
      [
        "source",
        "from",
        "parent",
        "owner",
        "subject",
        "left"
      ]
    )

  const target =
    firstString(
      record,
      [
        "target",
        "to",
        "child",
        "dependent",
        "object",
        "right"
      ]
    )

  if (
    !source
    || !target
  ) {
    return null
  }

  const type =
    firstString(
      record,
      [
        "type",
        "relation",
        "relationship",
        "kind",
        "edge"
      ]
    )
    || "related"

  return {
    id:
      hash(
        `${sourceName}:${source}:${target}:${type}`
      ),

    source,
    target,
    type,

    evidence:
      sourceName,

    raw:
      record
  }
}


function collectRelations(
  value: unknown,
  sourceName: string,
  output: Relation[] = [],
  depth = 0
) {
  if (
    depth > 10
  ) {
    return output
  }

  if (
    Array.isArray(value)
  ) {
    value.forEach(
      item =>
        collectRelations(
          item,
          sourceName,
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

    const relation =
      relationFromRecord(
        record,
        sourceName
      )

    if (relation) {
      output.push(
        relation
      )
    }

    Object.values(record)
      .forEach(
        item => {
          if (
            item
            && typeof item
            === "object"
          ) {
            collectRelations(
              item,
              sourceName,
              output,
              depth + 1
            )
          }
        }
      )
  }

  return output
}


function uniqueRelations(
  relations: Relation[]
) {
  const map =
    new Map<
      string,
      Relation
    >()

  relations.forEach(
    relation => {
      const key =
        [
          relation.source,
          relation.target,
          relation.type,
          relation.evidence
        ].join("::")

      if (!map.has(key)) {
        map.set(
          key,
          relation
        )
      }
    }
  )

  return [
    ...map.values()
  ]
}


const views: {
  id: View
  label: string
  description: string
  icon: any
}[] = [
  {
    id:
      "neighborhood",

    label:
      "Connected",

    description:
      "Everything directly connected to the selected element.",

    icon:
      CircleDot
  },

  {
    id:
      "path",

    label:
      "Path",

    description:
      "Find a relationship chain between two elements.",

    icon:
      Workflow
  },

  {
    id:
      "impact",

    label:
      "Impact",

    description:
      "See what may be affected if this element changes.",

    icon:
      Target
  },

  {
    id:
      "composition",

    label:
      "Composition",

    description:
      "See how elements combine into larger structures.",

    icon:
      Boxes
  },

  {
    id:
      "ownership",

    label:
      "Ownership",

    description:
      "See ownership boundaries without transferring authority.",

    icon:
      Shield
  },

  {
    id:
      "dependency",

    label:
      "Dependencies",

    description:
      "See what this depends on and what depends on it.",

    icon:
      GitBranch
  },

  {
    id:
      "history",

    label:
      "History",

    description:
      "Inspect lineage, derivation and supersession relationships.",

    icon:
      History
  },

  {
    id:
      "evidence",

    label:
      "Evidence",

    description:
      "See exactly where relationship evidence came from.",

    icon:
      FileCode2
  }
]


export default function KindredModule() {
  const {
    setActive,
    setComposerDraft,
    openSource,
    setLastActivity
  } = useWorkspaceStore()

  const [
    relations,
    setRelations
  ] = useState<
    Relation[]
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
    selected,
    setSelected
  ] = useState("")

  const [
    view,
    setView
  ] = useState<View>(
    "neighborhood"
  )

  const [
    pathTarget,
    setPathTarget
  ] = useState("")


  useEffect(() => {
    let alive = true

    async function load() {
      setLoading(true)

      const endpoints = [
        "/api/authority/relationships",
        "/api/graph",
        "/api/timeline",
        "/api/authority/slots"
      ]

      const loaded:
        Relation[] = []

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

          const body =
            await response.text()

          let payload:
            unknown = body

          try {
            payload =
              JSON.parse(body)
          } catch {
            payload =
              body
          }

          if (
            response.ok
          ) {
            collectRelations(
              payload,
              endpoint,
              loaded
            )
          }
        } catch {
          // Missing projection stays absent.
        }
      }

      if (!alive) {
        return
      }

      const next =
        uniqueRelations(
          loaded
        )

      setRelations(next)
      setLoading(false)

      setLastActivity(
        `kindred loaded ${next.length} relationships`
      )
    }

    load()

    return () => {
      alive = false
    }
  }, [
    setLastActivity
  ])


  const entities =
    useMemo(
      () => {
        const map =
          new Map<
            string,
            Entity
          >()

        relations.forEach(
          relation => {
            for (
              const label
              of [
                relation.source,
                relation.target
              ]
            ) {
              const current =
                map.get(label)
                ?? {
                  id:
                    hash(label),

                  label,

                  relations:
                    []
                }

              current.relations.push(
                relation
              )

              map.set(
                label,
                current
              )
            }
          }
        )

        return [
          ...map.values()
        ].sort(
          (
            left,
            right
          ) =>
            right.relations.length
            -
            left.relations.length
        )
      },
      [relations]
    )


  const visibleEntities =
    useMemo(
      () => {
        const term =
          query
            .trim()
            .toLowerCase()

        if (!term) {
          return entities
        }

        return entities.filter(
          entity =>
            entity.label
              .toLowerCase()
              .includes(term)
            || entity.relations
              .some(
                relation =>
                  relation.type
                    .toLowerCase()
                    .includes(term)
              )
        )
      },
      [
        entities,
        query
      ]
    )


  const selectedEntity =
    entities.find(
      entity =>
        entity.label
        === selected
    )
    ?? null


  const direct =
    selectedEntity
      ? selectedEntity.relations
      : []


  const outgoing =
    direct.filter(
      relation =>
        relation.source
        === selected
    )


  const incoming =
    direct.filter(
      relation =>
        relation.target
        === selected
    )


  const ownership =
    direct.filter(
      relation =>
        /owner|owns|authority|responsible/i
          .test(
            relation.type
          )
    )


  const historical =
    direct.filter(
      relation =>
        /lineage|supersed|derive|inherit|ancestor|history|migration/i
          .test(
            relation.type
          )
    )


  const composition =
    direct.filter(
      relation =>
        /compose|contain|instance|child|parent|member|slot/i
          .test(
            relation.type
          )
    )


  function shortestPath(
    start: string,
    target: string
  ): Relation[] {
    if (
      !start
      || !target
      || start === target
    ) {
      return []
    }

    const queue: {
      node: string
      path: Relation[]
    }[] = [
      {
        node:
          start,

        path:
          []
      }
    ]

    const seen =
      new Set([
        start
      ])

    while (
      queue.length > 0
    ) {
      const current =
        queue.shift()

      if (!current) {
        break
      }

      const candidates =
        relations.filter(
          relation =>
            relation.source
            === current.node
            || relation.target
            === current.node
        )

      for (
        const relation
        of candidates
      ) {
        const next =
          relation.source
          === current.node
            ? relation.target
            : relation.source

        if (
          seen.has(next)
        ) {
          continue
        }

        const path = [
          ...current.path,
          relation
        ]

        if (
          next === target
        ) {
          return path
        }

        seen.add(next)

        queue.push({
          node:
            next,

          path
        })
      }
    }

    return []
  }


  const path =
    useMemo(
      () =>
        shortestPath(
          selected,
          pathTarget
        ),
      [
        selected,
        pathTarget,
        relations
      ]
    )


  function askPalaver(
    relation?: Relation
  ) {
    const payload =
      relation
        ? JSON.stringify(
            relation.raw,
            null,
            2
          )
        : JSON.stringify(
            direct.map(
              item => ({
                source:
                  item.source,

                target:
                  item.target,

                type:
                  item.type,

                evidence:
                  item.evidence
              })
            ),
            null,
            2
          )

    setComposerDraft(
      [
        "Help me understand these Kindred relationships.",
        "Do not treat relationship topology as authority.",
        `selected element: ${selected || "none"}`,
        "",
        payload
      ].join("\n")
    )

    setActive("chat")
  }


  function sourceCandidate(
    relation: Relation
  ) {
    const candidates = [
      relation.source,
      relation.target
    ]

    return candidates.find(
      candidate =>
        /[/.][a-z0-9_-]+\.[a-z0-9]+$/i
          .test(candidate)
    )
  }


  function relationRows() {
    if (
      !selectedEntity
    ) {
      return []
    }

    switch (view) {
      case "ownership":
        return ownership

      case "composition":
        return composition

      case "history":
        return historical

      case "dependency":
        return direct.filter(
          relation =>
            /depend|require|import|use|consume|provide/i
              .test(
                relation.type
              )
        )

      case "impact":
        return incoming

      case "evidence":
        return direct

      default:
        return direct
    }
  }


  return (
    <section className="kindred-module">
      <header className="kindred-hero">
        <div className="kindred-sigil">
          <Network
            size={21}
          />

          <i />
          <b />
        </div>

        <div className="kindred-title">
          <span>
            understand what connects to what
          </span>

          <h1>
            kindred
          </h1>

          <p>
            Select any Savant element to see its relationships, dependencies, ownership, history, composition, impact and evidence.
          </p>
        </div>

        <div className="kindred-metrics">
          <div>
            <b>
              {entities.length}
            </b>

            <span>
              elements
            </span>
          </div>

          <div>
            <b>
              {relations.length}
            </b>

            <span>
              relationships
            </span>
          </div>
        </div>
      </header>


      <div className="kindred-controls">
        <label>
          <Search
            size={14}
          />

          <input
            value={query}
            onChange={
              event =>
                setQuery(
                  event.target.value
                )
            }
            placeholder="Find any element, file, owner, instance or relationship…"
          />

          {query && (
            <button
              type="button"
              onClick={() =>
                setQuery("")
              }
            >
              <X
                size={13}
              />
            </button>
          )}
        </label>

        <nav>
          {views.map(
            item => {
              const Icon =
                item.icon

              return (
                <button
                  type="button"
                  key={item.id}
                  title={
                    item.description
                  }
                  className={
                    view === item.id
                      ? "active"
                      : ""
                  }
                  onClick={() =>
                    setView(
                      item.id
                    )
                  }
                >
                  <Icon
                    size={12}
                  />

                  {item.label}
                </button>
              )
            }
          )}
        </nav>
      </div>


      <main className="kindred-workspace">
        <aside className="kindred-elements">
          <header>
            <span>
              {loading
                ? "loading"
                : `${visibleEntities.length} elements`}
            </span>
          </header>

          <div>
            {visibleEntities
              .slice(
                0,
                1000
              )
              .map(
                entity => (
                  <button
                    type="button"
                    key={
                      entity.id
                    }
                    className={
                      selected
                      === entity.label
                        ? "active"
                        : ""
                    }
                    onClick={() =>
                      setSelected(
                        entity.label
                      )
                    }
                    title={
                      entity.label
                    }
                  >
                    <CircleDot
                      size={11}
                    />

                    <span>
                      {entity.label}
                    </span>

                    <b>
                      {entity.relations.length}
                    </b>
                  </button>
                )
              )}
          </div>
        </aside>


        <section className="kindred-detail">
          {!selectedEntity
            ? (
              <div className="kindred-empty">
                <Network
                  size={34}
                />

                <strong>
                  Choose an element
                </strong>

                <p>
                  Kindred will explain what it connects to and why.
                </p>
              </div>
            )
            : (
              <>
                <header className="kindred-selected">
                  <div>
                    <span>
                      selected element
                    </span>

                    <h2>
                      {selectedEntity.label}
                    </h2>
                  </div>

                  <button
                    type="button"
                    onClick={() =>
                      askPalaver()
                    }
                  >
                    <MessageSquareText
                      size={13}
                    />

                    ask palaver
                  </button>
                </header>


                {view === "path"
                  ? (
                    <section className="kindred-path">
                      <header>
                        <div>
                          <span>
                            from
                          </span>

                          <b>
                            {selected}
                          </b>
                        </div>

                        <ArrowRight
                          size={15}
                        />

                        <label>
                          <span>
                            to
                          </span>

                          <select
                            value={
                              pathTarget
                            }
                            onChange={
                              event =>
                                setPathTarget(
                                  event.target.value
                                )
                            }
                          >
                            <option value="">
                              choose an element
                            </option>

                            {entities
                              .filter(
                                entity =>
                                  entity.label
                                  !== selected
                              )
                              .map(
                                entity => (
                                  <option
                                    key={
                                      entity.id
                                    }
                                    value={
                                      entity.label
                                    }
                                  >
                                    {entity.label}
                                  </option>
                                )
                              )}
                          </select>
                        </label>
                      </header>

                      <div className="kindred-path-chain">
                        {path.map(
                          (
                            relation,
                            index
                          ) => (
                            <motion.article
                              key={
                                `${relation.id}-${index}`
                              }
                              initial={{
                                opacity:
                                  0,

                                x:
                                  -10
                              }}
                              animate={{
                                opacity:
                                  1,

                                x:
                                  0
                              }}
                              transition={{
                                delay:
                                  index
                                  * .06
                              }}
                            >
                              <strong>
                                {relation.source}
                              </strong>

                              <div>
                                <i />

                                <span>
                                  {relation.type}
                                </span>

                                <ArrowRight
                                  size={12}
                                />
                              </div>

                              <strong>
                                {relation.target}
                              </strong>
                            </motion.article>
                          )
                        )}

                        {pathTarget
                          && path.length === 0
                          && (
                            <div className="kindred-empty compact">
                              No relationship path was found in the currently exposed Kindred evidence.
                            </div>
                          )}
                      </div>
                    </section>
                  )
                  : (
                    <section className="kindred-relations">
                      <header>
                        <div>
                          <span>
                            {views.find(
                              item =>
                                item.id
                                === view
                            )?.label}
                          </span>

                          <p>
                            {views.find(
                              item =>
                                item.id
                                === view
                            )?.description}
                          </p>
                        </div>

                        <strong>
                          {relationRows().length}
                        </strong>
                      </header>


                      <AnimatePresence
                        initial={false}
                      >
                        {relationRows()
                          .map(
                            (
                              relation,
                              index
                            ) => {
                              const file =
                                sourceCandidate(
                                  relation
                                )

                              return (
                                <motion.article
                                  key={
                                    relation.id
                                  }
                                  initial={{
                                    opacity:
                                      0,

                                    y:
                                      6
                                  }}
                                  animate={{
                                    opacity:
                                      1,

                                    y:
                                      0
                                  }}
                                  transition={{
                                    delay:
                                      Math.min(
                                        index,
                                        20
                                      )
                                      * .015
                                  }}
                                >
                                  <div className="kindred-relation-main">
                                    <button
                                      type="button"
                                      onClick={() =>
                                        setSelected(
                                          relation.source
                                        )
                                      }
                                    >
                                      {relation.source}
                                    </button>

                                    <div>
                                      <Link2
                                        size={12}
                                      />

                                      <span>
                                        {relation.type}
                                      </span>

                                      <ArrowRight
                                        size={12}
                                      />
                                    </div>

                                    <button
                                      type="button"
                                      onClick={() =>
                                        setSelected(
                                          relation.target
                                        )
                                      }
                                    >
                                      {relation.target}
                                    </button>
                                  </div>

                                  <footer>
                                    <span>
                                      evidence:
                                      {" "}
                                      {relation.evidence}
                                    </span>

                                    <div>
                                      {file && (
                                        <button
                                          type="button"
                                          onClick={() =>
                                            openSource(
                                              file
                                            )
                                          }
                                        >
                                          <FileCode2
                                            size={12}
                                          />

                                          file
                                        </button>
                                      )}

                                      <button
                                        type="button"
                                        onClick={() =>
                                          askPalaver(
                                            relation
                                          )
                                        }
                                      >
                                        <Sparkles
                                          size={12}
                                        />

                                        explain
                                      </button>
                                    </div>
                                  </footer>
                                </motion.article>
                              )
                            }
                          )}
                      </AnimatePresence>


                      {relationRows().length
                        === 0
                        && (
                          <div className="kindred-empty compact">
                            No relationships of this type are currently exposed for this element.
                          </div>
                        )}
                    </section>
                  )}


                <footer className="kindred-direction">
                  <div>
                    <b>
                      {outgoing.length}
                    </b>

                    <span>
                      outward relationships
                    </span>
                  </div>

                  <div>
                    <b>
                      {incoming.length}
                    </b>

                    <span>
                      inward relationships
                    </span>
                  </div>

                  <p>
                    Relationship evidence is descriptive. It does not itself establish authority.
                  </p>
                </footer>
              </>
            )}
        </section>
      </main>
    </section>
  )
}
