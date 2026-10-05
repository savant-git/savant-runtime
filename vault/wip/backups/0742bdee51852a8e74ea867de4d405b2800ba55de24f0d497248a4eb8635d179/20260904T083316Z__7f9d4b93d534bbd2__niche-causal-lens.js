(() => {
  "use strict";

  const SCHEMA =
    "savant.niche.causal-lens.v1";

  const runtime = {
    initialized: false,
    open: false,
    taskId: null,
    task: null,
    related: new Map(),
    generation: 0,
    controller: null,
    previousFocus: null,
    lens: "causal"
  };

  const represented = value =>
    value !== null &&
    value !== undefined &&
    value !== "";

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

  const text = (
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
    text(value, "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");

  const normalizeIds = values => {
    const ids = [];

    for (const value of values) {
      if (
        typeof value === "string" &&
        value.length
      ) {
        ids.push(value);
        continue;
      }

      if (
        value &&
        typeof value === "object"
      ) {
        const id =
          first(
            value,
            [
              "task_id",
              "taskId",
              "id"
            ]
          );

        if (
          typeof id === "string" &&
          id.length
        ) {
          ids.push(id);
        }
      }
    }

    return unique(ids);
  };

  const taskId = task =>
    first(
      task,
      [
        "task_id",
        "taskId",
        "id"
      ]
    );

  const taskTitle = task =>
    first(
      task,
      [
        "title",
        "name",
        "purpose"
      ]
    );

  const currentTaskId = () => {
    let state = {};

    try {
      state =
        window.Niche?.state?.() ||
        {};
    } catch {
      state = {};
    }

    return (
      runtime.taskId ||
      state.selectedTaskId ||
      state.recommendedTaskId ||
      null
    );
  };

  const directDependencies = task =>
    normalizeIds(
      array(task?.dependencies)
    );

  const unsatisfiedDependencies = task =>
    normalizeIds(
      array(
        task?.unsatisfied_dependencies
      )
    );

  const blockers = task =>
    normalizeIds(
      array(task?.blockers)
    );

  const directDependents = task =>
    normalizeIds(
      array(task?.dependents)
    );

  const constraints = task => {
    const values = [];

    for (
      const key of [
        "constraints",
        "constraint",
        "conditions",
        "preconditions"
      ]
    ) {
      const value = task?.[key];

      if (Array.isArray(value)) {
        value.forEach(item => {
          if (represented(item)) {
            values.push(text(item));
          }
        });
      } else if (represented(value)) {
        values.push(text(value));
      }
    }

    return unique(values);
  };

  const fetchJson = async (
    url,
    controller
  ) => {
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
        error?.name === "AbortError"
      ) {
        return null;
      }

      return null;
    }
  };

  const fetchTask = async (
    id,
    controller
  ) => {
    if (!id) {
      return null;
    }

    const payload =
      await fetchJson(
        `/api/tasks/${
          encodeURIComponent(id)
        }`,
        controller
      );

    return (
      payload?.task ||
      payload ||
      null
    );
  };

  const fetchContext = async id => {
    runtime.generation += 1;

    const generation =
      runtime.generation;

    runtime.controller?.abort();

    const controller =
      new AbortController();

    runtime.controller =
      controller;

    const focal =
      await fetchTask(
        id,
        controller
      );

    if (
      generation !==
        runtime.generation ||
      !focal
    ) {
      return null;
    }

    const relationIds =
      unique([
        ...directDependencies(focal),
        ...unsatisfiedDependencies(
          focal
        ),
        ...blockers(focal),
        ...directDependents(focal)
      ]).filter(
        relatedId =>
          relatedId !== id
      );

    const relatedPairs =
      await Promise.all(
        relationIds.map(
          async relatedId => [
            relatedId,
            await fetchTask(
              relatedId,
              controller
            )
          ]
        )
      );

    if (
      generation !==
      runtime.generation
    ) {
      return null;
    }

    const related =
      new Map();

    for (
      const [relatedId, task]
      of relatedPairs
    ) {
      if (task) {
        related.set(
          relatedId,
          task
        );
      }
    }

    if (
      runtime.controller ===
      controller
    ) {
      runtime.controller = null;
    }

    return {
      focal,
      related
    };
  };

  const relationTitle = id => {
    const related =
      runtime.related.get(id);

    return (
      taskTitle(related) ||
      id
    );
  };

  const relationButton = (
    id,
    kind
  ) => `
    <button
      type="button"
      class="niche-causal-lens-node"
      data-causal-lens-task="${
        escapeHtml(id)
      }"
      data-causal-relation="${
        escapeHtml(kind)
      }"
    >
      <span
        class="niche-causal-lens-node-id"
      >
        ${escapeHtml(id)}
      </span>

      <span
        class="niche-causal-lens-node-title"
      >
        ${escapeHtml(
          relationTitle(id)
        )}
      </span>
    </button>
  `;

  const empty = message => `
    <div class="niche-causal-lens-empty">
      ${escapeHtml(message)}
    </div>
  `;

  const relationSection = (
    title,
    ids,
    kind,
    emptyMessage
  ) => `
    <section
      class="niche-causal-lens-section"
      data-causal-section="${
        escapeHtml(kind)
      }"
    >
      <header
        class="niche-causal-lens-section-head"
      >
        <span>${escapeHtml(title)}</span>
        <span>${ids.length}</span>
      </header>

      <div
        class="niche-causal-lens-node-list"
      >
        ${
          ids.length
            ? ids.map(
                id =>
                  relationButton(
                    id,
                    kind
                  )
              ).join("")
            : empty(emptyMessage)
        }
      </div>
    </section>
  `;

  const renderCausal = task => {
    const dependencies =
      directDependencies(task);

    const unsatisfied =
      unsatisfiedDependencies(task);

    const blockedBy =
      blockers(task);

    const dependents =
      directDependents(task);

    const conditionValues =
      constraints(task);

    return `
      <div
        class="niche-causal-lens-grid"
      >
        ${relationSection(
          "DIRECT PREREQUISITES",
          dependencies,
          "prerequisite",
          "No direct prerequisite is represented."
        )}

        ${relationSection(
          "UNSATISFIED PREREQUISITES",
          unsatisfied,
          "unsatisfied",
          "No unsatisfied prerequisite is represented."
        )}

        ${relationSection(
          "BLOCKED BY",
          blockedBy,
          "blocker",
          "No blocker is represented."
        )}

        <section
          class="niche-causal-lens-section"
          data-causal-section="constraint"
        >
          <header
            class="niche-causal-lens-section-head"
          >
            <span>CONSTRAINTS</span>
            <span>
              ${conditionValues.length}
            </span>
          </header>

          <div
            class="niche-causal-lens-node-list"
          >
            ${
              conditionValues.length
                ? conditionValues
                    .map(
                      value => `
                        <div
                          class="
                            niche-causal-lens-fact
                          "
                        >
                          ${escapeHtml(value)}
                        </div>
                      `
                    )
                    .join("")
                : empty(
                    "No explicit constraint is represented."
                  )
            }
          </div>
        </section>

        ${relationSection(
          "DIRECT CONSEQUENCES",
          dependents,
          "consequence",
          "No direct dependent is represented."
        )}
      </div>
    `;
  };

  const renderAuthority = task => {
    const fields = [
      [
        "owner",
        first(
          task,
          [
            "authority_owner",
            "task_owner",
            "owner"
          ]
        )
      ],
      [
        "authority effect",
        first(
          task,
          ["authority_effect"]
        )
      ],
      [
        "authority class",
        first(
          task,
          [
            "authority_classification",
            "authority_class"
          ]
        )
      ],
      [
        "basis",
        first(
          task,
          [
            "authority_basis",
            "source_basis",
            "basis"
          ]
        )
      ],
      [
        "provenance",
        first(
          task,
          [
            "provenance",
            "source_ref",
            "source_path",
            "source",
            "origin"
          ]
        )
      ],
      [
        "lineage",
        first(
          task,
          [
            "lineage",
            "ancestry",
            "parent_task_id",
            "parent_id"
          ]
        )
      ],
      [
        "supersedes",
        first(
          task,
          ["supersedes"]
        )
      ],
      [
        "superseded by",
        first(
          task,
          ["superseded_by"]
        )
      ]
    ];

    return `
      <div
        class="niche-causal-lens-facts"
      >
        ${fields.map(
          ([label, value]) => `
            <div
              class="niche-causal-lens-fact-row"
              data-represented="${
                represented(value)
                  ? "true"
                  : "false"
              }"
            >
              <span
                class="niche-causal-lens-fact-label"
              >
                ${escapeHtml(label)}
              </span>

              <span
                class="niche-causal-lens-fact-value"
              >
                ${escapeHtml(value)}
              </span>
            </div>
          `
        ).join("")}
      </div>

      <div
        class="niche-causal-lens-boundary"
      >
        Missing authority fields remain
        not projected. Causal position,
        filesystem placement, visual
        prominence, readiness, and priority
        do not establish authority.
      </div>
    `;
  };

  const renderUnlock = task => {
    const direct =
      directDependents(task);

    const secondOrder =
      unique(
        direct.flatMap(id =>
          directDependents(
            runtime.related.get(id)
          )
        )
      ).filter(
        id =>
          id !== taskId(task) &&
          !direct.includes(id)
      );

    return `
      ${relationSection(
        "DIRECT UNLOCK HORIZON",
        direct,
        "unlock-direct",
        "No direct dependent is represented."
      )}

      ${relationSection(
        "SECOND-ORDER VISIBLE HORIZON",
        secondOrder,
        "unlock-second",
        "No second-order consequence can be deterministically derived from the currently resolved neighborhood."
      )}

      <div
        class="niche-causal-lens-boundary"
      >
        The second-order band is bounded by
        the task neighborhood actually
        resolved for this lens. It is not a
        claim of complete transitive closure.
      </div>
    `;
  };

  const renderBlocker = task => {
    const explicit =
      blockers(task);

    const unsatisfied =
      unsatisfiedDependencies(task);

    const combined =
      unique([
        ...explicit,
        ...unsatisfied
      ]);

    return `
      ${relationSection(
        "REPRESENTED BLOCKING FIELD",
        combined,
        "blocking",
        "No blocker or unsatisfied dependency is represented."
      )}

      <div
        class="niche-causal-lens-facts"
      >
        <div
          class="niche-causal-lens-fact-row"
          data-represented="true"
        >
          <span
            class="niche-causal-lens-fact-label"
          >
            explicit blockers
          </span>

          <span
            class="niche-causal-lens-fact-value"
          >
            ${explicit.length}
          </span>
        </div>

        <div
          class="niche-causal-lens-fact-row"
          data-represented="true"
        >
          <span
            class="niche-causal-lens-fact-label"
          >
            unsatisfied dependencies
          </span>

          <span
            class="niche-causal-lens-fact-value"
          >
            ${unsatisfied.length}
          </span>
        </div>
      </div>

      <div
        class="niche-causal-lens-boundary"
      >
        Blocker Lens reports represented
        blockers and unsatisfied
        dependencies only. It does not
        infer severity, duration,
        probability, ownership, or priority.
      </div>
    `;
  };

  const render = () => {
    const body =
      document.getElementById(
        "niche-causal-lens-body"
      );

    const title =
      document.getElementById(
        "niche-causal-lens-task"
      );

    if (!body) {
      return;
    }

    const task =
      runtime.task;

    if (!task) {
      if (title) {
        title.textContent =
          "NO TASK RESOLVED";
      }

      body.innerHTML = empty(
        "The selected task is unavailable. Causal Lens will not reconstruct missing relationships."
      );

      return;
    }

    const id =
      taskId(task) ||
      runtime.taskId ||
      "unknown";

    if (title) {
      title.textContent =
        `${id} · ${
          taskTitle(task) ||
          "untitled"
        }`;
    }

    document
      .querySelectorAll(
        "[data-causal-lens-mode]"
      )
      .forEach(button => {
        button.setAttribute(
          "aria-pressed",
          button.dataset
            .causalLensMode ===
            runtime.lens
            ? "true"
            : "false"
        );
      });

    if (
      runtime.lens === "authority"
    ) {
      body.innerHTML =
        renderAuthority(task);
      return;
    }

    if (
      runtime.lens === "unlock"
    ) {
      body.innerHTML =
        renderUnlock(task);
      return;
    }

    if (
      runtime.lens === "blocker"
    ) {
      body.innerHTML =
        renderBlocker(task);
      return;
    }

    body.innerHTML =
      renderCausal(task);
  };

  const ensureShell = () => {
    if (
      document.getElementById(
        "niche-causal-lens"
      )
    ) {
      return;
    }

    const shell =
      document.createElement("aside");

    shell.id =
      "niche-causal-lens";

    shell.className =
      "niche-causal-lens";

    shell.hidden = true;

    shell.setAttribute(
      "aria-label",
      "Causal Lens"
    );

    shell.innerHTML = `
      <header
        class="niche-causal-lens-head"
      >
        <div>
          <p
            class="niche-causal-lens-kicker"
          >
            causal neighborhood /
            deterministic projection
          </p>

          <h2
            class="niche-causal-lens-title"
          >
            CAUSAL LENS
          </h2>

          <p
            class="niche-causal-lens-task"
            id="niche-causal-lens-task"
          ></p>
        </div>

        <button
          type="button"
          class="niche-causal-lens-close"
          aria-label="Close Causal Lens"
        >
          ×
        </button>
      </header>

      <nav
        class="niche-causal-lens-modes"
        aria-label="Causal Lens modes"
      >
        <button
          type="button"
          data-causal-lens-mode="causal"
          aria-pressed="true"
        >
          causal
        </button>

        <button
          type="button"
          data-causal-lens-mode="authority"
          aria-pressed="false"
        >
          authority
        </button>

        <button
          type="button"
          data-causal-lens-mode="unlock"
          aria-pressed="false"
        >
          unlock
        </button>

        <button
          type="button"
          data-causal-lens-mode="blocker"
          aria-pressed="false"
        >
          blocker
        </button>
      </nav>

      <div
        class="niche-causal-lens-body"
        id="niche-causal-lens-body"
      ></div>
    `;

    document.body.append(shell);

    shell
      .querySelector(
        ".niche-causal-lens-close"
      )
      ?.addEventListener(
        "click",
        close
      );

    shell
      .querySelector(
        ".niche-causal-lens-modes"
      )
      ?.addEventListener(
        "click",
        event => {
          const button =
            event.target.closest(
              "[data-causal-lens-mode]"
            );

          if (!button) {
            return;
          }

          runtime.lens =
            button.dataset
              .causalLensMode;

          render();
        }
      );

    shell.addEventListener(
      "click",
      event => {
        const node =
          event.target.closest(
            "[data-causal-lens-task]"
          );

        if (!node) {
          return;
        }

        const id =
          node.dataset
            .causalLensTask;

        void open(id);

        const existing =
          [...document.querySelectorAll(
            "[data-task-id]"
          )].find(
            candidate =>
              candidate.dataset
                .taskId === id
          );

        if (existing) {
          existing.click();
        }

        window
          .NicheCrossViewContinuity
          ?.select?.(id);
      }
    );
  };

  const refresh = async id => {
    const resolved =
      id ||
      currentTaskId();

    runtime.taskId =
      resolved;

    if (!resolved) {
      runtime.task = null;
      runtime.related.clear();
      render();
      return false;
    }

    const context =
      await fetchContext(
        resolved
      );

    if (!context) {
      runtime.task = null;
      runtime.related.clear();
      render();
      return false;
    }

    runtime.task =
      context.focal;

    runtime.related =
      context.related;

    render();

    return true;
  };

  const open = async (
    id,
    lens = null
  ) => {
    ensureShell();

    if (
      typeof lens === "string" &&
      [
        "causal",
        "authority",
        "unlock",
        "blocker"
      ].includes(lens)
    ) {
      runtime.lens = lens;
    }

    const shell =
      document.getElementById(
        "niche-causal-lens"
      );

    if (!shell) {
      return;
    }

    runtime.previousFocus =
      document.activeElement;

    runtime.open = true;
    shell.hidden = false;

    await refresh(id);

    shell
      .querySelector(
        ".niche-causal-lens-close"
      )
      ?.focus();
  };

  const close = () => {
    runtime.open = false;

    runtime.controller?.abort();

    const shell =
      document.getElementById(
        "niche-causal-lens"
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
              "[data-action='causal-lens']",
              "[data-command='causal-lens']",
              "[data-causal-lens]"
            ].join(",")
          );

        if (!trigger) {
          return;
        }

        const node =
          trigger.closest(
            "[data-task-id]"
          );

        void open(
          node?.dataset?.taskId ||
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
            "c"
        ) {
          event.preventDefault();
          void open();
        }
      }
    );
  };

  const bindRuntime = () => {
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

    window.addEventListener(
      "niche:continuity-selection",
      event => {
        const id =
          event.detail?.taskId;

        if (
          runtime.open &&
          id &&
          id !== runtime.taskId
        ) {
          void refresh(id);
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
    bindRuntime();

    document.documentElement.dataset
      .nicheCausalLens =
      "ready";

    window.dispatchEvent(
      new CustomEvent(
        "niche:causal-lens-ready",
        {
          detail: {
            schema: SCHEMA,
            lenses: [
              "causal",
              "authority",
              "unlock",
              "blocker"
            ],
            authorityEffect: "none",
            projectionOnly: true
          }
        }
      )
    );
  };

  window.NicheCausalLens =
    Object.freeze({
      open,
      close,
      refresh,

      setLens: lens => {
        if (
          ![
            "causal",
            "authority",
            "unlock",
            "blocker"
          ].includes(lens)
        ) {
          return false;
        }

        runtime.lens = lens;
        render();

        return true;
      },

      state: () => ({
        schema: SCHEMA,
        open: runtime.open,
        taskId: runtime.taskId,
        lens: runtime.lens,
        relatedTaskCount:
          runtime.related.size,
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
