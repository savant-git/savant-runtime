import React from "react"
import type {SavantMarkMode} from "./savant-mark-types"
function MarkFallback({
  mode,
}: {
  mode: SavantMarkMode
}) {
  return (
    <div
      className={
        "savant-mark__fallback " +
        `savant-mark__fallback--${mode}`
      }
      aria-hidden="true"
    >
      s
    </div>
  )
}


export class SavantMarkBoundary
  extends React.Component<
    {
      mode: SavantMarkMode
      children: React.ReactNode
    },
    {
      failed: boolean
    }
  > {
  state = {
    failed: false,
  }

  static getDerivedStateFromError() {
    return {
      failed: true,
    }
  }

  componentDidCatch(
    error: unknown,
  ) {
    console.error(
      "savant mark failed to load",
      error,
    )
  }

  render() {
    if (
      this.state.failed
    ) {
      return (
        <MarkFallback
          mode={
            this.props.mode
          }
        />
      )
    }

    return this.props.children
  }
}
