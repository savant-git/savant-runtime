import React, { useEffect, useMemo, useRef, useState } from "react";
import "./styles/global.css";

const missions = [
  {
    id: "01",
    name: "artemis i",
    phase: "complete",
    type: "uncrewed lunar flight test",
    destination: "lunar orbit",
    distance: "1.4m mi",
    duration: "25d 10h",
    year: "2022",
    description:
      "The opening flight of the Artemis architecture validated Orion, the Space Launch System, ground systems, navigation, communications, recovery, and deep-space operations.",
  },
  {
    id: "02",
    name: "artemis ii",
    phase: "next",
    type: "crewed lunar flyby",
    destination: "beyond the moon",
    distance: "deep space",
    duration: "~10 days",
    year: "next",
    description:
      "Four astronauts extend the architecture into crewed deep space, testing Orion life-support and human operations beyond low Earth orbit.",
  },
  {
    id: "03",
    name: "artemis iii",
    phase: "landing",
    type: "crewed lunar expedition",
    destination: "lunar south pole",
    distance: "238k mi+",
    duration: "mission defined",
    year: "future",
    description:
      "The campaign advances toward sustained human exploration of the lunar south polar region and the systems required for increasingly capable expeditions.",
  },
];

const telemetry = [
  ["vehicle", "orion"],
  ["launch system", "sls"],
  ["domain", "cislunar"],
  ["network", "deep space"],
];

function usePointerField() {
  useEffect(() => {
    const move = (event) => {
      document.documentElement.style.setProperty(
        "--pointer-x",
        `${event.clientX}px`
      );
      document.documentElement.style.setProperty(
        "--pointer-y",
        `${event.clientY}px`
      );
      document.documentElement.style.setProperty(
        "--mx",
        `${event.clientX / window.innerWidth - 0.5}`
      );
      document.documentElement.style.setProperty(
        "--my",
        `${event.clientY / window.innerHeight - 0.5}`
      );
    };

    window.addEventListener("pointermove", move, { passive: true });
    return () => window.removeEventListener("pointermove", move);
  }, []);
}

function Starfield() {
  const canvasRef = useRef(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    const context = canvas.getContext("2d", { alpha: true });
    let frame;
    let width = 0;
    let height = 0;
    let stars = [];

    const resize = () => {
      const ratio = Math.min(window.devicePixelRatio || 1, 2);
      width = window.innerWidth;
      height = window.innerHeight;

      canvas.width = width * ratio;
      canvas.height = height * ratio;
      canvas.style.width = `${width}px`;
      canvas.style.height = `${height}px`;

      context.setTransform(ratio, 0, 0, ratio, 0, 0);

      stars = Array.from({ length: Math.floor(width / 4) }, (_, index) => ({
        x: Math.random() * width,
        y: Math.random() * height,
        z: Math.random(),
        r: Math.random() * 1.2 + 0.15,
        phase: Math.random() * Math.PI * 2,
        index,
      }));
    };

    const draw = (time) => {
      context.clearRect(0, 0, width, height);

      for (const star of stars) {
        const pulse =
          0.2 +
          Math.max(
            0,
            Math.sin(time * 0.00045 + star.phase)
          ) *
            0.55;

        context.beginPath();
        context.arc(star.x, star.y, star.r, 0, Math.PI * 2);
        context.fillStyle = `rgba(220,235,255,${
          pulse * (0.25 + star.z * 0.75)
        })`;
        context.fill();
      }

      frame = requestAnimationFrame(draw);
    };

    resize();
    window.addEventListener("resize", resize);
    frame = requestAnimationFrame(draw);

    return () => {
      window.removeEventListener("resize", resize);
      cancelAnimationFrame(frame);
    };
  }, []);

  return <canvas className="starfield" ref={canvasRef} aria-hidden="true" />;
}

function OrbitalScene({ progress }) {
  return (
    <div className="orbital-scene" aria-hidden="true">
      <div className="orbital-stage">
        <div className="lunar-halo" />

        <div className="moon">
          <div className="moon-noise" />
          <div className="moon-shadow" />
          <span className="crater crater-a" />
          <span className="crater crater-b" />
          <span className="crater crater-c" />
          <span className="crater crater-d" />
          <span className="crater crater-e" />
        </div>

        <div className="orbit orbit-one">
          <span />
        </div>

        <div className="orbit orbit-two">
          <span />
        </div>

        <div className="orbit orbit-three">
          <span />
        </div>

        <div
          className="trajectory"
          style={{ "--trajectory": progress }}
        >
          <div className="trajectory-line" />
          <div className="orion-marker">
            <span className="orion-core" />
            <span className="orion-wing left" />
            <span className="orion-wing right" />
          </div>
        </div>

        <div className="coordinate-ring ring-a" />
        <div className="coordinate-ring ring-b" />
        <div className="coordinate-ring ring-c" />
      </div>
    </div>
  );
}

