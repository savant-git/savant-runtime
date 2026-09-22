(() => {
  "use strict";

  const SCHEMA =
    "savant.niche.temporal-ghost.v1";

  const runtime = {
    initialized: false,
    open: false,
    taskId: null,
    task: null,
    history: [],
    generation: 0,
    controller: null,
    previousFocus: null
  };

  const FIELDS = [
    ["state", ["state", "status"]],
    ["priority", ["priority"]],
    ["readiness", ["readiness", "ready"]],
    ["objective", ["objective", "objective_id"]],
    ["parent", ["parent_task_id", "parent_id"]],
    ["completion", ["completion_condition"]],
    ["evidence", ["evidence_requirement"]],
    ["updated", ["updated_at", "modified_at"]]
  ];

  const represented = value =>
    value !== null &&
    value !== undefined &&
    value !== "";

  const valueText = (
    value,
    fallback = "not projected"
  ) => {
    if (!represented(value)) {
      return fallback;
    }

    if (typeof value === "object") {
      try {
        return JSON.stringify(value);
      } catch {
        return fallback;
      }
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

  const normalizeHistory = payload => {
    const candidate =
      Array.isArray(payload)
        ? payload
        : Array.isArray(payload?.history)
          ? payload.history
          : Array.isArray(payload?.events)
            ? payload.events
            : Array.isArray(payload?.items)
              ? payload.items
              : [];

    return candidate;
  };

  const eventTaskId = event =>
    first(
      event,
      [
        "task_id",
        "taskId",
        "entity_id",
        "subject_id"
      ]
    );

  const eventTime = event =>
    first(
      event,
      [
        "created_at",
        "timestamp",
        "occurred_at",
        "at",
        "time"
      ]
    );

  const eventLabel = event =>
    first(
      event,
      [
        "transition",
        "action",
        "event",
        "type",
        "state"
      ]
    ) ||
    "history event";

  const eventSnapshot = event =>
    first(
      event,
      [
        "task",
        "snapshot",
        "after",
        "state_after",
        "payload"
      ]
    );

  const fetchPair = async taskId => {
    runtime.generation += 1;

    const generation =
      runtime.generation;

    runtime.controller?.abort();

    const controller =
      new AbortController();

    runtime.controller =
      controller;

    const request = async url => {
      try {
        const response =
          await fetch(
            url,
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

        if (!response.ok) {
          return null;
        }

        return await response.json();
      } catch (error) {
        if (
          error?.name ===
          "AbortError"
        ) {
          return null;
        }

        return null;
      }
    };

    const [
      taskPayload,
      historyPayload
    ] = await Promise.all([
      request(
        `/api/tasks/${
          encodeURIComponent(taskId)
        }`
      ),
      request("/api/history")
    ]);

    if (
      generation !==
      runtime.generation
    ) {
      return null;
    }

    const task =
      taskPayload?.task ||
      taskPayload;

    const history =
      normalizeHistory(
        historyPayload
      ).filter(event => {
        const id =
          eventTaskId(event);

        return (
          id === null ||
          id === taskId
        );
      });

    return {
      task,
      history
    };
  };

  const historicalSnapshot = (
    history,
    taskId
  ) => {
    for (
      let index =
        history.length - 1;
      index >= 0;
      index -= 1
    ) {
      const event =
        history[index];

      const id =
        eventTaskId(event);

      if (
        id !== null &&
        id !== taskId
      ) {
        continue;
      }

      const snapshot =
        eventSnapshot(event);

      if (
        snapshot &&
        typeof snapshot ===
          "object" &&
        !Array.isArray(snapshot)
      ) {
        return snapshot;
      }
    }

    return null;
  };

  const comparable = value => {
    if (!represented(value)) {
      return null;
    }

    if (typeof value === "object") {
      try {
        return JSON.stringify(
          value,
          Object.keys(value).sort()
        );
      } catch {
        return valueText(value);
      }
    }

    return String(value);
  };

  const fieldRows = (
    task,
    other
  ) =>
    FIELDS.map(
      ([label, keys]) => {
        const value =
          first(task, keys);

        const otherValue =
          first(other, keys);

        const changed =
          other &&
          comparable(value) !==
            comparable(otherValue);

        return `
          <div
            class="niche-ghost-field"
            data-changed="${
              changed
                ? "true"
                : "false"
            }"
          >
            <span class="niche-ghost-label">
              ${escapeHtml(label)}
            </span>

            <span class="niche-ghost-value">
              ${escapeHtml(value)}
            </span>
          </div>
        `;
      }
    ).join("");

  const renderHistory = history => {
    if (!history.length) {
      return `
        <div class="niche-ghost-empty">
          No task-specific history is
          represented by the current
          history response.
        </div>
      `;
    }

    return `
      <section class="niche-ghost-history">
        <div class="niche-ghost-history-head">
          represented history
        </div>

        <ol class="niche-ghost-history-list">
          ${history
            .slice(-20)
            .reverse()
            .map(event => `
              <li class="niche-ghost-history-item">
                <span class="niche-ghost-history-time">
                  ${escapeHtml(
                    eventTime(event)
                  )}
                </span>

                <span>
                  ${escapeHtml(
                    eventLabel(event)
                  )}
                </span>
              </li>
            `)
            .join("")}
        </ol>
      </section>
    `;
  };

  const render = (
    task,
    history
  ) => {
    const body =
      document.getElementById(
        "niche-ghost-body"
      );

    if (!body) {
      return;
    }

    if (!task) {
      body.innerHTML = `
        <div class="niche-ghost-empty">
          Current task data is unavailable.
          Temporal Ghost cannot construct a
          comparison and will not fabricate
          historical state.
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

    const past =
      historicalSnapshot(
        history,
        id
      );

    body.innerHTML = `
      <div class="niche-ghost-summary">
        <span class="niche-ghost-chip">
          task:${escapeHtml(id)}
        </span>

        <span class="niche-ghost-chip">
          mode:read-only
        </span>

        <span class="niche-ghost-chip">
          history:${history.length}
        </span>

        <span class="niche-ghost-chip">
          snapshot:${
            past
              ? "represented"
              : "unavailable"
          }
        </span>
      </div>

      <div class="niche-ghost-comparison">
        <section
          class="niche-ghost-column"
          data-temporal="past"
        >
          <div class="niche-ghost-column-head">
            historical represented state
          </div>

          ${
            past
              ? `
                <div class="niche-ghost-fields">
                  ${fieldRows(
                    past,
                    task
                  )}
                </div>
              `
              : `
                <div class="niche-ghost-empty">
                  History does not expose a
                  task snapshot suitable for
                  deterministic reconstruction.
                </div>
              `
          }
        </section>

        <section
          class="niche-ghost-column"
          data-temporal="present"
        >
          <div class="niche-ghost-column-head">
            current represented state
          </div>

          <div class="niche-ghost-fields">
            ${fieldRows(
              task,
              past
            )}
          </div>
        </section>
      </div>

      ${renderHistory(history)}

      <div class="niche-ghost-boundary">
        Temporal Ghost is read-only. It
        displays history and historical
        snapshots only when the backend
        represents them. Missing snapshots
        remain unavailable rather than being
        reconstructed from assumptions.
      </div>
    `;
  };

  const ensureShell = () => {
    if (
      document.getElementById(
        "niche-temporal-ghost"
      )
    ) {
      return;
    }

    const shell =
      document.createElement("section");

    shell.id =
      "niche-temporal-ghost";

    shell.className =
      "niche-temporal-ghost";

    shell.hidden = true;

    shell.setAttribute(
      "role",
      "dialog"
    );

    shell.setAttribute(
      "aria-modal",
      "true"
    );

    shell.setAttribute(
      "aria-label",
      "Temporal Ghost"
    );

    shell.innerHTML = `
      <header class="niche-ghost-head">
        <div>
          <p class="niche-ghost-kicker">
            immutable history / comparison
          </p>

          <h2 class="niche-ghost-title">
            TEMPORAL GHOST
          </h2>
        </div>

        <button
          type="button"
          class="niche-ghost-close"
          aria-label="Close Temporal Ghost"
        >
          ×
        </button>
      </header>

      <div
        class="niche-ghost-body"
        id="niche-ghost-body"
      ></div>
    `;

    document.body.append(shell);

    shell
      .querySelector(
        ".niche-ghost-close"
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
      runtime.history = [];
      render(null, []);
      return;
    }

    const pair =
      await fetchPair(id);

    if (!pair) {
      render(null, []);
      return;
    }

    runtime.task =
      pair.task;

    runtime.history =
      pair.history;

    render(
      runtime.task,
      runtime.history
    );
  };

  const open = async taskId => {
    ensureShell();

    const shell =
      document.getElementById(
        "niche-temporal-ghost"
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
        ".niche-ghost-close"
      )
      ?.focus();
  };

  const close = () => {
    runtime.open = false;
    runtime.controller?.abort();

    const shell =
      document.getElementById(
        "niche-temporal-ghost"
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
              "[data-action='temporal-ghost']",
              "[data-command='temporal-ghost']",
              "[data-temporal-ghost]"
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
            "g"
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
      .nicheTemporalGhost =
      "ready";

    window.dispatchEvent(
      new CustomEvent(
        "niche:temporal-ghost-ready",
        {
          detail: {
            schema: SCHEMA,
            readOnly: true,
            authorityEffect: "none",
            projectionOnly: true
          }
        }
      )
    );
  };

  window.NicheTemporalGhost =
    Object.freeze({
      open,
      close,
      refresh,

      state: () => ({
        schema: SCHEMA,
        open: runtime.open,
        taskId: runtime.taskId,
        historyCount:
          runtime.history.length,
        readOnly: true,
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
