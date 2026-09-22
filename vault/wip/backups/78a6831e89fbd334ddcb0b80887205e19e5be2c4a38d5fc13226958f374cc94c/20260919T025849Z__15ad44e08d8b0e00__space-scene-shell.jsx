import {
  useEffect,
  useMemo,
  useRef,
  useState
} from "react";

import SpaceScene from "./space-scene.jsx";
import SceneOverlay from "../components/scene-overlay.jsx";

import {
  createCameraState,
  useCinematicPointerControls
} from "./cinematic-environment.jsx";

import {
  getQualityProfile
} from "../lib/quality.js";

import "../styles/scene-overlay.css";
import "../styles/cinematic-environment.css";

const validModes = new Set([
  "earth",
  "transit",
  "moon",
  "gateway"
]);

export default function SpaceSceneShell() {
  const rootRef = useRef(null);

  const cameraState = useRef(
    createCameraState()
  );

  const quality = useMemo(
    () => getQualityProfile(),
    []
  );

  const reducedMotion =
    useMemo(
      () =>
        window.matchMedia(
          "(prefers-reduced-motion: reduce)"
        ).matches,
      []
    );

  const [mode, setMode] =
    useState("earth");

  useCinematicPointerControls(
    rootRef,
    cameraState,
    reducedMotion
  );

  useEffect(() => {
    function readMode() {
      const hash =
        window.location.hash
          .slice(1)
          .toLowerCase();

      if (validModes.has(hash)) {
        setMode(hash);
      }
    }

    readMode();

    window.addEventListener(
      "hashchange",
      readMode
    );

    return () =>
      window.removeEventListener(
        "hashchange",
        readMode
      );
  }, []);

  function selectMode(nextMode) {
    if (!validModes.has(nextMode)) {
      return;
    }

    setMode(nextMode);

    const targets = {
      earth: {
        yaw: -0.16,
        pitch: 0.02
      },
      transit: {
        yaw: 0.04,
        pitch: 0
      },
      moon: {
        yaw: 0.34,
        pitch: 0.045
      },
      gateway: {
        yaw: 0.2,
        pitch: 0.16
      }
    };

    const target =
      targets[nextMode];

    cameraState.current.targetYaw =
      target.yaw;

    cameraState.current.targetPitch =
      target.pitch;

    window.history.replaceState(
      {},
      "",
      `${window.location.pathname}${window.location.search}#${nextMode}`
    );
  }

  return (
    <div
      ref={rootRef}
      className="space-scene-shell"
      data-scene-mode={mode}
      data-quality={quality.tier}
    >
      <SpaceScene
        externalCameraState={
          cameraState
        }
      />

      <SceneOverlay
        mode={mode}
        quality={quality.tier}
        onModeChange={selectMode}
      />

      <div
        className="cinematic-camera-affordance"
        aria-hidden="true"
      >
        <i />

        <span>
          DRAG TO LOOK
        </span>
      </div>
    </div>
  );
}
