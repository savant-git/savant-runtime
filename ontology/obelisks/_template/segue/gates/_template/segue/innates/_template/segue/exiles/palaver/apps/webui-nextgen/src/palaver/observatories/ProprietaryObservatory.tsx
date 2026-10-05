import {
  useCallback,
  useEffect,
  useMemo,
  useState
} from "react"

import {
  AnimatePresence,
  motion
} from "framer-motion"

import {
  Activity,
  ArrowRight,
  Check,
  Clipboard,
  Crosshair,
  Database,
  Eye,
  Filter,
  Gauge,
  Layers3,
  MessageSquareText,
  Pin,
  PinOff,
  RefreshCw,
  Search,
  Sigma,
  X
} from "lucide-react"

import {
  ObservatoryKind,
  observatorySpecs
} from "./observatory-specs"

import {
  useWorkspaceStore
} from "../state/workspace-store"


type SourceState = {
  endpoint: string
  ok: boolean
  status: number
  payload: unknown
}


type RecordRow = {
  id: string
  source: string
  path: string
  depth: number
  value: unknown
  text: string
  fields: Record<string, string>
  timestamp: number | null
  signature: string
}


function stableStringify(
  value: unknown
): string {
  if (
    value === null
    || typeof value !== "object"
  ) {
    return JSON.stringify(value)
  }

  if (Array.isArray(value)) {
    return `[${value
      .map(stableStringify)
      .join(",")}]`
  }

  return `{${Object
    .keys(value as Record<string, unknown>)
    .sort()
    .map(key =>
      `${JSON.stringify(key)}:${stableStringify(
        (value as Record<string, unknown>)[key]
      )}`
    )
    .join(",")}}`
}


function tinyHash(
  text: string
) {
  let hash = 2166136261

  for (
    let index = 0;
    index < text.length;
    index += 1
  ) {
    hash ^= text.charCodeAt(index)

    hash = Math.imul(
      hash,
      16777619
    )
  }

  return (
    hash >>> 0
  ).toString(16)
}


function scalarFields(
  value: unknown
): Record<string, string> {
  if (
    !value
    || typeof value !== "object"
    || Array.isArray(value)
  ) {
    return {
      value: String(value ?? "")
    }
  }

  const out:
    Record<string, string> = {}

  for (
    const [
      key,
      item
    ] of Object.entries(value)
  ) {
    if (
      item === null
      || typeof item === "string"
      || typeof item === "number"
      || typeof item === "boolean"
    ) {
      out[key] =
        String(item ?? "")
    }
  }

  return out
}


function parseTimestamp(
  fields: Record<string, string>
): number | null {
  const keys = [
    "timestamp",
    "time",
    "date",
    "created",
    "updated",
    "mtime",
    "modified"
  ]

  for (const key of keys) {
    const raw =
      fields[key]

    if (!raw) continue

    const numeric =
      Number(raw)

    if (
      Number.isFinite(numeric)
      && numeric > 1000000000
    ) {
      return numeric > 1000000000000
        ? numeric
        : numeric * 1000
    }

    const parsed =
      Date.parse(raw)

    if (
      Number.isFinite(parsed)
    ) {
      return parsed
    }
  }

  return null
}


