import {
  Component,
  type ErrorInfo,
  type ReactNode,
} from "react"
import {
  RefreshCw,
  TriangleAlert,
} from "lucide-react"

type Props = {
  children: ReactNode
}

type State = {
  failed: boolean
  message: string
}

export default class PalaverBoundary extends Component<
  Props,
  State
> {
  state: State = {
    failed: false,
    message: "",
  }

  static getDerivedStateFromError(
    error: unknown,
  ): State {
    return {
      failed: true,
      message:
        error instanceof Error
          ? error.message
          : String(error),
    }
  }

  componentDidCatch(
    error: unknown,
    info: ErrorInfo,
  ) {
    console.error(
      "palaver presentation failure",
      error,
      info,
    )
  }

  private reload = () => {
    window.location.reload()
  }

  render() {
    if (!this.state.failed) {
      return this.props.children
    }

    return (
      <main
        className="palaver-boundary"
        role="alert"
      >
        <section className="palaver-boundary-card">
          <span className="palaver-boundary-kicker">
            <TriangleAlert
              size={15}
              aria-hidden="true"
            />
            presentation interrupted
          </span>

          <h1>
            palaver is still there.
          </h1>

          <p>
            The browser presentation failed before
            it could finish rendering. No recovery
            action here mutates SAVANT runtime state.
          </p>

          {this.state.message && (
            <pre>
              {this.state.message}
            </pre>
          )}

          <button
            type="button"
            onClick={this.reload}
          >
            <RefreshCw
              size={15}
              aria-hidden="true"
            />
            reload palaver
          </button>
        </section>
      </main>
    )
  }
}
