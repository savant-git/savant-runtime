(() => {
  "use strict";

  const SCHEMA =
    "savant.niche.semantic-runtime.v1";

  const INTERVAL_MS = 15000;

  const runtime = {
    initialized: false,
    generation: 0,
    controller: null,
    timer: null,
    state: "unknown",
    health: null,
    fabric: null,
    updatedAt: null,
    signature: null
  };

  const text = (
    value,
    fallback = "unknown"
  ) => {
    if (
      value === undefined ||
      value === null ||
      value === ""
    ) {
      return fallback;
    }

    return String(value);
  };

  const first = (
    object,
    paths
  ) => {
    for (const path of paths) {
      let current = object;
      let valid = true;

      for (
        const segment of path
      ) {
        if (
          current === null ||
          current === undefined ||
          !Object.prototype
            .hasOwnProperty.call(
              current,
              segment
            )
        ) {
          valid = false;
          break;
        }

        current =
          current[segment];
      }

      if (
        valid &&
        current !== undefined &&
        current !== null
      ) {
        return current;
      }
    }

    return null;
  };

  const ensureInstrument = () => {
    if (
      document.getElementById(
        "niche-semantic-runtime"
      )
    ) {
      return;
    }

    const instrument =
      document.createElement("section");

    instrument.id =
      "niche-semantic-runtime";

    instrument.className =
      "niche-semantic-runtime";

    instrument.dataset.state =
      "unknown";

    instrument.setAttribute(
      "aria-label",
      "Niche projection health"
    );

    instrument.innerHTML = `
      <span
        class="niche-runtime-mark"
        aria-hidden="true"
      ></span>

      <div class="niche-runtime-main">
        <span class="niche-runtime-kicker">
          projection health / freshness
        </span>

        <span
          class="niche-runtime-state"
          id="niche-runtime-state"
        >
          UNKNOWN
        </span>
      </div>

      <div class="niche-runtime-cells">
        <span class="niche-runtime-cell">
          <span class="niche-runtime-cell-label">
            tasks
          </span>
          <span
            class="niche-runtime-cell-value"
            id="niche-runtime-tasks"
          >
            unknown
          </span>
        </span>

        <span class="niche-runtime-cell">
          <span class="niche-runtime-cell-label">
            surfaces
          </span>
          <span
            class="niche-runtime-cell-value"
            id="niche-runtime-surfaces"
          >
            unknown
          </span>
        </span>

        <span class="niche-runtime-cell">
          <span class="niche-runtime-cell-label">
            sequence
          </span>
          <span
            class="niche-runtime-cell-value"
            id="niche-runtime-sequence"
          >
            unknown
          </span>
        </span>

        <span class="niche-runtime-cell">
          <span class="niche-runtime-cell-label">
            changes
          </span>
          <span
            class="niche-runtime-cell-value"
            id="niche-runtime-changes"
          >
            unknown
          </span>
        </span>

        <span class="niche-runtime-cell">
          <span class="niche-runtime-cell-label">
            age
          </span>
          <span
            class="niche-runtime-cell-value"
            id="niche-runtime-age"
          >
            unknown
          </span>
        </span>
      </div>
    `;

    const statusRail =
      document.getElementById(
        "statusrail"
      );

    if (
      statusRail?.parentNode
    ) {
      statusRail.insertAdjacentElement(
        "afterend",
        instrument
      );
      return;
    }

    const main =
      document.querySelector("main");

    if (main) {
      main.prepend(instrument);
      return;
    }

    document.body.prepend(
      instrument
    );
  };

  const requestJson = async (
    url,
    signal
  ) => {
    try {
      const response =
        await fetch(
          url,
          {
            signal,
            cache: "no-store",
            headers: {
              Accept:
                "application/json"
            }
          }
        );

      if (!response.ok) {
        return {
          state: "unavailable",
          status: response.status,
          payload: null
        };
      }

      return {
        state: "available",
        status: response.status,
        payload:
          await response.json()
      };
    } catch (error) {
      if (
        error?.name ===
        "AbortError"
      ) {
        return {
          state: "aborted",
          status: null,
          payload: null
        };
      }

      return {
        state: "unavailable",
        status: null,
        payload: null
      };
    }
  };

  const aggregateState = (
    health,
    fabric
  ) => {
    const states = [
      health?.state,
      fabric?.state
    ];

    if (
      states.every(
        state =>
          state === "available"
      )
    ) {
      return "available";
    }

    if (
      states.every(
        state =>
          state === "unavailable"
      )
    ) {
      return "unavailable";
    }

    if (
      states.includes("available") &&
      states.includes("unavailable")
    ) {
      return "degraded";
    }

    return "unknown";
  };

  const extract = (
    health,
    fabric
  ) => {
    const healthPayload =
      health?.payload || {};

    const fabricPayload =
      fabric?.payload || {};

    return {
      tasks:
        first(
          healthPayload,
          [
            ["task_count"],
            ["tasks", "count"],
            ["database", "task_count"]
          ]
        ),

      surfaces:
        first(
          fabricPayload,
          [
            ["surface_count"],
            ["metadata", "surface_count"],
            ["catalog", "surface_count"],
            ["health", "surface_count"]
          ]
        ),

      sequence:
        first(
          fabricPayload,
          [
            ["sequence"],
            ["metadata", "sequence"],
            ["receipt", "sequence"],
            ["health", "sequence"]
          ]
        ),

      changes:
        first(
          fabricPayload,
          [
            ["change_count"],
            ["metadata", "change_count"],
            ["receipt", "change_count"],
            ["health", "change_count"]
          ]
        ),

      hash:
        first(
          fabricPayload,
          [
            ["hash"],
            ["metadata", "hash"],
            ["receipt", "hash"],
            ["content_hash"]
          ]
        )
    };
  };

  const ageText = () => {
    if (!runtime.updatedAt) {
      return "unknown";
    }

    const seconds =
      Math.max(
        0,
        Math.floor(
          (
            Date.now() -
            runtime.updatedAt
          ) / 1000
        )
      );

    if (seconds < 60) {
      return `${seconds}s`;
    }

    return `${
      Math.floor(seconds / 60)
    }m`;
  };

  const setText = (
    id,
    value
  ) => {
    const node =
      document.getElementById(id);

    if (node) {
      node.textContent =
        text(value);
    }
  };

  const render = (
    extracted,
    changed
  ) => {
    ensureInstrument();

    const instrument =
      document.getElementById(
        "niche-semantic-runtime"
      );

    if (!instrument) {
      return;
    }

    instrument.dataset.state =
      runtime.state;

    setText(
      "niche-runtime-state",
      runtime.state
    );

    setText(
      "niche-runtime-tasks",
      extracted.tasks
    );

    setText(
      "niche-runtime-surfaces",
      extracted.surfaces
    );

    setText(
      "niche-runtime-sequence",
      extracted.sequence
    );

    setText(
      "niche-runtime-changes",
      extracted.changes
    );

    setText(
      "niche-runtime-age",
      ageText()
    );

    if (changed) {
      instrument.classList.remove(
        "niche-runtime-changed"
      );

      void instrument.offsetWidth;

      instrument.classList.add(
        "niche-runtime-changed"
      );
    }
  };

  const refresh = async () => {
    if (
      document.visibilityState ===
      "hidden"
    ) {
      return;
    }

    runtime.generation += 1;

    const generation =
      runtime.generation;

    runtime.controller?.abort();

    const controller =
      new AbortController();

    runtime.controller =
      controller;

    const [
      health,
      fabric
    ] = await Promise.all([
      requestJson(
        "/api/health",
        controller.signal
      ),
      requestJson(
        "/api/living/fabric",
        controller.signal
      )
    ]);

    if (
      generation !==
      runtime.generation
    ) {
      return;
    }

    if (
      health.state === "aborted" ||
      fabric.state === "aborted"
    ) {
      return;
    }

    runtime.health = health;
    runtime.fabric = fabric;
    runtime.state =
      aggregateState(
        health,
        fabric
      );
    runtime.updatedAt =
      Date.now();

    const extracted =
      extract(
        health,
        fabric
      );

    const signature =
      JSON.stringify({
        state: runtime.state,
        tasks: extracted.tasks,
        surfaces: extracted.surfaces,
        sequence: extracted.sequence,
        changes: extracted.changes,
        hash: extracted.hash
      });

    const changed =
      runtime.signature !== null &&
      runtime.signature !==
        signature;

    runtime.signature =
      signature;

    render(
      extracted,
      changed
    );

    window.dispatchEvent(
      new CustomEvent(
        "niche:semantic-runtime-update",
        {
          detail: {
            schema: SCHEMA,
            state: runtime.state,
            tasks: extracted.tasks,
            surfaces:
              extracted.surfaces,
            sequence:
              extracted.sequence,
            changes:
              extracted.changes,
            hash:
              extracted.hash,
            updatedAt:
              new Date(
                runtime.updatedAt
              ).toISOString(),
            changed,
            authorityEffect: "none",
            projectionOnly: true
          }
        }
      )
    );
  };

  const updateAge = () => {
    setText(
      "niche-runtime-age",
      ageText()
    );
  };

  const bindLifecycle = () => {
    document.addEventListener(
      "visibilitychange",
      () => {
        if (
          document.visibilityState ===
          "visible"
        ) {
          void refresh();
        }
      }
    );

    window.addEventListener(
      "online",
      () => {
        void refresh();
      }
    );

    window.addEventListener(
      "offline",
      () => {
        runtime.state =
          "unavailable";

        const extracted =
          extract(
            runtime.health,
            runtime.fabric
          );

        render(
          extracted,
          true
        );
      }
    );

    window.addEventListener(
      "focus",
      () => {
        void refresh();
      }
    );
  };

  const initialize = () => {
    if (runtime.initialized) {
      return;
    }

    runtime.initialized = true;

    ensureInstrument();
    bindLifecycle();

    void refresh();

    runtime.timer =
      window.setInterval(
        () => {
          void refresh();
          updateAge();
        },
        INTERVAL_MS
      );

    document.documentElement.dataset
      .nicheSemanticRuntime =
      "ready";

    window.dispatchEvent(
      new CustomEvent(
        "niche:semantic-runtime-ready",
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

  window.NicheSemanticRuntime =
    Object.freeze({
      refresh,

      state: () => ({
        schema: SCHEMA,
        availability:
          runtime.state,
        updatedAt:
          runtime.updatedAt
            ? new Date(
                runtime.updatedAt
              ).toISOString()
            : null,
        generation:
          runtime.generation,
        authorityEffect: "none",
        projectionOnly: true
      })
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
