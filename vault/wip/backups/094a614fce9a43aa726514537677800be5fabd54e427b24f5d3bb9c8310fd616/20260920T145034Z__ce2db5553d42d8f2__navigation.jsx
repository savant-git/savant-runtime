import { useEffect, useState } from "react";

const links = [
  ["missions", "Missions"],
  ["systems", "Architecture"],
  ["trajectory", "Flight"],
  ["moon", "Surface"],
  ["gateway", "Gateway"],
  ["future", "Moon → Mars"]
];

export default function Navigation() {
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState("hero");

  useEffect(() => {
    const sections = [
      document.getElementById("hero"),
      ...links.map(([id]) => document.getElementById(id))
    ].filter(Boolean);

    const observer = new IntersectionObserver(
      entries => {
        const visible = entries
          .filter(entry => entry.isIntersecting)
          .sort(
            (a, b) =>
              b.intersectionRatio - a.intersectionRatio
          );

        if (visible[0]) {
          setActive(visible[0].target.id);
        }
      },
      {
        threshold: [0.2, 0.45, 0.7]
      }
    );

    sections.forEach(section => observer.observe(section));

    return () => observer.disconnect();
  }, []);

  function travel(id) {
    setOpen(false);

    document
      .getElementById(id)
      ?.scrollIntoView({
        behavior: "smooth",
        block: "start"
      });
  }

  return (
    <>
      <header className="topbar">
        <button
          className="brand"
          onClick={() => travel("hero")}
          aria-label="Return to Artemis introduction"
        >
          <span className="brand-mark">A</span>

          <span className="brand-copy">
            <strong>ARTEMIS</strong>
            <small>MOON TO MARS</small>
          </span>
        </button>

        <div className="status-strip">
          <span className="status-dot" />
          <span>EXPERIENCE ONLINE</span>
          <span className="status-divider" />
          <span>EARTH // LUNAR SPACE</span>
        </div>

        <button
          className="menu-trigger"
          aria-expanded={open}
          aria-controls="primary-navigation"
          onClick={() => setOpen(value => !value)}
        >
          <span>{open ? "CLOSE" : "EXPLORE"}</span>

          <span className={`menu-icon ${open ? "open" : ""}`}>
            <i />
            <i />
          </span>
        </button>
      </header>

      <nav
        id="primary-navigation"
        className={`navigation-panel ${open ? "open" : ""}`}
        aria-hidden={!open}
      >
        <div className="navigation-panel-inner">
          <div className="navigation-overline">
            FLIGHT DIRECTORY
          </div>

          <div className="navigation-links">
            {links.map(([id, label], index) => (
              <button
                key={id}
                onClick={() => travel(id)}
              >
                <span>
                  {String(index + 1).padStart(2, "0")}
                </span>

                <strong>{label}</strong>

                <i>↗</i>
              </button>
            ))}
          </div>

          <div className="navigation-footer">
            <span>ARTEMIS</span>
            <p>
              An independent interactive visualization based on
              NASA's Artemis exploration program.
            </p>
          </div>
        </div>
      </nav>

      <aside className="section-rail">
        <span className="rail-word">FLIGHT PLAN</span>

        <button
          className={active === "hero" ? "active" : ""}
          onClick={() => travel("hero")}
          aria-label="Introduction"
        >
          <i />
        </button>

        {links.map(([id, label]) => (
          <button
            key={id}
            className={active === id ? "active" : ""}
            onClick={() => travel(id)}
            aria-label={label}
          >
            <i />
          </button>
        ))}
      </aside>
    </>
  );
}
