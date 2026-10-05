import {
  useEffect,
  useMemo,
  useRef,
  useState
} from "react";

import gsap from "gsap";

import {
  getMission,
  getMissionPhaseObjects,
  getMissionSystems,
  getMissionSources,
  missions
} from "../data/missions.js";

function clamp(value, minimum, maximum) {
  return Math.min(maximum, Math.max(minimum, value));
}

function polarPoint(angle, radius, cx = 50, cy = 50) {
  const radians = (angle * Math.PI) / 180;

  return {
    x: cx + Math.cos(radians) * radius,
    y: cy + Math.sin(radians) * radius
  };
}

export default function TrajectoryEngine({
  initialMissionId = "artemis-2"
}) {
  const rootRef = useRef(null);
  const trackRef = useRef(null);
  const stageRef = useRef(null);

  const initialMission =
    getMission(initialMissionId) ?? missions[0];

  const [missionId, setMissionId] =
    useState(initialMission.id);

  const [phaseIndex, setPhaseIndex] =
    useState(0);

  const [playing, setPlaying] =
    useState(false);

  const [expanded, setExpanded] =
    useState(false);

  const [pointer, setPointer] =
    useState({ x: 50, y: 50 });

  const mission = useMemo(
    () => getMission(missionId) ?? missions[0],
    [missionId]
  );

  const phases = useMemo(
    () => getMissionPhaseObjects(mission),
    [mission]
  );

  const systems = useMemo(
    () => getMissionSystems(mission),
    [mission]
  );

  const sources = useMemo(
    () => getMissionSources(mission),
    [mission]
  );

  const currentPhase =
    phases[phaseIndex] ?? phases[0];

  const progress =
    phases.length > 1
      ? phaseIndex / (phases.length - 1)
      : 0;

  const orbitalNodes = useMemo(
    () =>
      phases.map((phase, index) => {
        const count = Math.max(phases.length, 1);
        const angle =
          -145 +
          (index / Math.max(count - 1, 1)) * 290;

        const radius =
          index % 2 === 0 ? 34 : 40;

        return {
          phase,
          index,
          angle,
          ...polarPoint(angle, radius)
        };
      }),
    [phases]
  );

  useEffect(() => {
    setPhaseIndex(0);
    setPlaying(false);
  }, [missionId]);

  useEffect(() => {
    if (!trackRef.current) {
      return;
    }

    gsap.to(trackRef.current, {
      "--trajectory-progress":
        `${progress * 100}%`,
      duration: 0.72,
      ease: "power3.out"
    });

    if (stageRef.current) {
      gsap.fromTo(
        stageRef.current.querySelector(
          ".orbital-current-vector"
        ),
        {
          opacity: 0.15,
          scale: 0.7
        },
        {
          opacity: 1,
          scale: 1,
          duration: 0.8,
          ease: "expo.out"
        }
      );
    }
  }, [progress]);

  useEffect(() => {
    if (!playing) {
      return undefined;
    }

    if (phaseIndex >= phases.length - 1) {
      setPhaseIndex(0);
    }

    const timer = window.setInterval(() => {
      setPhaseIndex(current => {
        if (current >= phases.length - 1) {
          setPlaying(false);
          return current;
        }

        return current + 1;
      });
    }, 1350);

    return () => window.clearInterval(timer);
  }, [playing, phases.length, phaseIndex]);

  useEffect(() => {
    const handleKeyDown = event => {
      if (
        !rootRef.current?.contains(
          document.activeElement
        )
      ) {
        return;
      }

      if (event.key === "ArrowRight") {
        event.preventDefault();
        setPlaying(false);

        setPhaseIndex(current =>
          clamp(
            current + 1,
            0,
            phases.length - 1
          )
        );
      }

      if (event.key === "ArrowLeft") {
        event.preventDefault();
        setPlaying(false);

        setPhaseIndex(current =>
          clamp(
            current - 1,
            0,
            phases.length - 1
          )
        );
      }

      if (
        event.key === " " ||
        event.key === "Enter"
      ) {
        if (
          document.activeElement ===
          rootRef.current
        ) {
          event.preventDefault();
          setPlaying(value => !value);
        }
      }

      if (event.key === "Escape") {
        setExpanded(false);
      }
    };

    window.addEventListener(
      "keydown",
      handleKeyDown
    );

    return () =>
      window.removeEventListener(
        "keydown",
        handleKeyDown
      );
  }, [phases.length]);

  useEffect(() => {
    document.body.classList.toggle(
      "trajectory-expanded",
      expanded
    );

    return () =>
      document.body.classList.remove(
        "trajectory-expanded"
      );
  }, [expanded]);

  function selectPhase(index) {
    setPlaying(false);
    setPhaseIndex(index);

    const phase = phases[index];
    const url = new URL(window.location.href);

    url.searchParams.set(
      "mission",
      mission.id
    );

    if (phase) {
      url.searchParams.set(
        "phase",
        phase.id
      );
    }

    window.history.replaceState(
      {},
      "",
      url
    );
  }

  function selectMission(id) {
    const nextMission = getMission(id);

    if (!nextMission) {
      return;
    }

    setMissionId(id);

    const url = new URL(window.location.href);

    url.searchParams.set("mission", id);
    url.searchParams.delete("phase");

    window.history.replaceState(
      {},
      "",
      url
    );
  }

  function trackPointer(event) {
    if (!stageRef.current) {
      return;
    }

    const rect =
      stageRef.current.getBoundingClientRect();

    const x =
      ((event.clientX - rect.left) /
        rect.width) *
      100;

    const y =
      ((event.clientY - rect.top) /
        rect.height) *
      100;

    setPointer({
      x: clamp(x, 0, 100),
      y: clamp(y, 0, 100)
    });
  }

  return (
    <section
      ref={rootRef}
      className={`trajectory-engine ${
        expanded ? "expanded" : ""
      }`}
      aria-label="Interactive Artemis mission trajectory"
      tabIndex={0}
    >
      <header className="trajectory-engine-header">
        <div>
          <span className="section-kicker">
            MISSION ARCHITECTURE / LIVE MODEL
          </span>

          <h3>
            Follow the mission,
            <br />
            <em>through space.</em>
          </h3>
        </div>

        <div className="trajectory-engine-status">
          <span>{mission.statusLabel}</span>
          <strong>{mission.name}</strong>
          <small>{mission.destination}</small>
        </div>

        <button
          type="button"
          className="trajectory-expand"
          aria-pressed={expanded}
          onClick={() =>
            setExpanded(value => !value)
          }
        >
          <span>
            {expanded
              ? "EXIT FLIGHT MODE"
              : "ENTER FLIGHT MODE"}
          </span>
          <i>↗</i>
        </button>
      </header>

      <nav
        className="trajectory-mission-selector"
        aria-label="Select Artemis mission"
      >
        {missions.map(item => (
          <button
            key={item.id}
            type="button"
            className={
              item.id === mission.id
                ? "active"
                : ""
            }
            aria-pressed={
              item.id === mission.id
            }
            onClick={() =>
              selectMission(item.id)
            }
          >
            <span>{item.index}</span>
            <strong>
              ARTEMIS {item.numeral}
            </strong>
            <small>{item.year}</small>
          </button>
        ))}
      </nav>

      <div
        ref={stageRef}
        className="trajectory-orbital-stage"
        onPointerMove={trackPointer}
        style={{
          "--flight-pointer-x":
            `${pointer.x}%`,
          "--flight-pointer-y":
            `${pointer.y}%`
        }}
      >
        <div className="orbital-space-glow" />
        <div className="orbital-grid" />

        <div className="orbital-reticle">
          <i />
          <i />
        </div>

        <div className="orbital-earth">
          <div className="orbital-earth-atmosphere" />
          <div className="orbital-earth-surface" />
          <span>EARTH</span>
          <small>ORIGIN // 00</small>
        </div>

        <div className="orbital-moon">
          <div />
          <span>LUNA</span>
          <small>DESTINATION</small>
        </div>

        <svg
          className="orbital-vector-map"
          viewBox="0 0 100 100"
          preserveAspectRatio="none"
          aria-hidden="true"
        >
          <defs>
            <linearGradient
              id="flight-vector-gradient"
              x1="0"
              y1="0"
              x2="1"
              y2="0"
            >
              <stop
                offset="0%"
                stopColor="rgba(255,255,255,.15)"
              />
              <stop
                offset="55%"
                stopColor="rgba(151,205,238,.9)"
              />
              <stop
                offset="100%"
                stopColor="rgba(255,255,255,.3)"
              />
            </linearGradient>
          </defs>

          <path
            className="orbital-vector-base"
            d="M 17 72 C 29 18, 69 9, 84 38 C 92 54, 78 76, 61 64 C 49 56, 58 35, 78 31"
          />

          <path
            className="orbital-vector-active"
            pathLength="1"
            style={{
              strokeDasharray: 1,
              strokeDashoffset:
                1 - progress
            }}
            d="M 17 72 C 29 18, 69 9, 84 38 C 92 54, 78 76, 61 64 C 49 56, 58 35, 78 31"
          />
        </svg>

        <div
          className="orbital-current-vector"
          style={{
            left:
              `${18 + progress * 61}%`,
            top:
              `${70 - Math.sin(progress * Math.PI) * 45}%`
          }}
        >
          <i />
          <span>
            {currentPhase?.shortLabel}
          </span>
        </div>

        {orbitalNodes.map(
          ({
            phase,
            index,
            x,
            y
          }) => {
            const state =
              index < phaseIndex
                ? "complete"
                : index === phaseIndex
                  ? "active"
                  : "future";

            return (
              <button
                key={`${phase.id}-${index}`}
                className={`orbital-phase ${state}`}
                style={{
                  left: `${x}%`,
                  top: `${y}%`
                }}
                onClick={() =>
                  selectPhase(index)
                }
                aria-current={
                  index === phaseIndex
                    ? "step"
                    : undefined
                }
              >
                <i />
                <span>
                  {String(index + 1).padStart(
                    2,
                    "0"
                  )}
                </span>
                <strong>
                  {phase.shortLabel}
                </strong>
              </button>
            );
          }
        )}

        <div className="orbital-stage-coordinate coordinate-top">
          CISELUNAR NAVIGATION PLANE
        </div>

        <div className="orbital-stage-coordinate coordinate-side">
          VECTOR // {mission.numeral}
        </div>

        <div className="orbital-stage-readout">
          <span>
            CURRENT PHASE
          </span>

          <strong>
            {currentPhase?.label}
          </strong>

          <p>{mission.objective}</p>

          <div>
            <small>
              SEQUENCE
            </small>
            <b>
              {String(
                phaseIndex + 1
              ).padStart(2, "0")}
              /
              {String(
                phases.length
              ).padStart(2, "0")}
            </b>
          </div>

          <div>
            <small>
              PROGRESS
            </small>
            <b>
              {Math.round(progress * 100)}%
            </b>
          </div>
        </div>
      </div>

      <div className="trajectory-stage">
        <div className="trajectory-stage-meta">
          <span>
            PHASE{" "}
            {String(
              phaseIndex + 1
            ).padStart(2, "0")}
          </span>

          <span>
            {String(
              phases.length
            ).padStart(2, "0")}{" "}
            TOTAL
          </span>
        </div>

        <div className="trajectory-stage-copy">
          <span className="trajectory-phase-code">
            {currentPhase?.shortLabel}
          </span>

          <h4>
            {currentPhase?.label}
          </h4>

          <p>
            {mission.objective}
          </p>
        </div>

        <div
          ref={trackRef}
          className="trajectory-track"
          style={{
            "--trajectory-progress":
              `${progress * 100}%`
          }}
        >
          <div className="trajectory-track-base" />
          <div className="trajectory-track-progress" />

          {phases.map((phase, index) => {
            const phaseProgress =
              phases.length > 1
                ? index /
                  (phases.length - 1)
                : 0;

            const state =
              index < phaseIndex
                ? "complete"
                : index === phaseIndex
                  ? "active"
                  : "future";

            return (
              <button
                key={`${phase.id}-${index}`}
                type="button"
                className={`trajectory-phase-node ${state}`}
                style={{
                  left:
                    `${phaseProgress * 100}%`
                }}
                aria-label={
                  `${phase.label}, phase ${
                    index + 1
                  } of ${phases.length}`
                }
                aria-current={
                  index === phaseIndex
                    ? "step"
                    : undefined
                }
                onClick={() =>
                  selectPhase(index)
                }
              >
                <i />
                <span>
                  {phase.shortLabel}
                </span>
              </button>
            );
          })}
        </div>

        <div className="trajectory-controls">
          <button
            type="button"
            disabled={phaseIndex === 0}
            onClick={() =>
              selectPhase(
                clamp(
                  phaseIndex - 1,
                  0,
                  phases.length - 1
                )
              )
            }
          >
            ← PREVIOUS
          </button>

          <button
            type="button"
            className="trajectory-play"
            onClick={() => {
              if (
                phaseIndex ===
                phases.length - 1
              ) {
                setPhaseIndex(0);
              }

              setPlaying(value => !value);
            }}
          >
            {playing
              ? "PAUSE TRAJECTORY"
              : phaseIndex ===
                  phases.length - 1
                ? "REPLAY TRAJECTORY"
                : "PLAY TRAJECTORY"}
          </button>

          <button
            type="button"
            disabled={
              phaseIndex ===
              phases.length - 1
            }
            onClick={() =>
              selectPhase(
                clamp(
                  phaseIndex + 1,
                  0,
                  phases.length - 1
                )
              )
            }
          >
            NEXT →
          </button>
        </div>
      </div>

      <div className="trajectory-intelligence">
        <article>
          <span>MISSION TYPE</span>
          <strong>
            {mission.missionType}
          </strong>
        </article>

        <article>
          <span>CREW</span>
          <strong>
            {mission.crew === 0
              ? "UNCREWED"
              : `${mission.crew} CREW`}
          </strong>
        </article>

        <article>
          <span>FLIGHT WINDOW</span>
          <strong>
            {mission.launch}
          </strong>
        </article>

        <article>
          <span>CONFIGURATION</span>
          <strong>
            {systems
              .map(
                system =>
                  system.shortName
              )
              .join(" / ")}
          </strong>
        </article>
      </div>

      <div className="trajectory-system-relations">
        <span className="trajectory-relation-label">
          ACTIVE ARCHITECTURE
        </span>

        <div>
          {systems.map(system => (
            <button
              key={system.id}
              type="button"
              onClick={() =>
                document
                  .getElementById("systems")
                  ?.scrollIntoView({
                    behavior: "smooth"
                  })
              }
            >
              <small>
                {system.index}
              </small>

              <strong>
                {system.shortName}
              </strong>

              <span>
                {system.type}
              </span>
            </button>
          ))}
        </div>
      </div>

      <details className="trajectory-provenance">
        <summary>
          SOURCE PROVENANCE
        </summary>

        <div>
          <p>
            Mission information is a
            presentation of current NASA
            source material. NASA remains
            the external authority.
          </p>

          {sources.map(source => (
            <a
              key={source.id}
              href={source.url}
              target="_blank"
              rel="noreferrer"
            >
              <span>
                {source.authority}
              </span>

              <strong>
                {source.title}
              </strong>

              <small>
                ACCESSED{" "}
                {source.accessed}
              </small>
            </a>
          ))}
        </div>
      </details>

      <div
        className="sr-only"
        aria-live="polite"
      >
        {mission.name}. Current phase:{" "}
        {currentPhase?.label}.
      </div>
    </section>
  );
}
