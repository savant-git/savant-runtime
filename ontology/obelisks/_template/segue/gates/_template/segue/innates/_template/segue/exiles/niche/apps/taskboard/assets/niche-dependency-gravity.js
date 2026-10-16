(() => {
  "use strict";

  const SCHEMA =
    "savant.niche.dependency-gravity.v1";

  const runtime = {
    initialized: false,
    open: false,
    taskId: null,
    task: null,
    generation: 0,
    controller: null,
    previousFocus: null
  };

  const array = value =>
    Array.isArray(value)
      ? value
      : [];

  const normalizeIds = values => {
    const ids = [];

    for (const value of values) {
      if (
        typeof value === "string" &&
        value.length > 0
      ) {
        ids.push(value);
        continue;
      }

      if (
        value &&
        typeof value === "object"
      ) {
        const id =
          value.task_id ||
          value.id ||
          value.taskId;

        if (
          typeof id === "string" &&
          id.length > 0
        ) {
          ids.push(id);
        }
      }
    }

    return [...new Set(ids)];
  };

  const valueText = (
    value,
    fallback = "unknown"
  ) => {
    if (
      value === null ||
      value === undefined ||
      value === ""
    ) {
      return fallback;
    }

    return String(value);
  };

  const escapeHtml = value =>
    valueText(value, "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");

  const currentTaskId = () => {
    const state =
      window.Niche?.state?.();

    return (
      runtime.taskId ||
      state?.selectedTaskId ||
      state?.recommendedTaskId ||
      null
    );
  };

  const fetchTask = async taskId => {
    if (!taskId) {
      return null;
    }

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
          `/api/tasks/${
            encodeURIComponent(taskId)
          }`,
          {
            signal: controller.signal,
            cache: "no-store",
            headers: {
              Accept: "application/json"
            }
          }
        );

      if (
        generation !==
          runtime.generation ||
        !response.ok
      ) {
        return null;
      }

      const payload =
        await response.json();

      if (
        generation !==
        runtime.generation
      ) {
        return null;
      }

      return payload?.task || payload;
    } catch (error) {
      if (
        error?.name === "AbortError"
      ) {
        return null;
      }

      return null;
    } finally {
      if (
        runtime.controller ===
        controller
      ) {
        runtime.controller = null;
      }
    }
  };

  const upstream = task =>
    normalizeIds([
      ...array(task?.dependencies),
      ...array(
        task?.unsatisfied_dependencies
      ),
      ...array(task?.blockers)
    ]);

  const downstream = task =>
    normalizeIds(
      array(task?.dependents)
    );

  const renderNodes = (
    ids,
    emptyMessage
  ) => {
    if (!ids.length) {
      return `
        <div class="niche-gravity-empty">
          ${escapeHtml(emptyMessage)}
        </div>
      `;
    }

    return `
      <div class="niche-gravity-stack">
        ${ids.map(
          id => `
            <button
              type="button"
              class="niche-gravity-node"
              data-gravity-task="${
                escapeHtml(id)
              }"
            >
              ${escapeHtml(id)}
            </button>
          `
        ).join("")}
      </div>
    `;
  };

  const render = task => {
    const body =
      document.getElementById(
        "niche-gravity-body"
      );

    if (!body) {
      return;
    }

    if (!task) {
      body.innerHTML = `
        <div class="niche-gravity-empty">
          Dependency topology is unavailable.
          No relationship has been inferred.
        </div>
      `;

      return;
    }

    const id =
      task.task_id ||
      task.id ||
      runtime.taskId ||
      "unknown";

    const parents =
      upstream(task);

    const children =
      downstream(task);

    body.innerHTML = `
      <div class="niche-gravity-summary">
        <span class="niche-gravity-chip">
          origin:${escapeHtml(id)}
        </span>

        <span class="niche-gravity-chip">
          upstream:${parents.length}
        </span>

        <span class="niche-gravity-chip">
          downstream:${children.length}
        </span>

        <span class="niche-gravity-chip">
          metric:topology-only
        </span>
      </div>

      <div class="niche-gravity-field">
        <section
          class="niche-gravity-band"
          data-band="upstream"
        >
          <span class="niche-gravity-label">
            represented upstream
          </span>

          ${renderNodes(
            parents,
            "No upstream relationship is represented."
          )}
        </section>

        <section
          class="niche-gravity-band"
          data-band="origin"
        >
          <span class="niche-gravity-label">
            focal task
          </span>

          <div class="niche-gravity-origin">
            <div class="niche-gravity-node">
              ${escapeHtml(id)}
            </div>
          </div>
        </section>

        <section
          class="niche-gravity-band"
          data-band="downstream"
        >
          <span class="niche-gravity-label">
            represented downstream
          </span>

          ${renderNodes(
            children,
            "No downstream relationship is represented."
          )}
        </section>
      </div>

      <div class="niche-gravity-boundary">
        Dependency Gravity is a deterministic
        topology projection. Position and
        visual weight represent relationship
        direction only. They do not establish
        priority, authority, urgency,
        readiness, effort, probability,
        scheduling order, or execution value.
      </div>
    `;
  };

  const ensureShell = () => {
    if (
      document.getElementById(
        "niche-dependency-gravity"
      )
    ) {
      return;
    }

    const shell =
      document.createElement("aside");

    shell.id =
      "niche-dependency-gravity";

    shell.className =
      "niche-dependency-gravity";

    shell.hidden = true;

    shell.setAttribute(
      "aria-label",
      "Dependency Gravity"
    );

    shell.innerHTML = `
      <header class="niche-gravity-head">
        <div>
          <p class="niche-gravity-kicker">
            causal topology / directional field
          </p>

          <h2 class="niche-gravity-title">
            DEPENDENCY GRAVITY
          </h2>
        </div>

        <button
          type="button"
          class="niche-gravity-close"
          aria-label="Close Dependency Gravity"
        >
          ×
        </button>
      </header>

      <div
        class="niche-gravity-body"
        id="niche-gravity-body"
      ></div>
    `;

    document.body.append(shell);

    shell
      .querySelector(
        ".niche-gravity-close"
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
            "[data-gravity-task]"
          );

        if (!button) {
          return;
        }

        const id =
          button.dataset.gravityTask;

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

        void open(id);
      }
    );
  };

  const refresh = async taskId => {
    const id =
      taskId ||
      currentTaskId();

    runtime.taskId = id;

    if (!id) {
      runtime.task = null;
      render(null);
      return;
    }

    const task =
      await fetchTask(id);

    runtime.task = task;
    render(task);
  };

  const open = async taskId => {
    ensureShell();

    const shell =
      document.getElementById(
        "niche-dependency-gravity"
      );

    if (!shell) {
      return;
    }

    runtime.previousFocus =
      document.activeElement;

    runtime.open = true;
    shell.hidden = false;

    await refresh(taskId);

    shell
      .querySelector(
        ".niche-gravity-close"
      )
      ?.focus();
  };

  const close = () => {
    runtime.open = false;
    runtime.controller?.abort();

    const shell =
      document.getElementById(
        "niche-dependency-gravity"
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
              "[data-action='dependency-gravity']",
              "[data-command='dependency-gravity']",
              "[data-dependency-gravity]"
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

  const bindKeyboard = () => {
    document.addEventListener(
      "keydown",
      event => {
        const target =
          event.target;

        const editing =
          target instanceof
            HTMLInputElement ||
          target instanceof
            HTMLTextAreaElement ||
          target?.isContentEditable;

        if (
          event.key === "Escape" &&
          runtime.open
        ) {
          event.preventDefault();
          close();
          return;
        }

        if (
          editing ||
          runtime.open
        ) {
          return;
        }

        if (
          event.altKey &&
          event.shiftKey &&
          event.key.toLowerCase() === "d"
        ) {
          event.preventDefault();
          void open();
        }
      }
    );
  };

  const bindRefresh = () => {
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
  };

  const initialize = () => {
    if (runtime.initialized) {
      return;
    }

    runtime.initialized = true;

    ensureShell();
    bindTriggers();
    bindKeyboard();
    bindRefresh();

    document.documentElement.dataset
      .nicheDependencyGravity =
      "ready";

    window.dispatchEvent(
      new CustomEvent(
        "niche:dependency-gravity-ready",
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

  window.NicheDependencyGravity =
    Object.freeze({
      open,
      close,
      refresh,

      state: () => ({
        schema: SCHEMA,
        open: runtime.open,
        taskId: runtime.taskId,
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