function flattenPayload(
  source: string,
  value: unknown,
  path = "$",
  depth = 0,
  output: RecordRow[] = []
): RecordRow[] {
  if (depth > 9) {
    return output
  }

  const fields =
    scalarFields(value)

  const serialized =
    stableStringify(value)

  const row: RecordRow = {
    id:
      `${tinyHash(source)}-${tinyHash(path)}-${tinyHash(serialized)}`,

    source,
    path,
    depth,
    value,

    text:
      `${path} ${Object
        .entries(fields)
        .map(
          ([key, item]) =>
            `${key} ${item}`
        )
        .join(" ")}`
        .toLowerCase(),

    fields,

    timestamp:
      parseTimestamp(fields),

    signature:
      tinyHash(serialized)
  }

  const isUsefulObject =
    value !== null
    && typeof value === "object"
    && (
      Object.keys(fields).length > 0
      || Array.isArray(value)
    )

  if (
    isUsefulObject
    || depth === 0
  ) {
    output.push(row)
  }

  if (Array.isArray(value)) {
    value.forEach(
      (
        item,
        index
      ) =>
        flattenPayload(
          source,
          item,
          `${path}[${index}]`,
          depth + 1,
          output
        )
    )

    return output
  }

  if (
    value
    && typeof value === "object"
  ) {
    for (
      const [
        key,
        item
      ] of Object.entries(
        value
      )
    ) {
      if (
        item
        && typeof item
        === "object"
      ) {
        flattenPayload(
          source,
          item,
          `${path}.${key}`,
          depth + 1,
          output
        )
      }
    }
  }

  return output
}


function relevance(
  row: RecordRow,
  keys: string[]
) {
  let score = 0

  for (const key of keys) {
    const needle =
      key.toLowerCase()

    if (
      row.text.includes(
        needle
      )
    ) {
      score += 1
    }
  }

  return score
}


function titleFor(
  row: RecordRow
) {
  const preferred = [
    "name",
    "id",
    "title",
    "path",
    "node",
    "source",
    "type",
    "kind",
    "class"
  ]

  for (
    const key of preferred
  ) {
    if (row.fields[key]) {
      return row.fields[key]
    }
  }

  return row.path
}


