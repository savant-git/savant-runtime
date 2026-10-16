(() => {
  "use strict";

  const SCHEMA =
    "savant.niche.execution-tunnel.v1";

  const STORAGE_KEY =
    "savant.niche.interface.execution-tunnel";

  const runtime = {
    initialized: false,
    open: false,
    taskId: null,
    task: null,
    controller: null,
    previousFocus: null
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

  const value = (
    input,
    fallback = "unknown"
  ) => {
    if (
      input === undefined ||
      input === null ||
      input === ""
    ) {
      return fallback;
    }

    return String(input);
  };

  const escapeHtml = input =>
    value(input, "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");

  const safeStorageSet = (
    key,
    storedValue
  ) => {
    try {
      window.localStorage.setItem(
        key,
        storedValue
      );
    } catch {
      return;
    }
  };

  const currentTaskId = () => {
    const nicheState =
      window.Niche?.state?.();

    return (
      nicheState?.selectedTaskId ||
      nicheState?.recommendedTaskId ||
      runtime.taskId ||
      null
    );
  };

  const dependencies = task =>
    unique([
      ...list(task?.dependencies),
      ...list(
        task?.unsatisfied_dependencies
      )
    ]);

  const blockers = task =>
    unique([
      ...list(task?.blockers),
      ...list(
        task?.unsatisfied_dependencies
      )
    ]);

  const dependents = task =>
    unique(
      list(task?.dependents)
    );

  const receipts = task =>
    list(task?.receipts);

  const completion = task =>
    task?.completion_condition ??
    task?.completion ??
    task?.acceptance ??
    task?.done_when ??
    null;

  const purpose = task =>
    task?.purpose ??
    task?.description ??
    null;

  const taskState = task => {
    if (!task) {
      return "unknown";
    }

    if (task.ready === true) {
      return "ready";
    }

    if (
      blockers(task).length > 0
    ) {
      return "blocked";
    }

    return value(
      task.status,
      "unknown"
    ).toLowerCase();
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

      return (
        payload?.task ||
        payload
      );
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

  const renderList = (
    items,
    emptyText
  ) => {
    if (!items.length) {
      return `
        <div class="niche-tunnel-empty">
          ${escapeHtml(emptyText)}
        </div>
      `;
    }

    return `
      <ul class="niche-tunnel-list">
        ${items.map(
          item => `
            <li>
              ${escapeHtml(item)}
            </li>
          `
        ).join("")}
      </ul>
    `;
  };

  const findExistingAction = names => {
    for (const selector of names) {
      const node =
        document.querySelector(
          selector
        );

      if (node) {
        return node;
      }
    }

    return null;
  };

  const invokeExistingAction =
    selectors => {
      const node =
        findExistingAction(
          selectors
        );

      if (!node) {
        return false;
      }

      node.click();
      return true;
    };

  const primaryAction = task => {
    const status =
      value(
        task?.status,
        ""
      ).toLowerCase();

    if (
      [
        "active",
        "in_progress",
        "in-progress",
        "started"
      ].includes(status)
    ) {
      return {
        label: "continue",
        kind: "continue"
      };
    }

    if (task?.ready === true) {
      return {
        label: "start next",
        kind: "start"
      };
    }

    return {
      label: "return to board",
      kind: "return"
    };
  };

  const render = task => {
    const body =
      document.getElementById(
        "niche-execution-tunnel-body"
      );

    const title =
      document.getElementById(
        "niche-execution-tunnel-title"
      );

    if (!body || !title) {
      return;
    }

    if (!task) {
      title.textContent =
        "EXECUTION TUNNEL";

      body.innerHTML = `
        <div class="niche-tunnel-empty">
          No current task payload is available.
          No task state has been inferred.
        </div>
      `;

      return;
    }

    const id =
      task.task_id ||
      task.id ||
      "unknown";

    const action =
      primaryAction(task);

    const directDependencies =
      dependencies(task);

    const directBlockers =
      blockers(task);

    const directDependents =
      dependents(task);

    const taskReceipts =
      receipts(task);

    title.textContent =
      task.title ||
      id;

    body.innerHTML = `
      <div class="niche-tunnel-grid">
        <main class="niche-tunnel-primary">
          <article
            class="niche-tunnel-task"
            data-state="${
              escapeHtml(
                taskState(task)
              )
            }"
          >
            <span class="niche-tunnel-label">
              current executable context
            </span>

            <p class="niche-tunnel-task-id">
              ${escapeHtml(id)}
            </p>

            <h2 class="niche-tunnel-task-title">
              ${escapeHtml(
                task.title ||
                "Untitled task"
              )}
            </h2>

            <p class="niche-tunnel-purpose">
              ${escapeHtml(
                purpose(task) ||
                "Purpose is not projected in the resolved task payload."
              )}
            </p>

            <div class="niche-tunnel-status">
              <span class="niche-tunnel-badge">
                state:${
                  escapeHtml(
                    taskState(task)
                  )
                }
              </span>

              <span class="niche-tunnel-badge">
                priority:${
                  escapeHtml(
                    task.priority ??
                    "unknown"
                  )
                }
              </span>

              <span class="niche-tunnel-badge">
                readiness:${
                  task.ready === true
                    ? "ready"
                    : task.ready === false
                      ? "not-ready"
                      : "unknown"
                }
              </span>

              <span class="niche-tunnel-badge">
                evidence:${
                  taskReceipts.length
                }
              </span>
            </div>
          </article>

          <section class="niche-tunnel-panel">
            <h3>completion condition</h3>
            <p>
              ${escapeHtml(
                completion(task) ||
                "Completion condition is not projected in the resolved task payload."
              )}
            </p>
          </section>

          <section class="niche-tunnel-panel">
            <h3>required context / dependencies</h3>
            ${renderList(
              directDependencies,
              "No dependency is represented in the resolved task payload."
            )}
          </section>

          <div class="niche-tunnel-controls">
            <button
              type="button"
              class="niche-tunnel-context-action"
              data-tunnel-action="${
                action.kind
              }"
              data-primary="true"
            >
              ${action.label}
            </button>

            <button
              type="button"
              class="niche-tunnel-context-action"
              data-tunnel-action="evidence"
            >
              show evidence
            </button>

            <button
              type="button"
              class="niche-tunnel-context-action"
              data-tunnel-action="why"
            >
              show why
            </button>

            <button
              type="button"
              class="niche-tunnel-context-action"
              data-tunnel-action="board"
            >
              return to board
            </button>
          </div>
        </main>

        <aside class="niche-tunnel-secondary">
          <section class="niche-tunnel-panel">
            <h3>blockers</h3>
            ${renderList(
              directBlockers,
              "No blocker is represented in the resolved task payload."
            )}
          </section>

          <section class="niche-tunnel-panel">
            <h3>direct unlocks</h3>
            ${renderList(
              directDependents,
              "No direct dependent is represented in the resolved task payload."
            )}
          </section>

          <section class="niche-tunnel-panel">
            <h3>evidence gate</h3>
            <p>
              ${
                taskReceipts.length
              } represented receipt${
                taskReceipts.length === 1
                  ? ""
                  : "s"
              }.
            </p>
          </section>

          <section class="niche-tunnel-panel">
            <h3>authority boundary</h3>
            <p>
              This tunnel is a deterministic
              interface projection.
              Authoritative task mutation remains
              owned by Niche's existing transition
              controls.
            </p>
          </section>
        </aside>
      </div>
    `;
  };

  const ensureShell = () => {
    if (
      document.getElementById(
        "niche-execution-tunnel"
      )
    ) {
      return;
    }

    const tunnel =
      document.createElement(
        "section"
      );

    tunnel.id =
      "niche-execution-tunnel";

    tunnel.className =
      "niche-execution-tunnel";

    tunnel.hidden = true;

    tunnel.setAttribute(
      "role",
      "dialog"
    );

    tunnel.setAttribute(
      "aria-modal",
      "true"
    );

    tunnel.setAttribute(
      "aria-labelledby",
      "niche-execution-tunnel-title"
    );

    tunnel.innerHTML = `
      <header class="niche-tunnel-head">
        <div>
          <p class="niche-tunnel-kicker">
            savant / niche / execution focus
          </p>

          <h1
            class="niche-tunnel-title"
            id="niche-execution-tunnel-title"
          >
            EXECUTION TUNNEL
          </h1>
        </div>

        <button
          type="button"
          class="niche-tunnel-close"
          aria-label="Return to Niche board"
        >
          ×
        </button>
      </header>

      <div
        class="niche-tunnel-body"
        id="niche-execution-tunnel-body"
      ></div>
    `;

    document.body.append(tunnel);

    tunnel
      .querySelector(
        ".niche-tunnel-close"
      )
      ?.addEventListener(
        "click",
        close
      );

    tunnel.addEventListener(
      "click",
      event => {
        const action =
          event.target.closest(
            "[data-tunnel-action]"
          );

        if (!action) {
          return;
        }

        handleAction(
          action.dataset.tunnelAction
        );
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

    const tunnel =
      document.getElementById(
        "niche-execution-tunnel"
      );

    if (!tunnel) {
      return;
    }

    runtime.previousFocus =
      document.activeElement;

    runtime.open = true;

    tunnel.hidden = false;

    document.body.classList.add(
      "niche-execution-tunnel-open"
    );

    safeStorageSet(
      STORAGE_KEY,
      "open"
    );

    await refresh(taskId);

    tunnel
      .querySelector(
        ".niche-tunnel-close"
      )
      ?.focus();
  };

  const close = () => {
    const tunnel =
      document.getElementById(
        "niche-execution-tunnel"
      );

    runtime.open = false;

    if (tunnel) {
      tunnel.hidden = true;
    }

    document.body.classList.remove(
      "niche-execution-tunnel-open"
    );

    safeStorageSet(
      STORAGE_KEY,
      "closed"
    );

    if (
      runtime.previousFocus &&
      document.contains(
        runtime.previousFocus
      )
    ) {
      runtime.previousFocus.focus();
    }
  };

  const handleAction = action => {
    if (
      action === "return" ||
      action === "board"
    ) {
      close();
      return;
    }

    if (
      action === "start" ||
      action === "continue"
    ) {
      close();

      invokeExistingAction([
        "#start-next",
        "[data-action='start-next']",
        "[data-command='start-next']"
      ]);

      return;
    }

    if (action === "evidence") {
      close();

      invokeExistingAction([
        "[data-view='evidence']",
        "[data-route='evidence']",
        "[data-nav='evidence']"
      ]);

      return;
    }

    if (action === "why") {
      close();

      if (
        window.NicheCausalField?.open
      ) {
        window.NicheCausalField.open();
        return;
      }

      invokeExistingAction([
        "[data-action='show-why']",
        "[data-command='show-why']"
      ]);
    }
  };

  const trapKeyboard = event => {
    if (!runtime.open) {
      return;
    }

    if (event.key === "Escape") {
      event.preventDefault();
      close();
      return;
    }

    if (event.key !== "Tab") {
      return;
    }

    const tunnel =
      document.getElementById(
        "niche-execution-tunnel"
      );

    if (!tunnel) {
      return;
    }

    const focusable =
      [...tunnel.querySelectorAll(
        [
          "button:not([disabled])",
          "[href]",
          "input:not([disabled])",
          "select:not([disabled])",
          "textarea:not([disabled])",
          "[tabindex]:not([tabindex='-1'])"
        ].join(",")
      )].filter(
        node =>
          !node.hidden &&
          node.getClientRects().length > 0
      );

    if (!focusable.length) {
      return;
    }

    const first =
      focusable[0];

    const last =
      focusable[
        focusable.length - 1
      ];

    if (
      event.shiftKey &&
      document.activeElement === first
    ) {
      event.preventDefault();
      last.focus();
      return;
    }

    if (
      !event.shiftKey &&
      document.activeElement === last
    ) {
      event.preventDefault();
      first.focus();
    }
  };

  const bindKeyboard = () => {
    document.addEventListener(
      "keydown",
      event => {
        trapKeyboard(event);

        if (runtime.open) {
          return;
        }

        const target =
          event.target;

        const editing =
          target instanceof
            HTMLInputElement ||
          target instanceof
            HTMLTextAreaElement ||
          target?.isContentEditable;

        if (editing) {
          return;
        }

        if (
          event.key.toLowerCase() ===
            "x" &&
          !event.ctrlKey &&
          !event.metaKey &&
          !event.altKey
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
    bindKeyboard();

    document.documentElement.dataset
      .nicheExecutionTunnel =
      "ready";

    window.dispatchEvent(
      new CustomEvent(
        "niche:execution-tunnel-ready",
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

  window.NicheExecutionTunnel =
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
    document.readyState ===
    "loading"
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
