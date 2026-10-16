import {
  useEffect,
  useRef
} from "react";

import {
  useFrame,
  useThree
} from "@react-three/fiber";

const sampleWindow = 1.5;
const badWindowsToDrop = 2;
const goodWindowsToRecover = 6;

const thresholds = {
  high: {
    drop: 42,
    recover: 56,
    minimumDpr: 0.9
  },

  medium: {
    drop: 32,
    recover: 45,
    minimumDpr: 0.8
  },

  low: {
    drop: 23,
    recover: 32,
    minimumDpr: 0.68
  }
};

export default function CinematicRuntimeGovernor({
  quality,
  cameraState
}) {
  const gl = useThree(
    state => state.gl
  );

  const elapsed =
    useRef(0);

  const frames =
    useRef(0);

  const badWindows =
    useRef(0);

  const goodWindows =
    useRef(0);

  const level =
    useRef(0);

  const baseDpr =
    useRef(
      gl.getPixelRatio()
    );

  useEffect(() => {
    baseDpr.current =
      gl.getPixelRatio();

    if (
      cameraState?.current
    ) {
      cameraState.current.performanceLevel =
        0;

      cameraState.current.performanceFps =
        0;

      cameraState.current.runtimeDegraded =
        false;
    }

    return () => {
      gl.setPixelRatio(
        baseDpr.current
      );
    };
  }, [
    cameraState,
    gl
  ]);

  useFrame(
    (
      _state,
      delta
    ) => {
      elapsed.current +=
        delta;

      frames.current += 1;

      if (
        elapsed.current <
        sampleWindow
      ) {
        return;
      }

      const fps =
        frames.current /
        elapsed.current;

      elapsed.current = 0;
      frames.current = 0;

      const profile =
        thresholds[
          quality.tier
        ] ??
        thresholds.medium;

      if (
        cameraState?.current
      ) {
        cameraState.current.performanceFps =
          fps;
      }

      if (
        fps <
        profile.drop
      ) {
        badWindows.current +=
          1;

        goodWindows.current =
          0;
      } else if (
        fps >=
        profile.recover
      ) {
        goodWindows.current +=
          1;

        badWindows.current =
          0;
      } else {
        badWindows.current =
          Math.max(
            0,
            badWindows.current -
              1
          );

        goodWindows.current =
          0;
      }

      if (
        badWindows.current >=
          badWindowsToDrop &&
        level.current < 3
      ) {
        level.current +=
          1;

        badWindows.current =
          0;

        const multiplier =
          level.current === 1
            ? 0.86
            : level.current === 2
              ? 0.74
              : 0.64;

        gl.setPixelRatio(
          Math.max(
            profile.minimumDpr,
            baseDpr.current *
              multiplier
          )
        );
      }

      if (
        goodWindows.current >=
          goodWindowsToRecover &&
        level.current > 0
      ) {
        level.current -=
          1;

        goodWindows.current =
          0;

        const multiplier =
          level.current === 0
            ? 1
            : level.current === 1
              ? 0.86
              : 0.74;

        gl.setPixelRatio(
          Math.max(
            profile.minimumDpr,
            baseDpr.current *
              multiplier
          )
        );
      }

      if (
        cameraState?.current
      ) {
        cameraState.current.performanceLevel =
          level.current;

        cameraState.current.runtimeDegraded =
          level.current > 0;
      }
    }
  );

  return null;
}
