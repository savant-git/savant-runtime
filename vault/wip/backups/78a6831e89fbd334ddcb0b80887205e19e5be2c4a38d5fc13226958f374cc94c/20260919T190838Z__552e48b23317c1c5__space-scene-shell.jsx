import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState
} from "react";

import SpaceScene from "./space-scene.jsx";
import SceneOverlay from "../components/scene-overlay.jsx";
import CinematicFlightConsole from "../components/cinematic-flight-console.jsx";

import {
  CinematicObjectInspector,
  CinematicObjectInteractionProvider
} from "./cinematic-object-interaction.jsx";

import CinematicSelectionBridge from "./cinematic-selection-bridge.jsx";

import {
  createCameraState,
  useCinematicPointerControls
} from "./cinematic-environment.jsx";

import {
  getQualityProfile
} from "../lib/quality.js";

import "../styles/scene-overlay.css";
import "../styles/cinematic-environment.css";
import "../styles/flight-console.css";
import "../styles/object-inspector.css";

const sceneModes = {
  earth: {
    id: "earth",
    yaw: -0.22,
    pitch: -0.04,
    label: "EARTH"
  },

  transit: {
    id: "transit",
    yaw: 0,
    pitch: 0,
    label: "TRANSIT"
  },

  moon: {
    id: "moon",
    yaw: 0.31,
    pitch: 0.035,
    label: "MOON"
  },

  gateway: {
    id: "gateway",
    yaw: 0.24,
    pitch: 0.17,
    label: "GATEWAY"
  }
};

const modeOrder = [
  "earth",
  "transit",
  "moon",
  "gateway"
];

function normalizeMode(
  value
) {
  return Object.prototype
    .hasOwnProperty.call(
      sceneModes,
      value
    )
    ? value
    : "transit";
}

