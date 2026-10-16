import {
  useCallback,
  useEffect,
  useLayoutEffect,
  useMemo,
  useRef,
  useState,
} from "react";

import type {
  CSSProperties,
  KeyboardEvent as ReactKeyboardEvent,
} from "react";

import {
  mountSavantExperience,
} from "./experience";

import "./enhanced.css";


interface LandingPageProps {
  entered: boolean;
  onReady?: () => void;
}


interface Capability {
  index: string;
  name: string;
  description: string;
  signal: string;
}


interface Command {
  id: string;
  label: string;
  detail: string;
  keywords: string[];
}


const capabilities:
  Capability[] = [
    {
      index: "01",
      name: "Palaver",
      description:
        "Conversation becomes an operational interface rather than a detached chat surface.",
      signal: "interaction",
    },
    {
      index: "02",
      name: "Envoy",
      description:
        "Persona and cognitive composition remain explicit, modular, and independently addressable.",
      signal: "identity",
    },
    {
      index: "03",
      name: "Opus",
      description:
        "Model execution is separated from conversation, authority, memory, and mutation.",
      signal: "execution",
    },
    {
      index: "04",
      name: "Coda",
      description:
        "Durable mutation is bounded as its own capability instead of being hidden inside reasoning.",
      signal: "mutation",
    },
    {
      index: "05",
      name: "Niche",
      description:
        "Work is governed as finite, explicit, stateful tasks rather than ephemeral intention.",
      signal: "governance",
    },
    {
      index: "06",
      name: "Scrybe",
      description:
        "Context and recall are treated as composable substrates with provenance and replay.",
      signal: "memory",
    },
  ];


const principles = [
  [
    "Authority",
    "Meaning has precedence. Implementation follows authority, never the reverse.",
  ],
  [
    "Composition",
    "Atomic substance is instantiated once and reused through explicit composition.",
  ],
  [
    "Projection",
    "Derived structures emerge deterministically instead of becoming duplicate truth.",
  ],
  [
    "Lineage",
    "Identity, provenance, dependencies, and dependents remain visible and recoverable.",
  ],
  [
    "Optionality",
    "Systems evolve by extension and reversible migration rather than destructive replacement.",
  ],
  [
    "Determinism",
    "The same authoritative primitives should produce the same derived state.",
  ],
] as const;


const architecture = [
  "conversation",
  "persona",
  "execution",
  "mutation",
  "governance",
  "memory",
  "substantiation",
  "presentation",
  "authority",
  "normalization",
  "assurance",
  "evolution",
  "derivation",
  "mechanics",
  "evidence",
  "knowledge",
  "projection",
  "identity",
  "composition",
];


const authority = [
  "current directive",
  "authoritative graph",
  "accepted decisions",
  "constitutional canon",
  "verified implementation",
  "admitted evidence",
  "deterministic projection",
];


const navigation = [
  {
    id: "home",
    label: "Signal",
  },
  {
    id: "system",
    label: "System",
  },
  {
    id: "principles",
    label: "Principles",
  },
  {
    id: "architecture",
    label: "Architecture",
  },
  {
    id: "authority",
    label: "Authority",
  },
  {
    id: "contact",
    label: "Contact",
  },
];


const commands:
  Command[] = [
    {
      id: "home",
      label: "Return to signal",
      detail: "Beginning of the Savant system",
      keywords: [
        "home",
        "top",
        "signal",
        "start",
      ],
    },
    {
      id: "system",
      label: "Explore system",
      detail: "Bounded operational capabilities",
      keywords: [
        "system",
        "palaver",
        "envoy",
        "opus",
        "coda",
        "niche",
        "scrybe",
      ],
    },
    {
      id: "principles",
      label: "Read governing logic",
      detail:
        "Authority, composition, projection and lineage",
      keywords: [
        "principles",
        "authority",
        "composition",
        "projection",
        "lineage",
      ],
    },
    {
      id: "architecture",
      label: "Inspect architecture",
      detail: "The modular Savant edifice",
      keywords: [
        "architecture",
        "runtime",
        "modules",
        "edifice",
      ],
    },
    {
      id: "authority",
      label: "Inspect authority",
      detail:
        "How Savant distinguishes truth from derivation",
      keywords: [
        "authority",
        "truth",
        "canon",
        "evidence",
      ],
    },
    {
      id: "manifesto",
      label: "Read proposition",
      detail:
        "The composition premise behind Savant",
      keywords: [
        "manifesto",
        "proposition",
        "identity",
        "meaning",
      ],
    },
    {
      id: "contact",
      label: "Repository and contact",
      detail: "Public Savant runtime",
      keywords: [
        "contact",
        "repository",
        "github",
      ],
    },
  ];