function Rail({ active, setActive }) {
  return (
    <aside className="mission-rail">
      <div className="rail-axis">
        <span className="rail-live" />
      </div>

      {missions.map((mission, index) => (
        <button
          className={`rail-node ${active === index ? "active" : ""}`}
          key={mission.id}
          onClick={() => setActive(index)}
          aria-label={`open ${mission.name}`}
        >
          <span className="node-index">{mission.id}</span>
          <span className="node-dot" />
          <span className="node-copy">
            <strong>{mission.name}</strong>
            <small>{mission.type}</small>
          </span>
        </button>
      ))}
    </aside>
  );
}

function Navigation({ menuOpen, setMenuOpen }) {
  return (
    <>
      <header className="navigation">
        <a className="brand" href="#top" aria-label="Artemis home">
          <span className="brand-mark">
            <i />
            <b />
          </span>
          <span className="brand-word">artemis</span>
        </a>

        <div className="nav-status">
          <span className="status-pulse" />
          lunar exploration network
          <span>•</span>
          online
        </div>

        <button
          className={`menu-trigger ${menuOpen ? "open" : ""}`}
          onClick={() => setMenuOpen((value) => !value)}
          aria-label="toggle navigation"
        >
          <span />
          <span />
        </button>
      </header>

      <div className={`nav-overlay ${menuOpen ? "open" : ""}`}>
        <div className="nav-overlay-grid">
          <div className="nav-kicker">
            <span>exploration index</span>
            <small>01 / 05</small>
          </div>

          <nav>
            {[
              ["01", "mission"],
              ["02", "architecture"],
              ["03", "moon"],
              ["04", "science"],
              ["05", "future"],
            ].map(([number, label]) => (
              <a
                href={`#${label}`}
                key={label}
                onClick={() => setMenuOpen(false)}
              >
                <small>{number}</small>
                <span>{label}</span>
                <i>↗</i>
              </a>
            ))}
          </nav>

          <div className="nav-meta">
            <span>human deep-space exploration</span>
            <span>earth → moon → mars</span>
          </div>
        </div>
      </div>
    </>
  );
}

function Telemetry() {
  return (
    <div className="telemetry">
      {telemetry.map(([label, value]) => (
        <div key={label}>
          <span>{label}</span>
          <strong>{value}</strong>
        </div>
      ))}
    </div>
  );
}

function Hero({ active, setActive, scrollProgress }) {
  const mission = missions[active];

  return (
    <section className="hero" id="mission">
      <div className="hero-grid" />

      <OrbitalScene progress={scrollProgress} />

      <div className="hero-copy">
        <div className="eyebrow">
          <span>nasa lunar exploration</span>
          <i />
          <span>mission architecture / 001</span>
        </div>

        <h1>
          <span className="hero-line hero-line-one">return</span>
          <span className="hero-line hero-line-two">
            <i>to</i> the
          </span>
          <span className="hero-line hero-line-three">moon.</span>
        </h1>

        <div className="hero-subgrid">
          <p>
            A new human deep-space architecture, built not around a
            single destination, but around the ability to keep going.
          </p>

          <a href="#architecture" className="explore-control">
            <span>enter mission architecture</span>
            <i>↘</i>
          </a>
        </div>
      </div>

      <Rail active={active} setActive={setActive} />

      <div className="mission-readout">
        <div className="readout-header">
          <span>{mission.id}</span>
          <span>{mission.phase}</span>
        </div>
        <strong>{mission.name}</strong>
        <p>{mission.destination}</p>
      </div>

      <Telemetry />

      <div className="scroll-cue">
        <span>scroll to descend</span>
        <i />
      </div>
    </section>
  );
}

function Architecture() {
  const [hover, setHover] = useState(0);

  const systems = [
    {
      number: "01",
      title: "launch",
      label: "space launch system",
      body:
        "Heavy-lift propulsion provides the energy required to send Orion, crew, cargo, and exploration systems beyond Earth orbit.",
    },
    {
      number: "02",
      title: "transit",
      label: "orion",
      body:
        "The crew spacecraft carries astronauts through launch, deep-space transit, lunar operations, reentry, and recovery.",
    },
    {
      number: "03",
      title: "surface",
      label: "lunar systems",
      body:
        "Landing, mobility, power, communications, science, and habitation expand the campaign from visits into sustained exploration.",
    },
    {
      number: "04",
      title: "network",
      label: "gateway + deep space",
      body:
        "Orbital infrastructure and communications create a flexible staging architecture around the Moon.",
    },
  ];

  return (
    <section className="architecture" id="architecture">
      <div className="section-index">
        <span>02</span>
        <small>system architecture</small>
      </div>

      <div className="architecture-title">
        <p>one campaign.</p>
        <h2>
          many systems.
          <br />
          <em>one trajectory.</em>
        </h2>
      </div>

      <div className="architecture-deck">
        {systems.map((system, index) => (
          <article
            key={system.number}
            className={hover === index ? "active" : ""}
            onMouseEnter={() => setHover(index)}
            onFocus={() => setHover(index)}
            tabIndex="0"
          >
            <div className="system-top">
              <span>{system.number}</span>
              <i>+</i>
            </div>

            <div className="system-graphic">
              <span className={`system-symbol symbol-${index + 1}`}>
                <i />
                <b />
              </span>
            </div>

            <small>{system.label}</small>
            <h3>{system.title}</h3>
            <p>{system.body}</p>
          </article>
        ))}
      </div>
    </section>
  );
}

