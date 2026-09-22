import React from "react"
import ReactDOM from "react-dom/client"
import App from "./App"
import {
  installPalaverSessionTransport,
} from "./palaver/runtime/session-transport"
import "./styles.css"

installPalaverSessionTransport()

ReactDOM.createRoot(
  document.getElementById("root")!
).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
)
