(() => {
  "use strict";

  const SCHEMA =
    "savant.niche.unlock-horizon.v1";

  const runtime = {
    initialized: false,
    open: false,
    taskId: null,
    task: null,
    generation: 0,
    controller: null,
    taskCache: new Map(),
    previousFocus: null
  };

  const array = value =>
    Array.isArray(value)
      ? value
      : [];

  const unique = values =>
    [...new Set(
      values.filter(
        value =>
          typeof value === "string" &&
          value.length > 0
      )
    )];

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

  const escapeHtml = value =>
    text(value, "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");

  const currentTaskId = () => {
    const niche =
      window.Niche?.state?.();

    return (
      runtime.taskId ||
      niche?.selectedTaskId ||
      niche?.recommendedTaskId ||
      null
    );
  };

  const dependents = task =>
    unique(
      array(task?.dependents)
    );

  const requestTask = async (
    taskId,
    signal
  ) => {
    if (!taskId) {
      return null;
    }

    if (
      runtime.taskCache.has(taskId)
    ) {
      return runtime.taskCache.get(
        taskId
      );
    }

    try {
      const response =
        await fetch(
          `/api/tasks/${
            encodeURIComponent(taskId)
          }`,
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
        return null;
      }

      const payload =
        await response.json();

      const task =
        payload?.task ||
        payload;

      if (task) {
        runtime.taskCache.set(
          taskId,
          task
        );
      }

      return task;
    } catch (error) {
      if (
        error?.name === "AbortError"
      ) {
        return null;
      }

      return null;
    }
  };

  const resolveHorizon = async taskId => {
    runtime.generation += 1;

    const generation =
      runtime.generation;

    runtime.controller?.abort();

    const controller =
      new AbortController();

    runtime.controller =
      controller;

    const root =
      await requestTask(
        taskId,
        controller.signal
      );

    if (
      generation !==
      runtime.generation ||
      !root
    ) {
      return null;
    }

    const direct =
      dependents(root);

    const secondSet =
      new Set();

    for (const id of direct) {
      const child =
        await requestTask(
          id,
          controller.signal
        );

      if (
        generation !==
        runtime.generation
      ) {
        return null;
      }

      dependents(child)
        .forEach(candidate => {
          if (
            candidate !== taskId &&
            !direct.includes(candidate)
          ) {
            secondSet.add(candidate);
          }
        });
    }

    const second =
      [...secondSet];

    const transitiveSet =
      new Set();

    for (const id of second) {
      const child =
        await requestTask(
          id,
          controller.signal
        );

      if (
        generation !==
        runtime.generation
      ) {
        return null;
      }

      dependents(child)
        .forEach(candidate => {
          if (
            candidate !== taskId &&
            !direct.includes(candidate) &&
            !second.includes(candidate)
          ) {
            transitiveSet.add(
              candidate
            );
          }
        });
    }

    return {
      root,
      direct,
      second,
      transitive:
        [...transitiveSet]
    };
  };

  const renderList = (
    items,
    emptyText
  ) => {
    if (!items.length) {
      return `
        <div class="niche-horizon-empty">
          ${escapeHtml(emptyText)}
        </div>
      `;
    }

    return `
      <ul class="niche-horizon-list">
        ${items.map(
          id => `
            <li>
              <button
                type="button"
                class="niche-horizon-task"
                data-horizon-task="${
                  escapeHtml(id)
                }"
              >
                ${escapeHtml(id)}
              </button>
            </li>
          `
        ).join("")}
      </ul>
    `;
  };

  const render = horizon => {
    const body =
      document.getElementById(
        "niche-horizon-body"
      );

    if (!body) {
      return;
    }

    if (!horizon) {
      body.innerHTML = `
        <div class="niche-horizon-empty">
          Unlock topology is unavailable.
          No downstream relationship has
          been inferred beyond represented
          task dependents.
        </div>
      `;

      return;
    }

    const id =
      horizon.root?.task_id ||
      horizon.root?.id ||
      runtime.taskId ||
      "unknown";

    body.innerHTML = `
      <div class="niche-horizon-summary">
        <span class="niche-horizon-chip">
          origin:${escapeHtml(id)}
        </span>

        <span class="niche-horizon-chip">
          direct:${horizon.direct.length}
        </span>

        <span class="niche-horizon-chip">
          second:${horizon.second.length}
        </span>

        <span class="niche-horizon-chip">
          transitive-visible:${
            horizon.transitive.length
          }
        </span>
      </div>

      <div class="niche-horizon-track">
        <section
          class="niche-horizon-band"
          data-tier="direct"
        >
          <div class="niche-horizon-tier">
            <span>direct</span>
            <span>one represented edge</span>
          </div>

          ${renderList(
            horizon.direct,
            "No direct dependent is represented."
          )}
        </section>

        <section
          class="niche-horizon-band"
          data-tier="second"
        >
          <div class="niche-horizon-tier">
            <span>second order</span>
            <span>two represented edges</span>
          </div>

          ${renderList(
            horizon.second,
            "No second-order dependent was resolved from represented dependents."
          )}
        </section>

        <section
          class="niche-horizon-band"
          data-tier="transitive"
        >
          <div class="niche-horizon-tier">
            <span>transitive</span>
            <span>three represented edges</span>
          </div>

          ${renderList(
            horizon.transitive,
            "No third-order dependent was resolved."
          )}
        </section>
      </div>

      <div class="niche-horizon-boundary">
        Horizon depth is deliberately bounded
        to three represented dependent edges.
        This is a deterministic topology
        projection, not a priority score,
        authority claim, or guarantee that
        completing the origin alone makes
        downstream tasks executable.
      </div>
    `;
  };

  const ensureShell = () => {
    if (
      document.getElementById(
        "niche-unlock-horizon"
      )
    ) {
      return;
    }

    const shell =
      document.createElement("aside");

    shell.id =
      "niche-unlock-horizon";

    shell.className =
      "niche-unlock-horizon";

    shell.hidden = true;

    shell.setAttribute(
      "aria-label",
      "Unlock horizon"
    );

    shell.innerHTML = `
      <header class="niche-horizon-head">
        <div>
          <p class="niche-horizon-kicker">
            downstream topology
          </p>

          <h2 class="niche-horizon-title">
            UNLOCK HORIZON
          </h2>
        </div>

        <button
          type="button"
          class="niche-horizon-close"
          aria-label="Close unlock horizon"
        >
          ×
        </button>
      </header>

      <div
        class="niche-horizon-body"
        id="niche-horizon-body"
      ></div>
    `;

    document.body.append(shell);

    shell
      .querySelector(
        ".niche-horizon-close"
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
            "[data-horizon-task]"
          );

        if (!button) {
          return;
        }

        const id =
          button.dataset
            .horizonTask;

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

    const horizon =
      await resolveHorizon(id);

    if (!horizon) {
      render(null);
      return;
    }

    runtime.task =
      horizon.root;

    render(horizon);
  };

  const open = async taskId => {
    ensureShell();

    const shell =
      document.getElementById(
        "niche-unlock-horizon"
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
        ".niche-horizon-close"
      )
      ?.focus();
  };

  const close = () => {
    const shell =
      document.getElementById(
        "niche-unlock-horizon"
      );

    runtime.open = false;

    runtime.controller?.abort();

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
              "[data-action='unlock-horizon']",
              "[data-command='unlock-horizon']",
              "[data-unlock-horizon]"
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
          event.key.toLowerCase() ===
            "u"
        ) {
          event.preventDefault();
          void open();
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

    document.documentElement.dataset
      .nicheUnlockHorizon =
      "ready";

    window.dispatchEvent(
      new CustomEvent(
        "niche:unlock-horizon-ready",
        {
          detail: {
            schema: SCHEMA,
            authorityEffect: "none",
            projectionOnly: true,
            maximumDepth: 3
          }
        }
      )
    );
  };

  window.NicheUnlockHorizon =
    Object.freeze({
      open,
      close,
      refresh,

      state: () => ({
        schema: SCHEMA,
        open: runtime.open,
        taskId: runtime.taskId,
        cachedTasks:
          runtime.taskCache.size,
        maximumDepth: 3,
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
