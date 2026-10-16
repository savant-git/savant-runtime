import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState
} from "react";

import SpaceScene from "./space-scene.jsx";

import SceneOverlay from "../components/scene-overlay.jsx";

import {
  CinematicObjectInspector,
  CinematicObjectInteractionProvider
} from "./cinematic-object-interaction.jsx";

import CinematicSelectionBridge from "./cinematic-selection-bridge.jsx";

import {
  createCameraState
} from "./cinematic-environment.jsx";

import {
  getQualityProfile
} from "../lib/quality.js";

import "../styles/scene-overlay.css";
import "../styles/cinematic-environment.css";
import "../styles/object-inspector.css";
import "../styles/mobile-stabilization.css";

const modes =
  Object.freeze({
    earth: Object.freeze({
      yaw: -0.22,
      pitch: -0.04
    }),

    transit: Object.freeze({
      yaw: 0,
      pitch: 0
    }),

    moon: Object.freeze({
      yaw: 0.31,
      pitch: 0.035
    }),

    gateway: Object.freeze({
      yaw: 0.24,
      pitch: 0.17
    })
  });

function normalizeMode(
  value
) {
  return Object.prototype
    .hasOwnProperty.call(
      modes,
      value
    )
    ? value
    : "transit";
}

function initialMode() {
  if (
    typeof window ===
    "undefined"
  ) {
    return "transit";
  }

  return normalizeMode(
    window.location.hash
      .replace(
        /^#/,
        ""
      )
      .toLowerCase()
  );
}

function Shell() {
  const shellRef =
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
    initialMode
  );

  const setCameraMode =
    useCallback(
      (
        nextMode,
        immediate = false
      ) => {
        const normalized =
          normalizeMode(
            nextMode
          );

        const preset =
          modes[
            normalized
          ];

        const state =
          cameraState.current;

        setMode(
          normalized
        );

        state.targetYaw =
          preset.yaw;

        state.targetPitch =
          preset.pitch;

        if (
          immediate
        ) {
          state.yaw =
            preset.yaw;

          state.pitch =
            preset.pitch;

          state.yawVelocity =
            0;

          state.pitchVelocity =
            0;
        }

        if (
          typeof window !==
          "undefined"
        ) {
          const hash =
            `#${normalized}`;

          if (
            window.location.hash !==
            hash
          ) {
            window.history
              .replaceState(
                null,
                "",
                hash
              );
          }
        }
      },
      []
    );

  useEffect(() => {
    setCameraMode(
      mode,
      true
    );
  }, []);

  useEffect(() => {
    const element =
      shellRef.current;

    if (!element) {
      return undefined;
    }

    let pointerId =
      null;

    let previousX =
      0;

    let previousY =
      0;

    const ignored =
      "a,button,input,textarea,select,[role='button'],[contenteditable='true']";

    const pointerDown =
      event => {
        if (
          event.button !==
            undefined &&
          event.button !== 0
        ) {
          return;
        }

        if (
          event.target instanceof
            Element &&
          event.target.closest(
            ignored
          )
        ) {
          return;
        }

        pointerId =
          event.pointerId;

        previousX =
          event.clientX;

        previousY =
          event.clientY;

        cameraState.current.dragging =
          true;

        element.setPointerCapture?.(
          pointerId
        );
      };

    const pointerMove =
      event => {
        if (
          pointerId ===
            null ||
          event.pointerId !==
            pointerId
        ) {
          return;
        }

        const dx =
          event.clientX -
          previousX;

        const dy =
          event.clientY -
          previousY;

        previousX =
          event.clientX;

        previousY =
          event.clientY;

        const state =
          cameraState.current;

        const sensitivity =
          quality.tier ===
          "low"
            ? 0.0027
            : 0.00225;

        state.targetYaw =
          THREEClamp(
            state.targetYaw -
              dx *
                sensitivity,
            -0.72,
            0.72
          );

        state.targetPitch =
          THREEClamp(
            state.targetPitch -
              dy *
                sensitivity,
            -0.38,
            0.38
          );

        state.yawVelocity =
          -dx *
          sensitivity *
          5;

        state.pitchVelocity =
          -dy *
          sensitivity *
          5;
      };

    const pointerEnd =
      event => {
        if (
          pointerId ===
            null ||
          event.pointerId !==
            pointerId
        ) {
          return;
        }

        cameraState.current.dragging =
          false;

        element.releasePointerCapture?.(
          pointerId
        );

        pointerId =
          null;
      };

    element.addEventListener(
      "pointerdown",
      pointerDown,
      {
        passive: true
      }
    );

    element.addEventListener(
      "pointermove",
      pointerMove,
      {
        passive: true
      }
    );

    element.addEventListener(
      "pointerup",
      pointerEnd,
      {
        passive: true
      }
    );

    element.addEventListener(
      "pointercancel",
      pointerEnd,
      {
        passive: true
      }
    );

    return () => {
      element.removeEventListener(
        "pointerdown",
        pointerDown
      );

      element.removeEventListener(
        "pointermove",
        pointerMove
      );

      element.removeEventListener(
        "pointerup",
        pointerEnd
      );

      element.removeEventListener(
        "pointercancel",
        pointerEnd
      );
    };
  }, [
    quality.tier
  ]);

  useEffect(() => {
    const hashChange =
      () => {
        setCameraMode(
          initialMode()
        );
      };

    window.addEventListener(
      "hashchange",
      hashChange
    );

    return () => {
      window.removeEventListener(
        "hashchange",
        hashChange
      );
    };
  }, [
    setCameraMode
  ]);

  return (
    <div
      ref={shellRef}
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
          setCameraMode
        }
      />

      <SpaceScene
        externalCameraState={
          cameraState
        }
        mode={mode}
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

      <SceneOverlay
        mode={mode}
        quality={
          quality.tier
        }
        onModeChange={
          setCameraMode
        }
      />

      <CinematicObjectInspector />
    </div>
  );
}

function THREEClamp(
  value,
  minimum,
  maximum
) {
  return Math.max(
    minimum,
    Math.min(
      maximum,
      value
    )
  );
}

export default function SpaceSceneShell() {
  return (
    <CinematicObjectInteractionProvider>
      <Shell />
    </CinematicObjectInteractionProvider>
  );
}
