(() => {
  "use strict";

  const SCHEMA =
    "savant.niche.provenance-thread.v1";

  const runtime = {
    initialized: false,
    open: false,
    taskId: null,
    task: null,
    controller: null,
    previousFocus: null
  };

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

  const firstRepresented = (
    object,
    keys
  ) => {
    for (const key of keys) {
      const candidate =
        object?.[key];

      if (
        candidate !== undefined &&
        candidate !== null &&
        candidate !== ""
      ) {
        return candidate;
      }
    }

    return null;
  };

  const authorityClassification = task => {
    const explicit =
      firstRepresented(
        task,
        [
          "authority_classification",
          "authority_effect",
          "authority"
        ]
      );

    if (
      typeof explicit === "string"
    ) {
      return explicit;
    }

    return "unknown";
  };

  const authorityOwner = task =>
    firstRepresented(
      task,
      [
        "authority_owner",
        "owner",
        "task_owner"
      ]
    );

  const authorityBasis = task =>
    firstRepresented(
      task,
      [
        "authority_basis",
        "basis",
        "source_basis"
      ]
    );

  const provenance = task =>
    firstRepresented(
      task,
      [
        "provenance",
        "source",
        "source_ref",
        "source_path",
        "origin"
      ]
    );

  const lineage = task =>
    firstRepresented(
      task,
      [
        "lineage",
        "parent_task_id",
        "parent_id",
        "ancestry"
      ]
    );

  const supersession = task =>
    firstRepresented(
      task,
      [
        "supersedes",
        "superseded_by",
        "supersession"
      ]
    );

  const renderNode = ({
    label,
    value,
    kind = "unknown",
    note = null
  }) => `
    <li
      class="niche-provenance-node"
      data-kind="${escapeHtml(kind)}"
    >
      <span
        class="niche-provenance-marker"
        aria-hidden="true"
      ></span>

      <div class="niche-provenance-card">
        <span class="niche-provenance-label">
          ${escapeHtml(label)}
        </span>

        <span class="niche-provenance-value">
          ${escapeHtml(
            value ??
            "not projected"
          )}
        </span>

        ${
          note
            ? `
              <div class="niche-provenance-note">
                ${escapeHtml(note)}
              </div>
            `
            : ""
        }
      </div>
    </li>
  `;

  const render = task => {
    const body =
      document.getElementById(
        "niche-provenance-body"
      );

    if (!body) {
      return;
    }

    if (!task) {
      body.innerHTML = `
        <div class="niche-provenance-empty">
          Provenance is unavailable for the
          current selection. Nothing has been
          inferred from filesystem placement.
        </div>
      `;

      return;
    }

    const id =
      task.task_id ||
      task.id ||
      "unknown";

    const classification =
      authorityClassification(task);

    const owner =
      authorityOwner(task);

    const basis =
      authorityBasis(task);

    const source =
      provenance(task);

    const ancestry =
      lineage(task);

    const supersessionValue =
      supersession(task);

    const classificationKind =
      classification === "none"
        ? "projection"
        : classification ===
            "authoritative"
          ? "authoritative"
          : "unknown";

    body.innerHTML = `
      <div class="niche-provenance-summary">
        <span class="niche-provenance-chip">
          task:${escapeHtml(id)}
        </span>

        <span class="niche-provenance-chip">
          authority:${escapeHtml(classification)}
        </span>

        <span class="niche-provenance-chip">
          ui:projection-only
        </span>
      </div>

      <ol class="niche-provenance-chain">
        ${renderNode({
          label: "task identity",
          value: id,
          kind: "authoritative",
          note:
            "Identity is displayed from the resolved Niche task payload."
        })}

        ${renderNode({
          label: "authority classification",
          value: classification,
          kind: classificationKind,
          note:
            classification === "unknown"
              ? "No explicit authority classification is represented by the resolved payload."
              : "Classification is displayed without promotion by this interface."
        })}

        ${renderNode({
          label: "owner",
          value: owner,
          kind:
            owner
              ? "authoritative"
              : "unknown",
          note:
            owner
              ? "Owner value is source-derived from the resolved task payload."
              : "Owner is not projected."
        })}

        ${renderNode({
          label: "authority basis",
          value: basis,
          kind:
            basis
              ? "authoritative"
              : "unknown",
          note:
            basis
              ? "Basis is displayed as supplied."
              : "Authority basis is not projected."
        })}

        ${renderNode({
          label: "provenance / source",
          value: source,
          kind:
            source
              ? "projection"
              : "unknown",
          note:
            source
              ? "Source value is displayed without treating physical placement as authority."
              : "Provenance is not represented by the resolved payload."
        })}

        ${renderNode({
          label: "lineage / ancestry",
          value: ancestry,
          kind:
            ancestry
              ? "projection"
              : "unknown",
          note:
            ancestry
              ? "Lineage is displayed from represented task data."
              : "Lineage is not projected."
        })}

        ${renderNode({
          label: "supersession",
          value: supersessionValue,
          kind:
            supersessionValue
              ? "projection"
              : "unknown",
          note:
            supersessionValue
              ? "Supersession is displayed without modifying accepted history."
              : "No supersession relationship is represented."
        })}
      </ol>

      <div class="niche-provenance-actions">
        <button
          type="button"
          class="niche-provenance-action"
          data-provenance-action="causal"
        >
          causal lens
        </button>

        <button
          type="button"
          class="niche-provenance-action"
          data-provenance-action="close"
        >
          return
        </button>
      </div>
    `;
  };

  const ensureShell = () => {
    if (
      document.getElementById(
        "niche-provenance-thread"
      )
    ) {
      return;
    }

    const shell =
      document.createElement("aside");

    shell.id =
      "niche-provenance-thread";

    shell.className =
      "niche-provenance-thread";

    shell.hidden = true;

    shell.setAttribute(
      "aria-label",
      "Provenance thread"
    );

    shell.innerHTML = `
      <header class="niche-provenance-head">
        <div>
          <p class="niche-provenance-kicker">
            authority / lineage / source
          </p>

          <h2 class="niche-provenance-title">
            PROVENANCE THREAD
          </h2>
        </div>

        <button
          type="button"
          class="niche-provenance-close"
          aria-label="Close provenance thread"
        >
          ×
        </button>
      </header>

      <div
        class="niche-provenance-body"
        id="niche-provenance-body"
      ></div>
    `;

    document.body.append(shell);

    shell
      .querySelector(
        ".niche-provenance-close"
      )
      ?.addEventListener(
        "click",
        close
      );

    shell.addEventListener(
      "click",
      event => {
        const action =
          event.target.closest(
            "[data-provenance-action]"
          );

        if (!action) {
          return;
        }

        if (
          action.dataset
            .provenanceAction ===
          "close"
        ) {
          close();
          return;
        }

        if (
          action.dataset
            .provenanceAction ===
          "causal"
        ) {
          close();

          if (
            window.NicheCausalField?.open
          ) {
            window.NicheCausalField.open();
          }
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
        "niche-provenance-thread"
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
        ".niche-provenance-close"
      )
      ?.focus();
  };

  const close = () => {
    const shell =
      document.getElementById(
        "niche-provenance-thread"
      );

    runtime.open = false;

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
              "[data-action='provenance-thread']",
              "[data-command='provenance-thread']",
              "[data-provenance-thread]"
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
          event.key.toLowerCase() === "p"
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
      .nicheProvenanceThread =
      "ready";

    window.dispatchEvent(
      new CustomEvent(
        "niche:provenance-thread-ready",
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

  window.NicheProvenanceThread =
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
