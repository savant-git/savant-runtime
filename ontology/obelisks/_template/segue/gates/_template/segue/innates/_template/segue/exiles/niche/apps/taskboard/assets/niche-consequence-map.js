(() => {
  "use strict";

  const SCHEMA =
    "savant.niche.consequence-map.v1";

  const runtime = {
    initialized: false,
    open: false,
    taskId: null,
    generation: 0,
    controller: null,
    previousFocus: null,
    focal: null,
    direct: new Map(),
    second: new Map()
  };

  const array = value =>
    Array.isArray(value)
      ? value
      : [];

  const first = (object, keys) => {
    for (const key of keys) {
      const value = object?.[key];

      if (
        value !== null &&
        value !== undefined &&
        value !== ""
      ) {
        return value;
      }
    }

    return null;
  };

  const idOf = value => {
    if (
      typeof value === "string" &&
      value
    ) {
      return value;
    }

    if (
      value &&
      typeof value === "object"
    ) {
      const id =
        first(
          value,
          ["task_id", "taskId", "id"]
        );

      return (
        typeof id === "string" &&
        id
          ? id
          : null
      );
    }

    return null;
  };

  const idsOf = values =>
    [...new Set(
      array(values)
        .map(idOf)
        .filter(Boolean)
    )];

  const dependentsOf = task =>
    idsOf(task?.dependents);

  const titleOf = task =>
    first(
      task,
      ["title", "name", "purpose"]
    );

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

  const currentTaskId = () => {
    let state = {};

    try {
      state =
        window.Niche?.state?.() ||
        {};
    } catch {
      state = {};
    }

    return (
      runtime.taskId ||
      state.selectedTaskId ||
      state.recommendedTaskId ||
      null
    );
  };

  const fetchTask = async (
    id,
    controller
  ) => {
    if (!id) {
      return null;
    }

    try {
      const response =
        await fetch(
          `/api/tasks/${
            encodeURIComponent(id)
          }`,
          {
            signal: controller.signal,
            cache: "no-store",
            headers: {
              Accept: "application/json"
            }
          }
        );

      if (!response.ok) {
        return null;
      }

      const payload =
        await response.json();

      return payload?.task || payload;
    } catch (error) {
      if (
        error?.name === "AbortError"
      ) {
        return null;
      }

      return null;
    }
  };

  const resolve = async id => {
    runtime.generation += 1;

    const generation =
      runtime.generation;

    runtime.controller?.abort();

    const controller =
      new AbortController();

    runtime.controller =
      controller;

    const focal =
      await fetchTask(
        id,
        controller
      );

    if (
      generation !==
        runtime.generation ||
      !focal
    ) {
      return null;
    }

    const directIds =
      dependentsOf(focal);

    const directPairs =
      await Promise.all(
        directIds.map(
          async directId => [
            directId,
            await fetchTask(
              directId,
              controller
            )
          ]
        )
      );

    if (
      generation !==
      runtime.generation
    ) {
      return null;
    }

    const direct =
      new Map();

    for (
      const [directId, task]
      of directPairs
    ) {
      direct.set(
        directId,
        task
      );
    }

    const secondIds =
      [...new Set(
        directPairs
          .flatMap(
            ([, task]) =>
              task
                ? dependentsOf(task)
                : []
          )
          .filter(
            secondId =>
              secondId !== id &&
              !directIds.includes(
                secondId
              )
          )
      )];

    const secondPairs =
      await Promise.all(
        secondIds.map(
          async secondId => [
            secondId,
            await fetchTask(
              secondId,
              controller
            )
          ]
        )
      );

    if (
      generation !==
      runtime.generation
    ) {
      return null;
    }

    const second =
      new Map();

    for (
      const [secondId, task]
      of secondPairs
    ) {
      second.set(
        secondId,
        task
      );
    }

    if (
      runtime.controller ===
      controller
    ) {
      runtime.controller = null;
    }

    return {
      focal,
      direct,
      second
    };
  };

  const node = (id, task) => `
    <button
      type="button"
      class="niche-consequence-map-node"
      data-consequence-task="${
        escapeHtml(id)
      }"
    >
      <span
        class="niche-consequence-map-node-id"
      >
        ${escapeHtml(id)}
      </span>

      <span
        class="niche-consequence-map-node-title"
      >
        ${escapeHtml(
          titleOf(task) ||
          (
            task
              ? "title not projected"
              : "task payload unavailable"
          )
        )}
      </span>
    </button>
  `;

  const level = (
    name,
    levelName,
    tasks,
    emptyMessage
  ) => `
    <section
      class="niche-consequence-map-level"
      data-level="${escapeHtml(levelName)}"
    >
      <header
        class="niche-consequence-map-level-head"
      >
        <span>${escapeHtml(name)}</span>
        <span>${tasks.size}</span>
      </header>

      <div
        class="niche-consequence-map-list"
      >
        ${
          tasks.size
            ? [...tasks.entries()]
                .map(
                  ([id, task]) =>
                    node(id, task)
                )
                .join("")
            : `
              <div
                class="niche-consequence-map-empty"
              >
                ${escapeHtml(emptyMessage)}
              </div>
            `
        }
      </div>
    </section>
  `;

  const render = () => {
    const body =
      document.getElementById(
        "niche-consequence-map-body"
      );

    if (!body) {
      return;
    }

    if (!runtime.focal) {
      body.innerHTML = `
        <div
          class="niche-consequence-map-empty"
        >
          Downstream consequence topology
          is unavailable. Nothing has been
          reconstructed from missing data.
        </div>
      `;

      return;
    }

    body.innerHTML = `
      <div
        class="niche-consequence-map-summary"
      >
        <span
          class="niche-consequence-map-chip"
        >
          origin:${
            escapeHtml(runtime.taskId)
          }
        </span>

        <span
          class="niche-consequence-map-chip"
        >
          direct:${runtime.direct.size}
        </span>

        <span
          class="niche-consequence-map-chip"
        >
          second:${runtime.second.size}
        </span>

        <span
          class="niche-consequence-map-chip"
        >
          depth:2
        </span>
      </div>

      <div
        class="niche-consequence-map-levels"
      >
        ${level(
          "DIRECT CONSEQUENCES",
          "direct",
          runtime.direct,
          "No direct dependent is represented."
        )}

        ${level(
          "SECOND-ORDER VISIBLE CONSEQUENCES",
          "second",
          runtime.second,
          "No second-order consequence is derivable from the resolved direct neighborhood."
        )}

        <section
          class="niche-consequence-map-level"
          data-level="boundary"
        >
          <header
            class="niche-consequence-map-level-head"
          >
            <span>BEYOND RESOLVED HORIZON</span>
            <span>unknown</span>
          </header>

          <div
            class="niche-consequence-map-list"
          >
            <div
              class="niche-consequence-map-empty"
            >
              This projection deliberately
              stops after two represented
              dependency hops. Consequences
              beyond that boundary are not
              asserted by this instrument.
            </div>
          </div>
        </section>
      </div>

      <div
        class="niche-consequence-map-boundary"
      >
        Consequence Map shows represented
        dependency connectivity, not a
        prediction that a downstream task
        will execute, change, succeed, fail,
        or become ready. Direct and
        second-order placement describes
        graph distance only.
      </div>
    `;
  };

  const refresh = async id => {
    const resolved =
      id ||
      currentTaskId();

    runtime.taskId =
      resolved;

    if (!resolved) {
      runtime.focal = null;
      runtime.direct.clear();
      runtime.second.clear();
      render();
      return false;
    }

    const result =
      await resolve(resolved);

    if (!result) {
      runtime.focal = null;
      runtime.direct.clear();
      runtime.second.clear();
      render();
      return false;
    }

    runtime.focal =
      result.focal;

    runtime.direct =
      result.direct;

    runtime.second =
      result.second;

    render();

    return true;
  };

  const ensureShell = () => {
    if (
      document.getElementById(
        "niche-consequence-map"
      )
    ) {
      return;
    }

    const shell =
      document.createElement("aside");

    shell.id =
      "niche-consequence-map";

    shell.className =
      "niche-consequence-map";

    shell.hidden = true;

    shell.setAttribute(
      "aria-label",
      "Consequence Map"
    );

    shell.innerHTML = `
      <header
        class="niche-consequence-map-head"
      >
        <div>
          <p
            class="niche-consequence-map-kicker"
          >
            downstream / bounded horizon
          </p>

          <h2
            class="niche-consequence-map-title"
          >
            CONSEQUENCE MAP
          </h2>
        </div>

        <button
          type="button"
          class="niche-consequence-map-close"
          aria-label="Close Consequence Map"
        >
          ×
        </button>
      </header>

      <div
        class="niche-consequence-map-body"
        id="niche-consequence-map-body"
      ></div>
    `;

    document.body.append(shell);

    shell
      .querySelector(
        ".niche-consequence-map-close"
      )
      ?.addEventListener(
        "click",
        close
      );

    shell.addEventListener(
      "click",
      event => {
        const button =
          event.target.closest(
            "[data-consequence-task]"
          );

        if (!button) {
          return;
        }

        const id =
          button.dataset
            .consequenceTask;

        window
          .NicheCrossViewContinuity
          ?.select?.(id);

        const existing =
          [...document.querySelectorAll(
            "[data-task-id]"
          )].find(
            candidate =>
              candidate.dataset
                .taskId === id
          );

        if (existing) {
          existing.click();
        }

        void refresh(id);
      }
    );
  };

  const open = async id => {
    ensureShell();

    const shell =
      document.getElementById(
        "niche-consequence-map"
      );

    if (!shell) {
      return;
    }

    runtime.previousFocus =
      document.activeElement;

    runtime.open = true;
    shell.hidden = false;

    await refresh(id);

    shell
      .querySelector(
        ".niche-consequence-map-close"
      )
      ?.focus();
  };

  const close = () => {
    runtime.open = false;
    runtime.controller?.abort();

    const shell =
      document.getElementById(
        "niche-consequence-map"
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
              "[data-action='consequence-map']",
              "[data-command='consequence-map']",
              "[data-consequence-map]"
            ].join(",")
          );

        if (!trigger) {
          return;
        }

        const taskNode =
          trigger.closest(
            "[data-task-id]"
          );

        void open(
          taskNode?.dataset?.taskId ||
          currentTaskId()
        );
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
          void refresh(
            runtime.taskId
          );
        }
      }
    );

    window.addEventListener(
      "niche:continuity-selection",
      event => {
        const id =
          event.detail?.taskId;

        if (
          runtime.open &&
          id &&
          id !== runtime.taskId
        ) {
          void refresh(id);
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
      .nicheConsequenceMap =
      "ready";

    window.dispatchEvent(
      new CustomEvent(
        "niche:consequence-map-ready",
        {
          detail: {
            schema: SCHEMA,
            depth: 2,
            authorityEffect: "none",
            projectionOnly: true
          }
        }
      )
    );
  };

  window.NicheConsequenceMap =
    Object.freeze({
      open,
      close,
      refresh,

      state: () => ({
        schema: SCHEMA,
        open: runtime.open,
        taskId: runtime.taskId,
        directCount:
          runtime.direct.size,
        secondOrderCount:
          runtime.second.size,
        resolvedDepth: 2,
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