function prefersReducedMotion() {
  return window
    .matchMedia(
      "(prefers-reduced-motion: reduce)",
    )
    .matches;
}


export function LandingPage({
  entered,
  onReady,
}: LandingPageProps) {
  const root =
    useRef<HTMLElement>(null);

  const commandInputRef =
    useRef<HTMLInputElement>(null);

  const [
    commandOpen,
    setCommandOpen,
  ] = useState(false);

  const [
    mobileNavigationOpen,
    setMobileNavigationOpen,
  ] = useState(false);

  const [
    activeSection,
    setActiveSection,
  ] = useState("home");

  const [
    activeArchitecture,
    setActiveArchitecture,
  ] = useState(
    "conversation",
  );

  const [
    expandedCapability,
    setExpandedCapability,
  ] = useState<
    string | null
  >(null);

  const [
    commandQuery,
    setCommandQuery,
  ] = useState("");

  const [
    commandCursor,
    setCommandCursor,
  ] = useState(0);

  const [
    localTime,
    setLocalTime,
  ] = useState("");


  const architectureString =
    useMemo(
      () =>
        architecture.join(
          " · ",
        ),
      [],
    );


  const visibleCommands =
    useMemo(
      () => {
        const query =
          commandQuery
            .trim()
            .toLowerCase();

        if (!query) {
          return commands;
        }

        return commands.filter(
          (command) =>
            [
              command.label,
              command.detail,
              ...command.keywords,
            ]
              .join(" ")
              .toLowerCase()
              .includes(query),
        );
      },
      [commandQuery],
    );


  useLayoutEffect(
    () => {
      onReady?.();
    },
    [onReady],
  );


  useEffect(
    () =>
      mountSavantExperience({
        root,
        entered,
      }),
    [entered],
  );


  useEffect(
    () => {
      const update = () => {
        setLocalTime(
          new Intl.DateTimeFormat(
            undefined,
            {
              hour: "2-digit",
              minute: "2-digit",
              second: "2-digit",
            },
          ).format(
            new Date(),
          ),
        );
      };

      update();

      const timer =
        window.setInterval(
          update,
          1000,
        );

      return () =>
        window.clearInterval(
          timer,
        );
    },
    [],
  );


  useEffect(
    () => {
      const onSection = (
        event: Event,
      ) => {
        const custom =
          event as CustomEvent<{
            section?: string;
          }>;

        if (
          custom.detail.section
        ) {
          setActiveSection(
            custom.detail.section,
          );
        }
      };

      window.addEventListener(
        "savant:section",
        onSection,
      );

      return () => {
        window.removeEventListener(
          "savant:section",
          onSection,
        );
      };
    },
    [],
  );


  const closeCommand =
    useCallback(
      () => {
        setCommandOpen(false);
        setCommandQuery("");
        setCommandCursor(0);
      },
      [],
    );


  useEffect(
    () => {
      const keydown = (
        event: KeyboardEvent,
      ) => {
        if (
          (
            event.metaKey
            || event.ctrlKey
          )
          && event.key
            .toLowerCase()
          === "k"
        ) {
          event.preventDefault();

          setCommandOpen(
            (value) => !value,
          );

          setMobileNavigationOpen(
            false,
          );

          return;
        }

        if (
          event.key === "Escape"
        ) {
          closeCommand();

          setMobileNavigationOpen(
            false,
          );
        }
      };

      window.addEventListener(
        "keydown",
        keydown,
      );

      return () => {
        window.removeEventListener(
          "keydown",
          keydown,
        );
      };
    },
    [closeCommand],
  );


  useEffect(
    () => {
      if (!commandOpen) {
        return;
      }

      window.requestAnimationFrame(
        () => {
          commandInputRef.current
            ?.focus();
        },
      );
    },
    [commandOpen],
  );


  useEffect(
    () => {
      setCommandCursor(0);
    },
    [commandQuery],
  );


  const jump =
    useCallback(
      (
        id: string,
      ) => {
        closeCommand();

        setMobileNavigationOpen(
          false,
        );

        const target =
          document.getElementById(
            id,
          );

        if (!target) {
          return;
        }

        const navigate = () => {
          target.scrollIntoView({
            behavior:
              prefersReducedMotion()
                ? "auto"
                : "smooth",
            block: "start",
          });

          history.replaceState(
            null,
            "",
            `#${id}`,
          );
        };

        if (
          !prefersReducedMotion()
          && typeof document.startViewTransition
            === "function"
        ) {
          document.startViewTransition(
            navigate,
          );

          return;
        }

        navigate();
      },
      [closeCommand],
    );


  function commandKeyDown(
    event:
      ReactKeyboardEvent<HTMLInputElement>,
  ) {
    if (
      visibleCommands.length === 0
    ) {
      return;
    }

    if (
      event.key === "ArrowDown"
    ) {
      event.preventDefault();

      setCommandCursor(
        (current) =>
          (
            current + 1
          )
          % visibleCommands.length,
      );

      return;
    }

    if (
      event.key === "ArrowUp"
    ) {
      event.preventDefault();

      setCommandCursor(
        (current) =>
          (
            current
            - 1
            + visibleCommands.length
          )
          % visibleCommands.length,
      );

      return;
    }

    if (
      event.key === "Enter"
    ) {
      event.preventDefault();

      const command =
        visibleCommands[
          commandCursor
        ];

      if (command) {
        jump(command.id);
      }
    }
  }


  return (
    <main
      ref={root}
      id="site-main"
      className={
        `site ${
          entered
            ? "site--entered"
            : ""
        }`
      }
      tabIndex={-1}
      aria-hidden={!entered}
      data-active-section={
        activeSection
      }
    >
      <a
        className="site__skip"
        href="#system"
      >
        Skip to content
      </a>

      <div
        className="site__ambient"
        aria-hidden="true"
      >
        <div
          className="site__cursor-light"
        />

        <div
          className="site__grid"
        />

        <div
          className="site__noise"
        />
      </div>

      <div
        className="site__progress"
        aria-hidden="true"
      >
        <span />
      </div>

      <nav
        className="site__nav"
        aria-label="Primary"
      >
        <a
          className="brand"
          href="#home"
          data-magnetic
          onClick={(event) => {
            event.preventDefault();
            jump("home");
          }}
        >
          <span
            className="brand__mark"
          >
            S
          </span>

          <span
            className="brand__word"
          >
            SAVANT
          </span>
        </a>

        <div
          className="site__nav-links"
        >
          {navigation
            .slice(1, 5)
            .map((item) => (
              <a
                key={item.id}
                href={`#${item.id}`}
                aria-current={
                  activeSection
                  === item.id
                    ? "location"
                    : undefined
                }
                onClick={(event) => {
                  event.preventDefault();
                  jump(item.id);
                }}
              >
                {item.label}
              </a>
            ))}
        </div>

        <div
          className="site__nav-actions"
        >
          <span
            className="site__section-state"
            aria-live="polite"
          >
            {activeSection}
          </span>

          <button
            type="button"
            className="mobile-navigation-trigger"
            aria-expanded={
              mobileNavigationOpen
            }
            aria-controls="mobile-navigation"
            onClick={() => {
              setMobileNavigationOpen(
                (value) => !value,
              );
            }}
          >
            <span>
              Menu
            </span>

            <i aria-hidden="true">
              {mobileNavigationOpen
                ? "×"
                : "≡"}
            </i>
          </button>

          <button
            type="button"
            className="command-trigger"
            data-magnetic
            onClick={() => {
              setCommandOpen(true);
            }}
            aria-expanded={
              commandOpen
            }
          >
            <span>
              Command
            </span>

            <kbd>
              ⌘K
            </kbd>
          </button>
        </div>
      </nav>

      {mobileNavigationOpen && (
        <div
          id="mobile-navigation"
          className="mobile-navigation"
        >
          {navigation.map(
            (
              item,
              index,
            ) => (
              <button
                type="button"
                key={item.id}
                className={
                  activeSection
                  === item.id
                    ? "active"
                    : ""
                }
                onClick={() => {
                  jump(item.id);
                }}
              >
                <span>
                  {String(
                    index + 1,
                  ).padStart(
                    2,
                    "0",
                  )}
                </span>

                <strong>
                  {item.label}
                </strong>

                <i>
                  ↘
                </i>
              </button>
            ),
          )}
        </div>
      )}

      <section
        id="home"
        className="site__hero"
        data-section="home"
      >
        <div
          className="hero__signal"
          data-parallax="6"
          aria-hidden="true"
        >
          <span />
          <span />
          <span />
        </div>

        <div
          className="hero__meta"
          data-reveal
        >
          <span>
            Self-hosted intelligence architecture
          </span>

          <span
            className="hero__meta-status"
          >
            <i />
            system active
          </span>
        </div>

        <div
          className="hero__title-wrap"
        >
          <p
            className="eyebrow"
            data-reveal
          >
            intelligence / composition / emergence
          </p>

          <h1 data-reveal>
            <span>
              SAVANT
            </span>
          </h1>

          <div
            className="hero__thesis"
            data-reveal
          >
            <p>
              Intelligence is not a feature.
            </p>

            <p>
              It is a system of explicit authority,
              reusable substance, deterministic projection,
              and controlled evolution.
            </p>
          </div>
        </div>

        <div
          className="hero__footer"
          data-reveal
        >
          <button
            type="button"
            className="site__cta"
            data-magnetic
            onClick={() => {
              jump("system");
            }}
          >
            <span>
              Enter the architecture
            </span>

            <span aria-hidden="true">
              ↘
            </span>
          </button>

          <div
            className="hero__coordinates"
          >
            <span>
              runtime / active
            </span>

            <span>
              {localTime || "—"}
            </span>
          </div>
        </div>

        <div
          className="hero__orbital"
          aria-hidden="true"
        >
          <div
            className={
              "hero__orbital-ring "
              + "hero__orbital-ring--one"
            }
          />

          <div
            className={
              "hero__orbital-ring "
              + "hero__orbital-ring--two"
            }
          />

          <div
            className="hero__orbital-core"
          />
        </div>
      </section>

      <section
        id="system"
        className={
          "site__section "
          + "system-section"
        }
        data-section="system"
      >
        <header
          className="section-heading"
        >
          <p
            className="eyebrow"
            data-reveal
          >
            01 / substantiated system
          </p>

          <h2 data-reveal>
            Not an assistant.
            <br />
            <em>
              An architecture.
            </em>
          </h2>

          <p
            className="section-heading__lede"
            data-reveal
          >
            Savant decomposes intelligence into bounded
            capabilities so conversation, identity,
            execution, memory, mutation, authority,
            and presentation do not collapse into one
            opaque machine.
          </p>
        </header>

        <div
          className="capability-grid"
        >
          {capabilities.map(
            (capability) => {
              const expanded =
                expandedCapability
                === capability.name;

              return (
                <article
                  key={capability.name}
                  className={
                    `capability-card ${
                      expanded
                        ? "capability-card--expanded"
                        : ""
                    }`
                  }
                  data-depth
                  data-reveal
                >
                  <button
                    type="button"
                    className="capability-card__control"
                    aria-expanded={expanded}
                    onClick={() => {
                      setExpandedCapability(
                        (current) =>
                          current
                          === capability.name
                            ? null
                            : capability.name,
                      );
                    }}
                  >
                    <span
                      className="capability-card__top"
                    >
                      <span>
                        {capability.index}
                      </span>

                      <span
                        className="capability-card__signal"
                      >
                        {capability.signal}
                      </span>
                    </span>

                    <span
                      className="capability-card__main"
                    >
                      <strong>
                        {capability.name}
                      </strong>

                      <i aria-hidden="true">
                        {expanded
                          ? "−"
                          : "+"}
                      </i>
                    </span>

                    <span
                      className="capability-card__description"
                    >
                      {capability.description}
                    </span>
                  </button>

                  <div
                    className="capability-card__trace"
                    data-trace
                  />
                </article>
              );
            },
          )}
        </div>
      </section>

      <section
        id="principles"
        className={
          "site__section "
          + "principles-section"
        }
        data-section="principles"
      >
        <div
          className="principles-intro"
        >
          <p
            className="eyebrow"
            data-reveal
          >
            02 / governing logic
          </p>

          <h2 data-reveal>
            Substance once.
            <br />
            Meaning preserved.
            <br />
            Structure emerges.
          </h2>
        </div>

        <div
          className="principles-list"
        >
          {principles.map(
            (
              [
                name,
                description,
              ],
              index,
            ) => (
              <article
                key={name}
                className="principle"
                data-reveal
              >
                <span
                  className="principle__index"
                >
                  {String(
                    index + 1,
                  ).padStart(
                    2,
                    "0",
                  )}
                </span>

                <h3>
                  {name}
                </h3>

                <p>
                  {description}
                </p>

                <span
                  className="principle__arrow"
                  aria-hidden="true"
                >
                  ↗
                </span>
              </article>
            ),
          )}
        </div>
      </section>

      <section
        id="architecture"
        className={
          "site__section "
          + "architecture-section"
        }
        data-section="architecture"
      >
        <div
          className="architecture-stage"
        >
          <p
            className="eyebrow"
            data-reveal
          >
            03 / modular edifice
          </p>

          <h2 data-reveal>
            Components do not merely connect.
            <br />
            They substantiate one another.
          </h2>

          <div
            className="architecture-interface"
            data-reveal
          >
            <div
              className="architecture-field"
            >
              <div
                className="architecture-field__core"
              >
                <span>
                  SAVANT
                </span>

                <small>
                  runtime
                </small>
              </div>

              {architecture
                .slice(0, 12)
                .map(
                  (
                    item,
                    index,
                  ) => (
                    <button
                      type="button"
                      key={item}
                      className={
                        `architecture-node ${
                          activeArchitecture
                          === item
                            ? "architecture-node--active"
                            : ""
                        }`
                      }
                      style={
                        {
                          "--node-index":
                            index,
                        } as CSSProperties
                      }
                      onClick={() => {
                        setActiveArchitecture(
                          item,
                        );
                      }}
                      aria-pressed={
                        activeArchitecture
                        === item
                      }
                    >
                      {item}
                    </button>
                  ),
                )}

              <div
                className={
                  "architecture-field__orbit "
                  + "architecture-field__orbit--a"
                }
                aria-hidden="true"
              />

              <div
                className={
                  "architecture-field__orbit "
                  + "architecture-field__orbit--b"
                }
                aria-hidden="true"
              />
            </div>

            <aside
              className="architecture-inspector"
              aria-live="polite"
            >
              <span>
                selected primitive
              </span>

              <strong>
                {activeArchitecture}
              </strong>

              <p>
                {activeArchitecture} remains an
                independently addressable component
                within the larger Savant composition.
              </p>

              <small>
                selection changes presentation only;
                it does not alter authority.
              </small>
            </aside>
          </div>
        </div>

        <div
          className="architecture-marquee"
          aria-label={
            architectureString
          }
        >
          <div>
            <span>
              {architectureString}
            </span>

            <span aria-hidden="true">
              {architectureString}
            </span>
          </div>
        </div>
      </section>

      <section
        id="authority"
        className={
          "site__section "
          + "authority-section"
        }
        data-section="authority"
      >
        <div
          className="authority-copy"
        >
          <p
            className="eyebrow"
            data-reveal
          >
            04 / authority before inference
          </p>

          <h2 data-reveal>
            The system knows the difference between
            what is true, what is derived, and what
            is merely possible.
          </h2>
        </div>

        <div
          className="authority-stack"
        >
          {authority.map(
            (
              item,
              index,
            ) => (
              <div
                className="authority-row"
                key={item}
                data-reveal
              >
                <span>
                  {String(
                    index + 1,
                  ).padStart(
                    2,
                    "0",
                  )}
                </span>

                <strong>
                  {item}
                </strong>

                <i />
              </div>
            ),
          )}
        </div>
      </section>

      <section
        id="manifesto"
        className={
          "site__section "
          + "manifesto-section"
        }
        data-section="manifesto"
      >
        <div
          className="manifesto__number"
          data-parallax="16"
          aria-hidden="true"
        >
          01
        </div>

        <div
          className="manifesto__copy"
        >
          <p
            className="eyebrow"
            data-reveal
          >
            the proposition
          </p>

          <blockquote
            data-reveal
          >
            A system becomes more intelligent when
            its parts can remain themselves while
            becoming something larger.
          </blockquote>

          <p data-reveal>
            Savant is built around that premise:
            preserve identity, preserve authority,
            preserve history, and let higher-order
            structures emerge through composition
            rather than duplication.
          </p>
        </div>
      </section>

      <footer
        id="contact"
        className="site__footer"
        data-section="contact"
      >
        <div
          className="footer__statement"
          data-reveal
        >
          <p className="eyebrow">
            Savant / system online
          </p>

          <h2>
            Intelligence,
            <br />
            given form.
          </h2>
        </div>

        <div
          className="footer__meta"
          data-reveal
        >
          <div>
            <span>
              Repository
            </span>

            <a
              href="https://github.com/savant-git/savant-runtime"
              target="_blank"
              rel="noreferrer"
            >
              savant-runtime ↗
            </a>
          </div>

          <div>
            <span>
              Interface
            </span>

            <button
              type="button"
              onClick={() => {
                jump("home");
              }}
            >
              return to signal ↑
            </button>
          </div>
        </div>

        <div
          className="footer__wordmark"
          aria-hidden="true"
        >
          SAVANT
        </div>
      </footer>

      {commandOpen && (
        <div
          className="command-layer"
          role="dialog"
          aria-modal="true"
          aria-label="Savant command palette"
          onPointerDown={(event) => {
            if (
              event.currentTarget
              === event.target
            ) {
              closeCommand();
            }
          }}
        >
          <div
            className={
              "command-palette "
              + "command-palette--enhanced"
            }
          >
            <header>
              <span>
                SAVANT / NAVIGATE
              </span>

              <kbd>
                ESC
              </kbd>
            </header>

            <label
              className="command-search"
            >
              <span aria-hidden="true">
                /
              </span>

              <input
                ref={commandInputRef}
                value={commandQuery}
                onChange={(event) => {
                  setCommandQuery(
                    event.target.value,
                  );
                }}
                onKeyDown={
                  commandKeyDown
                }
                placeholder="Search Savant"
                aria-label={
                  "Search navigation commands"
                }
                autoComplete="off"
              />

              <small>
                {visibleCommands.length}
              </small>
            </label>

            <div
              className="command-results"
              role="listbox"
            >
              {visibleCommands.map(
                (
                  command,
                  index,
                ) => (
                  <button
                    type="button"
                    role="option"
                    aria-selected={
                      index
                      === commandCursor
                    }
                    className={
                      index
                      === commandCursor
                        ? "active"
                        : ""
                    }
                    key={command.id}
                    onPointerEnter={() => {
                      setCommandCursor(
                        index,
                      );
                    }}
                    onClick={() => {
                      jump(command.id);
                    }}
                  >
                    <span>
                      {String(
                        index + 1,
                      ).padStart(
                        2,
                        "0",
                      )}
                    </span>

                    <span>
                      <strong>
                        {command.label}
                      </strong>

                      <small>
                        {command.detail}
                      </small>
                    </span>

                    <i>
                      ↘
                    </i>
                  </button>
                ),
              )}

              {visibleCommands.length
              === 0 && (
                <div
                  className="command-empty"
                >
                  No matching destination.
                </div>
              )}
            </div>

            <footer
              className="command-footer"
            >
              <span>
                ↑ ↓ navigate
              </span>

              <span>
                enter select
              </span>

              <span>
                esc close
              </span>
            </footer>
          </div>
        </div>
      )}
    </main>
  );
}
