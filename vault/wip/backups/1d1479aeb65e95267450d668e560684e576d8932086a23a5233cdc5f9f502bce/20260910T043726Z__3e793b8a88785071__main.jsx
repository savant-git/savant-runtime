import React from "react"
import ReactDOM from "react-dom/client"

import "@xterm/xterm/css/xterm.css"

import "./styles.css"
import "./styles/terminal.css"
import "./styles/workstation.css"
import "./styles/modules.css"
import "./styles/expansion.css"
import "./styles/cinematic.css"
import "./styles/interaction.css"
import "./styles/chat-enhanced.css"


const rootElement =
  document.getElementById(
    "root"
  )


if (!rootElement) {
  throw new Error(
    "palaver root element is missing"
  )
}


const root =
  ReactDOM.createRoot(
    rootElement
  )


function BootSurface({
  title,
  message,
  error = false
}) {
  return (
    <main
      style={{
        width:
          "100vw",

        minHeight:
          "100dvh",

        boxSizing:
          "border-box",

        margin:
          0,

        padding:
          "24px",

        background:
          "#030407",

        color:
          "#ece8dc",

        fontFamily:
          (
            "ui-monospace, "
            + "SFMono-Regular, "
            + "Menlo, Monaco, "
            + "Consolas, monospace"
          )
      }}
    >
      <div
        style={{
          maxWidth:
            "760px",

          margin:
            "12vh auto 0"
        }}
      >
        <h1
          style={{
            margin:
              "0 0 14px",

            fontSize:
              "18px",

            fontWeight:
              600,

            letterSpacing:
              ".08em"
          }}
        >
          {title}
        </h1>

        <pre
          style={{
            margin:
              0,

            whiteSpace:
              "pre-wrap",

            overflowWrap:
              "anywhere",

            color:
              error
                ? "#d57b7b"
                : (
                  "rgba("
                  + "236,232,220,.62"
                  + ")"
                ),

            fontSize:
              "13px",

            lineHeight:
              1.6
          }}
        >
          {message}
        </pre>
      </div>
    </main>
  )
}


function showBoot() {
  root.render(
    <BootSurface
      title="palaver"
      message={
        "loading workspace…"
      }
    />
  )
}


function showFailure(
  stage,
  failure
) {
  const message =
    failure
    instanceof Error
      ? (
        `${failure.name}: `
        + `${failure.message}\n\n`
        + (
          failure.stack
          || ""
        )
      )
      : String(
          failure
        )

  console.error(
    (
      `palaver ${stage} `
      + "failure"
    ),
    failure
  )

  root.render(
    <BootSurface
      title={
        "palaver boot failure"
      }
      message={
        `${stage}\n\n${message}`
      }
      error
    />
  )
}


class PalaverBoundary
  extends React.Component {
  constructor(
    props
  ) {
    super(
      props
    )

    this.state = {
      error:
        null
    }
  }


  static getDerivedStateFromError(
    error
  ) {
    return {
      error
    }
  }


  componentDidCatch(
    error,
    info
  ) {
    console.error(
      (
        "palaver render "
        + "failure"
      ),
      error,
      info
    )
  }


  render() {
    if (
      !this.state.error
    ) {
      return this.props
        .children
    }

    const failure =
      this.state.error

    const message =
      failure
      instanceof Error
        ? (
          `${failure.name}: `
          + `${failure.message}\n\n`
          + (
            failure.stack
            || ""
          )
        )
        : String(
            failure
          )

    return (
      <BootSurface
        title={
          "palaver render failure"
        }
        message={
          message
        }
        error
      />
    )
  }
}


async function bootPalaver() {
  showBoot()

  let App

  try {
    const appModule =
      await import(
        "./App.tsx"
      )

    App =
      appModule.default

    if (
      typeof App
      !== "function"
      && typeof App
      !== "object"
    ) {
      throw new Error(
        (
          "App.tsx did not "
          + "export a usable "
          + "default component"
        )
      )
    }
  } catch (
    error
  ) {
    showFailure(
      "application import",
      error
    )

    return
  }


  try {
    root.render(
      <React.StrictMode>
        <PalaverBoundary>
          <App />
        </PalaverBoundary>
      </React.StrictMode>
    )
  } catch (
    error
  ) {
    showFailure(
      "application render",
      error
    )
  }
}


bootPalaver()
  .catch(
    error => {
      showFailure(
        "bootstrap",
        error
      )
    }
  )
