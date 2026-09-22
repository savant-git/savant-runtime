import { useEffect, useRef } from "react";

import gsap from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";

import Navigation from "./components/navigation.jsx";
import MissionExplorer from "./components/mission-explorer.jsx";
import SystemGrid from "./components/system-grid.jsx";
import SpaceScene from "./scenes/space-scene.jsx";

gsap.registerPlugin(ScrollTrigger);

export default function App() {
  const root = useRef();

  useEffect(() => {
    const reducedMotion = window.matchMedia(
      "(prefers-reduced-motion: reduce)"
    ).matches;

    if (reducedMotion) {
      document.documentElement.classList.add(
        "reduced-motion"
      );

      return;
    }

    const context = gsap.context(() => {
      gsap.from(".hero-overline", {
        opacity: 0,
        y: 16,
        duration: 0.8,
        delay: 0.2,
        ease: "power3.out"
      });

      gsap.from(".hero-title span", {
        opacity: 0,
        yPercent: 80,
        rotateX: -35,
        stagger: 0.09,
        duration: 1.25,
        delay: 0.35,
        ease: "power4.out"
      });

      gsap.from(".hero-deck", {
        opacity: 0,
        y: 30,
        duration: 1,
        delay: 0.9,
        ease: "power3.out"
      });

      gsap.from(".hero-actions", {
        opacity: 0,
        y: 24,
        duration: 0.9,
        delay: 1.05,
        ease: "power3.out"
      });

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
                start: "top 72%"
              },
              opacity: 0,
              y: 55,
              stagger: 0.09,
              duration: 1,
              ease: "power3.out"
            }
          );
        });

      gsap.to(".hero-interface", {
        scrollTrigger: {
          trigger: "#hero",
          start: "top top",
          end: "bottom top",
          scrub: true
        },
        y: -110,
        opacity: 0.1,
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
    }, root);

    return () => context.revert();
  }, []);

  function scrollTo(id) {
    document
      .getElementById(id)
      ?.scrollIntoView({
        behavior: "smooth"
      });
  }

  return (
    <div ref={root} className="app">
      <SpaceScene />

      <div className="grain" />
      <div className="vignette" />

      <Navigation />

      <main>
        <section
          id="hero"
          className="hero"
        >
          <div className="hero-interface">
            <div className="hero-overline">
              <span>
                NASA // ARTEMIS PROGRAM
              </span>

              <i />

              <span>MOON TO MARS</span>
            </div>

            <h1 className="hero-title">
              <span>WE</span>
              <span>GO</span>
              <span className="outlined">
                FORWARD.
              </span>
            </h1>

            <p className="hero-deck">
              A new generation of lunar
              exploration. One evolving
              architecture connecting Earth,
              lunar space, the Moon and the
              technologies that carry humanity
              farther.
            </p>

            <div className="hero-actions">
              <button
                className="primary-action"
                onClick={() =>
                  scrollTo("missions")
                }
              >
                ENTER FLIGHT PLAN
                <span>↘</span>
              </button>

              <button
                className="secondary-action"
                onClick={() =>
                  scrollTo("systems")
                }
              >
                EXPLORE ARCHITECTURE
              </button>
            </div>
          </div>

          <div className="hero-orbit-ui">
            <div className="orbit-ring ring-one" />
            <div className="orbit-ring ring-two" />

            <span className="orbit-label label-earth">
              EARTH
            </span>

            <span className="orbit-label label-moon">
              MOON
            </span>

            <span className="orbit-coordinate">
              TRAJECTORY // ARTEMIS
            </span>
          </div>

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
          className="content-section reveal-section"
        >
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
              surface systems work as one
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
              Artemis missions combine
              launch, orbital operations,
              translunar flight, lunar
              operations and high-energy
              Earth return into a connected
              mission profile.
            </p>
          </div>

          <div className="trajectory-map">
            <div className="trajectory-line">
              <div className="trajectory-line-fill" />
            </div>

            <div className="trajectory-node node-one">
              <i />
              <span>01</span>
              <strong>LAUNCH</strong>
              <small>EARTH</small>
            </div>

            <div className="trajectory-node node-two">
              <i />
              <span>02</span>
              <strong>DEPARTURE</strong>
              <small>TRANS-LUNAR</small>
            </div>

            <div className="trajectory-node node-three">
              <i />
              <span>03</span>
              <strong>LUNAR SPACE</strong>
              <small>OPERATIONS</small>
            </div>

            <div className="trajectory-node node-four">
              <i />
              <span>04</span>
              <strong>RETURN</strong>
              <small>EARTH</small>
            </div>
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
