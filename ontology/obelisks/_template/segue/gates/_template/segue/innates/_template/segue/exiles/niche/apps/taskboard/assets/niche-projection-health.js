(() => {
  "use strict";

  const SCHEMA =
    "savant.niche.projection-health.v1";

  const runtime = {
    initialized: false,
    open: false,
    generation: 0,
    controller: null,
    previousFocus: null,
    checkedAt: null,
    surfaces: new Map()
  };

  const endpointDefinitions = [
    {
      id: "health",
      label: "task engine",
      url: "/api/health"
    },
    {
      id: "tasks",
      label: "task projection",
      url: "/api/tasks"
    },
    {
      id: "dashboard",
      label: "dashboard projection",
      url: "/api/dashboard"
    },
    {
      id: "state",
      label: "state projection",
      url: "/api/state"
    },
    {
      id: "history",
      label: "history projection",
      url: "/api/history"
    },
    {
      id: "living",
      label: "living observatory",
      url: "/api/living"
    },
    {
      id: "fabric",
      label: "living fabric",
      url: "/api/living/fabric"
    }
  ];

  const escapeHtml = value =>
    String(
      value === null ||
      value === undefined
        ? ""
        : value
    )
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");

  const classifyPayload = (
    response,
    payload
  ) => {
    if (!response.ok) {
      return "unavailable";
    }

    if (
      payload &&
      typeof payload === "object"
    ) {
      if (
        payload.healthy === false ||
        payload.degraded === true
      ) {
        return "degraded";
      }

      const state =
        String(
          payload.availability ||
          payload.status ||
          ""
        ).toLowerCase();

      if (
        state === "degraded" ||
        state === "partial"
      ) {
        return "degraded";
      }

      if (
        state === "unavailable" ||
        state === "failed" ||
        state === "error"
      ) {
        return "unavailable";
      }
    }

    return "available";
  };

  const describePayload = (
    response,
    payload,
    elapsed
  ) => {
    const fragments = [
      `http ${response.status}`,
      `${elapsed}ms`
    ];

    if (
      payload &&
      typeof payload === "object"
    ) {
      const sequence =
        payload.sequence ??
        payload.fabric_sequence ??
        payload.metadata?.sequence;

      const count =
        payload.task_count ??
        payload.count ??
        payload.surface_count ??
        payload.metadata?.surface_count;

      if (
        sequence !== null &&
        sequence !== undefined
      ) {
        fragments.push(
          `sequence ${sequence}`
        );
      }

      if (
        count !== null &&
        count !== undefined
      ) {
        fragments.push(
          `count ${count}`
        );
      }
    }

    return fragments.join(" · ");
  };

  const probe = async (
    definition,
    controller
  ) => {
    const started =
      performance.now();

    try {
      const response =
        await fetch(
          definition.url,
          {
            signal: controller.signal,
            cache: "no-store",
            headers: {
              Accept: "application/json"
            }
          }
        );

      const elapsed =
        Math.max(
          0,
          Math.round(
            performance.now() -
            started
          )
        );

      let payload = null;

      try {
        payload =
          await response.json();
      } catch {
        payload = null;
      }

      return {
        id: definition.id,
        label: definition.label,
        state:
          classifyPayload(
            response,
            payload
          ),
        detail:
          describePayload(
            response,
            payload,
            elapsed
          )
      };
    } catch (error) {
      if (
        error?.name === "AbortError"
      ) {
        return null;
      }

      return {
        id: definition.id,
        label: definition.label,
        state: "unavailable",
        detail: "request failed"
      };
    }
  };

  const aggregate = rows => {
    if (!rows.length) {
      return "unknown";
    }

    if (
      rows.every(
        row =>
          row.state === "available"
      )
    ) {
      return "available";
    }

    if (
      rows.every(
        row =>
          row.state === "unavailable"
      )
    ) {
      return "unavailable";
    }

    if (
      rows.some(
        row =>
          row.state === "degraded" ||
          row.state === "unavailable"
      )
    ) {
      return "degraded";
    }

    return "unknown";
  };

  const render = () => {
    const body =
      document.getElementById(
        "niche-projection-health-body"
      );

    if (!body) {
      return;
    }

    const rows =
      [...runtime.surfaces.values()];

    const overall =
      aggregate(rows);

    body.innerHTML = `
      <div
        class="niche-projection-health-summary"
      >
        <span
          class="niche-projection-health-chip"
          data-state="${escapeHtml(overall)}"
        >
          overall:${escapeHtml(overall)}
        </span>

        <span
          class="niche-projection-health-chip"
        >
          surfaces:${rows.length}
        </span>

        <span
          class="niche-projection-health-chip"
        >
          checked:${
            escapeHtml(
              runtime.checkedAt ||
              "not checked"
            )
          }
        </span>
      </div>

      <div
        class="niche-projection-health-list"
      >
        ${
          rows.length
            ? rows.map(
                row => `
                  <div
                    class="
                      niche-projection-health-row
                    "
                    data-state="${
                      escapeHtml(row.state)
                    }"
                  >
                    <span
                      class="
                        niche-projection-health-name
                      "
                    >
                      ${escapeHtml(row.label)}
                    </span>

                    <span
                      class="
                        niche-projection-health-detail
                      "
                    >
                      ${escapeHtml(row.detail)}
                    </span>

                    <span
                      class="
                        niche-projection-health-state
                      "
                    >
                      ${escapeHtml(row.state)}
                    </span>
                  </div>
                `
              ).join("")
            : `
              <div
                class="
                  niche-projection-health-boundary
                "
              >
                Projection availability has
                not been checked.
              </div>
            `
        }
      </div>

      <div
        class="niche-projection-health-boundary"
      >
        Projection Health reports transport
        and explicitly represented health
        state only. Availability does not
        establish authority, correctness,
        freshness of source authority, or
        semantic completeness. A successful
        HTTP response means only that the
        projection answered this probe.
      </div>
    `;
  };

  const refresh = async () => {
    runtime.generation += 1;

    const generation =
      runtime.generation;

    runtime.controller?.abort();

    const controller =
      new AbortController();

    runtime.controller =
      controller;

    const rows =
      (
        await Promise.all(
          endpointDefinitions.map(
            definition =>
              probe(
                definition,
                controller
              )
          )
        )
      ).filter(Boolean);

    if (
      generation !==
      runtime.generation
    ) {
      return false;
    }

    runtime.surfaces =
      new Map(
        rows.map(
          row => [
            row.id,
            row
          ]
        )
      );

    runtime.checkedAt =
      new Date().toISOString();

    if (
      runtime.controller ===
      controller
    ) {
      runtime.controller = null;
    }

    render();

    window.dispatchEvent(
      new CustomEvent(
        "niche:projection-health-update",
        {
          detail: {
            schema: SCHEMA,
            state:
              aggregate(rows),
            surfaces:
              rows.map(
                row => ({
                  ...row
                })
              ),
            checkedAt:
              runtime.checkedAt,
            authorityEffect: "none",
            projectionOnly: true
          }
        }
      )
    );

    return true;
  };

  const ensureShell = () => {
    if (
      document.getElementById(
        "niche-projection-health"
      )
    ) {
      return;
    }

    const shell =
      document.createElement("aside");

    shell.id =
      "niche-projection-health";

    shell.className =
      "niche-projection-health";

    shell.hidden = true;

    shell.setAttribute(
      "aria-label",
      "Projection Health"
    );

    shell.innerHTML = `
      <header
        class="niche-projection-health-head"
      >
        <div>
          <p
            class="
              niche-projection-health-kicker
            "
          >
            availability / degradation
          </p>

          <h2
            class="
              niche-projection-health-title
            "
          >
            PROJECTION HEALTH
          </h2>
        </div>

        <button
          type="button"
          class="
            niche-projection-health-close
          "
          aria-label="
            Close Projection Health
          "
        >
          ×
        </button>
      </header>

      <div
        class="
          niche-projection-health-body
        "
        id="
          niche-projection-health-body
        "
      ></div>
    `;

    document.body.append(shell);

    shell
      .querySelector(
        ".niche-projection-health-close"
      )
      ?.addEventListener(
        "click",
        close
      );
  };

  const open = async () => {
    ensureShell();

    const shell =
      document.getElementById(
        "niche-projection-health"
      );

    if (!shell) {
      return;
    }

    runtime.previousFocus =
      document.activeElement;

    runtime.open = true;
    shell.hidden = false;

    render();
    await refresh();

    shell
      .querySelector(
        ".niche-projection-health-close"
      )
      ?.focus();
  };

  const close = () => {
    runtime.open = false;

    runtime.controller?.abort();

    const shell =
      document.getElementById(
        "niche-projection-health"
      );

    if (shell) {
      shell.hidden = true;
    }

    if (
      runtime.previousFocus &&
      document.contains(
        runtime.previousFocus
      )
    ) {
      runtime.previousFocus.focus();
    }
  };

  const bindTriggers = () => {
    document.addEventListener(
      "click",
      event => {
        const trigger =
          event.target.closest(
            [
              "[data-action='projection-health']",
              "[data-command='projection-health']",
              "[data-projection-health]"
            ].join(",")
          );

        if (trigger) {
          void open();
        }
      },
      true
    );
  };

  const bindRuntime = () => {
    window.addEventListener(
      "niche:semantic-runtime-update",
      event => {
        if (
          runtime.open &&
          event.detail?.changed
        ) {
          void refresh();
        }
      }
    );

    document.addEventListener(
      "visibilitychange",
      () => {
        if (
          !document.hidden &&
          runtime.open
        ) {
          void refresh();
        }
      }
    );
  };

  const initialize = () => {
    if (runtime.initialized) {
      return;
    }

    runtime.initialized = true;

    ensureShell();
    bindTriggers();
    bindRuntime();

    document.documentElement.dataset
      .nicheProjectionHealth =
      "ready";

    window.dispatchEvent(
      new CustomEvent(
        "niche:projection-health-ready",
        {
          detail: {
            schema: SCHEMA,
            authorityEffect: "none",
            projectionOnly: true
          }
        }
      )
    );
  };

  window.NicheProjectionHealth =
    Object.freeze({
      open,
      close,
      refresh,

      state: () => {
        const rows =
          [...runtime.surfaces.values()];

        return {
          schema: SCHEMA,
          open: runtime.open,
          state: aggregate(rows),
          checkedAt:
            runtime.checkedAt,
          surfaces:
            rows.map(
              row => ({
                ...row
              })
            ),
          authorityEffect: "none",
          projectionOnly: true
        };
      }
    });

  if (
    document.readyState === "loading"
  ) {
    document.addEventListener(
      "DOMContentLoaded",
      initialize,
      { once: true }
    );
  } else {
    initialize();
  }
})();
