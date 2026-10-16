import {
  useEffect,
  useMemo,
  useState
} from "react";

import SpaceScene from "./space-scene.jsx";
import SceneOverlay from "../components/scene-overlay.jsx";
import { getQualityProfile } from "../lib/quality.js";

import "../styles/scene-overlay.css";

const validModes = new Set([
  "earth",
  "transit",
  "moon",
  "gateway"
]);

export default function SpaceSceneShell() {
  const quality = useMemo(
    () => getQualityProfile(),
    []
  );

  const [mode, setMode] = useState(
    "earth"
  );

  useEffect(() => {
    if (typeof window === "undefined") {
      return undefined;
    }

    function readSceneMode() {
      const hash = window.location.hash
        .replace("#", "")
        .trim()
        .toLowerCase();

      if (validModes.has(hash)) {
        setMode(hash);
      }
    }

    readSceneMode();

    window.addEventListener(
      "hashchange",
      readSceneMode
    );

    return () => {
      window.removeEventListener(
        "hashchange",
        readSceneMode
      );
    };
  }, []);

  function selectMode(nextMode) {
    if (!validModes.has(nextMode)) {
      return;
    }

    setMode(nextMode);

    if (typeof window !== "undefined") {
      window.history.replaceState(
        {},
        "",
        `${window.location.pathname}${window.location.search}#${nextMode}`
      );
    }
  }

  return (
    <div
      className="space-scene-shell"
      data-scene-mode={mode}
    >
      <SpaceScene />

      <SceneOverlay
        mode={mode}
        quality={quality.tier}
        onModeChange={selectMode}
      />
    </div>
  );
}