function formatSource(
  endpoint: string
) {
  return endpoint
    .replace(/^\/api\//, "")
    .replace(/\//g, " · ")
}


function JsonInspector({
  value
}: {
  value: unknown
}) {
  return (
    <pre className="po-json">
      {JSON.stringify(
        value,
        null,
        2
      )}
    </pre>
  )
}


export default function ProprietaryObservatory({
  kind
}: {
  kind: ObservatoryKind
}) {
  const spec =
    observatorySpecs[kind]

  const {
    setActive,
    setComposerDraft,
    setLastActivity
  } = useWorkspaceStore()

  const [
    sources,
    setSources
  ] = useState<SourceState[]>([])

  const [
    loading,
    setLoading
  ] = useState(true)

  const [
    query,
    setQuery
  ] = useState("")

  const [
    lens,
    setLens
  ] = useState("all")

  const [
    selectedId,
    setSelectedId
  ] = useState<string | null>(
    null
  )

  const [
    pinned,
    setPinned
  ] = useState<string[]>([])

  const [
    copied,
    setCopied
  ] = useState(false)

  const [
    sort,
    setSort
  ] = useState<
    "signal" |
    "recent" |
    "source"
  >("signal")


  const refresh =
    useCallback(
      async () => {
        setLoading(true)

        const results =
          await Promise.all(
            spec.sources.map(
              async endpoint => {
                try {
                  const response =
                    await fetch(
                      endpoint,
                      {
                        cache:
                          "no-store"
                      }
                    )

                  let payload:
                    unknown = null

                  const text =
                    await response.text()

                  try {
                    payload =
                      text
                        ? JSON.parse(text)
                        : null
                  } catch {
                    payload = text
                  }

                  return {
                    endpoint,
                    ok: response.ok,
                    status:
                      response.status,
                    payload
                  }
                } catch {
                  return {
                    endpoint,
                    ok: false,
                    status: 0,
                    payload: null
                  }
                }
              }
            )
          )

        setSources(results)

        setLastActivity(
          `${spec.name} refreshed`
        )

        setLoading(false)
      },
      [
        spec,
        setLastActivity
      ]
    )


  useEffect(() => {
    refresh()
  }, [refresh])


  const rows =
    useMemo(
      () => {
        const all =
          sources
            .filter(
              source =>
                source.ok
                && source.payload
                !== null
            )
            .flatMap(
              source =>
                flattenPayload(
                  source.endpoint,
                  source.payload
                )
            )

        const unique =
          new Map<
            string,
            RecordRow
          >()

        for (const row of all) {
          const key =
            `${row.source}:${row.signature}`

          if (!unique.has(key)) {
            unique.set(
              key,
              row
            )
          }
        }

        return [
          ...unique.values()
        ]
      },
      [sources]
    )


  const filtered =
    useMemo(
      () => {
        const terms =
          query
            .toLowerCase()
            .trim()
            .split(/\s+/)
            .filter(Boolean)

        let next =
          rows.filter(row => {
            if (
              terms.length > 0
              && !terms.every(
                term =>
                  row.text.includes(
                    term
                  )
              )
            ) {
              return false
            }

            if (
              lens === "all"
            ) {
              return true
            }

            return row.text.includes(
              lens.toLowerCase()
            )
          })

        next = [...next]

        if (sort === "recent") {
          next.sort(
            (a, b) =>
              (
                b.timestamp
                ?? 0
              )
              -
              (
                a.timestamp
                ?? 0
              )
          )
        } else if (
          sort === "source"
        ) {
          next.sort(
            (a, b) =>
              a.source.localeCompare(
                b.source
              )
          )
        } else {
          next.sort(
            (a, b) =>
              relevance(
                b,
                spec.primaryKeys
              )
              -
              relevance(
                a,
                spec.primaryKeys
              )
          )
        }

        return next
      },
      [
        lens,
        query,
        rows,
        sort,
        spec.primaryKeys
      ]
    )


  const selected =
    useMemo(
      () =>
        rows.find(
          row =>
            row.id
            === selectedId
        )
        ?? null,
      [
        rows,
        selectedId
      ]
    )


  const pinnedRows =
    useMemo(
      () =>
        pinned
          .map(
            id =>
              rows.find(
                row =>
                  row.id
                  === id
              )
          )
          .filter(
            (
              row
            ): row is RecordRow =>
              Boolean(row)
          ),
      [
        pinned,
        rows
      ]
    )


  const liveSources =
    sources.filter(
      source => source.ok
    ).length


  const uniqueSources =
    new Set(
      rows.map(
        row => row.source
      )
    ).size


  const signalRows =
    rows.filter(
      row =>
        relevance(
          row,
          spec.primaryKeys
        ) > 0
    ).length


  function togglePin(
    id: string
  ) {
    setPinned(
      current =>
        current.includes(id)
          ? current.filter(
              value =>
                value !== id
            )
          : [
              ...current,
              id
            ].slice(-4)
    )
  }


  function askPalaver(
    row: RecordRow
  ) {
    setComposerDraft(
      [
        `Inspect this ${spec.name} record.`,
        "",
        `source: ${row.source}`,
        `path: ${row.path}`,
        "",
        "Treat this as projection/evidence only; preserve authority distinctions.",
        "",
        JSON.stringify(
          row.value,
          null,
          2
        )
      ].join("\n")
    )

    setActive("chat")

    setLastActivity(
      `${spec.name} record attached to palaver`
    )
  }


  async function copySelected() {
    if (!selected) return

    await navigator.clipboard.writeText(
      JSON.stringify(
        selected.value,
        null,
        2
      )
    )

    setCopied(true)

    window.setTimeout(
      () => setCopied(false),
      1000
    )
  }


  return (
    <section
      className={
        `proprietary-observatory po-${kind} po-accent-${spec.accent}`
      }
    >
      <header className="po-header">
        <div className="po-identity">
          <div className="po-emblem">
            <Crosshair size={18} />
          </div>

          <div>
            <span>
              {spec.instrument}
            </span>

            <h1>
              {spec.name}
            </h1>

            <p>
              {spec.description}
            </p>
          </div>
        </div>

        <div className="po-header-actions">
          <button
            type="button"
            onClick={refresh}
            disabled={loading}
          >
            <RefreshCw
              size={14}
              className={
                loading
                  ? "spin"
                  : ""
              }
            />
            refresh
          </button>
        </div>
      </header>


      <section className="po-telemetry">
        <article>
          <Database size={14} />
          <div>
            <b>
              {liveSources}
              /
              {spec.sources.length}
            </b>
            <span>
              sources live
            </span>
          </div>
        </article>

        <article>
          <Layers3 size={14} />
          <div>
            <b>
              {rows.length}
            </b>
            <span>
              records projected
            </span>
          </div>
        </article>

        <article>
          <Sigma size={14} />
          <div>
            <b>
              {signalRows}
            </b>
            <span>
              domain signals
            </span>
          </div>
        </article>

        <article>
          <Activity size={14} />
          <div>
            <b>
              {uniqueSources}
            </b>
            <span>
              active strata
            </span>
          </div>
        </article>
      </section>


      <section className="po-source-ribbon">
        {sources.map(
          source => (
            <div
              key={source.endpoint}
              className={
                source.ok
                  ? "po-source live"
                  : "po-source unavailable"
              }
              title={
                `${source.endpoint} · HTTP ${source.status}`
              }
            >
              <i />
              <span>
                {formatSource(
                  source.endpoint
                )}
              </span>
            </div>
          )
        )}
      </section>


      <section className="po-controls">
        <label className="po-search">
          <Search size={14} />

          <input
            value={query}
            onChange={
              event =>
                setQuery(
                  event.target.value
                )
            }
            placeholder={
              `${spec.verb} across live projections…`
            }
          />

          {query && (
            <button
              type="button"
              onClick={() =>
                setQuery("")
              }
            >
              <X size={13} />
            </button>
          )}
        </label>

        <div className="po-sort">
          <Filter size={13} />

          {[
            "signal",
            "recent",
            "source"
          ].map(value => (
            <button
              type="button"
              key={value}
              className={
                sort === value
                  ? "active"
                  : ""
              }
              onClick={() =>
                setSort(
                  value as
                    "signal" |
                    "recent" |
                    "source"
                )
              }
            >
              {value}
            </button>
          ))}
        </div>
      </section>


      <nav className="po-lenses">
        {spec.lenses.map(
          value => (
            <button
              type="button"
              key={value}
              className={
                lens === value
                  ? "active"
                  : ""
              }
              onClick={() =>
                setLens(value)
              }
            >
              <Eye size={12} />
              {value}
            </button>
          )
        )}
      </nav>


      <section className="po-workbench">
        <div className="po-results">
          <header>
            <div>
              <span>
                projection field
              </span>

              <b>
                {filtered.length}
                {" "}
                visible
              </b>
            </div>

            <Gauge size={14} />
          </header>

          <div className="po-record-list">
            <AnimatePresence
              initial={false}
            >
              {filtered
                .slice(0, 500)
                .map(
                  (
                    row,
                    index
                  ) => {
                    const score =
                      relevance(
                        row,
                        spec.primaryKeys
                      )

                    const isPinned =
                      pinned.includes(
                        row.id
                      )

                    return (
                      <motion.button
                        type="button"
                        key={row.id}
                        className={
                          [
                            "po-record",
                            selectedId
                            === row.id
                              ? "selected"
                              : "",
                            isPinned
                              ? "pinned"
                              : ""
                          ]
                            .filter(Boolean)
                            .join(" ")
                        }
                        onClick={() =>
                          setSelectedId(
                            row.id
                          )
                        }
                        initial={{
                          opacity: 0,
                          y: 5
                        }}
                        animate={{
                          opacity: 1,
                          y: 0
                        }}
                        transition={{
                          duration: .16,
                          delay:
                            Math.min(
                              index,
                              20
                            )
                            * .008
                        }}
                      >
                        <div className="po-record-head">
                          <strong>
                            {titleFor(row)}
                          </strong>

                          <span>
                            {score}
                          </span>
                        </div>

                        <div className="po-record-path">
                          {row.path}
                        </div>

                        <footer>
                          <span>
                            {formatSource(
                              row.source
                            )}
                          </span>

                          {row.timestamp && (
                            <time>
                              {new Date(
                                row.timestamp
                              ).toLocaleString()}
                            </time>
                          )}
                        </footer>
                      </motion.button>
                    )
                  }
                )}
            </AnimatePresence>

            {!loading
              && filtered.length
              === 0
              && (
                <div className="po-empty">
                  no matching projection
                </div>
              )}
          </div>
        </div>


        <div className="po-inspector">
          {selected
            ? (
              <>
                <header className="po-inspector-head">
                  <div>
                    <span>
                      selected record
                    </span>

                    <h2>
                      {titleFor(
                        selected
                      )}
                    </h2>
                  </div>

                  <div>
                    <button
                      type="button"
                      onClick={() =>
                        togglePin(
                          selected.id
                        )
                      }
                      title="Pin for comparison"
                    >
                      {pinned.includes(
                        selected.id
                      )
                        ? <PinOff size={14} />
                        : <Pin size={14} />
                      }
                    </button>

                    <button
                      type="button"
                      onClick={
                        copySelected
                      }
                      title="Copy JSON"
                    >
                      {copied
                        ? <Check size={14} />
                        : <Clipboard size={14} />
                      }
                    </button>

                    <button
                      type="button"
                      onClick={() =>
                        askPalaver(
                          selected
                        )
                      }
                      title="Attach to Palaver"
                    >
                      <MessageSquareText
                        size={14}
                      />
                    </button>
                  </div>
                </header>

                <section className="po-provenance">
                  <div>
                    <span>
                      projection source
                    </span>

                    <b>
                      {selected.source}
                    </b>
                  </div>

                  <div>
                    <span>
                      projection path
                    </span>

                    <b>
                      {selected.path}
                    </b>
                  </div>

                  <div>
                    <span>
                      domain signal
                    </span>

                    <b>
                      {relevance(
                        selected,
                        spec.primaryKeys
                      )}
                    </b>
                  </div>
                </section>

                <div className="po-field-grid">
                  {Object.entries(
                    selected.fields
                  )
                    .slice(0, 20)
                    .map(
                      ([
                        key,
                        value
                      ]) => (
                        <div key={key}>
                          <span>
                            {key}
                          </span>

                          <b>
                            {value}
                          </b>
                        </div>
                      )
                    )}
                </div>

                <JsonInspector
                  value={
                    selected.value
                  }
                />
              </>
            )
            : (
              <div className="po-inspector-empty">
                <Crosshair size={26} />

                <span>
                  select a record
                </span>

                <p>
                  Inspect its exact projected data,
                  source path and domain signal.
                </p>
              </div>
            )}
        </div>
      </section>


      {pinnedRows.length > 0 && (
        <section className="po-comparison">
          <header>
            <div>
              <span>
                comparative aperture
              </span>

              <b>
                {pinnedRows.length}
                {" "}
                pinned
              </b>
            </div>

            <button
              type="button"
              onClick={() =>
                setPinned([])
              }
            >
              clear
            </button>
          </header>

          <div className="po-comparison-grid">
            {pinnedRows.map(
              row => (
                <article
                  key={row.id}
                >
                  <header>
                    <strong>
                      {titleFor(row)}
                    </strong>

                    <button
                      type="button"
                      onClick={() =>
                        togglePin(
                          row.id
                        )
                      }
                    >
                      <X size={12} />
                    </button>
                  </header>

                  <span>
                    {formatSource(
                      row.source
                    )}
                  </span>

                  <div>
                    {Object
                      .entries(
                        row.fields
                      )
                      .slice(0, 8)
                      .map(
                        ([
                          key,
                          value
                        ]) => (
                          <p key={key}>
                            <i>
                              {key}
                            </i>

                            <b>
                              {value}
                            </b>
                          </p>
                        )
                      )}
                  </div>
                </article>
              )
            )}
          </div>
        </section>
      )}


      <footer className="po-footer">
        <span>
          projections do not alter authority
        </span>

        <ArrowRight size={12} />

        <span>
          selected evidence can be handed to palaver
        </span>
      </footer>
    </section>
  )
}
