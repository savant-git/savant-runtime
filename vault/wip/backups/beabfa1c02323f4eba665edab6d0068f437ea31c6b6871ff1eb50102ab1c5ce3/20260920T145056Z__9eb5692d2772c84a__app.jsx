import {
  useEffect,
  useRef,
  useState
} from "react";

import gsap from "gsap";

import {
  ScrollTrigger
} from "gsap/ScrollTrigger";

import Navigation from "./components/navigation.jsx";
import MissionExplorer from "./components/mission-explorer.jsx";
import SystemGrid from "./components/system-grid.jsx";
import TrajectoryEngine from "./components/trajectory-engine.jsx";
import SpaceSceneShell from "./scenes/space-scene-shell.jsx";

gsap.registerPlugin(
  ScrollTrigger
);

const chapters = [
  {
    id: "hero",
    index: "00",
    label: "FORWARD"
  },
  {
    id: "missions",
    index: "01",
    label: "MISSIONS"
  },
  {
    id: "systems",
    index: "02",
    label: "SYSTEMS"
  },
  {
    id: "trajectory",
    index: "03",
    label: "TRAJECTORY"
  },
  {
    id: "moon",
    index: "04",
    label: "MOON"
  },
  {
    id: "gateway",
    index: "05",
    label: "GATEWAY"
  },
  {
    id: "future",
    index: "06",
    label: "MARS"
  }
];

