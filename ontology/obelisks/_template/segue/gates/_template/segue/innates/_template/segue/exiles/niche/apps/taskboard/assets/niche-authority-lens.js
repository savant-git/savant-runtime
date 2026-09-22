(() => {
  "use strict";

  const SCHEMA =
    "savant.niche.authority-lens.v1";

  const runtime = {
    initialized: false,
    open: false,
    taskId: null,
    task: null,
    generation: 0,
    controller: null,
    previousFocus: null
  };

  const text = (
    value,
    fallback = "not projected"
  ) => {
    if (
      value === null ||
      value === undefined ||
      value === ""
    ) {
      return fallback;
    }

    if (
      typeof value === "object"
    ) {
      try {
        return JSON.stringify(value);
      } catch {
        return fallback;
      }
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

  const represented = value =>
    value !== null &&
    value !== undefined &&
    value !== "";

  const first = (
    object,
    keys
  ) => {
    for (const key of keys) {
      if (
        object &&
        Object.prototype
          .hasOwnProperty.call(
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

  const row = (
    label,
    value,
    state = null
  ) => {
    const actualState =
      state ||
      (
        represented(value)
          ? "represented"
          : "unknown"
      );

    return `
      <div
        class="niche-authority-row"
        data-state="${
          escapeHtml(actualState)
        }"
      >
        <span class="niche-authority-label">
          ${escapeHtml(label)}
        </span>

        <span class="niche-authority-value">
          ${escapeHtml(value)}
        </span>
      </div>
    `;
  };

  const render = task => {
    const body =
      document.getElementById(
        "niche-authority-body"
      );

    if (!body) {
      return;
    }

    if (!task) {
      body.innerHTML = `
        <div class="niche-authority-boundary">
          Authority data is unavailable for
          the current selection. The interface
          will not infer authority from paths,
          visual prominence, task state, or
          dependency position.
        </div>
      `;

      return;
    }

    const id =
      first(
        task,
        ["task_id", "id"]
      ) ||
      runtime.taskId ||
      "unknown";

    const owner =
      first(
        task,
        [
          "authority_owner",
          "task_owner",
          "owner"
        ]
      );

    const effect =
      first(
        task,
        [
          "authority_effect"
        ]
      );

    const classification =
      first(
        task,
        [
          "authority_classification",
          "authority_class"
        ]
      );

    const basis =
      first(
        task,
        [
          "authority_basis",
          "source_basis",
          "basis"
        ]
      );

    const provenance =
      first(
        task,
        [
          "provenance",
          "source_ref",
          "source_path",
          "source",
          "origin"
        ]
      );

    const lineage =
      first(
        task,
        [
          "lineage",
          "ancestry",
          "parent_task_id",
          "parent_id"
        ]
      );

    const supersedes =
      first(
        task,
        [
          "supersedes"
        ]
      );

    const supersededBy =
      first(
        task,
        [
          "superseded_by"
        ]
      );

    body.innerHTML = `
      <div class="niche-authority-summary">
        <span class="niche-authority-chip">
          task:${escapeHtml(id)}
        </span>

        <span class="niche-authority-chip">
          lens:projection-only
        </span>

        <span class="niche-authority-chip">
          inference:none
        </span>
      </div>

      <div class="niche-authority-grid">
        ${row(
          "task identity",
          id
        )}

        ${row(
          "authority owner",
          owner
        )}

        ${row(
          "authority effect",
          effect
        )}

        ${row(
          "authority classification",
          classification
        )}

        ${row(
          "authority basis",
          basis
        )}

        ${row(
          "provenance",
          provenance
        )}

        ${row(
          "lineage / ancestry",
          lineage
        )}

        ${row(
          "supersedes",
          supersedes
        )}

        ${row(
          "superseded by",
          supersededBy
        )}

        ${row(
          "interface authority",
          "none",
          "projection"
        )}

        ${row(
          "filesystem authority",
          "not inferred",
          "projection"
        )}
      </div>

      <div class="niche-authority-boundary">
        Missing values remain explicitly
        “not projected.” Niche does not
        convert absence into a negative fact,
        and this lens does not promote
        projections, filesystem placement,
        dependency structure, or interface
        prominence into authority.
      </div>
    `;
  };

  const ensureShell = () => {
    if (
      document.getElementById(
        "niche-authority-lens"
      )
    ) {
      return;
    }

    const shell =
      document.createElement("aside");

    shell.id =
      "niche-authority-lens";

    shell.className =
      "niche-authority-lens";

    shell.hidden = true;

    shell.setAttribute(
      "aria-label",
      "Authority lens"
    );

    shell.innerHTML = `
      <header class="niche-authority-head">
        <div>
          <p class="niche-authority-kicker">
            authority / provenance / lineage
          </p>

          <h2 class="niche-authority-title">
            AUTHORITY LENS
          </h2>
        </div>

        <button
          type="button"
          class="niche-authority-close"
          aria-label="Close authority lens"
        >
          ×
        </button>
      </header>

      <div
        class="niche-authority-body"
        id="niche-authority-body"
      ></div>
    `;

    document.body.append(shell);

    shell
      .querySelector(
        ".niche-authority-close"
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

  const open = async taskId => {
    ensureShell();

    const shell =
      document.getElementById(
        "niche-authority-lens"
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
        ".niche-authority-close"
      )
      ?.focus();
  };

  const close = () => {
    runtime.open = false;

    runtime.controller?.abort();

    const shell =
      document.getElementById(
        "niche-authority-lens"
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
              "[data-action='authority-lens']",
              "[data-command='authority-lens']",
              "[data-authority-lens]"
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
          event.key.toLowerCase() === "a"
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
      .nicheAuthorityLens =
      "ready";

    window.dispatchEvent(
      new CustomEvent(
        "niche:authority-lens-ready",
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

  window.NicheAuthorityLens =
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