function readHashMode() {
  if (
    typeof window ===
    "undefined"
  ) {
    return "transit";
  }

  return normalizeMode(
    window.location.hash
      .replace(/^#/, "")
      .trim()
      .toLowerCase()
  );
}

function SceneModeTransition({
  mode
}) {
  const previousMode =
    useRef(mode);

  const [
    transitioning,
    setTransitioning
  ] = useState(false);

  useEffect(() => {
    if (
      previousMode.current ===
      mode
    ) {
      return undefined;
    }

    previousMode.current =
      mode;

    setTransitioning(
      true
    );

    const timer =
      window.setTimeout(
        () => {
          setTransitioning(
            false
          );
        },
        720
      );

    return () => {
      window.clearTimeout(
        timer
      );
    };
  }, [mode]);

  return (
    <div
      className={[
        "cinematic-mode-transition",
        transitioning
          ? "is-transitioning"
          : ""
      ]
        .filter(Boolean)
        .join(" ")}
      data-mode={mode}
      aria-hidden="true"
    >
      <div className="cinematic-mode-transition__veil" />

      <div className="cinematic-mode-transition__line" />

      <div className="cinematic-mode-transition__label">
        <span>
          NAVIGATION VECTOR
        </span>

        <strong>
          {
            sceneModes[
              mode
            ].label
          }
        </strong>
      </div>
    </div>
  );
}

function CameraAffordance({
  mode,
  cameraState
}) {
  const [
    dragging,
    setDragging
  ] = useState(false);

  useEffect(() => {
    let frame = 0;

    const update =
      () => {
        const next =
          Boolean(
            cameraState
              .current
              .dragging
          );

        setDragging(
          current =>
            current ===
            next
              ? current
              : next
        );

        frame =
          window.requestAnimationFrame(
            update
          );
      };

    frame =
      window.requestAnimationFrame(
        update
      );

    return () => {
      window.cancelAnimationFrame(
        frame
      );
    };
  }, [cameraState]);

  return (
    <div
      className={[
        "cinematic-camera-affordance",
        dragging
          ? "is-dragging"
          : ""
      ]
        .filter(Boolean)
        .join(" ")}
      aria-hidden="true"
    >
      <span className="cinematic-camera-affordance__axis">
        POV
      </span>

      <span className="cinematic-camera-affordance__mode">
        {
          sceneModes[
            mode
          ].label
        }
      </span>

      <span className="cinematic-camera-affordance__instruction">
        {dragging
          ? "FREE LOOK ACTIVE"
          : "DRAG TO LOOK"}
      </span>
    </div>
  );
}

function ShellContent() {
  const interactionRef =
    useRef(null);

  const cameraState =
    useRef(
      createCameraState()
    );

  const quality =
    useMemo(
      () =>
        getQualityProfile(),
      []
    );

  const [
    mode,
    setMode
  ] = useState(
    readHashMode
  );

  useCinematicPointerControls(
    interactionRef,
    cameraState
  );

  const applyCameraPreset =
    useCallback(
      (
        nextMode,
        immediate = false
      ) => {
        const preset =
          sceneModes[
            normalizeMode(
              nextMode
            )
          ];

        const state =
          cameraState.current;

        state.targetYaw =
          preset.yaw;

        state.targetPitch =
          preset.pitch;

        state.yawVelocity =
          immediate
            ? 0
            : (
                preset.yaw -
                state.yaw
              ) *
              0.45;

        state.pitchVelocity =
          immediate
            ? 0
            : (
                preset.pitch -
                state.pitch
              ) *
              0.45;

        if (immediate) {
          state.yaw =
            preset.yaw;

          state.pitch =
            preset.pitch;
        }
      },
      []
    );

  const selectMode =
    useCallback(
      (
        requestedMode,
        options = {}
      ) => {
        const nextMode =
          normalizeMode(
            requestedMode
          );

        setMode(
          nextMode
        );

        applyCameraPreset(
          nextMode,
          Boolean(
            options.immediate
          )
        );

        if (
          typeof window !==
            "undefined" &&
          options.writeHash !==
            false
        ) {
          const nextHash =
            `#${nextMode}`;

          if (
            window.location.hash !==
            nextHash
          ) {
            window.history
              .replaceState(
                null,
                "",
                nextHash
              );
          }
        }
      },
      [applyCameraPreset]
    );

  const resetCamera =
    useCallback(() => {
      applyCameraPreset(
        mode,
        false
      );
    }, [
      applyCameraPreset,
      mode
    ]);

  useEffect(() => {
    applyCameraPreset(
      mode,
      true
    );
  }, [
    applyCameraPreset,
    mode
  ]);

  useEffect(() => {
    const onHashChange =
      () => {
        const nextMode =
          readHashMode();

        setMode(
          nextMode
        );

        applyCameraPreset(
          nextMode,
          false
        );
      };

    window.addEventListener(
      "hashchange",
      onHashChange
    );

    return () => {
      window.removeEventListener(
        "hashchange",
        onHashChange
      );
    };
  }, [applyCameraPreset]);

  useEffect(() => {
    const onKeyDown =
      event => {
        const target =
          event.target;

        if (
          target instanceof
            HTMLElement &&
          (
            target.matches(
              "input, textarea, select, button"
            ) ||
            target.isContentEditable
          )
        ) {
          return;
        }

        if (
          event.key === "1"
        ) {
          selectMode(
            "earth"
          );
        }

        if (
          event.key === "2"
        ) {
          selectMode(
            "transit"
          );
        }

        if (
          event.key === "3"
        ) {
          selectMode(
            "moon"
          );
        }

        if (
          event.key === "4"
        ) {
          selectMode(
            "gateway"
          );
        }

        if (
          event.key
            .toLowerCase() ===
          "r"
        ) {
          resetCamera();
        }

        if (
          event.key === "["
        ) {
          const index =
            modeOrder.indexOf(
              mode
            );

          selectMode(
            modeOrder[
              (
                index -
                1 +
                modeOrder.length
              ) %
                modeOrder.length
            ]
          );
        }

        if (
          event.key === "]"
        ) {
          const index =
            modeOrder.indexOf(
              mode
            );

          selectMode(
            modeOrder[
              (
                index +
                1
              ) %
                modeOrder.length
            ]
          );
        }
      };

    window.addEventListener(
      "keydown",
      onKeyDown
    );

    return () => {
      window.removeEventListener(
        "keydown",
        onKeyDown
      );
    };
  }, [
    mode,
    resetCamera,
    selectMode
  ]);

  return (
    <div
      className="space-scene-shell"
      data-scene-mode={
        mode
      }
      data-quality={
        quality.tier
      }
    >
      <CinematicSelectionBridge
        onModeRequest={
          selectMode
        }
      />

      <SpaceScene
        externalCameraState={
          cameraState
        }
        mode={mode}
      />

      <div
        className="cinematic-interaction-surface"
        aria-hidden="true"
        data-scene-mode={
          mode
        }
        onDoubleClick={
          resetCamera
        }
        ref={
          interactionRef
        }
      />

      <div
        className="cinematic-atmospheric-glass"
        aria-hidden="true"
      />

      <div
        className="cinematic-optical-frame"
        aria-hidden="true"
      >
        <span className="cinematic-optical-frame__corner cinematic-optical-frame__corner--tl" />
        <span className="cinematic-optical-frame__corner cinematic-optical-frame__corner--tr" />
        <span className="cinematic-optical-frame__corner cinematic-optical-frame__corner--bl" />
        <span className="cinematic-optical-frame__corner cinematic-optical-frame__corner--br" />
      </div>

      <SceneModeTransition
        mode={mode}
      />

      <SceneOverlay
        mode={mode}
        quality={
          quality.tier
        }
        onModeChange={
          selectMode
        }
      />

      <CinematicFlightConsole
        mode={mode}
        cameraState={
          cameraState
        }
        quality={
          quality.tier
        }
        onModeChange={
          selectMode
        }
      />

      <CinematicObjectInspector />

      <CameraAffordance
        mode={mode}
        cameraState={
          cameraState
        }
      />
    </div>
  );
}

export default function SpaceSceneShell() {
  return (
    <CinematicObjectInteractionProvider>
      <ShellContent />
    </CinematicObjectInteractionProvider>
  );
}
