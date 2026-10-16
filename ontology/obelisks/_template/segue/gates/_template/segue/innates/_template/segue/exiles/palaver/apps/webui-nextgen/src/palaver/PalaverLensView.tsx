import {
  Braces,
  Copy,
  File,
  FileJson,
  Folder,
  Search,
} from "lucide-react"
import {
  useMemo,
  useState,
} from "react"
import PalaverGraph from "./PalaverGraph"

type LensId =
  | "runtime"
  | "files"
  | "graph"
  | "memory"

type Props = {
  lens: LensId
  data: unknown
  onAsk: (
    prompt: string,
  ) => void
}

type Primitive =
  | string
  | number
  | boolean
  | null

function primitive(
  value: unknown,
): value is Primitive {
  return (
    value === null ||
    typeof value ===
      "string" ||
    typeof value ===
      "number" ||
    typeof value ===
      "boolean"
  )
}

function flatten(
  value: unknown,
  prefix = "",
  output: Array<{
    path: string
    value: Primitive
  }> = [],
) {
  if (primitive(value)) {
    output.push({
      path:
        prefix || "value",
      value,
    })

    return output
  }

  if (
    Array.isArray(value)
  ) {
    value.forEach(
      (
        item,
        index,
      ) => {
        flatten(
          item,
          `${prefix}[${index}]`,
          output,
        )
      },
    )

    return output
  }

  if (
    value &&
    typeof value === "object"
  ) {
    Object.entries(
      value,
    ).forEach(
      ([key, item]) => {
        flatten(
          item,
          prefix
            ? `${prefix}.${key}`
            : key,
          output,
        )
      },
    )
  }

  return output
}

function FileExplorer({
  data,
  onAsk,
}: {
  data: unknown
  onAsk: (
    prompt: string,
  ) => void
}) {
  const [query, setQuery] =
    useState("")

  const rows = useMemo(
    () => flatten(data),
    [data],
  )

  const visible =
    useMemo(() => {
      const normalized =
        query
          .trim()
          .toLowerCase()

      if (!normalized) {
        return rows.slice(
          0,
          500,
        )
      }

      return rows
        .filter((row) =>
          `${row.path} ${String(
            row.value,
          )}`
            .toLowerCase()
            .includes(
              normalized,
            ),
        )
        .slice(0, 500)
    }, [
      query,
      rows,
    ])

  return (
    <div className="palaver-file-browser">
      <div className="palaver-file-search">
        <Search size={15} />

        <input
          value={query}
          placeholder="filter files and values"
          onChange={(
            event,
          ) =>
            setQuery(
              event.target.value,
            )
          }
        />

        <span>
          {visible.length}
        </span>
      </div>

      <div className="palaver-file-list">
        {visible.map(
          (row) => {
            const text =
              String(
                row.value,
              )

            const fileLike =
              row.path.includes(
                "path",
              ) ||
              text.startsWith(
                "/root/",
              )

            const Icon =
              fileLike
                ? File
                : typeof row.value ===
                    "string"
                  ? FileJson
                  : Folder

            return (
              <button
                key={`${row.path}:${text}`}
                onClick={() =>
                  onAsk(
                    `Explain this SAVANT item and why it matters: ${row.path} = ${text}`,
                  )
                }
              >
                <Icon
                  size={15}
                />

                <span>
                  <strong>
                    {row.path}
                  </strong>

                  <small>
                    {text}
                  </small>
                </span>
              </button>
            )
          },
        )}
      </div>
    </div>
  )
}

function RuntimeView({
  data,
  onAsk,
}: {
  data: unknown
  onAsk: (
    prompt: string,
  ) => void
}) {
  const rows = useMemo(
    () =>
      flatten(data).slice(
        0,
        250,
      ),
    [data],
  )

  return (
    <div className="palaver-runtime-view">
      <div className="palaver-runtime-summary">
        <strong>
          {rows.length}
        </strong>
        <span>
          readable runtime facts
        </span>

        <button
          onClick={() =>
            onAsk(
              "Review the currently visible runtime information, summarize what matters, identify anything abnormal, and give me the single best next action.",
            )
          }
        >
          interpret
        </button>
      </div>

      <div className="palaver-runtime-facts">
        {rows.map(
          (row) => (
            <article
              key={row.path}
            >
              <span>
                {row.path}
              </span>

              <strong>
                {String(
                  row.value,
                )}
              </strong>
            </article>
          ),
        )}
      </div>
    </div>
  )
}

function RawView({
  data,
}: {
  data: unknown
}) {
  const value =
    JSON.stringify(
      data,
      null,
      2,
    )

  return (
    <div className="palaver-raw-view">
      <button
        onClick={() =>
          navigator.clipboard.writeText(
            value,
          )
        }
      >
        <Copy size={14} />
        copy
      </button>

      <pre>{value}</pre>
    </div>
  )
}

export default function PalaverLensView({
  lens,
  data,
  onAsk,
}: Props) {
  if (lens === "graph") {
    return (
      <PalaverGraph
        data={data}
        onAsk={onAsk}
      />
    )
  }

  if (
    lens === "files" ||
    lens === "memory"
  ) {
    return (
      <FileExplorer
        data={data}
        onAsk={onAsk}
      />
    )
  }

  if (lens === "runtime") {
    return (
      <RuntimeView
        data={data}
        onAsk={onAsk}
      />
    )
  }

  return (
    <RawView
      data={data}
    />
  )
}