function LunarSection() {
  return (
    <section className="lunar-section" id="moon">
      <div className="lunar-sticky">
        <div className="lunar-disc">
          <div className="lunar-disc-inner" />
          <div className="lunar-coordinate longitude" />
          <div className="lunar-coordinate latitude" />
          <span className="landing-zone zone-a">
            <i />
            south polar region
          </span>
          <span className="landing-zone zone-b">
            <i />
            illumination study
          </span>
        </div>

        <div className="lunar-copy">
          <div className="section-index">
            <span>03</span>
            <small>the lunar frontier</small>
          </div>

          <h2>
            the moon
            <br />
            is not the
            <br />
            <em>finish line.</em>
          </h2>

          <p>
            It is a proving ground for the technologies, operations,
            science, logistics, and human experience required to work
            farther from Earth.
          </p>

          <div className="coordinate-data">
            <span>polar exploration</span>
            <strong>90° s</strong>
          </div>
        </div>
      </div>
    </section>
  );
}

function MissionSequence({ active, setActive }) {
  return (
    <section className="sequence" id="science">
      <div className="sequence-head">
        <div className="section-index">
          <span>04</span>
          <small>flight sequence</small>
        </div>

        <h2>the campaign is the spacecraft.</h2>
      </div>

      <div className="sequence-stage">
        <div className="sequence-axis" />

        {missions.map((mission, index) => (
          <button
            key={mission.id}
            onClick={() => setActive(index)}
            className={`sequence-mission ${
              active === index ? "active" : ""
            }`}
          >
            <span className="sequence-number">{mission.id}</span>
            <span className="sequence-point" />
            <div>
              <small>{mission.year}</small>
              <strong>{mission.name}</strong>
              <span>{mission.type}</span>
            </div>
          </button>
        ))}

        <div className="sequence-future">
          <span className="sequence-point" />
          <div>
            <small>continuum</small>
            <strong>mars</strong>
            <span>the architecture extends outward</span>
          </div>
        </div>
      </div>

      <div className="mission-focus">
        <span className="focus-id">{missions[active].id}</span>

        <div>
          <small>selected mission</small>
          <h3>{missions[active].name}</h3>
          <p>{missions[active].description}</p>
        </div>

        <dl>
          <div>
            <dt>destination</dt>
            <dd>{missions[active].destination}</dd>
          </div>
          <div>
            <dt>distance</dt>
            <dd>{missions[active].distance}</dd>
          </div>
          <div>
            <dt>duration</dt>
            <dd>{missions[active].duration}</dd>
          </div>
        </dl>
      </div>
    </section>
  );
}

function Future() {
  return (
    <section className="future" id="future">
      <div className="future-orbit orbit-left" />
      <div className="future-orbit orbit-right" />

      <div className="future-copy">
        <span>05 / beyond</span>

        <h2>
          moon
          <i>→</i>
          mars
        </h2>

        <p>
          Artemis is an evolving exploration architecture designed to
          increase what humans can reach, learn, build, and sustain
          beyond Earth.
        </p>

        <a
          href="https://www.nasa.gov/humans-in-space/artemis/"
          target="_blank"
          rel="noreferrer"
        >
          <span>explore official artemis</span>
          <i>↗</i>
        </a>
      </div>

      <footer>
        <span>artemis / human exploration</span>
        <span>earth • moon • deep space</span>
      </footer>
    </section>
  );
}

export default function App() {
  const [activeMission, setActiveMission] = useState(1);
  const [menuOpen, setMenuOpen] = useState(false);
  const [scrollProgress, setScrollProgress] = useState(0);

  usePointerField();

  useEffect(() => {
    const update = () => {
      const maximum =
        document.documentElement.scrollHeight - window.innerHeight;

      setScrollProgress(
        maximum > 0 ? Math.min(1, window.scrollY / maximum) : 0
      );
    };

    update();
    window.addEventListener("scroll", update, { passive: true });

    return () => window.removeEventListener("scroll", update);
  }, []);

  const progressLabel = useMemo(
    () => String(Math.round(scrollProgress * 100)).padStart(2, "0"),
    [scrollProgress]
  );

  return (
    <main id="top">
      <Starfield />
      <div className="grain" aria-hidden="true" />
      <div className="pointer-light" aria-hidden="true" />

      <Navigation
        menuOpen={menuOpen}
        setMenuOpen={setMenuOpen}
      />

      <div className="progress">
        <span style={{ height: `${scrollProgress * 100}%` }} />
        <small>{progressLabel}</small>
      </div>

      <Hero
        active={activeMission}
        setActive={setActiveMission}
        scrollProgress={scrollProgress}
      />

      <Architecture />
      <LunarSection />

      <MissionSequence
        active={activeMission}
        setActive={setActiveMission}
      />

      <Future />
    </main>
  );
}
