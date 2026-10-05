import { useEffect, useMemo, useRef, useState } from "react";
import gsap from "gsap";
import { systems } from "../data/missions.js";

const relationMap = {
  sls: ["orion", "egs"],
  orion: ["sls", "gateway", "hls"],
  egs: ["sls"],
  gateway: ["orion", "hls", "surface"],
  hls: ["orion", "gateway", "surface"],
  surface: ["gateway", "hls"]
};

function systemId(system) {
  return system.id ?? system.slug ?? system.shortName?.toLowerCase();
}

export default function SystemGrid() {
  const rootRef = useRef(null);
  const stageRef = useRef(null);

  const [activeId, setActiveId] = useState(
    systemId(systems[0])
  );

  const [inspectId, setInspectId] = useState(null);

  const [pointer, setPointer] = useState({
    x: 50,
    y: 50
  });

  const activeSystem = useMemo(
    () =>
      systems.find(
        system => systemId(system) === activeId
      ) ?? systems[0],
    [activeId]
  );

  const activeRelations =
    relationMap[activeId] ?? [];

  useEffect(() => {
    if (!rootRef.current) return;

    const context = gsap.context(() => {
      gsap.fromTo(
        ".architecture-node",
        {
          opacity: 0,
          scale: 0.86,
          y: 28
        },
        {
          opacity: 1,
          scale: 1,
          y: 0,
          stagger: 0.07,
          duration: 0.75,
          ease: "expo.out"
        }
      );

      gsap.fromTo(
        ".architecture-core",
        {
          opacity: 0,
          scale: 0.72
        },
        {
          opacity: 1,
          scale: 1,
          duration: 1.1,
          ease: "expo.out"
        }
      );
    }, rootRef);

    return () => context.revert();
  }, []);

  useEffect(() => {
    if (!stageRef.current) return;

    gsap.to(
      stageRef.current.querySelector(
        ".architecture-space"
      ),
      {
        rotateX:
          (pointer.y - 50) * -0.035,
        rotateY:
          (pointer.x - 50) * 0.045,
        duration: 0.85,
        ease: "power3.out"
      }
    );
  }, [pointer]);

  function trackPointer(event) {
    if (!stageRef.current) return;

    const rect =
      stageRef.current.getBoundingClientRect();

    setPointer({
      x:
        ((event.clientX - rect.left) /
          rect.width) *
        100,
      y:
        ((event.clientY - rect.top) /
          rect.height) *
        100
    });
  }

  function activate(id) {
    setActiveId(id);
    setInspectId(id);

    const url = new URL(window.location.href);
    url.searchParams.set("system", id);

    window.history.replaceState(
      {},
      "",
      url
    );
  }

  return (
    <div
      ref={rootRef}
      className="system-grid-evolved"
    >
      <div className="architecture-toolbar">
        <div>
          <span>
            ARTEMIS INTEGRATED ARCHITECTURE
          </span>
          <strong>
            SYSTEM RELATION MODEL
          </strong>
        </div>

        <div>
          <small>ACTIVE NODE</small>
          <strong>
            {activeSystem?.shortName ??
              activeSystem?.name}
          </strong>
        </div>
      </div>

      <div
        ref={stageRef}
        className="architecture-stage"
        onPointerMove={trackPointer}
        onPointerLeave={() =>
          setPointer({
            x: 50,
            y: 50
          })
        }
        style={{
          "--architecture-x":
            `${pointer.x}%`,
          "--architecture-y":
            `${pointer.y}%`
        }}
      >
        <div className="architecture-glow" />
        <div className="architecture-grid-plane" />

        <div className="architecture-space">
          <div className="architecture-orbit orbit-a" />
          <div className="architecture-orbit orbit-b" />
          <div className="architecture-orbit orbit-c" />

          <svg
            className="architecture-links"
            viewBox="0 0 100 100"
            preserveAspectRatio="none"
            aria-hidden="true"
          >
            <path d="M50 50 L20 25" />
            <path d="M50 50 L79 23" />
            <path d="M50 50 L18 72" />
            <path d="M50 50 L82 72" />
            <path d="M20 25 L79 23" />
            <path d="M18 72 L82 72" />
            <path d="M20 25 L18 72" />
            <path d="M79 23 L82 72" />
          </svg>

          <div className="architecture-core">
            <div className="architecture-core-rings">
              <i />
              <i />
              <i />
            </div>

            <span>ARTEMIS</span>
            <strong>
              EXPLORATION
              <br />
              ARCHITECTURE
            </strong>
            <small>
              INTEGRATED SYSTEM
            </small>
          </div>

          {systems.map(
            (system, index) => {
              const id = systemId(system);

              const positions = [
                ["20%", "25%"],
                ["79%", "23%"],
                ["18%", "72%"],
                ["82%", "72%"],
                ["50%", "13%"],
                ["50%", "85%"]
              ];

              const [left, top] =
                positions[
                  index % positions.length
                ];

              const active =
                id === activeId;

              const related =
                activeRelations.includes(id);

              return (
                <button
                  key={id}
                  type="button"
                  className={[
                    "architecture-node",
                    active ? "active" : "",
                    related ? "related" : ""
                  ]
                    .filter(Boolean)
                    .join(" ")}
                  style={{
                    left,
                    top
                  }}
                  onPointerEnter={() =>
                    setActiveId(id)
                  }
                  onFocus={() =>
                    setActiveId(id)
                  }
                  onClick={() =>
                    activate(id)
                  }
                >
                  <span>
                    {system.index ??
                      String(
                        index + 1
                      ).padStart(2, "0")}
                  </span>

                  <i />

                  <strong>
                    {system.shortName ??
                      system.name}
                  </strong>

                  <small>
                    {system.type}
                  </small>
                </button>
              );
            }
          )}
        </div>

        <div className="architecture-coordinate coord-north">
          LUNAR SYSTEM PLANE // 02
        </div>

        <div className="architecture-coordinate coord-east">
          INTEGRATION VECTOR
        </div>

        <aside className="architecture-readout">
          <span>
            SELECTED SYSTEM
          </span>

          <strong>
            {activeSystem?.name ??
              activeSystem?.shortName}
          </strong>

          <small>
            {activeSystem?.type}
          </small>

          <p>
            {activeSystem?.description ??
              activeSystem?.summary ??
              "Integrated Artemis exploration system."}
          </p>

          <div>
            <span>
              RELATIONS
            </span>

            <strong>
              {String(
                activeRelations.length
              ).padStart(2, "0")}
            </strong>
          </div>

          <button
            type="button"
            onClick={() =>
              setInspectId(activeId)
            }
          >
            INSPECT SYSTEM
            <span>↗</span>
          </button>
        </aside>
      </div>

      <div className="architecture-ledger">
        {systems.map(
          (system, index) => {
            const id = systemId(system);

            return (
              <button
                key={id}
                type="button"
                className={
                  id === activeId
                    ? "active"
                    : ""
                }
                onClick={() =>
                  activate(id)
                }
              >
                <span>
                  {system.index ??
                    String(
                      index + 1
                    ).padStart(2, "0")}
                </span>

                <div>
                  <strong>
                    {system.shortName ??
                      system.name}
                  </strong>

                  <small>
                    {system.type}
                  </small>
                </div>

                <i />
              </button>
            );
          }
        )}
      </div>

      {inspectId && (
        <div
          className="system-inspector"
          role="dialog"
          aria-modal="true"
          aria-label="Artemis system inspector"
        >
          <button
            type="button"
            className="system-inspector-backdrop"
            aria-label="Close system inspector"
            onClick={() =>
              setInspectId(null)
            }
          />

          <article>
            <header>
              <span>
                SYSTEM /{" "}
                {activeSystem?.index}
              </span>

              <button
                type="button"
                onClick={() =>
                  setInspectId(null)
                }
              >
                CLOSE ×
              </button>
            </header>

            <div className="system-inspector-index">
              {activeSystem?.index}
            </div>

            <span className="section-kicker">
              {activeSystem?.type}
            </span>

            <h3>
              {activeSystem?.name ??
                activeSystem?.shortName}
            </h3>

            <p>
              {activeSystem?.description ??
                activeSystem?.summary ??
                "Integrated Artemis exploration system."}
            </p>

            <div className="system-inspector-relations">
              <span>
                CONNECTED ARCHITECTURE
              </span>

              {activeRelations.length ? (
                activeRelations.map(
                  relationId => {
                    const related =
                      systems.find(
                        system =>
                          systemId(
                            system
                          ) === relationId
                      );

                    if (!related) {
                      return null;
                    }

                    return (
                      <button
                        key={relationId}
                        type="button"
                        onClick={() =>
                          setActiveId(
                            relationId
                          )
                        }
                      >
                        <span>
                          {related.index}
                        </span>

                        <strong>
                          {related.shortName ??
                            related.name}
                        </strong>
                      </button>
                    );
                  }
                )
              ) : (
                <small>
                  NO EXPLICIT RELATIONS
                </small>
              )}
            </div>
          </article>
        </div>
      )}
    </div>
  );
}
