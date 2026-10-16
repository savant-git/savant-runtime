(() => {
  "use strict";

  const SCHEMA =
    "savant.niche.evidence-gate.v1";

  const runtime = {
    initialized: false,
    open: false,
    taskId: null,
    task: null,
    generation: 0,
    controller: null,
    previousFocus: null
  };

  const represented = value =>
    value !== null &&
    value !== undefined &&
    value !== "";

  const array = value =>
    Array.isArray(value)
      ? value
      : [];

  const first = (
    object,
    keys
  ) => {
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

  const evidenceRequirement = task => {
    const explicit =
      first(
        task,
        [
          "evidence_required",
          "requires_evidence"
        ]
      );

    if (explicit === true) {
      return {
        state: "required",
        label: "required",
        explicit: true
      };
    }

    if (explicit === false) {
      return {
        state: "represented",
        label: "not required",
        explicit: true
      };
    }

    const requirement =
      first(
        task,
        [
          "evidence_requirement",
          "evidence_requirements"
        ]
      );

    if (!represented(requirement)) {
      return {
        state: "unknown",
        label: "requirement unknown",
        explicit: false
      };
    }

    if (
      typeof requirement === "object" &&
      !Array.isArray(requirement)
    ) {
      if (requirement.required === true) {
        return {
          state: "required",
          label: "required",
          explicit: true
        };
      }

      if (requirement.required === false) {
        return {
          state: "represented",
          label: "not required",
          explicit: true
        };
      }
    }

    return {
      state: "represented",
      label: valueText(requirement),
      explicit: true
    };
  };

  const receipts = task => {
    const candidates = [
      task?.receipts,
      task?.evidence,
      task?.evidence_receipts,
      task?.completion_receipts
    ];

    for (const candidate of candidates) {
      if (Array.isArray(candidate)) {
        return {
          represented: true,
          items: candidate
        };
      }
    }

    return {
      represented: false,
      items: []
    };
  };

  const receiptText = item => {
    if (
      typeof item === "string" ||
      typeof item === "number"
    ) {
      return String(item);
    }

    if (
      item &&
      typeof item === "object"
    ) {
      const preferred =
        first(
          item,
          [
            "receipt_id",
            "id",
            "source",
            "path",
            "uri",
            "reference",
            "summary",
            "description"
          ]
        );

      if (preferred) {
        return valueText(preferred);
      }

      return valueText(item);
    }

    return "unrepresented receipt";
  };

  const row = (
    label,
    value,
    state = null
  ) => `
    <div
      class="niche-evidence-row"
      data-state="${
        escapeHtml(
          state ||
          (
            represented(value)
              ? "represented"
              : "unknown"
          )
        )
      }"
    >
      <span class="niche-evidence-label">
        ${escapeHtml(label)}
      </span>

      <span class="niche-evidence-value">
        ${escapeHtml(value)}
      </span>
    </div>
  `;

  const renderReceipts = receiptState => {
    if (!receiptState.represented) {
      return `
        <div class="niche-evidence-empty">
          Receipt collection is not projected
          by the resolved task payload.
        </div>
      `;
    }

    if (!receiptState.items.length) {
      return `
        <div class="niche-evidence-empty">
          A receipt collection is represented
          and currently contains zero entries.
          This does not establish that evidence
          is unnecessary.
        </div>
      `;
    }

    return `
      <section class="niche-evidence-receipts">
        <div class="niche-evidence-receipts-head">
          represented receipts
        </div>

        <ol class="niche-evidence-receipt-list">
          ${receiptState.items
            .map(
              item => `
                <li class="niche-evidence-receipt">
                  ${escapeHtml(
                    receiptText(item)
                  )}
                </li>
              `
            )
            .join("")}
        </ol>
      </section>
    `;
  };

  const render = task => {
    const body =
      document.getElementById(
        "niche-evidence-body"
      );

    if (!body) {
      return;
    }

    if (!task) {
      body.innerHTML = `
        <div class="niche-evidence-empty">
          Evidence semantics are unavailable
          for the current selection. No
          requirement has been inferred.
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

    const requirement =
      evidenceRequirement(task);

    const receiptState =
      receipts(task);

    const completion =
      first(
        task,
        [
          "completion_condition",
          "completion_conditions",
          "done_when"
        ]
      );

    const evidenceState =
      receiptState.represented
        ? (
            receiptState.items.length
              ? "present"
              : "represented-empty"
          )
        : "not-projected";

    body.innerHTML = `
      <div class="niche-evidence-summary">
        <span class="niche-evidence-chip">
          task:${escapeHtml(id)}
        </span>

        <span
          class="niche-evidence-chip"
          data-state="${
            escapeHtml(requirement.state)
          }"
        >
          requirement:${
            escapeHtml(requirement.label)
          }
        </span>

        <span
          class="niche-evidence-chip"
          data-state="${
            receiptState.items.length
              ? "present"
              : "unknown"
          }"
        >
          evidence:${
            escapeHtml(evidenceState)
          }
        </span>
      </div>

      <div class="niche-evidence-grid">
        ${row(
          "evidence requirement",
          requirement.label,
          requirement.state
        )}

        ${row(
          "completion condition",
          completion
        )}

        ${row(
          "receipt collection",
          receiptState.represented
            ? "represented"
            : "not projected"
        )}

        ${row(
          "receipt count",
          receiptState.represented
            ? receiptState.items.length
            : "unknown"
        )}
      </div>

      ${renderReceipts(receiptState)}

      <div class="niche-evidence-boundary">
        Evidence Gate never infers a
        requirement from task priority,
        readiness, status, completion state,
        an empty receipt collection, or visual
        prominence. Missing requirement data
        remains unknown.
      </div>
    `;
  };

  const ensureShell = () => {
    if (
      document.getElementById(
        "niche-evidence-gate"
      )
    ) {
      return;
    }

    const shell =
      document.createElement("aside");

    shell.id =
      "niche-evidence-gate";

    shell.className =
      "niche-evidence-gate";

    shell.hidden = true;

    shell.setAttribute(
      "aria-label",
      "Evidence Gate"
    );

    shell.innerHTML = `
      <header class="niche-evidence-head">
        <div>
          <p class="niche-evidence-kicker">
            requirement / receipts / completion
          </p>

          <h2 class="niche-evidence-title">
            EVIDENCE GATE
          </h2>
        </div>

        <button
          type="button"
          class="niche-evidence-close"
          aria-label="Close Evidence Gate"
        >
          ×
        </button>
      </header>

      <div
        class="niche-evidence-body"
        id="niche-evidence-body"
      ></div>
    `;

    document.body.append(shell);

    shell
      .querySelector(
        ".niche-evidence-close"
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
        "niche-evidence-gate"
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
        ".niche-evidence-close"
      )
      ?.focus();
  };

  const close = () => {
    runtime.open = false;
    runtime.controller?.abort();

    const shell =
      document.getElementById(
        "niche-evidence-gate"
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
              "[data-action='evidence-gate']",
              "[data-command='evidence-gate']",
              "[data-evidence-gate]"
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
          event.key.toLowerCase() === "e"
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
      .nicheEvidenceGate =
      "ready";

    window.dispatchEvent(
      new CustomEvent(
        "niche:evidence-gate-ready",
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

  window.NicheEvidenceGate =
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
