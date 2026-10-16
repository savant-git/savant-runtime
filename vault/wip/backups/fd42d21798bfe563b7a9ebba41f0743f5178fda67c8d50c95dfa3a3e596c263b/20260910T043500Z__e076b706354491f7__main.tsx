import React from "react"
import ReactDOM from "react-dom/client"
import App from "./App"
import "./styles.css"
import "./styles-palaver-advanced.css"
import "./styles-palaver-conversation.css"
import "./styles-palaver-focus.css"

ReactDOM.createRoot(
  document.getElementById(
    "root",
  )!,
).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)
