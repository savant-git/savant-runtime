(() => {
  "use strict";

  const SCHEMA =
    "savant.niche.readiness-boundary.v1";

  const runtime = {
    initialized: false,
    open: false,
    generation: 0,
    controller: null,
    previousFocus: null,
    tasks: [],
    regions: {
      established: [],
      ready: [],
      blocked: [],
      future: []
    }
  };

  const array = value =>
    Array.isArray(value)
      ? value
      : [];

  const represented = value =>
    value !== null &&
    value !== undefined &&
    value !== "";

  const first = (object, keys) => {
    for (const key of keys) {
      if (
        object &&
        Object.prototype.hasOwnProperty.call(
          object,
          key
        ) &&
        represented(object[key])
      ) {
        return object[key];
      }
    }

    return null;
  };

  const idOf = task =>
    first(
      task,
      ["task_id", "taskId", "id"]
    );

  const stateOf = task =>
    String(
      first(
        task,
        ["state", "status"]
      ) || "unknown"
    ).toLowerCase();

  const readinessOf = task => {
    const value =
      first(
        task,
        [
          "readiness",
          "readiness_state",
          "ready"
        ]
      );

    if (value === true) {
      return "ready";
    }

    if (value === false) {
      return "not-ready";
    }

    return represented(value)
      ? String(value).toLowerCase()
      : "unknown";
  };

  const dependencies = task =>
    array(task?.dependencies);

  const unsatisfied = task =>
    array(
      task?.unsatisfied_dependencies
    );

  const blockers = task =>
    array(task?.blockers);

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

  const explicitReady = task => {
    const readiness =
      readinessOf(task);

    return (
      readiness === "ready" ||
      readiness === "true"
    );
  };

  const explicitBlocked = task => {
    const readiness =
      readinessOf(task);

    const state =
      stateOf(task);

    return (
      blockers(task).length > 0 ||
      unsatisfied(task).length > 0 ||
      readiness === "blocked" ||
      state === "blocked"
    );
  };

  const terminal = task => {
    const state =
      stateOf(task);

    return [
      "complete",
      "completed",
      "done",
      "cancelled",
      "canceled"
    ].includes(state);
  };

  const established = task => {
    if (terminal(task)) {
      return true;
    }

    const state =
      stateOf(task);

    return [
      "active",
      "started",
      "in_progress",
      "in-progress",
      "running"
    ].includes(state);
  };

  const classify = task => {
    if (established(task)) {
      return "established";
    }

    if (explicitBlocked(task)) {
      return "blocked";
    }

    if (explicitReady(task)) {
      return "ready";
    }

    /*
    The future region is intentionally
    conservative. It means only that the
    task is represented but is not placed
    into another region by explicit fields.
    */
    return "future";
  };

  const normalizeTasks = payload => {
    if (Array.isArray(payload)) {
      return payload;
    }

    for (
      const key of [
        "tasks",
        "items",
        "results"
      ]
    ) {
      if (
        Array.isArray(payload?.[key])
      ) {
        return payload[key];
      }
    }

    return [];
  };

  const fetchTasks = async () => {
    runtime.generation += 1;

    const generation =
      runtime.generation;

    runtime.controller?.abort();

    const controller =
      new AbortController();

    runtime.controller =
      controller;

    try {
      const response =
        await fetch(
          "/api/tasks",
          {
            signal: controller.signal,
            cache: "no-store",
            headers: {
              Accept: "application/json"
            }
          }
        );

      if (
        !response.ok ||
        generation !== runtime.generation
      ) {
        return null;
      }

      const payload =
        await response.json();

      if (
        generation !== runtime.generation
      ) {
        return null;
      }

      return normalizeTasks(payload);
    } catch (error) {
      if (
        error?.name === "AbortError"
      ) {
        return null;
      }

      return null;
    } finally {
      if (
        runtime.controller === controller
      ) {
        runtime.controller = null;
      }
    }
  };

  const partition = tasks => {
    const regions = {
      established: [],
      ready: [],
      blocked: [],
      future: []
    };

    for (const task of tasks) {
      regions[classify(task)].push(task);
    }

    return regions;
  };

  const taskButton = task => {
    const id =
      idOf(task) ||
      "unknown";

    return `
      <button
        type="button"
        class="niche-readiness-task"
        data-readiness-task="${
          escapeHtml(id)
        }"
      >
        <span
          class="niche-readiness-task-id"
        >
          ${escapeHtml(id)}
        </span>

        <span
          class="niche-readiness-task-state"
        >
          ${escapeHtml(
            readinessOf(task)
          )}
        </span>
      </button>
    `;
  };

  const region = (
    key,
    label,
    emptyMessage
  ) => {
    const tasks =
      runtime.regions[key];

    return `
      <section
        class="niche-readiness-region"
        data-region="${escapeHtml(key)}"
      >
        <header
          class="niche-readiness-region-head"
        >
          <span>${escapeHtml(label)}</span>
          <span>${tasks.length}</span>
        </header>

        <div
          class="niche-readiness-list"
        >
          ${
            tasks.length
              ? tasks
                  .map(taskButton)
                  .join("")
              : `
                <div
                  class="niche-readiness-empty"
                >
                  ${escapeHtml(emptyMessage)}
                </div>
              `
          }
        </div>
      </section>
    `;
  };

  const render = () => {
    const body =
      document.getElementById(
        "niche-readiness-body"
      );

    if (!body) {
      return;
    }

    if (!runtime.tasks.length) {
      body.innerHTML = `
        <div class="niche-readiness-empty">
          No task projection is currently
          available to this instrument.
        </div>

        <div class="niche-readiness-note">
          No readiness state has been
          reconstructed from absent data.
        </div>
      `;

      return;
    }

    body.innerHTML = `
      <div class="niche-readiness-summary">
        <span class="niche-readiness-chip">
          tasks:${runtime.tasks.length}
        </span>

        <span class="niche-readiness-chip">
          established:${
            runtime.regions.established.length
          }
        </span>

        <span class="niche-readiness-chip">
          ready:${
            runtime.regions.ready.length
          }
        </span>

        <span class="niche-readiness-chip">
          blocked:${
            runtime.regions.blocked.length
          }
        </span>

        <span class="niche-readiness-chip">
          future:${
            runtime.regions.future.length
          }
        </span>
      </div>

      <div class="niche-readiness-regions">
        ${region(
          "established",
          "ESTABLISHED",
          "No established task is represented."
        )}

        ${region(
          "ready",
          "READY NOW",
          "No explicitly ready task is represented."
        )}

        ${region(
          "blocked",
          "BLOCKED / CONDITIONAL",
          "No blocker or unsatisfied dependency is represented."
        )}

        ${region(
          "future",
          "DEPENDENT FUTURE / UNCLASSIFIED",
          "No remaining represented task exists."
        )}
      </div>

      <div class="niche-readiness-note">
        READY NOW requires explicit readiness.
        BLOCKED / CONDITIONAL requires a
        represented blocker, unsatisfied
        dependency, or blocked state.
        ESTABLISHED reflects represented
        active or terminal state. The final
        region is deliberately conservative:
        it contains represented tasks not
        classifiable by those explicit
        signals and does not assert that they
        are truly future, executable, or
        dependent.
      </div>
    `;
  };

  const refresh = async () => {
    const tasks =
      await fetchTasks();

    if (!tasks) {
      runtime.tasks = [];
      runtime.regions =
        partition([]);
      render();
      return false;
    }

    runtime.tasks = tasks;
    runtime.regions =
      partition(tasks);

    render();

    window.dispatchEvent(
      new CustomEvent(
        "niche:readiness-boundary-update",
        {
          detail: {
            schema: SCHEMA,
            taskCount: tasks.length,
            counts: {
              established:
                runtime.regions
                  .established.length,
              ready:
                runtime.regions
                  .ready.length,
              blocked:
                runtime.regions
                  .blocked.length,
              future:
                runtime.regions
                  .future.length
            },
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
        "niche-readiness-boundary"
      )
    ) {
      return;
    }

    const shell =
      document.createElement("aside");

    shell.id =
      "niche-readiness-boundary";

    shell.className =
      "niche-readiness-boundary";

    shell.hidden = true;

    shell.setAttribute(
      "aria-label",
      "Executable Frontier"
    );

    shell.innerHTML = `
      <header class="niche-readiness-head">
        <div>
          <p class="niche-readiness-kicker">
            readiness / executable frontier
          </p>

          <h2 class="niche-readiness-title">
            EXECUTABLE FRONTIER
          </h2>
        </div>

        <button
          type="button"
          class="niche-readiness-close"
          aria-label="Close Executable Frontier"
        >
          ×
        </button>
      </header>

      <div
        class="niche-readiness-body"
        id="niche-readiness-body"
      ></div>
    `;

    document.body.append(shell);

    shell
      .querySelector(
        ".niche-readiness-close"
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
            "[data-readiness-task]"
          );

        if (!button) {
          return;
        }

        const id =
          button.dataset.readinessTask;

        window
          .NicheCrossViewContinuity
          ?.select?.(id);

        const existing =
          [...document.querySelectorAll(
            "[data-task-id]"
          )].find(
            node =>
              node.dataset.taskId === id
          );

        if (existing) {
          existing.click();
        }
      }
    );
  };

  const open = async () => {
    ensureShell();

    const shell =
      document.getElementById(
        "niche-readiness-boundary"
      );

    if (!shell) {
      return;
    }

    runtime.previousFocus =
      document.activeElement;

    runtime.open = true;
    shell.hidden = false;

    await refresh();

    shell
      .querySelector(
        ".niche-readiness-close"
      )
      ?.focus();
  };

  const close = () => {
    runtime.open = false;
    runtime.controller?.abort();

    const shell =
      document.getElementById(
        "niche-readiness-boundary"
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
              "[data-action='readiness-boundary']",
              "[data-command='readiness-boundary']",
              "[data-readiness-boundary]"
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
      .nicheReadinessBoundary =
      "ready";

    window.dispatchEvent(
      new CustomEvent(
        "niche:readiness-boundary-ready",
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

  window.NicheReadinessBoundary =
    Object.freeze({
      open,
      close,
      refresh,

      state: () => ({
        schema: SCHEMA,
        open: runtime.open,
        taskCount: runtime.tasks.length,
        counts: {
          established:
            runtime.regions.established.length,
          ready:
            runtime.regions.ready.length,
          blocked:
            runtime.regions.blocked.length,
          future:
            runtime.regions.future.length
        },
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
