import {
  useEffect,
  useState
} from "react"

import {
  CheckCircle2,
  Cpu,
  RefreshCw,
  Route,
  Server,
  TerminalSquare,
  XCircle
} from "lucide-react"


type Surface = {
  name: string
  explanation: string
  endpoint: string
  icon: any
  ok: boolean
  value: unknown
}


const definitions = [
  {
    name: "Palaver",
    explanation:
      "Main conversation and application server",
    endpoint:
      "/api/health",
    icon:
      Server
  },

  {
    name: "Terminal",
    explanation:
      "Real Ubuntu terminal bridge",
    endpoint:
      "/api/terminal/health",
    icon:
      TerminalSquare
  },

  {
    name: "Runtime",
    explanation:
      "Current Palaver runtime information",
    endpoint:
      "/api/runtime",
    icon:
      Cpu
  },

  {
    name: "API",
    explanation:
      "Everything the interface can currently request",
    endpoint:
      "/api/routes",
    icon:
      Route
  }
]


export default function SystemModule() {
  const [
    surfaces,
    setSurfaces
  ] = useState<Surface[]>([])

  const [
    loading,
    setLoading
  ] = useState(false)


  async function load() {
    setLoading(true)

    const values =
      await Promise.all(
        definitions.map(
          async definition => {
            try {
              const response =
                await fetch(
                  definition.endpoint,
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
                value = text
              }

              return {
                ...definition,
                value,
                ok:
                  response.ok
              }
            } catch (
              reason
            ) {
              return {
                ...definition,

                value: {
                  error:
                    String(reason)
                },

                ok: false
              }
            }
          }
        )
      )

    setSurfaces(values)
    setLoading(false)
  }


  useEffect(() => {
    load()
  }, [])


  return (
    <section className="system-dashboard">
      <header className="module-hero">
        <div>
          <Server
            size={19}
          />

          <div>
            <span>
              is everything working?
            </span>

            <h1>
              system
            </h1>

            <p>
              Simple status for the services that make Palaver work.
            </p>
          </div>
        </div>

        <button
          type="button"
          onClick={load}
        >
          <RefreshCw
            size={14}
          />
          refresh
        </button>
      </header>


      <div className="system-status-summary">
        <strong>
          {surfaces.filter(
            surface =>
              surface.ok
          ).length}
          /
          {surfaces.length}
        </strong>

        <span>
          services available
        </span>
      </div>


      <div className="system-friendly-grid">
        {surfaces.map(
          surface => {
            const Icon =
              surface.icon

            return (
              <article
                key={
                  surface.endpoint
                }
                className={
                  surface.ok
                    ? "healthy"
                    : "unhealthy"
                }
              >
                <header>
                  <Icon
                    size={17}
                  />

                  <div>
                    <strong>
                      {surface.name}
                    </strong>

                    <span>
                      {surface.explanation}
                    </span>
                  </div>

                  {surface.ok
                    ? (
                      <CheckCircle2
                        size={16}
                      />
                    )
                    : (
                      <XCircle
                        size={16}
                      />
                    )
                  }
                </header>

                <div className="system-state">
                  <b>
                    {surface.ok
                      ? "working"
                      : "problem"}
                  </b>

                  <span>
                    {surface.endpoint}
                  </span>
                </div>

                <details>
                  <summary>
                    technical details
                  </summary>

                  <pre>
                    {JSON.stringify(
                      surface.value,
                      null,
                      2
                    )}
                  </pre>
                </details>
              </article>
            )
          }
        )}
      </div>

      {loading && (
        <div className="system-refreshing">
          checking services…
        </div>
      )}
    </section>
  )
}
