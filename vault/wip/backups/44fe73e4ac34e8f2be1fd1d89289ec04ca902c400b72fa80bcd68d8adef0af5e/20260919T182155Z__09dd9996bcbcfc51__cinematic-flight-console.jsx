import {
  useEffect,
  useMemo,
  useRef,
  useState
} from "react";

const modeData = {
  earth: {
    eyebrow: "DEPARTURE DOMAIN",
    title: "EARTH",
    vector: "ASCENT / TLI",
    range: "NEAR-EARTH",
    reference: "EARTH FIXED"
  },

  transit: {
    eyebrow: "CISLUNAR DOMAIN",
    title: "TRANSIT",
    vector: "OUTBOUND",
    range: "DEEP SPACE",
    reference: "INERTIAL"
  },

  moon: {
    eyebrow: "LUNAR DOMAIN",
    title: "MOON",
    vector: "APPROACH",
    range: "LUNAR PROXIMITY",
    reference: "MOON FIXED"
  },

  gateway: {
    eyebrow: "ORBITAL DOMAIN",
    title: "GATEWAY",
    vector: "RENDEZVOUS",
    range: "LUNAR ORBIT",
    reference: "NRHO FRAME"
  }
};

function formatSigned(
  value,
  digits = 2
) {
  const numeric =
    Number.isFinite(value)
      ? value
      : 0;

  return `${numeric >= 0 ? "+" : ""}${numeric.toFixed(
    digits
  )}`;
}

