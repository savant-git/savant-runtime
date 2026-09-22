import {
  createRoot
} from "react-dom/client";

import App from "./app.jsx";

import "./styles/base.css";
import "./styles/global.css";
import "./styles/mobile-stabilization.css";

const root =
  document.getElementById(
    "root"
  );

if (!root) {
  throw new Error(
    "Artemis root element was not found."
  );
}

createRoot(root).render(
  <App />
);
