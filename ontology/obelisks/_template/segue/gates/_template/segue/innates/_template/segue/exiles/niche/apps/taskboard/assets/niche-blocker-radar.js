(() => {
  "use strict";

  const SCHEMA =
    "savant.niche.blocker-radar.v1";

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
      value === null ||
      value === undefined ||
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
    const state =
      window.Niche?.state?.();

    return (
      runtime.taskId ||
      state?.selectedTaskId ||
      state?.recommendedTaskId ||
      null
    );
  };

  const blockers = task =>
    unique(
      array(task?.blockers)
    );

  const unsatisfied = task =>
    unique(
      array(
        task?.unsatisfied_dependencies
      )
    );

  const dependencies = task =>
    unique(
      array(task?.dependencies)
    );

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
            signal:
              controller.signal,
            cache: "no-store",
            headers: {
              Accept:
                "application/json"
            }
          }
        );

      if (
        generation !==
        runtime.generation
      ) {
        return null;
      }

      if (!response.ok) {
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
        error?.name ===
        "AbortError"
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

  const contactPosition = (
    index,
    total,
    radius
  ) => {
    const safeTotal =
      Math.max(total, 1);

    const angle =
      (
        Math.PI * 2 * index
      ) / safeTotal -
      Math.PI / 2;

    return {
      left:
        50 +
        Math.cos(angle) * radius,
      top:
        50 +
        Math.sin(angle) * radius
    };
  };

  const renderContacts = (
    blockerItems,
    dependencyItems
  ) => {
    const contacts = [];

    blockerItems.forEach(
      (id, index) => {
        const position =
          contactPosition(
            index,
            blockerItems.length,
            34
          );

        contacts.push(`
          <span
            class="niche-radar-contact"
            data-kind="blocker"
            title="${escapeHtml(id)}"
            style="
              left:${position.left}%;
              top:${position.top}%;
            "
          ></span>
        `);
      }
    );

    dependencyItems.forEach(
      (id, index) => {
        const position =
          contactPosition(
            index,
            dependencyItems.length,
            22
          );

        contacts.push(`
          <span
            class="niche-radar-contact"
            data-kind="dependency"
            title="${escapeHtml(id)}"
            style="
              left:${position.left}%;
              top:${position.top}%;
            "
          ></span>
        `);
      }
    );

    return contacts.join("");
  };

  const renderList = (
    items,
    kind,
    emptyText
  ) => {
    if (!items.length) {
      return `
        <div class="niche-radar-empty">
          ${escapeHtml(emptyText)}
        </div>
      `;
    }

    return `
      <ul class="niche-radar-list">
        ${items.map(
          id => `
            <li>
              <button
                type="button"
                class="niche-radar-task"
                data-kind="${kind}"
                data-radar-task="${
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

  const render = task => {
    const body =
      document.getElementById(
        "niche-radar-body"
      );

    if (!body) {
      return;
    }

    if (!task) {
      body.innerHTML = `
        <div class="niche-radar-empty">
          Blocker topology is unavailable.
          No blocker has been inferred.
        </div>
      `;

      return;
    }

    const id =
      task.task_id ||
      task.id ||
      runtime.taskId ||
      "unknown";

    const explicitBlockers =
      blockers(task);

    const unsatisfiedItems =
      unsatisfied(task);

    const representedDependencies =
      dependencies(task);

    const allBlockers =
      unique([
        ...explicitBlockers,
        ...unsatisfiedItems
      ]);

    const dependencyContext =
      representedDependencies.filter(
        dependency =>
          !allBlockers.includes(
            dependency
          )
      );

    body.innerHTML = `
      <div class="niche-radar-summary">
        <span class="niche-radar-chip">
          origin:${escapeHtml(id)}
        </span>

        <span class="niche-radar-chip">
          blockers:${allBlockers.length}
        </span>

        <span class="niche-radar-chip">
          dependency-context:${
            dependencyContext.length
          }
        </span>
      </div>

      <div
        class="niche-radar-field"
        aria-label="Represented blocker topology"
      >
        <span class="niche-radar-origin">
          ${escapeHtml(id)}
        </span>

        ${renderContacts(
          allBlockers,
          dependencyContext
        )}
      </div>

      <div class="niche-radar-sections">
        <section class="niche-radar-section">
          <span class="niche-radar-label">
            represented blockers
          </span>

          ${renderList(
            allBlockers,
            "blocker",
            "No blocker is represented in the resolved task payload."
          )}
        </section>

        <section class="niche-radar-section">
          <span class="niche-radar-label">
            other dependency context
          </span>

          ${renderList(
            dependencyContext,
            "dependency",
            "No additional dependency context is represented."
          )}
        </section>
      </div>

      <div class="niche-radar-boundary">
        Radar position is a deterministic
        visual arrangement only. Distance,
        angle, and ring position do not
        encode priority, severity, authority,
        duration, or probability.
      </div>
    `;
  };

  const ensureShell = () => {
    if (
      document.getElementById(
        "niche-blocker-radar"
      )
    ) {
      return;
    }

    const shell =
      document.createElement("aside");

    shell.id =
      "niche-blocker-radar";

    shell.className =
      "niche-blocker-radar";

    shell.hidden = true;

    shell.setAttribute(
      "aria-label",
      "Blocker radar"
    );

    shell.innerHTML = `
      <header class="niche-radar-head">
        <div>
          <p class="niche-radar-kicker">
            represented constraints
          </p>

          <h2 class="niche-radar-title">
            BLOCKER RADAR
          </h2>
        </div>

        <button
          type="button"
          class="niche-radar-close"
          aria-label="Close blocker radar"
        >
          ×
        </button>
      </header>

      <div
        class="niche-radar-body"
        id="niche-radar-body"
      ></div>
    `;

    document.body.append(shell);

    shell
      .querySelector(
        ".niche-radar-close"
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
            "[data-radar-task]"
          );

        if (!button) {
          return;
        }

        const id =
          button.dataset.radarTask;

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

        if (
          window.NicheCausalField?.open
        ) {
          window.NicheCausalField.open(
            id
          );
        }
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
        "niche-blocker-radar"
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
        ".niche-radar-close"
      )
      ?.focus();
  };

  const close = () => {
    const shell =
      document.getElementById(
        "niche-blocker-radar"
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
              "[data-action='blocker-radar']",
              "[data-command='blocker-radar']",
              "[data-blocker-radar]"
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
          event.key.toLowerCase() === "b"
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
      .nicheBlockerRadar =
      "ready";

    window.dispatchEvent(
      new CustomEvent(
        "niche:blocker-radar-ready",
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

  window.NicheBlockerRadar =
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
