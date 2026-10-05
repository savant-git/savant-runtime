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
  return Math.min(
    maximum,
    Math.max(minimum, value)
  );
}

export default function TrajectoryEngine({
  initialMissionId = "artemis-2"
}) {
  const rootRef = useRef(null);
  const trackRef = useRef(null);

  const initialMission =
    getMission(initialMissionId) ??
    missions[0];

  const [missionId, setMissionId] =
    useState(initialMission.id);

  const [phaseIndex, setPhaseIndex] =
    useState(0);

  const [playing, setPlaying] =
    useState(false);

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

  useEffect(() => {
    setPhaseIndex(0);
    setPlaying(false);
  }, [missionId]);

  useEffect(() => {
    if (!trackRef.current) {
      return;
    }

    gsap.to(
      trackRef.current.style,
      {
        duration: 0.65,
        ease: "power3.out",
        "--trajectory-progress":
          `${progress * 100}%`
      }
    );
  }, [progress]);

  useEffect(() => {
    if (!playing) {
      return undefined;
    }

    const timer = window.setInterval(() => {
      setPhaseIndex((current) => {
        if (current >= phases.length - 1) {
          setPlaying(false);
          return current;
        }

        return current + 1;
      });
    }, 1100);

    return () => {
      window.clearInterval(timer);
    };
  }, [playing, phases.length]);

  useEffect(() => {
    const handleKeyDown = (event) => {
      if (!rootRef.current?.contains(
        document.activeElement
      )) {
        return;
      }

      if (event.key === "ArrowRight") {
        event.preventDefault();

        setPhaseIndex((current) =>
          clamp(
            current + 1,
            0,
            phases.length - 1
          )
        );
      }

      if (event.key === "ArrowLeft") {
        event.preventDefault();

        setPhaseIndex((current) =>
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
          setPlaying((value) => !value);
        }
      }
    };

    window.addEventListener(
      "keydown",
      handleKeyDown
    );

    return () => {
      window.removeEventListener(
        "keydown",
        handleKeyDown
      );
    };
  }, [phases.length]);

  const selectPhase = (index) => {
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
  };

  const selectMission = (id) => {
    const nextMission = getMission(id);

    if (!nextMission) {
      return;
    }

    setMissionId(id);

    const url = new URL(window.location.href);

    url.searchParams.set(
      "mission",
      id
    );

    url.searchParams.delete("phase");

    window.history.replaceState(
      {},
      "",
      url
    );
  };

  return (
    <section
      ref={rootRef}
      className="trajectory-engine"
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
            not a slideshow.
          </h3>
        </div>

        <div className="trajectory-engine-status">
          <span>
            {mission.statusLabel}
          </span>

          <strong>
            {mission.name}
          </strong>

          <small>
            {mission.destination}
          </small>
        </div>
      </header>

      <nav
        className="trajectory-mission-selector"
        aria-label="Select Artemis mission"
      >
        {missions.map((item) => (
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
            <span>
              {item.index}
            </span>

            <strong>
              ARTEMIS {item.numeral}
            </strong>

            <small>
              {item.year}
            </small>
          </button>
        ))}
      </nav>

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
            ).padStart(2, "0")} TOTAL
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
            onClick={() =>
              setPlaying((value) => !value)
            }
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
          <span>
            MISSION TYPE
          </span>

          <strong>
            {mission.missionType}
          </strong>
        </article>

        <article>
          <span>
            CREW
          </span>

          <strong>
            {mission.crew === 0
              ? "UNCReWED"
              : `${mission.crew} CREW`}
          </strong>
        </article>

        <article>
          <span>
            FLIGHT WINDOW
          </span>

          <strong>
            {mission.launch}
          </strong>
        </article>

        <article>
          <span>
            CONFIGURATION
          </span>

          <strong>
            {systems
              .map(
                (system) =>
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
          {systems.map((system) => (
            <button
              key={system.id}
              type="button"
              onClick={() => {
                const element =
                  document.getElementById(
                    "systems"
                  );

                element?.scrollIntoView({
                  behavior: "smooth"
                });
              }}
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

          {sources.map((source) => (
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
        {mission.name}. Current phase:
        {" "}
        {currentPhase?.label}.
      </div>
    </section>
  );
}
