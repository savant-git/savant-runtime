import React from "react"
import type {SavantMarkMode} from "./savant-mark-types"

type Props = {
  mode: SavantMarkMode
  children: React.ReactNode
}

type State = {
  failed: boolean
  message: string
}

function errorMessage(error: unknown): string {
  if (error instanceof Error) {
    return error.message || error.name
  }

  try {
    return typeof error === "string" ? error : String(error)
  } catch {
    return "Unknown logo rendering error"
  }
}

export class SavantMarkBoundary extends React.Component<Props, State> {
  state: State = {
    failed: false,
    message: "",
  }

  static getDerivedStateFromError(error: unknown): State {
    return {
      failed: true,
      message: errorMessage(error),
    }
  }

  componentDidCatch(error: unknown, info: React.ErrorInfo) {
    console.error(
      "savant logo rendering failed",
      error,
      info.componentStack,
    )
  }

  render() {
    if (!this.state.failed) {
      return this.props.children
    }

    return (
      <div
        className={
          "savant-mark__fallback savant-mark__fallback--" +
          this.props.mode
        }
        role="alert"
        style={{
          position: "relative",
          zIndex: 100,
          pointerEvents: "auto",
          display: "flex",
          flexDirection: "column",
          alignItems: "stretch",
          justifyContent: "center",
          width: "100%",
          height: "100%",
          boxSizing: "border-box",
          padding: 8,
          overflow: "auto",
          color: "#f0d59e",
          background: "#132026",
          fontSize: 12,
          lineHeight: 1.4,
          textTransform: "none",
          letterSpacing: "normal",
        }}
      >
        <strong style={{fontSize: 12}}>
          Logo rendering failed
        </strong>

        <pre
          style={{
            margin: "6px 0",
            whiteSpace: "pre-wrap",
            overflowWrap: "anywhere",
            userSelect: "text",
            font: "11px/1.4 monospace",
          }}
        >
          {this.state.message}
        </pre>

        <button
          type="button"
          onClick={event => {
            event.stopPropagation()
            this.setState({
              failed: false,
              message: "",
            })
          }}
          style={{
            position: "relative",
            zIndex: 101,
            pointerEvents: "auto",
            minHeight: 36,
            border: "1px solid #b99a65",
            borderRadius: 6,
            background: "#20323a",
            color: "#f0d59e",
            fontSize: 12,
          }}
        >
          Retry logo
        </button>
      </div>
    )
  }
}
