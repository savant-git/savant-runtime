import {
  useEffect,
  useRef,
  useState
} from "react";

export default function CinematicMatteStage({
  cameraState,
  quality
}) {
  const stageRef =
    useRef(null);

  const frameRef =
    useRef(0);

  const [
    loaded,
    setLoaded
  ] = useState(false);

  useEffect(() => {
    const stage =
      stageRef.current;

    if (!stage) {
      return undefined;
    }

    let active = true;

    const update =
      () => {
        if (!active) {
          return;
        }

        const state =
          cameraState?.current;

        const yaw =
          state?.yaw || 0;

        const pitch =
          state?.pitch || 0;

        const velocity =
          Math.min(
            1,
            Math.hypot(
              state?.yawVelocity ||
                0,
              state?.pitchVelocity ||
                0
            ) *
              0.025
          );

        stage.style.setProperty(
          "--matte-x",
          `${yaw * -5.5}%`
        );

        stage.style.setProperty(
          "--matte-y",
          `${pitch * 5}%`
        );

        stage.style.setProperty(
          "--matte-scale",
          `${
            1.09 +
            velocity * 0.008
          }`
        );

        frameRef.current =
          window.requestAnimationFrame(
            update
          );
      };

    frameRef.current =
      window.requestAnimationFrame(
        update
      );

    return () => {
      active = false;

      window.cancelAnimationFrame(
        frameRef.current
      );
    };
  }, [cameraState]);

  return (
    <div
      ref={stageRef}
      className={[
        "cinematic-matte-stage",
        loaded
          ? "is-loaded"
          : "",
        quality?.tier ===
          "low"
          ? "is-efficient"
          : ""
      ]
        .filter(Boolean)
        .join(" ")}
      aria-hidden="true"
    >
      <img
        className="cinematic-matte-stage__image"
        src="/assets/artemis-deep-space-matte.webp"
        alt=""
        draggable="false"
        decoding="async"
        fetchPriority="high"
        onLoad={() =>
          setLoaded(true)
        }
      />

      <div className="cinematic-matte-stage__stellar-field cinematic-matte-stage__stellar-field--far" />

      <div className="cinematic-matte-stage__stellar-field cinematic-matte-stage__stellar-field--mid" />

      <div className="cinematic-matte-stage__nebula" />

      <div className="cinematic-matte-stage__solar-haze" />

      <div className="cinematic-matte-stage__depth-vignette" />

      <div className="cinematic-matte-stage__grain" />
    </div>
  );
}
