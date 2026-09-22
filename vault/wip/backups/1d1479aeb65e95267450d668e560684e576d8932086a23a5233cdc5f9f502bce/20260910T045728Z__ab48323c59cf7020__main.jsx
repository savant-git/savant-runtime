import React from "react"
import ReactDOM from "react-dom/client"
import App from "./App"
import "./styles.css"
import "./styles-palaver-advanced.css"
import "./styles-palaver-conversation.css"
import "./styles-palaver-focus.css"
import "./styles-palaver-finish.css"
import "./styles-palaver-production.css"
import "./styles-palaver-signature.css"
import "./styles-palaver-patch-review.css"
import "./styles-palaver-help.css"

const rootElement =
  document.getElementById("root")

if (!rootElement) {
  throw new Error(
    "palaver root element is missing",
  )
}

ReactDOM.createRoot(
  rootElement,
).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)
