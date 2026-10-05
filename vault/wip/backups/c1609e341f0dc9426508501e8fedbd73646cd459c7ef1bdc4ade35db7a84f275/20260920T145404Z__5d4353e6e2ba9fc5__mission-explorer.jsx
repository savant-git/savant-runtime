import { useEffect, useMemo, useRef, useState } from "react";
import gsap from "gsap";

import {
  getMission,
  getMissionPhaseObjects,
  getMissionSystems,
  getMissionSources,
  getMissionView,
  missions
} from "../data/missions.js";

export default function MissionExplorer({
  initialMissionId = "artemis-ii"
}) {
  const rootRef = useRef(null);
  const visualRef = useRef(null);

  const initial =
    getMissionView(initialMissionId) ??
    getMissionView(missions[0]);

  const [missionId, setMissionId] = useState(
    initial?.id ?? missions[0]?.id
  );

  const [phaseIndex, setPhaseIndex] = useState(0);

  const [pointer, setPointer] = useState({
    x: 0,
    y: 0
  });

  const mission = useMemo(
    () =>
      getMissionView(missionId) ??
      getMissionView(missions[0]),
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

  const phase = phases[phaseIndex] ?? phases[0];

  useEffect(() => {
    setPhaseIndex(0);

    if (!rootRef.current) {
      return undefined;
    }

    const context = gsap.context(() => {
      gsap.fromTo(
        ".mission-explorer-copy > *",
        {
          opacity: 0,
          y: 22
        },
        {
          opacity: 1,
          y: 0,
          stagger: 0.045,
          duration: 0.65,
          ease: "power3.out"
        }
      );

      gsap.fromTo(
        ".mission-visual-core",
        {
          scale: 0.84,
          opacity: 0
        },
        {
          scale: 1,
          opacity: 1,
          duration: 1,
          ease: "expo.out"
        }
      );
    }, rootRef);

    return () => context.revert();
  }, [missionId]);

  useEffect(() => {
    if (!visualRef.current) {
      return;
    }

    const space =
      visualRef.current.querySelector(
        ".mission-visual-space"
      );

    if (!space) {
      return;
    }

    gsap.to(space, {
      rotateX: pointer.y * -3,
      rotateY: pointer.x * 4,
      duration: 0.8,
      ease: "power3.out"
    });
  }, [pointer]);

  function chooseMission(id) {
    setMissionId(id);

    if (typeof window === "undefined") {
      return;
    }

    const url = new URL(window.location.href);

    url.searchParams.set("mission", id);
    url.searchParams.delete("phase");

    window.history.replaceState({}, "", url);
  }

  function choosePhase(index) {
    setPhaseIndex(index);

    if (typeof window === "undefined") {
      return;
    }

    const url = new URL(window.location.href);

    url.searchParams.set(
      "phase",
      String(index + 1)
    );

    window.history.replaceState({}, "", url);
  }

  function trackPointer(event) {
    if (!visualRef.current) {
      return;
    }

    const rect =
      visualRef.current.getBoundingClientRect();

    setPointer({
      x:
        ((event.clientX - rect.left) /
          rect.width -
          0.5) *
        2,
      y:
        ((event.clientY - rect.top) /
          rect.height -
          0.5) *
        2
    });
  }

  if (!mission) {
    return null;
  }

  return (
    <div
      ref={rootRef}
      className="mission-explorer"
    >
      <nav
        className="mission-switcher"
        aria-label="Artemis missions"
      >
        {missions.map(item => {
          const view = getMissionView(item);

          return (
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
                chooseMission(item.id)
              }
            >
              <span>{item.index}</span>

              <div>
                <strong>
                  ARTEMIS {item.numeral}
                </strong>

                <small>
                  {view?.statusLabel ??
                    item.status}
                </small>
              </div>

              <b>{item.year}</b>
            </button>
          );
        })}
      </nav>

      <div className="mission-explorer-stage">
        <article className="mission-explorer-copy">
          <div className="mission-code">
            <span>
              MISSION / {mission.index}
            </span>

            <i />

            <strong>
              {mission.statusLabel}
            </strong>
          </div>

          <h3>
            ARTEMIS
            <br />
            <em>{mission.numeral}</em>
          </h3>

          <p className="mission-objective">
            {mission.objective}
          </p>

          <div className="mission-metrics">
            <div>
              <small>MISSION</small>
              <strong>
                {mission.missionType}
              </strong>
            </div>

            <div>
              <small>CREW</small>
              <strong>
                {String(
                  mission.crew
                ).toUpperCase()}
              </strong>
            </div>

            <div>
              <small>WINDOW</small>
              <strong>
                {mission.launch}
              </strong>
            </div>

            <div>
              <small>DESTINATION</small>
              <strong>
                {mission.destination}
              </strong>
            </div>
          </div>

          <div className="mission-phase-readout">
            <span>CURRENT SEQUENCE</span>

            <strong>
              {phase?.label ?? "MISSION"}
            </strong>

            <small>
              {String(
                phaseIndex + 1
              ).padStart(2, "0")}
              {" / "}
              {String(
                phases.length
              ).padStart(2, "0")}
            </small>
          </div>

          <div className="mission-phase-controls">
            {phases.map((item, index) => (
              <button
                key={item.id}
                type="button"
                className={
                  index === phaseIndex
                    ? "active"
                    : ""
                }
                aria-pressed={
                  index === phaseIndex
                }
                onClick={() =>
                  choosePhase(index)
                }
              >
                <span>{item.index}</span>

                <strong>
                  {item.shortLabel}
                </strong>
              </button>
            ))}
          </div>
        </article>

        <div
          ref={visualRef}
          className="mission-visual"
          onPointerMove={trackPointer}
          onPointerLeave={() =>
            setPointer({
              x: 0,
              y: 0
            })
          }
        >
          <div className="mission-visual-space">
            <div className="mission-visual-grid" />

            <div className="mission-visual-orbit orbit-outer" />
            <div className="mission-visual-orbit orbit-middle" />
            <div className="mission-visual-orbit orbit-inner" />

            <div className="mission-visual-axis axis-horizontal" />
            <div className="mission-visual-axis axis-vertical" />

            <div className="mission-visual-core">
              <div className="mission-core-glow" />
              <div className="mission-core-body" />
              <div className="mission-core-shadow" />

              <span>LUNA</span>
            </div>

            <div
              className="mission-spacecraft"
              style={{
                "--mission-progress":
                  phases.length > 1
                    ? phaseIndex /
                      (phases.length - 1)
                    : 0
              }}
            >
              <div className="spacecraft-module">
                <i />
                <i />
                <i />
              </div>

              <span>
                {phase?.shortLabel ??
                  "MISSION"}
              </span>
            </div>

            <svg
              className="mission-vector"
              viewBox="0 0 100 100"
              preserveAspectRatio="none"
              aria-hidden="true"
            >
              <path
                d="M 7 78 C 20 22, 57 11, 83 28 C 96 37, 88 64, 63 63 C 44 63, 43 43, 57 31"
              />
            </svg>

            <div className="mission-visual-label label-a">
              <span>01</span>
              EARTH DEPARTURE
            </div>

            <div className="mission-visual-label label-b">
              <span>02</span>
              CISELUNAR SPACE
            </div>

            <div className="mission-visual-label label-c">
              <span>03</span>
              LUNAR OPERATIONS
            </div>

            <div className="mission-visual-coordinate">
              VECTOR // {mission.numeral}
            </div>
          </div>

          <div className="mission-visual-footer">
            <span>
              INTERACTIVE MISSION MODEL
            </span>

            <strong>
              MOVE POINTER TO INSPECT
            </strong>
          </div>
        </div>
      </div>

      <section className="mission-system-strip">
        <header>
          <span>
            ACTIVE SYSTEM ARCHITECTURE
          </span>

          <strong>
            {String(
              systems.length
            ).padStart(2, "0")}{" "}
            SYSTEMS
          </strong>
        </header>

        <div>
          {systems.map(system => (
            <article key={system.id}>
              <span>{system.index}</span>

              <div>
                <strong>
                  {system.shortName}
                </strong>

                <small>
                  {system.type}
                </small>
              </div>

              <i>↗</i>
            </article>
          ))}
        </div>
      </section>

      {sources.length > 0 && (
        <details className="mission-source-panel">
          <summary>
            <span>
              SOURCE PROVENANCE
            </span>

            <strong>
              {String(
                sources.length
              ).padStart(2, "0")}
            </strong>
          </summary>

          <div>
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
                  {source.accessed}
                </small>
              </a>
            ))}
          </div>
        </details>
      )}
    </div>
  );
}
