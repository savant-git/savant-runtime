import {
  useEffect,
  useMemo,
  useRef,
  useState
} from "react";

import gsap from "gsap";

import {
  getMissionPhaseObjects,
  getMissionSystems,
  getMissionSources,
  getMissionView,
  missions
} from "../data/missions.js";

function readInitialMission(
  fallbackId
) {
  if (
    typeof window ===
    "undefined"
  ) {
    return fallbackId;
  }

  const requested =
    new URL(
      window.location.href
    ).searchParams.get(
      "mission"
    );

  return (
    getMissionView(
      requested
    )?.id ??
    fallbackId
  );
}

function readInitialPhase(
  mission
) {
  if (
    typeof window ===
      "undefined" ||
    !mission
  ) {
    return 0;
  }

  const value =
    new URL(
      window.location.href
    ).searchParams.get(
      "phase"
    );

  if (!value) {
    return 0;
  }

  const numeric =
    Number(value);

  if (
    Number.isInteger(
      numeric
    ) &&
    numeric > 0
  ) {
    return numeric - 1;
  }

  const phases =
    getMissionPhaseObjects(
      mission
    );

  const byId =
    phases.findIndex(
      phase =>
        phase.id ===
        value
    );

  return byId >= 0
    ? byId
    : 0;
}