function useCameraTelemetry(
  cameraState
) {
  const [telemetry, setTelemetry] =
    useState({
      yaw: 0,
      pitch: 0,
      velocity: 0,
      dragging: false
    });

  const lastUpdate =
    useRef(0);

  useEffect(() => {
    let frame = 0;

    const update = timestamp => {
      if (
        timestamp -
          lastUpdate.current >=
        80
      ) {
        lastUpdate.current =
          timestamp;

        const state =
          cameraState.current;

        const yaw =
          Number.isFinite(
            state.yaw
          )
            ? state.yaw
            : 0;

        const pitch =
          Number.isFinite(
            state.pitch
          )
            ? state.pitch
            : 0;

        const yawVelocity =
          Number.isFinite(
            state.yawVelocity
          )
            ? state.yawVelocity
            : 0;

        const pitchVelocity =
          Number.isFinite(
            state.pitchVelocity
          )
            ? state.pitchVelocity
            : 0;

        setTelemetry({
          yaw,
          pitch,
          velocity:
            Math.hypot(
              yawVelocity,
              pitchVelocity
            ),
          dragging:
            Boolean(
              state.dragging
            )
        });
      }

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

  return telemetry;
}

function AttitudeIndicator({
  yaw,
  pitch
}) {
  const yawDegrees =
    yaw *
    (180 / Math.PI);

  const pitchDegrees =
    pitch *
    (180 / Math.PI);

  return (
    <div
      className="flight-attitude"
      aria-hidden="true"
    >
      <div className="flight-attitude__ring flight-attitude__ring--outer" />

      <div className="flight-attitude__ring flight-attitude__ring--inner" />

      <div
        className="flight-attitude__horizon"
        style={{
          transform: `translateY(${Math.max(
            -18,
            Math.min(
              18,
              pitchDegrees * 0.7
            )
          )}px) rotate(${Math.max(
            -16,
            Math.min(
              16,
              -yawDegrees * 0.18
            )
          )}deg)`
        }}
      />

      <div className="flight-attitude__reticle">
        <span />
        <i />
        <span />
      </div>

      <div
        className="flight-attitude__heading"
        style={{
          transform: `translateX(${Math.max(
            -22,
            Math.min(
              22,
              yawDegrees * 0.35
            )
          )}px)`
        }}
      />

      <div className="flight-attitude__center" />
    </div>
  );
}

function VectorGraph({
  yaw,
  pitch,
  velocity
}) {
  const points =
    useMemo(
      () =>
        Array.from(
          {
            length: 18
          },
          (_, index) => {
            const x =
              (index / 17) *
              100;

            const phase =
              index * 0.72;

            const y =
              50 +
              Math.sin(
                phase +
                  yaw * 2.5
              ) *
                (
                  7 +
                  Math.min(
                    velocity *
                      3,
                    8
                  )
                ) +
              pitch * 12;

            return `${x},${Math.max(
              10,
              Math.min(
                90,
                y
              )
            )}`;
          }
        ).join(" "),
      [
        pitch,
        velocity,
        yaw
      ]
    );

  return (
    <svg
      className="flight-vector-graph"
      viewBox="0 0 100 100"
      preserveAspectRatio="none"
      aria-hidden="true"
    >
      <line
        x1="0"
        y1="50"
        x2="100"
        y2="50"
        className="flight-vector-graph__axis"
      />

      <polyline
        points={points}
        className="flight-vector-graph__signal"
      />
    </svg>
  );
}

function ModeIndex({
  mode,
  onModeChange
}) {
  const modes = [
    "earth",
    "transit",
    "moon",
    "gateway"
  ];

  return (
    <div className="flight-mode-index">
      {modes.map(
        (
          item,
          index
        ) => (
          <button
            type="button"
            key={item}
            className={
              item === mode
                ? "is-active"
                : ""
            }
            onClick={() =>
              onModeChange(
                item
              )
            }
            aria-label={`Select ${item} scene`}
          >
            <span>
              {String(
                index + 1
              ).padStart(
                2,
                "0"
              )}
            </span>

            <strong>
              {item}
            </strong>
          </button>
        )
      )}
    </div>
  );
}

export default function CinematicFlightConsole({
  mode,
  cameraState,
  quality,
  onModeChange
}) {
  const telemetry =
    useCameraTelemetry(
      cameraState
    );

  const data =
    modeData[mode] ??
    modeData.transit;

  const yawDegrees =
    telemetry.yaw *
    (180 / Math.PI);

  const pitchDegrees =
    telemetry.pitch *
    (180 / Math.PI);

  const motion =
    Math.min(
      999,
      telemetry.velocity *
        100
    );

  return (
    <aside
      className={[
        "cinematic-flight-console",
        telemetry.dragging
          ? "is-manipulating"
          : ""
      ]
        .filter(Boolean)
        .join(" ")}
      aria-label="Interactive scene navigation"
    >
      <div className="flight-console__topline">
        <div>
          <span>
            ARTEMIS
          </span>

          <strong>
            FLIGHT ENVIRONMENT
          </strong>
        </div>

        <div className="flight-console__status">
          <i />

          <span>
            LIVE
          </span>
        </div>
      </div>

      <div className="flight-console__primary">
        <div className="flight-console__identity">
          <span>
            {data.eyebrow}
          </span>

          <strong>
            {data.title}
          </strong>

          <small>
            {data.vector}
          </small>
        </div>

        <AttitudeIndicator
          yaw={telemetry.yaw}
          pitch={
            telemetry.pitch
          }
        />
      </div>

      <div className="flight-console__telemetry">
        <div>
          <span>
            YAW
          </span>

          <strong>
            {formatSigned(
              yawDegrees
            )}
            °
          </strong>
        </div>

        <div>
          <span>
            PITCH
          </span>

          <strong>
            {formatSigned(
              pitchDegrees
            )}
            °
          </strong>
        </div>

        <div>
          <span>
            MOTION
          </span>

          <strong>
            {motion.toFixed(
              1
            )}
          </strong>
        </div>
      </div>

      <div className="flight-console__vector">
        <div className="flight-console__vector-heading">
          <span>
            CAMERA VECTOR
          </span>

          <strong>
            {telemetry.dragging
              ? "MANUAL"
              : "STABLE"}
          </strong>
        </div>

        <VectorGraph
          yaw={telemetry.yaw}
          pitch={
            telemetry.pitch
          }
          velocity={
            telemetry.velocity
          }
        />
      </div>

      <div className="flight-console__reference">
        <div>
          <span>
            RANGE
          </span>

          <strong>
            {data.range}
          </strong>
        </div>

        <div>
          <span>
            FRAME
          </span>

          <strong>
            {data.reference}
          </strong>
        </div>

        <div>
          <span>
            RENDER
          </span>

          <strong>
            {String(
              quality
            ).toUpperCase()}
          </strong>
        </div>
      </div>

      <ModeIndex
        mode={mode}
        onModeChange={
          onModeChange
        }
      />

      <div className="flight-console__footer">
        <span>
          DRAG
        </span>

        <i />

        <span>
          FREE LOOK
        </span>

        <i />

        <span>
          R RESET
        </span>
      </div>
    </aside>
  );
}
