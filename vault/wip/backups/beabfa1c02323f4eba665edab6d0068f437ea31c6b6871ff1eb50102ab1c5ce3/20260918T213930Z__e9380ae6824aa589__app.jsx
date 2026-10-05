import { useEffect, useRef, useState } from "react";

import gsap from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";

import Navigation from "./components/navigation.jsx";
import MissionExplorer from "./components/mission-explorer.jsx";
import SystemGrid from "./components/system-grid.jsx";
import SpaceScene from "./scenes/space-scene.jsx";

gsap.registerPlugin(ScrollTrigger);

const chapters = [
  ["hero", "00", "DEPARTURE"],
  ["missions", "01", "MISSIONS"],
  ["systems", "02", "ARCHITECTURE"],
  ["trajectory", "03", "FLIGHT"],
  ["moon", "04", "SURFACE"],
  ["gateway", "05", "GATEWAY"],
  ["future", "06", "HORIZON"]
];

const telemetry = [
  ["PROGRAM", "ARTEMIS"],
  ["VECTOR", "MOON → MARS"],
  ["MODE", "EXPLORATION"],
  ["SYSTEM", "NOMINAL"]
];

export default function App() {
  const root = useRef(null);
  const [activeChapter, setActiveChapter] =
    useState("hero");
  const [progress, setProgress] = useState(0);
  const [coordinates, setCoordinates] =
    useState({ x: 50, y: 50 });

  useEffect(() => {
    const reducedMotion = window.matchMedia(
      "(prefers-reduced-motion: reduce)"
    ).matches;

    const updateProgress = () => {
      const maximum =
        document.documentElement.scrollHeight -
        window.innerHeight;

      setProgress(
        maximum > 0
          ? Math.min(
              100,
              (window.scrollY / maximum) * 100
            )
          : 0
      );
    };

    const observers = chapters.map(([id]) => {
      const element = document.getElementById(id);

      if (!element) {
        return null;
      }

      const observer = new IntersectionObserver(
        entries => {
          entries.forEach(entry => {
            if (entry.isIntersecting) {
              setActiveChapter(id);
            }
          });
        },
        {
          rootMargin: "-35% 0px -50% 0px",
          threshold: 0
        }
      );

      observer.observe(element);

      return observer;
    });

    window.addEventListener(
      "scroll",
      updateProgress,
      { passive: true }
    );

    updateProgress();

    if (reducedMotion) {
      document.documentElement.classList.add(
        "reduced-motion"
      );

      return () => {
        observers.forEach(observer =>
          observer?.disconnect()
        );

        window.removeEventListener(
          "scroll",
          updateProgress
        );
      };
    }

    const context = gsap.context(() => {
      const intro = gsap.timeline({
        defaults: {
          ease: "power4.out"
        }
      });

      intro
        .from(".hero-overline", {
          opacity: 0,
          y: 18,
          duration: 0.7
        })
        .from(
          ".hero-title-line",
          {
            yPercent: 115,
            rotateX: -48,
            opacity: 0,
            stagger: 0.08,
            duration: 1.15
          },
          "-=.35"
        )
        .from(
          ".hero-deck",
          {
            opacity: 0,
            y: 28,
            duration: 0.8
          },
          "-=.65"
        )
        .from(
          ".hero-actions, .hero-bottom",
          {
            opacity: 0,
            y: 20,
            stagger: 0.08,
            duration: 0.7
          },
          "-=.55"
        )
        .from(
          ".flight-console",
          {
            opacity: 0,
            x: 35,
            duration: 0.9
          },
          "-=.8"
        );

      gsap.utils
        .toArray(".reveal-section")
        .forEach(section => {
          gsap.from(
            section.querySelectorAll(
              ".section-kicker, .section-title, .section-copy"
            ),
            {
              scrollTrigger: {
                trigger: section,
                start: "top 74%"
              },
              opacity: 0,
              y: 52,
              stagger: 0.08,
              duration: 0.95,
              ease: "power3.out"
            }
          );
        });

      gsap.to(".hero-interface", {
        scrollTrigger: {
          trigger: "#hero",
          start: "top top",
          end: "bottom top",
          scrub: 1
        },
        y: -130,
        scale: 0.94,
        opacity: 0.08,
        ease: "none"
      });

      gsap.to(".hero-orbit-ui", {
        scrollTrigger: {
          trigger: "#hero",
          start: "top top",
          end: "bottom top",
          scrub: 1.2
        },
        rotate: 18,
        scale: 1.18,
        opacity: 0,
        ease: "none"
      });

      gsap.to(".trajectory-line-fill", {
        scrollTrigger: {
          trigger: "#trajectory",
          start: "top 70%",
          end: "bottom 55%",
          scrub: true
        },
        scaleX: 1,
        transformOrigin: "left center",
        ease: "none"
      });

      gsap.utils
        .toArray(".feature-index")
        .forEach(index => {
          gsap.fromTo(
            index,
            {
              opacity: 0.05,
              y: 80
            },
            {
              opacity: 0.18,
              y: -40,
              scrollTrigger: {
                trigger: index.parentElement,
                start: "top bottom",
                end: "bottom top",
                scrub: true
              }
            }
          );
        });
    }, root);

    return () => {
      context.revert();

      observers.forEach(observer =>
        observer?.disconnect()
      );

      window.removeEventListener(
        "scroll",
        updateProgress
      );
    };
  }, []);

  function scrollTo(id) {
    document.getElementById(id)?.scrollIntoView({
      behavior: "smooth"
    });
  }

  function trackPointer(event) {
    const x =
      (event.clientX / window.innerWidth) * 100;
    const y =
      (event.clientY / window.innerHeight) * 100;

    setCoordinates({
      x: Math.round(x),
      y: Math.round(y)
    });

    document.documentElement.style.setProperty(
      "--pointer-x",
      `${x}%`
    );

    document.documentElement.style.setProperty(
      "--pointer-y",
      `${y}%`
    );
  }

  const active =
    chapters.find(
      ([id]) => id === activeChapter
    ) ?? chapters[0];

  return (
    <div
      ref={root}
      className="app"
      onPointerMove={trackPointer}
    >
      <SpaceScene />

      <div className="grain" />
      <div className="vignette" />
      <div className="pointer-light" />

      <Navigation />

      <aside
        className="chapter-rail"
        aria-label="Page chapters"
      >
        <div className="chapter-progress">
          <i
            style={{
              height: `${progress}%`
            }}
          />
        </div>

        <div className="chapter-list">
          {chapters.map(
            ([id, number, label]) => (
              <button
                key={id}
                className={
                  activeChapter === id
                    ? "active"
                    : ""
                }
                onClick={() => scrollTo(id)}
              >
                <span>{number}</span>
                <strong>{label}</strong>
              </button>
            )
          )}
        </div>
      </aside>

      <aside className="global-telemetry">
        <div>
          <small>CHAPTER</small>
          <strong>
            {active[1]} / {active[2]}
          </strong>
        </div>

        <div>
          <small>VIEW VECTOR</small>
          <strong>
            {coordinates.x
              .toString()
              .padStart(2, "0")}
            .
            {coordinates.y
              .toString()
              .padStart(2, "0")}
          </strong>
        </div>

        <div>
          <small>DOCUMENT</small>
          <strong>
            {Math.round(progress)
              .toString()
              .padStart(2, "0")}
            %
          </strong>
        </div>
      </aside>

      <main>
        <section
          id="hero"
          className="hero"
        >
          <div className="hero-depth-grid" />

          <div className="hero-interface">
            <div className="hero-overline">
              <span>
                NASA // ARTEMIS PROGRAM
              </span>

              <i />

              <span>
                HUMAN EXPLORATION SYSTEM
              </span>
            </div>

            <h1
              className="hero-title"
              aria-label="We go forward"
            >
              <span className="hero-title-mask">
                <span className="hero-title-line">
                  WE
                </span>
              </span>

              <span className="hero-title-mask">
                <span className="hero-title-line">
                  GO
                </span>
              </span>

              <span className="hero-title-mask">
                <span className="hero-title-line outlined">
                  FORWARD.
                </span>
              </span>
            </h1>

            <div className="hero-narrative">
              <span className="hero-narrative-index">
                A / 01
              </span>

              <p className="hero-deck">
                A living exploration
                architecture spanning Earth,
                lunar orbit and the surface of
                another world. Artemis turns
                individual missions into one
                continuously expanding human
                system.
              </p>
            </div>

            <div className="hero-actions">
              <button
                className="primary-action"
                onClick={() =>
                  scrollTo("missions")
                }
              >
                <span>
                  ENTER FLIGHT PLAN
                </span>
                <b>↘</b>
              </button>

              <button
                className="secondary-action"
                onClick={() =>
                  scrollTo("systems")
                }
              >
                ARCHITECTURE
                <span>02</span>
              </button>
            </div>
          </div>

          <div className="hero-orbit-ui">
            <div className="orbit-axis axis-x" />
            <div className="orbit-axis axis-y" />
            <div className="orbit-ring ring-one" />
            <div className="orbit-ring ring-two" />
            <div className="orbit-ring ring-three" />

            <div className="orbit-body earth-body">
              <i />
              <span>EARTH</span>
            </div>

            <div className="orbit-body moon-body">
              <i />
              <span>MOON</span>
            </div>

            <span className="orbit-coordinate coordinate-a">
              TRAJECTORY // ARTEMIS
            </span>

            <span className="orbit-coordinate coordinate-b">
              CISELUNAR VECTOR
            </span>
          </div>

          <aside className="flight-console">
            <header>
              <span>FLIGHT SYSTEM</span>
              <i />
              <strong>LIVE MODEL</strong>
            </header>

            {telemetry.map(
              ([label, value], index) => (
                <div
                  className="console-row"
                  key={label}
                >
                  <span>
                    0{index + 1}
                  </span>

                  <small>{label}</small>
                  <strong>{value}</strong>
                </div>
              )
            )}

            <div className="console-vector">
              <i />
              <i />
              <i />
              <i />
              <span>
                EARTH
                <b />
                LUNA
              </span>
            </div>
          </aside>

          <div className="hero-bottom">
            <div>
              <small>DESTINATION</small>
              <strong>
                LUNAR EXPLORATION
              </strong>
            </div>

            <div>
              <small>ARCHITECTURE</small>
              <strong>
                CREW + ORBIT + SURFACE
              </strong>
            </div>

            <div>
              <small>VECTOR</small>
              <strong>MOON → MARS</strong>
            </div>

            <div>
              <small>PROGRAM STATE</small>
              <strong>EVOLVING</strong>
            </div>
          </div>

          <button
            className="scroll-indicator"
            onClick={() =>
              scrollTo("missions")
            }
          >
            <span>SCROLL TO DEPART</span>
            <i />
          </button>
        </section>

        <section
          id="missions"
          className="content-section reveal-section"
        >
          <div className="section-number">
            01
          </div>

          <header className="section-header">
            <div>
              <span className="section-kicker">
                01 / MISSIONS
              </span>

              <h2 className="section-title">
                One campaign.
                <br />
                <em>
                  Increasing capability.
                </em>
              </h2>
            </div>

            <p className="section-copy">
              Artemis is not a single flight.
              It is an evolving sequence of
              missions designed to validate
              transportation, crew operations,
              lunar infrastructure and surface
              capability.
            </p>
          </header>

          <MissionExplorer />
        </section>

        <section
          id="systems"
          className="content-section reveal-section systems-stage"
        >
          <div className="section-number">
            02
          </div>

          <header className="section-header">
            <div>
              <span className="section-kicker">
                02 / ARCHITECTURE
              </span>

              <h2 className="section-title">
                A system
                <br />
                <em>of systems.</em>
              </h2>
            </div>

            <p className="section-copy">
              Launch, spacecraft, orbital
              infrastructure, landers and
              surface systems operate as one
              expanding exploration
              architecture.
            </p>
          </header>

          <SystemGrid />
        </section>

        <section
          id="trajectory"
          className="trajectory-section reveal-section"
        >
          <div className="trajectory-copy">
            <span className="section-kicker">
              03 / FLIGHT
            </span>

            <h2 className="section-title">
              Earth is
              <br />
              <em>the beginning.</em>
            </h2>

            <p className="section-copy">
              Launch, translunar injection,
              lunar operations and high-energy
              return become one continuous
              choreography across hundreds of
              thousands of kilometers.
            </p>
          </div>

          <div className="trajectory-map">
            <div className="trajectory-backplane">
              <i />
              <i />
              <i />
              <i />
            </div>

            <div className="trajectory-line">
              <div className="trajectory-line-fill" />
            </div>

            {[
              [
                "node-one",
                "01",
                "LAUNCH",
                "EARTH"
              ],
              [
                "node-two",
                "02",
                "DEPARTURE",
                "TRANS-LUNAR"
              ],
              [
                "node-three",
                "03",
                "LUNAR SPACE",
                "OPERATIONS"
              ],
              [
                "node-four",
                "04",
                "RETURN",
                "EARTH"
              ]
            ].map(
              ([
                className,
                number,
                title,
                detail
              ]) => (
                <div
                  className={`trajectory-node ${className}`}
                  key={number}
                >
                  <i />
                  <span>{number}</span>
                  <strong>{title}</strong>
                  <small>{detail}</small>
                </div>
              )
            )}
          </div>
        </section>

        <section
          id="moon"
          className="feature-section moon-section reveal-section"
        >
          <div className="feature-index">
            04
          </div>

          <div className="feature-copy">
            <span className="section-kicker">
              LUNAR SURFACE
            </span>

            <h2 className="section-title">
              The Moon
              <br />
              becomes a
              <br />
              <em>working world.</em>
            </h2>

            <p className="section-copy">
              Surface exploration combines
              astronauts, advanced spacesuits,
              science instruments, mobility
              systems and increasingly durable
              infrastructure.
            </p>

            <div className="feature-data">
              <div>
                <small>REGION</small>
                <strong>
                  SOUTH POLAR EXPLORATION
                </strong>
              </div>

              <div>
                <small>FOCUS</small>
                <strong>
                  SCIENCE + OPERATIONS
                </strong>
              </div>
            </div>
          </div>

          <div className="lunar-horizon">
            <div className="horizon-grid" />
            <div className="horizon-scan" />
            <span>89.9° S</span>
            <i />
          </div>
        </section>

        <section
          id="gateway"
          className="feature-section gateway-section reveal-section"
        >
          <div className="feature-index">
            05
          </div>

          <div className="gateway-object">
            <div className="gateway-halo halo-a" />
            <div className="gateway-halo halo-b" />
            <div className="gateway-core" />

            <div className="gateway-arm arm-left" />
            <div className="gateway-arm arm-right" />

            <div className="gateway-panel panel-left" />
            <div className="gateway-panel panel-right" />

            <span className="annotation annotation-a">
              <i />
              LUNAR ORBIT
            </span>

            <span className="annotation annotation-b">
              <i />
              MODULAR ARCHITECTURE
            </span>
          </div>

          <div className="feature-copy">
            <span className="section-kicker">
              GATEWAY
            </span>

            <h2 className="section-title">
              A foothold
              <br />
              <em>around the Moon.</em>
            </h2>

            <p className="section-copy">
              Gateway extends the exploration
              architecture into lunar orbit,
              supporting science and
              increasingly complex operations
              around the Moon.
            </p>
          </div>
        </section>

        <section
          id="future"
          className="future-section reveal-section"
        >
          <div className="future-rings">
            <i />
            <i />
            <i />
            <i />
          </div>

          <div className="future-coordinate">
            ARTEMIS // HORIZON VECTOR
          </div>

          <span className="section-kicker">
            06 / HORIZON
          </span>

          <h2 className="section-title">
            THE MOON IS
            <br />
            <em>NOT THE ENDPOINT.</em>
          </h2>

          <p className="section-copy">
            Artemis develops the operational
            knowledge, technologies and
            exploration systems needed for a
            sustained lunar presence and the
            longer human journey toward Mars.
          </p>

          <div className="future-route">
            <span>EARTH</span>
            <i />
            <span>MOON</span>
            <i />
            <span>MARS</span>
          </div>

          <a
            className="nasa-link"
            href="https://www.nasa.gov/humans-in-space/artemis/"
            target="_blank"
            rel="noreferrer"
          >
            VISIT OFFICIAL NASA ARTEMIS
            <span>↗</span>
          </a>
        </section>
      </main>

      <footer>
        <strong>ARTEMIS</strong>

        <p>
          Independent interactive design
          concept. Program information is
          derived from publicly available NASA
          Artemis material. NASA remains the
          authoritative source.
        </p>

        <span>MOON → MARS</span>
      </footer>
    </div>
  );
}