export default function App() {
  const rootRef = useRef(null);

  const [activeChapter, setActiveChapter] =
    useState("hero");

  const [progress, setProgress] =
    useState(0);

  useEffect(() => {
    const root = rootRef.current;

    if (!root) {
      return undefined;
    }

    const context =
      gsap.context(() => {
        gsap.fromTo(
          ".hero-copy > *",
          {
            opacity: 0,
            y: 34
          },
          {
            opacity: 1,
            y: 0,
            duration: 1.05,
            stagger: 0.07,
            ease: "power4.out"
          }
        );

        gsap.fromTo(
          ".hero-flight-console",
          {
            opacity: 0,
            x: 35
          },
          {
            opacity: 1,
            x: 0,
            duration: 1.1,
            delay: 0.25,
            ease: "power4.out"
          }
        );

        gsap.utils
          .toArray(
            ".reveal-section"
          )
          .forEach(section => {
            gsap.fromTo(
              section,
              {
                opacity: 0,
                y: 60
              },
              {
                opacity: 1,
                y: 0,
                duration: 1,
                ease: "power3.out",
                scrollTrigger: {
                  trigger: section,
                  start:
                    "top 82%",
                  once: true
                }
              }
            );
          });

        gsap.to(
          ".hero-depth-title",
          {
            yPercent: 18,
            ease: "none",
            scrollTrigger: {
              trigger: "#hero",
              start: "top top",
              end:
                "bottom top",
              scrub: true
            }
          }
        );

        gsap.to(
          ".hero-orbit-interface",
          {
            rotate: 26,
            scale: 1.08,
            ease: "none",
            scrollTrigger: {
              trigger: "#hero",
              start: "top top",
              end:
                "bottom top",
              scrub: true
            }
          }
        );

        gsap.to(
          ".lunar-horizon",
          {
            scale: 1.07,
            yPercent: -3,
            ease: "none",
            scrollTrigger: {
              trigger: "#moon",
              start:
                "top bottom",
              end:
                "bottom top",
              scrub: true
            }
          }
        );

        gsap.to(
          ".gateway-halo",
          {
            rotate: 120,
            ease: "none",
            scrollTrigger: {
              trigger:
                "#gateway",
              start:
                "top bottom",
              end:
                "bottom top",
              scrub: true
            }
          }
        );
      }, root);

    const sections =
      Array.from(
        root.querySelectorAll(
          "[data-chapter]"
        )
      );

    const observer =
      new IntersectionObserver(
        entries => {
          const visible =
            entries
              .filter(
                entry =>
                  entry.isIntersecting
              )
              .sort(
                (a, b) =>
                  b.intersectionRatio -
                  a.intersectionRatio
              )[0];

          if (visible) {
            setActiveChapter(
              visible.target
                .dataset.chapter
            );
          }
        },
        {
          threshold: [
            0.2,
            0.4,
            0.6
          ]
        }
      );

    sections.forEach(
      section =>
        observer.observe(
          section
        )
    );

    function updateProgress() {
      const height =
        document.documentElement
          .scrollHeight -
        window.innerHeight;

      setProgress(
        height > 0
          ? Math.min(
              1,
              Math.max(
                0,
                window.scrollY /
                  height
              )
            )
          : 0
      );
    }

    updateProgress();

    window.addEventListener(
      "scroll",
      updateProgress,
      {
        passive: true
      }
    );

    return () => {
      observer.disconnect();

      window.removeEventListener(
        "scroll",
        updateProgress
      );

      context.revert();

      ScrollTrigger
        .getAll()
        .forEach(
          trigger =>
            trigger.kill()
        );
    };
  }, []);

  function jumpTo(id) {
    document
      .getElementById(id)
      ?.scrollIntoView({
        behavior: "smooth",
        block: "start"
      });
  }

  return (
    <div
      ref={rootRef}
      className="artemis-app"
    >
      <SpaceSceneShell />

      <div
        className="depth-grid"
        aria-hidden="true"
      />

      <div
        className="pointer-light"
        aria-hidden="true"
      />

      <Navigation />

      <aside
        className="chapter-rail"
        aria-label="Page chapters"
      >
        {chapters.map(
          chapter => (
            <button
              key={chapter.id}
              type="button"
              className={
                activeChapter ===
                chapter.id
                  ? "active"
                  : ""
              }
              onClick={() =>
                jumpTo(
                  chapter.id
                )
              }
            >
              <span>
                {chapter.index}
              </span>

              <i />

              <strong>
                {chapter.label}
              </strong>
            </button>
          )
        )}
      </aside>

      <div
        className="global-telemetry"
        aria-hidden="true"
      >
        <span>
          ARTEMIS / EXPLORATION
        </span>

        <i />

        <strong>
          {String(
            Math.round(
              progress * 100
            )
          ).padStart(
            3,
            "0"
          )}
          %
        </strong>
      </div>

      <main>
        <section
          id="hero"
          data-chapter="hero"
          className="hero-section"
        >
          <div className="hero-depth-title">
            ARTEMIS
          </div>

          <div className="hero-copy">
            <div className="section-kicker">
              NASA / HUMAN
              EXPLORATION
            </div>

            <h1>
              WE GO
              <br />
              <em>FORWARD.</em>
            </h1>

            <p>
              A new generation
              of lunar exploration
              is assembling across
              Earth, deep space,
              lunar orbit, and the
              surface of the Moon.
            </p>

            <div className="hero-actions">
              <button
                type="button"
                onClick={() =>
                  jumpTo(
                    "missions"
                  )
                }
              >
                EXPLORE MISSIONS
                <span>↓</span>
              </button>

              <a
                href="https://www.nasa.gov/humans-in-space/artemis/"
                target="_blank"
                rel="noreferrer"
              >
                NASA ARTEMIS
                <span>↗</span>
              </a>
            </div>
          </div>

          <div
            className="hero-orbit-interface"
            aria-hidden="true"
          >
            <i />
            <i />
            <i />

            <div>
              <span>EARTH</span>
              <strong>
                MOON
              </strong>
              <small>
                MARS
              </small>
            </div>
          </div>

          <aside className="hero-flight-console">
            <header>
              <span>
                FLIGHT ENVIRONMENT
              </span>

              <i />

              <strong>
                INTERACTIVE
              </strong>
            </header>

            <div>
              <span>
                CAMERA
              </span>

              <strong>
                DIRECT MANIPULATION
              </strong>
            </div>

            <div>
              <span>
                DEPTH
              </span>

              <strong>
                HYBRID 2D / 3D
              </strong>
            </div>

            <div>
              <span>
                ENVIRONMENT
              </span>

              <strong>
                ADAPTIVE
              </strong>
            </div>

            <footer>
              <i />

              DRAG THE SCENE
            </footer>
          </aside>

          <div className="hero-bottom-metrics">
            <div>
              <span>DESTINATION</span>
              <strong>MOON</strong>
            </div>

            <div>
              <span>HORIZON</span>
              <strong>MARS</strong>
            </div>

            <div>
              <span>MODE</span>
              <strong>
                SUSTAINED
                EXPLORATION
              </strong>
            </div>
          </div>
        </section>

        <section
          id="missions"
          data-chapter="missions"
          className="content-section reveal-section"
        >
          <header className="section-heading">
            <span className="section-number">
              01
            </span>

            <div>
              <span className="section-kicker">
                THE CAMPAIGN
              </span>

              <h2>
                MISSIONS
              </h2>
            </div>

            <p>
              Explore the evolving
              Artemis campaign as
              connected missions,
              systems, phases, and
              destinations.
            </p>
          </header>

          <MissionExplorer />
        </section>

        <section
          id="systems"
          data-chapter="systems"
          className="content-section reveal-section"
        >
          <header className="section-heading">
            <span className="section-number">
              02
            </span>

            <div>
              <span className="section-kicker">
                INTEGRATED
                ARCHITECTURE
              </span>

              <h2>
                SYSTEMS
              </h2>
            </div>

            <p>
              Launch,
              transportation,
              orbital
              infrastructure, and
              surface systems form
              one exploration
              architecture.
            </p>
          </header>

          <SystemGrid />
        </section>

        <section
          id="trajectory"
          data-chapter="trajectory"
          className="content-section reveal-section trajectory-backplane"
        >
          <header className="section-heading">
            <span className="section-number">
              03
            </span>

            <div>
              <span className="section-kicker">
                MISSION GEOMETRY
              </span>

              <h2>
                TRAJECTORY
              </h2>
            </div>

            <p>
              Inspect mission
              sequences as an
              interactive spatial
              progression from
              launch through
              destination and
              return.
            </p>
          </header>

          <TrajectoryEngine />
        </section>

        <section
          id="moon"
          data-chapter="moon"
          className="feature-section lunar-feature reveal-section"
        >
          <div
            className="lunar-horizon"
            aria-hidden="true"
          >
            <div className="lunar-scan" />
          </div>

          <div className="feature-index">
            04
          </div>

          <article>
            <span className="section-kicker">
              THE LUNAR
              FRONTIER
            </span>

            <h2>
              RETURN.
              <br />
              LEARN.
              <br />
              REMAIN.
            </h2>

            <p>
              Artemis is designed
              around progressively
              more capable lunar
              exploration and the
              systems required for
              increasingly complex
              missions.
            </p>

            <button
              type="button"
              onClick={() => {
                window.location.hash =
                  "moon";
              }}
            >
              FOCUS LUNAR SPACE
              <span>↗</span>
            </button>
          </article>

          <aside>
            <span>
              ENVIRONMENT
            </span>

            <strong>
              LUNAR
            </strong>

            <i />

            <span>
              CAMERA STATE
            </span>

            <strong>
              INTERACTIVE
            </strong>
          </aside>
        </section>

        <section
          id="gateway"
          data-chapter="gateway"
          className="feature-section gateway-feature reveal-section"
        >
          <div
            className="gateway-halo"
            aria-hidden="true"
          >
            <i />
            <i />
            <i />
          </div>

          <div className="feature-index">
            05
          </div>

          <article>
            <span className="section-kicker">
              LUNAR ORBIT
            </span>

            <h2>
              GATEWAY
            </h2>

            <p>
              Lunar-orbiting
              infrastructure
              extends the
              exploration
              architecture beyond
              a single destination
              or mission.
            </p>

            <button
              type="button"
              onClick={() => {
                window.location.hash =
                  "gateway";
              }}
            >
              FOCUS GATEWAY
              <span>↗</span>
            </button>
          </article>

          <div className="gateway-readout">
            <span>
              ORBITAL
              INFRASTRUCTURE
            </span>

            <strong>
              DEEP SPACE
            </strong>

            <small>
              INTEGRATED
              ARCHITECTURE
            </small>
          </div>
        </section>

        <section
          id="future"
          data-chapter="future"
          className="future-section reveal-section"
        >
          <span className="section-number">
            06
          </span>

          <div>
            <span className="section-kicker">
              WHAT COMES NEXT
            </span>

            <h2>
              MOON
              <i>→</i>
              MARS
            </h2>

            <p>
              The lunar campaign
              develops experience,
              systems, operations,
              and knowledge for
              human exploration
              farther into deep
              space.
            </p>
          </div>

          <div
            className="future-vector"
            aria-hidden="true"
          >
            <i />
            <i />
            <i />

            <span>
              EARTH
            </span>

            <strong>
              MOON
            </strong>

            <b>
              MARS
            </b>
          </div>
        </section>
      </main>

      <footer className="site-footer">
        <div>
          <strong>
            ARTEMIS
          </strong>

          <span>
            HUMAN EXPLORATION
          </span>
        </div>

        <p>
          A cinematic
          visualization interface
          built around publicly
          presented Artemis
          exploration concepts.
        </p>

        <a
          href="https://www.nasa.gov/humans-in-space/artemis/"
          target="_blank"
          rel="noreferrer"
        >
          OFFICIAL NASA ARTEMIS
          <span>↗</span>
        </a>
      </footer>
    </div>
  );
}