export default function MissionExplorer({
  initialMissionId = "artemis-ii"
}) {
  const rootRef =
    useRef(null);

  const visualRef =
    useRef(null);

  const frameRef =
    useRef(0);

  const pointerRef =
    useRef({
      x: 0,
      y: 0
    });

  const fallback =
    getMissionView(
      initialMissionId
    ) ??
    getMissionView(
      missions[0]
    );

  const [
    missionId,
    setMissionId
  ] = useState(
    () =>
      readInitialMission(
        fallback?.id ??
          missions[0]?.id
      )
  );

  const mission =
    useMemo(
      () =>
        getMissionView(
          missionId
        ) ??
        getMissionView(
          missions[0]
        ),
      [
        missionId
      ]
    );

  const phases =
    useMemo(
      () =>
        getMissionPhaseObjects(
          mission
        ),
      [
        mission
      ]
    );

  const systems =
    useMemo(
      () =>
        getMissionSystems(
          mission
        ),
      [
        mission
      ]
    );

  const sources =
    useMemo(
      () =>
        getMissionSources(
          mission
        ),
      [
        mission
      ]
    );

  const [
    phaseIndex,
    setPhaseIndex
  ] = useState(
    () =>
      readInitialPhase(
        mission
      )
  );

  const phase =
    phases[
      Math.min(
        phaseIndex,
        Math.max(
          0,
          phases.length - 1
        )
      )
    ] ??
    phases[0];

  useEffect(() => {
    const nextIndex =
      readInitialPhase(
        mission
      );

    setPhaseIndex(
      Math.min(
        nextIndex,
        Math.max(
          0,
          phases.length - 1
        )
      )
    );

    if (
      !rootRef.current
    ) {
      return undefined;
    }

    const reduced =
      window.matchMedia(
        "(prefers-reduced-motion: reduce)"
      ).matches;

    if (reduced) {
      return undefined;
    }

    const context =
      gsap.context(
        () => {
          gsap.fromTo(
            ".mission-explorer-copy > *",
            {
              opacity: 0,
              y: 18
            },
            {
              opacity: 1,
              y: 0,
              stagger: 0.035,
              duration: 0.55,
              ease: "power3.out"
            }
          );

          gsap.fromTo(
            ".mission-visual-core",
            {
              scale: 0.9,
              opacity: 0
            },
            {
              scale: 1,
              opacity: 1,
              duration: 0.75,
              ease: "expo.out"
            }
          );
        },
        rootRef
      );

    return () =>
      context.revert();
  }, [
    missionId
  ]);

  useEffect(
    () => () => {
      if (
        frameRef.current
      ) {
        cancelAnimationFrame(
          frameRef.current
        );
      }
    },
    []
  );

  function updateUrl(
    nextMissionId,
    nextPhase
  ) {
    if (
      typeof window ===
      "undefined"
    ) {
      return;
    }

    const url =
      new URL(
        window.location.href
      );

    url.searchParams.set(
      "mission",
      nextMissionId
    );

    if (
      nextPhase ===
      undefined ||
      nextPhase ===
      null
    ) {
      url.searchParams.delete(
        "phase"
      );
    } else {
      url.searchParams.set(
        "phase",
        String(
          nextPhase + 1
        )
      );
    }

    window.history
      .replaceState(
        {},
        "",
        url
      );
  }

  function chooseMission(
    id
  ) {
    if (
      id ===
      missionId
    ) {
      return;
    }

    setMissionId(id);
    setPhaseIndex(0);

    updateUrl(
      id,
      null
    );
  }

  function choosePhase(
    index
  ) {
    const bounded =
      Math.max(
        0,
        Math.min(
          index,
          phases.length - 1
        )
      );

    setPhaseIndex(
      bounded
    );

    updateUrl(
      mission.id,
      bounded
    );
  }

  function applyPointer() {
    frameRef.current =
      0;

    const space =
      visualRef.current
        ?.querySelector(
          ".mission-visual-space"
        );

    if (!space) {
      return;
    }

    const {
      x,
      y
    } =
      pointerRef.current;

    space.style.transform =
      `rotateX(${y * -2.4}deg) rotateY(${x * 3.2}deg)`;
  }

  function trackPointer(
    event
  ) {
    if (
      !visualRef.current ||
      event.pointerType ===
        "touch"
    ) {
      return;
    }

    const rect =
      visualRef.current
        .getBoundingClientRect();

    pointerRef.current =
      {
        x:
          (
            (
              event.clientX -
              rect.left
            ) /
              rect.width -
            0.5
          ) *
          2,

        y:
          (
            (
              event.clientY -
              rect.top
            ) /
              rect.height -
            0.5
          ) *
          2
      };

    if (
      !frameRef.current
    ) {
      frameRef.current =
        requestAnimationFrame(
          applyPointer
        );
    }
  }

  function resetPointer() {
    pointerRef.current =
      {
        x: 0,
        y: 0
      };

    const space =
      visualRef.current
        ?.querySelector(
          ".mission-visual-space"
        );

    if (space) {
      space.style.transform =
        "rotateX(0deg) rotateY(0deg)";
    }
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
        {missions.map(
          item => {
            const view =
              getMissionView(
                item
              );

            return (
              <button
                key={
                  item.id
                }
                type="button"
                className={
                  item.id ===
                  mission.id
                    ? "active"
                    : ""
                }
                aria-pressed={
                  item.id ===
                  mission.id
                }
                onClick={() =>
                  chooseMission(
                    item.id
                  )
                }
              >
                <span>
                  {
                    item.index
                  }
                </span>

                <div>
                  <strong>
                    ARTEMIS{" "}
                    {
                      item.numeral
                    }
                  </strong>

                  <small>
                    {view?.statusLabel ??
                      item.status}
                  </small>
                </div>

                <b>
                  {
                    item.year
                  }
                </b>
              </button>
            );
          }
        )}
      </nav>

      <div className="mission-explorer-stage">
        <article className="mission-explorer-copy">
          <div className="mission-code">
            <span>
              MISSION /{" "}
              {
                mission.index
              }
            </span>

            <i />

            <strong>
              {
                mission.statusLabel
              }
            </strong>
          </div>

          <h3>
            ARTEMIS
            <br />

            <em>
              {
                mission.numeral
              }
            </em>
          </h3>

          <p className="mission-objective">
            {
              mission.objective
            }
          </p>

          <div className="mission-metrics">
            <div>
              <small>
                MISSION
              </small>

              <strong>
                {
                  mission.missionType
                }
              </strong>
            </div>

            <div>
              <small>
                CREW
              </small>

              <strong>
                {String(
                  mission.crew
                ).toUpperCase()}
              </strong>
            </div>

            <div>
              <small>
                WINDOW
              </small>

              <strong>
                {
                  mission.launch
                }
              </strong>
            </div>

            <div>
              <small>
                DESTINATION
              </small>

              <strong>
                {
                  mission.destination
                }
              </strong>
            </div>
          </div>

          <div className="mission-phase-readout">
            <span>
              CURRENT SEQUENCE
            </span>

            <strong>
              {phase?.label ??
                "MISSION"}
            </strong>

            <small>
              {String(
                phaseIndex + 1
              ).padStart(
                2,
                "0"
              )}
              {" / "}
              {String(
                phases.length
              ).padStart(
                2,
                "0"
              )}
            </small>
          </div>

          <div className="mission-phase-controls">
            {phases.map(
              (
                item,
                index
              ) => (
                <button
                  key={
                    item.id
                  }
                  type="button"
                  className={
                    index ===
                    phaseIndex
                      ? "active"
                      : ""
                  }
                  aria-pressed={
                    index ===
                    phaseIndex
                  }
                  onClick={() =>
                    choosePhase(
                      index
                    )
                  }
                >
                  <span>
                    {
                      item.index
                    }
                  </span>

                  <strong>
                    {
                      item.shortLabel
                    }
                  </strong>
                </button>
              )
            )}
          </div>
        </article>

        <div
          ref={visualRef}
          className="mission-visual"
          onPointerMove={
            trackPointer
          }
          onPointerLeave={
            resetPointer
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

              <span>
                LUNA
              </span>
            </div>

            <div
              className="mission-spacecraft"
              style={{
                "--mission-progress":
                  phases.length >
                  1
                    ? phaseIndex /
                      (
                        phases.length -
                        1
                      )
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
              <path d="M 7 78 C 20 22, 57 11, 83 28 C 96 37, 88 64, 63 63 C 44 63, 43 43, 57 31" />
            </svg>

            <div className="mission-visual-label label-a">
              <span>
                01
              </span>
              EARTH DEPARTURE
            </div>

            <div className="mission-visual-label label-b">
              <span>
                02
              </span>
              CISELUNAR SPACE
            </div>

            <div className="mission-visual-label label-c">
              <span>
                03
              </span>
              LUNAR OPERATIONS
            </div>

            <div className="mission-visual-coordinate">
              VECTOR //{" "}
              {
                mission.numeral
              }
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
            ).padStart(
              2,
              "0"
            )}{" "}
            SYSTEMS
          </strong>
        </header>

        <div>
          {systems.map(
            system => (
              <article
                key={
                  system.id
                }
              >
                <span>
                  {
                    system.index
                  }
                </span>

                <div>
                  <strong>
                    {
                      system.shortName
                    }
                  </strong>

                  <small>
                    {
                      system.type
                    }
                  </small>
                </div>

                <i>
                  ↗
                </i>
              </article>
            )
          )}
        </div>
      </section>

      {sources.length >
        0 && (
        <details className="mission-source-panel">
          <summary>
            <span>
              SOURCE PROVENANCE
            </span>

            <strong>
              {String(
                sources.length
              ).padStart(
                2,
                "0"
              )}
            </strong>
          </summary>

          <div>
            {sources.map(
              source => (
                <a
                  key={
                    source.id
                  }
                  href={
                    source.url
                  }
                  target="_blank"
                  rel="noreferrer"
                >
                  <span>
                    {
                      source.authority
                    }
                  </span>

                  <strong>
                    {
                      source.title
                    }
                  </strong>

                  <small>
                    {
                      source.accessed
                    }
                  </small>
                </a>
              )
            )}
          </div>
        </details>
      )}
    </div>
  );
}
