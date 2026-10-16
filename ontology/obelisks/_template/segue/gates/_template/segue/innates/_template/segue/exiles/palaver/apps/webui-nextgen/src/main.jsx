import React, { Suspense, lazy } from "react";
import ReactDOM from "react-dom/client";

import "@xterm/xterm/css/xterm.css";

import {
  installPalaverSessionTransport,
} from "./palaver/runtime/session-transport.ts";

import "./styles.css";
import "./styles/terminal.css";
import "./styles/workstation.css";
import "./styles/modules.css";
import "./styles/expansion.css";
import "./styles/cinematic.css";
import "./styles/interaction.css";
import "./styles/chat-enhanced.css";
import "./styles/mobile.css";

const SavantMark = lazy(
  () => import("./palaver/brand/savant-mark.tsx"),
);

const rootElement = document.getElementById("root");

if (!rootElement) {
  throw new Error("palaver root element is missing");
}

const root = ReactDOM.createRoot(rootElement);

function describeFailure(failure) {
  return failure instanceof Error
    ? `${failure.name}: ${failure.message}\n\n${failure.stack || ""}`
    : String(failure);
}

class MarkBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { failed: false };
  }

  static getDerivedStateFromError() {
    return { failed: true };
  }

  componentDidCatch(error) {
    console.error("palaver boot mark failure", error);
  }

  render() {
    return this.state.failed
      ? <span style={{ color: "#b08b45", fontSize: 32 }}>savant</span>
      : this.props.children;
  }
}

function BootSurface({ title, message, error = false }) {
  return (
    <main
      aria-busy={!error}
      style={{
        width: "100%",
        height: "100dvh",
        boxSizing: "border-box",
        margin: 0,
        padding: 24,
        overflow: "auto",
        background: "#07090b",
        color: "#e6e1d6",
        fontFamily: '"Arial Narrow", "Roboto Condensed", sans-serif',
        display: "grid",
        placeItems: "center",
      }}
    >
      <section style={{ width: "min(100%, 760px)" }}>
        {!error && (
          <div
            style={{
              minHeight: "min(60vh, 390px)",
              display: "grid",
              placeItems: "center",
              paddingBottom: 64,
              boxSizing: "border-box",
            }}
          >
            <MarkBoundary>
              <Suspense
                fallback={
                  <span style={{ color: "#b08b45", letterSpacing: ".2em" }}>
                    savant
                  </span>
                }
              >
                <SavantMark
                  mode="preloader"
                  state="thinking"
                  label="palaver"
                  active
                />
              </Suspense>
            </MarkBoundary>
          </div>
        )}

        <h1
          style={{
            margin: "0 0 14px",
            fontSize: 18,
            fontWeight: 600,
            letterSpacing: ".12em",
            textTransform: "lowercase",
            textAlign: error ? "left" : "center",
          }}
        >
          {title}
        </h1>

        <pre
          role={error ? "alert" : "status"}
          aria-live={error ? "assertive" : "polite"}
          style={{
            margin: 0,
            whiteSpace: "pre-wrap",
            overflowWrap: "anywhere",
            color: error ? "#d57b7b" : "#a9aaa4",
            fontFamily: "ui-monospace, monospace",
            fontSize: 13,
            lineHeight: 1.6,
            textAlign: error ? "left" : "center",
          }}
        >
          {message}
        </pre>
      </section>
    </main>
  );
}

function showFailure(stage, failure) {
  console.error(`palaver ${stage} failure`, failure);
  root.render(
    <BootSurface
      title="palaver boot failure"
      message={`${stage}\n\n${describeFailure(failure)}`}
      error
    />,
  );
}

class PalaverBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { error: null };
  }

  static getDerivedStateFromError(error) {
    return { error };
  }

  componentDidCatch(error, info) {
    console.error("palaver render failure", error, info);
  }

  render() {
    return this.state.error
      ? (
        <BootSurface
          title="palaver render failure"
          message={describeFailure(this.state.error)}
          error
        />
      )
      : this.props.children;
  }
}

async function bootPalaver() {
  root.render(
    <BootSurface
      title="palaver"
      message="loading cognitive workspace…"
    />,
  );

  try {
    installPalaverSessionTransport();
  } catch (error) {
    showFailure("session transport", error);
    return;
  }

  let App;

  try {
    const appModule = await import("./App.tsx");
    App = appModule.default;

    if (typeof App !== "function" && typeof App !== "object") {
      throw new Error("App.tsx did not export a usable default component");
    }
  } catch (error) {
    showFailure("advanced application import", error);
    return;
  }

  try {
    root.render(
      <React.StrictMode>
        <PalaverBoundary>
          <App />
        </PalaverBoundary>
      </React.StrictMode>,
    );
  } catch (error) {
    showFailure("advanced application render", error);
  }
}

bootPalaver().catch(error => showFailure("bootstrap", error));
