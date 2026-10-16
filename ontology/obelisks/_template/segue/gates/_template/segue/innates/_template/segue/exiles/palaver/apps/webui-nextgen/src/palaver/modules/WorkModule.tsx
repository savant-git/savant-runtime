import {
  useEffect,
  useMemo,
  useState
} from "react"

import {
  AlertTriangle,
  CheckCircle2,
  Circle,
  ClipboardList,
  MessageSquareText,
  RefreshCw
} from "lucide-react"

import {
  useWorkspaceStore
} from "../state/workspace-store"


function flatten(
  value: unknown,
  result:
    Record<string, unknown>[] = []
) {
  if (
    Array.isArray(value)
  ) {
    value.forEach(
      item =>
        flatten(
          item,
          result
        )
    )

    return result
  }

  if (
    value
    && typeof value
    === "object"
  ) {
    const record =
      value as
        Record<string, unknown>

    result.push(record)

    Object.values(record)
      .forEach(
        item =>
          flatten(
            item,
            result
          )
      )
  }

  return result
}


export default function WorkModule() {
  const {
    setActive,
    setComposerDraft,
    setLastActivity
  } = useWorkspaceStore()

  const [
    data,
    setData
  ] = useState<unknown>(
    null
  )

  const [
    loading,
    setLoading
  ] = useState(false)


  async function refresh() {
    setLoading(true)

    try {
      const response =
        await fetch(
          "/api/dashboard/state",
          {
            cache:
              "no-store"
          }
        )

      const value =
        await response.json()

      setData(value)

      setLastActivity(
        "work dashboard refreshed"
      )
    } catch (
      reason
    ) {
      setData({
        error:
          String(reason)
      })
    } finally {
      setLoading(false)
    }
  }


  useEffect(() => {
    refresh()
  }, [])


  const records =
    useMemo(
      () =>
        flatten(data),
      [data]
    )


  const tasks =
    records.filter(
      record =>
        record.id
        || record.task
        || record.title
        || record.status
    )


  function display(
    record:
      Record<string, unknown>
  ) {
    return String(
      record.title
      ?? record.task
      ?? record.name
      ?? record.id
      ?? "work item"
    )
  }


  function status(
    record:
      Record<string, unknown>
  ) {
    return String(
      record.status
      ?? record.state
      ?? "unknown"
    )
  }


  function discuss(
    record:
      Record<string, unknown>
  ) {
    setComposerDraft(
      [
        "Help me continue this work item.",
        "Explain only what matters and give me the minimum next action.",
        "",
        JSON.stringify(
          record,
          null,
          2
        )
      ].join("\n")
    )

    setActive("chat")
  }


  return (
    <section className="work-dashboard">
      <header className="module-hero">
        <div>
          <ClipboardList
            size={19}
          />

          <div>
            <span>
              what palaver is working on
            </span>

            <h1>
              work
            </h1>

            <p>
              Current tasks, states and next actions in one place.
            </p>
          </div>
        </div>

        <button
          type="button"
          onClick={refresh}
        >
          <RefreshCw
            size={14}
          />
          refresh
        </button>
      </header>


      <div className="work-summary">
        <article>
          <b>
            {tasks.length}
          </b>
          <span>
            work items
          </span>
        </article>

        <article>
          <b>
            {tasks.filter(
              record =>
                /active|running|current/i
                  .test(
                    status(record)
                  )
            ).length}
          </b>
          <span>
            active
          </span>
        </article>

        <article>
          <b>
            {tasks.filter(
              record =>
                /block|fail|error/i
                  .test(
                    status(record)
                  )
            ).length}
          </b>
          <span>
            blocked
          </span>
        </article>
      </div>


      <div className="work-cards">
        {tasks
          .slice(
            0,
            100
          )
          .map(
            (
              record,
              index
            ) => {
              const value =
                status(record)

              const Icon =
                /block|fail|error/i
                  .test(value)
                  ? AlertTriangle
                  : /complete|done|accepted/i
                      .test(value)
                    ? CheckCircle2
                    : Circle

              return (
                <article
                  key={
                    `${display(record)}-${index}`
                  }
                >
                  <header>
                    <Icon
                      size={14}
                    />

                    <strong>
                      {display(
                        record
                      )}
                    </strong>

                    <span>
                      {value}
                    </span>
                  </header>

                  <div>
                    {Object.entries(
                      record
                    )
                      .slice(
                        0,
                        8
                      )
                      .map(
                        ([
                          key,
                          item
                        ]) => (
                          <p key={key}>
                            <span>
                              {key}
                            </span>

                            <b>
                              {typeof item
                              === "object"
                                ? JSON.stringify(
                                    item
                                  )
                                : String(
                                    item
                                    ?? ""
                                  )}
                            </b>
                          </p>
                        )
                      )}
                  </div>

                  <button
                    type="button"
                    onClick={() =>
                      discuss(
                        record
                      )
                    }
                  >
                    <MessageSquareText
                      size={13}
                    />

                    continue in palaver
                  </button>
                </article>
              )
            }
          )}

        {!loading
          && tasks.length
          === 0
          && (
            <div className="module-empty">
              No work items were returned by the current dashboard projection.
            </div>
          )}
      </div>
    </section>
  )
}
