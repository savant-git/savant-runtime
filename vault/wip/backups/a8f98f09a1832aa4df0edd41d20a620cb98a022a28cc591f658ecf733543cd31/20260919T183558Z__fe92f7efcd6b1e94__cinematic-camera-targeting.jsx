import {
  useEffect,
  useRef
} from "react";

import {
  useFrame
} from "@react-three/fiber";

import * as THREE from "three";

import {
  useCinematicObjectInteraction
} from "./cinematic-object-interaction.jsx";

const targetProfiles = {
  orion: {
    yaw: -0.105,
    pitch: 0.105,
    fovBias: -2.4
  },

  gateway: {
    yaw: 0.245,
    pitch: 0.175,
    fovBias: -2.1
  },

  lander: {
    yaw: 0.29,
    pitch: -0.095,
    fovBias: -1.8
  }
};

export default function CinematicCameraTargeting({
  cameraState,
  reducedMotion
}) {
  const {
    selectedObject
  } =
    useCinematicObjectInteraction();

  const previousSelection =
    useRef(null);

  const restoreTarget =
    useRef({
      yaw: 0,
      pitch: 0
    });

  const lockStrength =
    useRef(0);

  useEffect(() => {
    if (
      !cameraState?.current
    ) {
      return;
    }

    const state =
      cameraState.current;

    if (
      selectedObject &&
      !previousSelection.current
    ) {
      restoreTarget.current = {
        yaw:
          Number.isFinite(
            state.targetYaw
          )
            ? state.targetYaw
            : state.yaw || 0,

        pitch:
          Number.isFinite(
            state.targetPitch
          )
            ? state.targetPitch
            : state.pitch || 0
      };
    }

    if (
      !selectedObject &&
      previousSelection.current
    ) {
      state.targetYaw =
        restoreTarget.current
          .yaw;

      state.targetPitch =
        restoreTarget.current
          .pitch;
    }

    previousSelection.current =
      selectedObject;
  }, [
    cameraState,
    selectedObject
  ]);

  useFrame(
    (
      frameState,
      delta
    ) => {
      if (
        !cameraState?.current
      ) {
        return;
      }

      const state =
        cameraState.current;

      const profile =
        selectedObject
          ? targetProfiles[
              selectedObject
            ]
          : null;

      const targetStrength =
        profile
          ? 1
          : 0;

      lockStrength.current =
        THREE.MathUtils.damp(
          lockStrength.current,
          targetStrength,
          reducedMotion
            ? 12
            : 4.8,
          delta
        );

      state.focusLock =
        lockStrength.current;

      state.focusTarget =
        selectedObject ||
        null;

      state.fovBias =
        THREE.MathUtils.damp(
          Number.isFinite(
            state.fovBias
          )
            ? state.fovBias
            : 0,
          profile
            ? profile.fovBias
            : 0,
          4.2,
          delta
        );

      if (!profile) {
        return;
      }

      const dragOverride =
        state.dragging
          ? 0.12
          : 1;

      const strength =
        lockStrength.current *
        dragOverride;

      state.targetYaw =
        THREE.MathUtils.damp(
          Number.isFinite(
            state.targetYaw
          )
            ? state.targetYaw
            : state.yaw || 0,
          profile.yaw,
          3.2 *
            strength,
          delta
        );

      state.targetPitch =
        THREE.MathUtils.damp(
          Number.isFinite(
            state.targetPitch
          )
            ? state.targetPitch
            : state.pitch || 0,
          profile.pitch,
          3.2 *
            strength,
          delta
        );

      if (
        !reducedMotion &&
        !state.dragging
      ) {
        const breathing =
          Math.sin(
            frameState.clock
              .elapsedTime *
              0.34
          ) *
          0.0008 *
          lockStrength.current;

        state.targetPitch +=
          breathing;
      }
    }
  );

  return null;
}
