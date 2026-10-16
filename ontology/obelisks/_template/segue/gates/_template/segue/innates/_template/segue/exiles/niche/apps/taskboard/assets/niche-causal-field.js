(() => {
  "use strict";

  const SCHEMA = "savant.niche.causal-field.v1";
  const STORAGE_KEY = "savant.niche.interface.causal-field.open";
  const TERMINAL_STATES = new Set([
    "completed",
    "rejected",
    "superseded"
  ]);

  const runtime = {
    initialized: false,
    open: false,
    lens: "causal",
    selectedTaskId: null,
    task: null,
    requestController: null,
    refreshTimer: null,
    observer: null,
    lastSignature: ""
  };

  const reducedMotion = () =>
    window.matchMedia?.("(prefers-reduced-motion: reduce)")?.matches === true;

  const text = (value, fallback = "unknown") => {
    if (value === null || value === undefined || value === "") {
      return fallback;
    }

    return String(value);
  };

  const list = value =>
    Array.isArray(value) ? value : [];

  const unique = values =>
    [...new Set(
      values.filter(
        value =>
          typeof value === "string" &&
          value.length > 0
      )
    )];

  const escapeHtml = value =>
    text(value, "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");

  const safeStorageGet = key => {
    try {
      return window.localStorage.getItem(key);
    } catch {
      return null;
    }
  };

  const safeStorageSet = (key, value) => {
    try {
      window.localStorage.setItem(key, value);
    } catch {
      return;
    }
  };

  const taskIdFromNode = node =>
    node
      ?.closest?.("[data-task-id]")
      ?.dataset
      ?.taskId || null;

  const selectedTaskId = () => {
    const nicheState = window.Niche?.state?.();

    return (
      nicheState?.selectedTaskId ||
      nicheState?.recommendedTaskId ||
      runtime.selectedTaskId ||
      document
        .querySelector("[data-task-id][aria-selected='true']")
        ?.dataset
        ?.taskId ||
      document
        .querySelector("[data-task-id].selected")
        ?.dataset
        ?.taskId ||
      document
        .querySelector("[data-task-id].is-selected")
        ?.dataset
        ?.taskId ||
      null
    );
  };

  const ensureShell = () => {
    if (document.getElementById("niche-causal-field")) {
      return;
    }

    const field = document.createElement("aside");

    field.id = "niche-causal-field";
    field.className = "niche-causal-field";
    field.hidden = true;
    field.setAttribute("aria-label", "Causal field");

    field.innerHTML = `
      <header class="niche-causal-head">
        <div>
          <p class="niche-causal-kicker">
            projection / causal intelligence
          </p>
          <h2 class="niche-causal-title">
            CAUSAL FIELD
          </h2>
        </div>

        <button
          class="niche-causal-close"
          type="button"
          aria-label="Close causal field"
        >
          ×
        </button>
      </header>

      <div
        class="niche-causal-body"
        id="niche-causal-body"
      >
        <div class="niche-causal-empty">
          Select a task to resolve its causal neighborhood.
        </div>
      </div>
    `;

    const command = document.createElement("button");

    command.type = "button";
    command.id = "niche-causal-command";
    command.className = "niche-causal-command";
    command.textContent = "causal field";
    command.setAttribute(
      "aria-controls",
      "niche-causal-field"
    );
    command.setAttribute(
      "aria-expanded",
      "false"
    );

    document.body.append(field, command);

    field
      .querySelector(".niche-causal-close")
      ?.addEventListener(
        "click",
        close
      );

    command.addEventListener(
      "click",
      () => {
        if (runtime.open) {
          close();
        } else {
          open();
        }
      }
    );

    field.addEventListener(
      "click",
      event => {
        const lensButton =
          event.target.closest(
            "[data-causal-lens]"
          );

        if (lensButton) {
          setLens(
            lensButton.dataset.causalLens
          );
          return;
        }

        const taskButton =
          event.target.closest(
            "[data-causal-task]"
          );

        if (taskButton) {
          selectTask(
            taskButton.dataset.causalTask
          );
        }
      }
    );
  };

  const open = () => {
    const field =
      document.getElementById(
        "niche-causal-field"
      );

    const command =
      document.getElementById(
        "niche-causal-command"
      );

    if (!field || !command) {
      return;
    }

    runtime.open = true;
    field.hidden = false;

    command.setAttribute(
      "aria-expanded",
      "true"
    );

    safeStorageSet(
      STORAGE_KEY,
      "1"
    );

    void refresh();
  };

  const close = () => {
    const field =
      document.getElementById(
        "niche-causal-field"
      );

    const command =
      document.getElementById(
        "niche-causal-command"
      );

    runtime.open = false;

    clearFocus();

    if (field) {
      field.hidden = true;
    }

    command?.setAttribute(
      "aria-expanded",
      "false"
    );

    safeStorageSet(
      STORAGE_KEY,
      "0"
    );
  };

  const fetchTask = async taskId => {
    if (!taskId) {
      return null;
    }

    runtime.requestController?.abort();

    const controller =
      new AbortController();

    runtime.requestController =
      controller;

    try {
      const response = await fetch(
        `/api/tasks/${encodeURIComponent(taskId)}`,
        {
          signal: controller.signal,
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
      if (error?.name === "AbortError") {
        return null;
      }

      return null;
    } finally {
      if (
        runtime.requestController ===
        controller
      ) {
        runtime.requestController = null;
      }
    }
  };

  const taskState = task => {
    if (!task) {
      return "unknown";
    }

    if (task.ready === true) {
      return "ready";
    }

    if (
      list(task.blockers).length ||
      list(
        task.unsatisfied_dependencies
      ).length
    ) {
      return "blocked";
    }

    if (
      TERMINAL_STATES.has(
        task.status
      )
    ) {
      return "complete";
    }

    return text(
      task.status,
      "unknown"
    ).toLowerCase();
  };

  const authority = task => {
    const projection =
      task?.projection_authoritative;

    const owner =
      task?.authority_owner ||
      task?.owner ||
      task?.authority?.owner ||
      "unknown";

    if (projection === true) {
      return {
        state: "authoritative",
        owner
      };
    }

    if (projection === false) {
      return {
        state: "projection",
        owner
      };
    }

    return {
      state: "unknown",
      owner
    };
  };

  const dependencies = task =>
    unique([
      ...list(task?.dependencies),
      ...list(
        task?.unsatisfied_dependencies
      )
    ]);

  const dependents = task =>
    unique(
      list(task?.dependents)
    );

  const transitive = task =>
    unique(
      list(
        task?.transitive_dependencies
      )
    );

  const blockerIds = task =>
    unique([
      ...list(task?.blockers),
      ...list(
        task?.unsatisfied_dependencies
      )
    ]);

  const receipts = task =>
    list(task?.receipts);

  const completionCondition = task =>
    task?.completion_condition ??
    task?.completion ??
    task?.acceptance ??
    task?.done_when ??
    null;

  const renderTaskList = (
    items,
    state,
    emptyMessage
  ) => {
    if (!items.length) {
      return `
        <div class="niche-causal-empty">
          ${escapeHtml(emptyMessage)}
        </div>
      `;
    }

    return `
      <ul class="niche-causal-list">
        ${items.map(item => {
          const id =
            typeof item === "string"
              ? item
              : item?.task_id ||
                item?.id ||
                "unknown";

          const title =
            typeof item === "string"
              ? item
              : item?.title ||
                item?.purpose ||
                id;

          return `
            <li
              class="niche-causal-item"
              data-state="${escapeHtml(state)}"
            >
              <span aria-hidden="true"></span>

              <div class="niche-causal-item-main">
                <strong>
                  ${escapeHtml(title)}
                </strong>

                <span>
                  ${escapeHtml(id)}
                </span>
              </div>

              <button
                class="niche-causal-action"
                type="button"
                data-causal-task="${escapeHtml(id)}"
                aria-label="Inspect ${escapeHtml(id)}"
              >
                open
              </button>
            </li>
          `;
        }).join("")}
      </ul>
    `;
  };

  const render = task => {
    const body =
      document.getElementById(
        "niche-causal-body"
      );

    if (!body) {
      return;
    }

    if (!task) {
      body.innerHTML = `
        <div class="niche-causal-empty">
          Current task intelligence is unavailable
          or no task is selected.
          No causal relationship is inferred.
        </div>
      `;

      return;
    }

    const id =
      task.task_id ||
      task.id ||
      "unknown";

    const upstream =
      dependencies(task);

    const downstream =
      dependents(task);

    const transitiveIds =
      transitive(task);

    const blockers =
      blockerIds(task);

    const taskAuthority =
      authority(task);

    const evidence =
      receipts(task);

    const completion =
      completionCondition(task);

    body.innerHTML = `
      <div class="niche-causal-readout">
        <div>
          <span class="niche-causal-label">
            task
          </span>
          <span class="niche-causal-value">
            ${escapeHtml(id)}
          </span>
        </div>

        <div>
          <span class="niche-causal-label">
            state
          </span>
          <span class="niche-causal-value">
            ${escapeHtml(taskState(task))}
          </span>
        </div>

        <div>
          <span class="niche-causal-label">
            authority
          </span>
          <span class="niche-causal-value">
            ${escapeHtml(taskAuthority.state)}
          </span>
        </div>
      </div>

      <section class="niche-causal-section">
        <h3>lens array</h3>

        <div class="niche-causal-grid">
          ${[
            [
              "causal",
              "causal lens",
              "constraints + direct consequences"
            ],
            [
              "authority",
              "authority lens",
              "ownership + projection boundary"
            ],
            [
              "unlock",
              "unlock horizon",
              "direct + represented transitive topology"
            ],
            [
              "blocker",
              "blocker radar",
              "represented constraints only"
            ]
          ].map(
            ([
              key,
              label,
              description
            ]) => `
              <button
                type="button"
                class="niche-causal-action"
                data-causal-lens="${key}"
                data-active="${
                  runtime.lens === key
                    ? "true"
                    : "false"
                }"
              >
                ${label}
                <small>
                  ${description}
                </small>
              </button>
            `
          ).join("")}
        </div>
      </section>

      ${
        runtime.lens === "causal"
          ? `
            <section class="niche-causal-section">
              <h3>upstream constraints</h3>

              ${renderTaskList(
                upstream,
                "warning",
                "No represented upstream dependency is available."
              )}
            </section>

            <section class="niche-causal-section">
              <h3>direct unlock horizon</h3>

              ${renderTaskList(
                downstream,
                "ready",
                "No represented direct dependent is available."
              )}
            </section>
          `
          : ""
      }

      ${
        runtime.lens === "authority"
          ? `
            <section class="niche-causal-section">
              <h3>authority signature</h3>

              <div class="niche-causal-chips">
                <span class="niche-causal-chip">
                  classification:${escapeHtml(taskAuthority.state)}
                </span>

                <span class="niche-causal-chip">
                  owner:${escapeHtml(taskAuthority.owner)}
                </span>

                <span class="niche-causal-chip">
                  ui:projection-only
                </span>

                <span class="niche-causal-chip">
                  filesystem-authority:false
                </span>
              </div>
            </section>

            <section class="niche-causal-section">
              <h3>provenance</h3>

              <div class="niche-causal-empty">
                ${escapeHtml(
                  task.provenance ||
                  task.source ||
                  task.authority_basis ||
                  "Provenance is not represented in the currently resolved task payload."
                )}
              </div>
            </section>
          `
          : ""
      }

      ${
        runtime.lens === "unlock"
          ? `
            <section class="niche-causal-section">
              <h3>direct</h3>

              ${renderTaskList(
                downstream,
                "ready",
                "No represented direct unlock is available."
              )}
            </section>

            <section class="niche-causal-section">
              <h3>represented transitive topology</h3>

              ${renderTaskList(
                transitiveIds,
                "warning",
                "No transitive relationship is represented by the resolved payload."
              )}
            </section>
          `
          : ""
      }

      ${
        runtime.lens === "blocker"
          ? `
            <section class="niche-causal-section">
              <h3>blocker radar</h3>

              ${renderTaskList(
                blockers,
                "blocked",
                "No represented blocker is available."
              )}
            </section>
          `
          : ""
      }

      <section class="niche-causal-section">
        <h3>evidence gate</h3>

        <div class="niche-causal-chips">
          <span class="niche-causal-chip">
            receipts:${evidence.length}
          </span>

          <span class="niche-causal-chip">
            completion:${
              completion
                ? "represented"
                : "not-projected"
            }
          </span>
        </div>

        <div
          class="niche-causal-empty"
          style="margin-top:.45rem"
        >
          ${escapeHtml(
            completion ||
            "Completion condition is not represented in the resolved payload."
          )}
        </div>
      </section>
    `;

    applyLensFocus(task);
  };

  const clearFocus = () => {
    document.body.classList.remove(
      "niche-causal-focus"
    );

    document.querySelectorAll(
      [
        ".niche-causal-related",
        ".niche-causal-origin",
        ".niche-causal-upstream",
        ".niche-causal-downstream",
        ".niche-causal-authority"
      ].join(", ")
    ).forEach(node => {
      node.classList.remove(
        "niche-causal-related",
        "niche-causal-origin",
        "niche-causal-upstream",
        "niche-causal-downstream",
        "niche-causal-authority"
      );
    });
  };

  const applyLensFocus = task => {
    clearFocus();

    if (!task || !runtime.open) {
      return;
    }

    const id =
      task.task_id ||
      task.id;

    if (!id) {
      return;
    }

    const upstream =
      new Set(
        dependencies(task)
      );

    const downstream =
      new Set(
        dependents(task)
      );

    const relevant =
      new Set([
        id,
        ...upstream,
        ...downstream
      ]);

    document.body.classList.add(
      "niche-causal-focus"
    );

    document
      .querySelectorAll("[data-task-id]")
      .forEach(node => {
        const nodeId =
          node.dataset.taskId;

        if (!relevant.has(nodeId)) {
          return;
        }

        node.classList.add(
          "niche-causal-related"
        );

        if (nodeId === id) {
          node.classList.add(
            "niche-causal-origin"
          );
        }

        if (upstream.has(nodeId)) {
          node.classList.add(
            "niche-causal-upstream"
          );
        }

        if (downstream.has(nodeId)) {
          node.classList.add(
            "niche-causal-downstream"
          );
        }

        if (
          runtime.lens ===
          "authority"
        ) {
          node.classList.add(
            "niche-causal-authority"
          );
        }
      });
  };

  const setLens = lens => {
    if (
      ![
        "causal",
        "authority",
        "unlock",
        "blocker"
      ].includes(lens)
    ) {
      return;
    }

    runtime.lens = lens;

    render(runtime.task);
  };

  const selectTask = taskId => {
    if (!taskId) {
      return;
    }

    runtime.selectedTaskId =
      taskId;

    const node =
      [...document.querySelectorAll(
        "[data-task-id]"
      )].find(
        candidate =>
          candidate.dataset.taskId ===
          taskId
      );

    if (node) {
      node.dispatchEvent(
        new MouseEvent(
          "click",
          {
            bubbles: true,
            cancelable: true,
            view: window
          }
        )
      );
    }

    void refresh(taskId);
  };

  const pulseChange = () => {
    if (reducedMotion()) {
      return;
    }

    const field =
      document.getElementById(
        "niche-causal-field"
      );

    if (!field) {
      return;
    }

    field.classList.remove(
      "niche-causal-pulse"
    );

    void field.offsetWidth;

    field.classList.add(
      "niche-causal-pulse"
    );
  };

  const refresh = async explicitTaskId => {
    if (!runtime.open) {
      return;
    }

    const id =
      explicitTaskId ||
      selectedTaskId();

    if (!id) {
      runtime.task = null;
      render(null);
      return;
    }

    const task =
      await fetchTask(id);

    if (!task) {
      runtime.task = null;
      render(null);
      return;
    }

    const signature =
      JSON.stringify({
        id:
          task.task_id ||
          task.id,
        status:
          task.status,
        ready:
          task.ready,
        blockers:
          list(task.blockers),
        unsatisfied:
          list(
            task.unsatisfied_dependencies
          ),
        dependents:
          list(task.dependents),
        receipts:
          list(task.receipts).length
      });

    const changed =
      Boolean(
        runtime.lastSignature &&
        runtime.lastSignature !==
          signature
      );

    runtime.selectedTaskId =
      task.task_id ||
      task.id ||
      id;

    runtime.task = task;
    runtime.lastSignature =
      signature;

    render(task);

    if (changed) {
      pulseChange();
    }
  };

  const queueRefresh = () => {
    if (
      !runtime.open ||
      runtime.refreshTimer !== null
    ) {
      return;
    }

    runtime.refreshTimer =
      window.setTimeout(
        () => {
          runtime.refreshTimer = null;
          void refresh();
        },
        80
      );
  };

  const bindSelection = () => {
    document.addEventListener(
      "click",
      event => {
        const id =
          taskIdFromNode(
            event.target
          );

        if (!id) {
          return;
        }

        runtime.selectedTaskId = id;

        if (runtime.open) {
          queueRefresh();
        }
      },
      true
    );

    document.addEventListener(
      "focusin",
      event => {
        const id =
          taskIdFromNode(
            event.target
          );

        if (id) {
          runtime.selectedTaskId = id;
        }
      }
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

        if (editing) {
          return;
        }

        if (
          event.key === "Escape" &&
          runtime.open
        ) {
          event.preventDefault();
          close();
          return;
        }

        if (
          event.altKey &&
          event.key.toLowerCase() ===
            "c"
        ) {
          event.preventDefault();

          if (runtime.open) {
            close();
          } else {
            open();
          }

          return;
        }

        if (!runtime.open) {
          return;
        }

        if (event.key === "1") {
          event.preventDefault();
          setLens("causal");
        }

        if (event.key === "2") {
          event.preventDefault();
          setLens("authority");
        }

        if (event.key === "3") {
          event.preventDefault();
          setLens("unlock");
        }

        if (event.key === "4") {
          event.preventDefault();
          setLens("blocker");
        }
      }
    );
  };

  const bindProjectionChanges = () => {
    runtime.observer =
      new MutationObserver(
        records => {
          if (!runtime.open) {
            return;
          }

          const meaningful =
            records.some(
              record => {
                if (
                  record.type !==
                  "childList"
                ) {
                  return false;
                }

                return [
                  ...record.addedNodes,
                  ...record.removedNodes
                ].some(
                  node =>
                    node.nodeType ===
                      Node.ELEMENT_NODE &&
                    (
                      node.matches?.(
                        "[data-task-id]"
                      ) ||
                      node.querySelector?.(
                        "[data-task-id]"
                      )
                    )
                );
              }
            );

          if (meaningful) {
            queueRefresh();
          }
        }
      );

    runtime.observer.observe(
      document.body,
      {
        childList: true,
        subtree: true
      }
    );

    window.addEventListener(
      "niche:executable-environment-ready",
      queueRefresh
    );

    window.addEventListener(
      "niche:frontend-ready",
      queueRefresh
    );
  };

  const initialize = () => {
    if (runtime.initialized) {
      return;
    }

    runtime.initialized = true;

    ensureShell();
    bindSelection();
    bindKeyboard();
    bindProjectionChanges();

    if (
      safeStorageGet(
        STORAGE_KEY
      ) === "1"
    ) {
      open();
    }

    document.documentElement.dataset.nicheCausalField =
      "ready";

    window.dispatchEvent(
      new CustomEvent(
        "niche:causal-field-ready",
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

  window.NicheCausalField =
    Object.freeze({
      open,
      close,
      refresh,
      selectTask,
      setLens,

      state: () => ({
        schema: SCHEMA,
        open: runtime.open,
        lens: runtime.lens,
        selectedTaskId:
          runtime.selectedTaskId,
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
