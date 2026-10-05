import {
  useEffect,
  useRef,
  useState
} from "react";

const lowUpdateMs =
  1000 / 30;

const normalUpdateMs =
  1000 / 60;

function clamp(
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

export default function CinematicMatteStage({
  cameraState,
  quality
}) {
  const stageRef =
    useRef(null);

  const imageRef =
    useRef(null);

  const farStarsRef =
    useRef(null);

  const midStarsRef =
    useRef(null);

  const frameRef =
    useRef(0);

  const lastUpdateRef =
    useRef(0);

  const lastValuesRef =
    useRef({
      x: Number.NaN,
      y: Number.NaN,
      scale: Number.NaN
    });

  const [
    loaded,
    setLoaded
  ] = useState(false);

  useEffect(() => {
    const image =
      imageRef.current;

    if (
      image?.complete &&
      image.naturalWidth >
        0
    ) {
      setLoaded(true);
    }
  }, []);

  useEffect(() => {
    const stage =
      stageRef.current;

    const image =
      imageRef.current;

    const farStars =
      farStarsRef.current;

    const midStars =
      midStarsRef.current;

    if (
      !stage ||
      !image
    ) {
      return undefined;
    }

    let active = true;

    const minimumInterval =
      quality?.tier ===
      "low"
        ? lowUpdateMs
        : normalUpdateMs;

    const update =
      timestamp => {
        if (!active) {
          return;
        }

        if (
          timestamp -
            lastUpdateRef.current <
          minimumInterval
        ) {
          frameRef.current =
            window.requestAnimationFrame(
              update
            );

          return;
        }

        lastUpdateRef.current =
          timestamp;

        const state =
          cameraState?.current;

        const yaw =
          clamp(
            state?.yaw ?? 0,
            -0.72,
            0.72
          );

        const pitch =
          clamp(
            state?.pitch ?? 0,
            -0.38,
            0.38
          );

        const velocity =
          Math.min(
            1,
            Math.hypot(
              state?.yawVelocity ??
                0,
              state?.pitchVelocity ??
                0
            ) *
              0.03
          );

        const x =
          yaw *
          -5.4;

        const y =
          pitch *
          4.7;

        const scale =
          1.085 +
          velocity *
            0.008;

        const previous =
          lastValuesRef.current;

        if (
          Math.abs(
            x -
              previous.x
          ) >
            0.015 ||
          Math.abs(
            y -
              previous.y
          ) >
            0.015 ||
          Math.abs(
            scale -
              previous.scale
          ) >
            0.0005
        ) {
          image.style.transform =
            `translate3d(${x}%, ${y}%, 0) scale(${scale})`;

          if (farStars) {
            farStars.style.transform =
              `translate3d(${x * 0.12}%, ${y * 0.12}%, 0)`;
          }

          if (midStars) {
            midStars.style.transform =
              `translate3d(${x * 0.28}%, ${y * 0.28}%, 0)`;
          }

          lastValuesRef.current =
            {
              x,
              y,
              scale
            };
        }

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
  }, [
    cameraState,
    quality?.tier
  ]);

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
        ref={imageRef}
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

      <div
        ref={farStarsRef}
        className="cinematic-matte-stage__stellar-field cinematic-matte-stage__stellar-field--far"
      />

      <div
        ref={midStarsRef}
        className="cinematic-matte-stage__stellar-field cinematic-matte-stage__stellar-field--mid"
      />

      <div className="cinematic-matte-stage__nebula" />

      <div className="cinematic-matte-stage__solar-haze" />

      <div className="cinematic-matte-stage__depth-vignette" />
    </div>
  );
}
