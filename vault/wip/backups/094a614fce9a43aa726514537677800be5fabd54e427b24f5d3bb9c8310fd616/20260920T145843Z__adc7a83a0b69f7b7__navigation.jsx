import {
  useEffect,
  useRef,
  useState
} from "react";

const links =
  Object.freeze([
    Object.freeze([
      "missions",
      "Missions"
    ]),
    Object.freeze([
      "systems",
      "Architecture"
    ]),
    Object.freeze([
      "trajectory",
      "Flight"
    ]),
    Object.freeze([
      "moon",
      "Surface"
    ]),
    Object.freeze([
      "gateway",
      "Gateway"
    ]),
    Object.freeze([
      "future",
      "Moon to Mars"
    ])
  ]);

export default function Navigation() {
  const [
    open,
    setOpen
  ] = useState(false);

  const [
    active,
    setActive
  ] = useState("hero");

  const menuButtonRef =
    useRef(null);

  const panelRef =
    useRef(null);

  useEffect(() => {
    const sections =
      [
        document.getElementById(
          "hero"
        ),
        ...links.map(
          ([id]) =>
            document.getElementById(
              id
            )
        )
      ].filter(Boolean);

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
                (
                  first,
                  second
                ) =>
                  second.intersectionRatio -
                  first.intersectionRatio
              )[0];

          if (visible) {
            setActive(
              visible.target.id
            );
          }
        },
        {
          rootMargin:
            "-30% 0px -55% 0px",
          threshold: [
            0,
            0.2,
            0.5
          ]
        }
      );

    sections.forEach(
      section =>
        observer.observe(
          section
        )
    );

    return () =>
      observer.disconnect();
  }, []);

  useEffect(() => {
    if (!open) {
      return undefined;
    }

    const previousOverflow =
      document.body.style
        .overflow;

    document.body.style.overflow =
      "hidden";

    const panel =
      panelRef.current;

    const focusable =
      panel?.querySelectorAll(
        "button,a[href],[tabindex]:not([tabindex='-1'])"
      ) ?? [];

    focusable[0]?.focus();

    const onKeyDown =
      event => {
        if (
          event.key ===
          "Escape"
        ) {
          setOpen(false);

          requestAnimationFrame(
            () =>
              menuButtonRef.current?.focus()
          );

          return;
        }

        if (
          event.key !==
            "Tab" ||
          focusable.length ===
            0
        ) {
          return;
        }

        const first =
          focusable[0];

        const last =
          focusable[
            focusable.length -
              1
          ];

        if (
          event.shiftKey &&
          document.activeElement ===
            first
        ) {
          event.preventDefault();
          last.focus();
        } else if (
          !event.shiftKey &&
          document.activeElement ===
            last
        ) {
          event.preventDefault();
          first.focus();
        }
      };

    window.addEventListener(
      "keydown",
      onKeyDown
    );

    return () => {
      document.body.style.overflow =
        previousOverflow;

      window.removeEventListener(
        "keydown",
        onKeyDown
      );
    };
  }, [
    open
  ]);

  function travel(
    id
  ) {
    setOpen(false);

    requestAnimationFrame(
      () => {
        document
          .getElementById(
            id
          )
          ?.scrollIntoView({
            behavior:
              window.matchMedia(
                "(prefers-reduced-motion: reduce)"
              ).matches
                ? "auto"
                : "smooth",
            block: "start"
          });
      }
    );
  }

  return (
    <>
      <header className="topbar">
        <button
          className="brand"
          type="button"
          onClick={() =>
            travel("hero")
          }
          aria-label="Return to Artemis introduction"
        >
          <span
            className="brand-mark"
            aria-hidden="true"
          >
            A
          </span>

          <span className="brand-copy">
            <strong>
              ARTEMIS
            </strong>

            <small>
              MOON TO MARS
            </small>
          </span>
        </button>

        <div
          className="status-strip"
          aria-hidden="true"
        >
          <span className="status-dot" />

          <span>
            EXPERIENCE ONLINE
          </span>

          <span className="status-divider" />

          <span>
            EARTH // LUNAR SPACE
          </span>
        </div>

        <button
          ref={menuButtonRef}
          className="menu-trigger"
          type="button"
          aria-expanded={open}
          aria-controls="primary-navigation"
          onClick={() =>
            setOpen(
              value =>
                !value
            )
          }
        >
          <span>
            {open
              ? "CLOSE"
              : "EXPLORE"}
          </span>

          <span
            className={[
              "menu-icon",
              open
                ? "open"
                : ""
            ]
              .filter(Boolean)
              .join(" ")}
            aria-hidden="true"
          >
            <i />
            <i />
          </span>
        </button>
      </header>

      <nav
        ref={panelRef}
        id="primary-navigation"
        className={[
          "navigation-panel",
          open
            ? "open"
            : ""
        ]
          .filter(Boolean)
          .join(" ")}
        aria-hidden={!open}
        aria-label="Artemis sections"
      >
        <div className="navigation-panel-inner">
          <div className="navigation-overline">
            FLIGHT DIRECTORY
          </div>

          <div className="navigation-links">
            {links.map(
              (
                [
                  id,
                  label
                ],
                index
              ) => (
                <button
                  key={id}
                  type="button"
                  onClick={() =>
                    travel(id)
                  }
                >
                  <span>
                    {String(
                      index + 1
                    ).padStart(
                      2,
                      "0"
                    )}
                  </span>

                  <strong>
                    {label}
                  </strong>

                  <i
                    aria-hidden="true"
                  >
                    ↗
                  </i>
                </button>
              )
            )}
          </div>

          <div className="navigation-footer">
            <span>
              ARTEMIS
            </span>

            <p>
              An independent
              interactive
              visualization based
              on NASA's Artemis
              exploration program.
            </p>
          </div>
        </div>
      </nav>

      <aside
        className="section-rail"
        aria-label="Section navigation"
      >
        <span
          className="rail-word"
          aria-hidden="true"
        >
          FLIGHT PLAN
        </span>

        <button
          type="button"
          className={
            active ===
            "hero"
              ? "active"
              : ""
          }
          onClick={() =>
            travel("hero")
          }
          aria-label="Introduction"
          aria-current={
            active ===
            "hero"
              ? "location"
              : undefined
          }
        >
          <i />
        </button>

        {links.map(
          ([
            id,
            label
          ]) => (
            <button
              key={id}
              type="button"
              className={
                active ===
                id
                  ? "active"
                  : ""
              }
              onClick={() =>
                travel(id)
              }
              aria-label={label}
              aria-current={
                active ===
                id
                  ? "location"
                  : undefined
              }
            >
              <i />
            </button>
          )
        )}
      </aside>
    </>
  );
}
