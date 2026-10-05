(() => {
  "use strict";

  const SCHEMA =
    "savant.niche.consequence-preview.v1";

  const runtime = {
    initialized: false,
    open: false,
    taskId: null,
    task: null,
    controller: null,
    trigger: null
  };

  const list = value =>
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
    const niche =
      window.Niche?.state?.();

    return (
      runtime.taskId ||
      niche?.selectedTaskId ||
      niche?.recommendedTaskId ||
      null
    );
  };

  const fetchTask = async taskId => {
    if (!taskId) {
      return null;
    }

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

  const immediate = task => {
    const effects = [];

    if (task?.ready === true) {
      effects.push(
        "The represented task is currently ready."
      );
    }

    if (
      list(
        task?.unsatisfied_dependencies
      ).length > 0
    ) {
      effects.push(
        "The represented task has unsatisfied dependencies."
      );
    }

    if (
      list(task?.blockers).length > 0
    ) {
      effects.push(
        "The represented task has blockers."
      );
    }

    return effects;
  };

  const connected = task =>
    unique(
      list(task?.dependents)
    );

  const renderList = (
    items,
    kind,
    emptyText
  ) => {
    if (!items.length) {
      return `
        <div class="niche-consequence-empty">
          ${escapeHtml(emptyText)}
        </div>
      `;
    }

    return `
      <ul class="niche-consequence-list">
        ${items.map(
          item => `
            <li
              class="niche-consequence-item"
              data-kind="${kind}"
            >
              ${escapeHtml(item)}
            </li>
          `
        ).join("")}
      </ul>
    `;
  };

  const render = task => {
    const body =
      document.getElementById(
        "niche-consequence-body"
      );

    if (!body) {
      return;
    }

    if (!task) {
      body.innerHTML = `
        <div class="niche-consequence-empty">
          Consequence data is unavailable.
          No consequence has been inferred.
        </div>
      `;

      return;
    }

    const certain =
      immediate(task);

    const downstream =
      connected(task);

    const id =
      task.task_id ||
      task.id ||
      "unknown";

    body.innerHTML = `
      <div class="niche-consequence-summary">
        <span class="niche-consequence-chip">
          task:${escapeHtml(id)}
        </span>

        <span class="niche-consequence-chip">
          certain:${certain.length}
        </span>

        <span class="niche-consequence-chip">
          connected:${downstream.length}
        </span>

        <span class="niche-consequence-chip">
          unknown:explicit
        </span>
      </div>

      <section class="niche-consequence-section">
        <h3>certain immediate</h3>

        ${renderList(
          certain,
          "certain",
          "No immediate consequence is explicitly established by the resolved task payload."
        )}
      </section>

      <section class="niche-consequence-section">
        <h3>connected downstream</h3>

        ${renderList(
          downstream,
          "connected",
          "No direct downstream dependent is represented by the resolved task payload."
        )}
      </section>

      <section class="niche-consequence-section">
        <h3>unknown</h3>

        ${renderList(
          [
            "Effects not represented by the current task payload remain unknown.",
            "This preview does not convert topology into authority or priority.",
            "Actual mutation consequences remain governed by the authoritative Niche transition path."
          ],
          "unknown",
          "Unknown consequence boundary unavailable."
        )}
      </section>
    `;
  };

  const ensureShell = () => {
    if (
      document.getElementById(
        "niche-consequence-preview"
      )
    ) {
      return;
    }

    const shell =
      document.createElement("aside");

    shell.id =
      "niche-consequence-preview";

    shell.className =
      "niche-consequence-preview";

    shell.hidden = true;

    shell.setAttribute(
      "aria-label",
      "Consequence preview"
    );

    shell.innerHTML = `
      <header class="niche-consequence-head">
        <div>
          <p class="niche-consequence-kicker">
            deterministic boundary
          </p>

          <h2 class="niche-consequence-title">
            CONSEQUENCE PREVIEW
          </h2>
        </div>

        <button
          type="button"
          class="niche-consequence-close"
          aria-label="Close consequence preview"
        >
          ×
        </button>
      </header>

      <div
        class="niche-consequence-body"
        id="niche-consequence-body"
      ></div>
    `;

    document.body.append(shell);

    shell
      .querySelector(
        ".niche-consequence-close"
      )
      ?.addEventListener(
        "click",
        close
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

  const open = async (
    taskId,
    trigger = null
  ) => {
    ensureShell();

    const shell =
      document.getElementById(
        "niche-consequence-preview"
      );

    if (!shell) {
      return;
    }

    runtime.open = true;
    runtime.trigger = trigger;

    shell.hidden = false;

    await refresh(taskId);

    shell
      .querySelector(
        ".niche-consequence-close"
      )
      ?.focus();
  };

  const close = () => {
    const shell =
      document.getElementById(
        "niche-consequence-preview"
      );

    runtime.open = false;

    if (shell) {
      shell.hidden = true;
    }

    if (
      runtime.trigger &&
      document.contains(
        runtime.trigger
      )
    ) {
      runtime.trigger.focus();
    }

    runtime.trigger = null;
  };

  const bindExistingPreviewControls = () => {
    document.addEventListener(
      "click",
      event => {
        const trigger =
          event.target.closest(
            [
              "[data-action='consequence-preview']",
              "[data-command='consequence-preview']",
              "[data-consequence-preview]"
            ].join(",")
          );

        if (!trigger) {
          return;
        }

        const taskNode =
          trigger.closest(
            "[data-task-id]"
          );

        const id =
          taskNode?.dataset?.taskId ||
          currentTaskId();

        void open(
          id,
          trigger
        );
      },
      true
    );
  };

  const bindKeyboard = () => {
    document.addEventListener(
      "keydown",
      event => {
        if (
          event.key === "Escape" &&
          runtime.open
        ) {
          event.preventDefault();
          close();
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
    bindExistingPreviewControls();
    bindKeyboard();

    document.documentElement.dataset
      .nicheConsequencePreview =
      "ready";

    window.dispatchEvent(
      new CustomEvent(
        "niche:consequence-preview-ready",
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

  window.NicheConsequencePreview =
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
      {
        once: true
      }
    );
  } else {
    initialize();
  }
})();
