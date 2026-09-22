(() => {
  "use strict";

  const SCHEMA =
    "savant.niche.causal-lens.v1";

  const runtime = {
    initialized: false,
    open: false,
    mode: "causal",
    taskId: null,
    focal: null,
    related: new Map(),
    generation: 0,
    controller: null,
    previousFocus: null
  };

  const array = value =>
    Array.isArray(value) ? value : [];

  const represented = value =>
    value !== null &&
    value !== undefined &&
    value !== "";

  const first = (object, keys) => {
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

  const idOf = value => {
    if (
      typeof value === "string" &&
      value
    ) {
      return value;
    }

    if (
      value &&
      typeof value === "object"
    ) {
      const id =
        first(
          value,
          ["task_id", "taskId", "id"]
        );

      return (
        typeof id === "string" &&
        id
          ? id
          : null
      );
    }

    return null;
  };

  const idsOf = values =>
    [...new Set(
      array(values)
        .map(idOf)
        .filter(Boolean)
    )];

  const escapeHtml = value =>
    String(
      value === null ||
      value === undefined
        ? ""
        : value
    )
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");

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
      state.selectedTaskId ||
      runtime.taskId ||
      state.recommendedTaskId ||
      null
    );
  };

  const fetchTask = async (
    id,
    controller
  ) => {
    if (!id) {
      return null;
    }

    try {
      const response =
        await fetch(
          `/api/tasks/${
            encodeURIComponent(id)
          }`,
          {
            signal: controller.signal,
            cache: "no-store",
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
      if (
        error?.name === "AbortError"
      ) {
        return null;
      }

      return null;
    }
  };

  const relationIds = task =>
    [...new Set([
      ...idsOf(task?.dependencies),
      ...idsOf(
        task?.unsatisfied_dependencies
      ),
      ...idsOf(task?.blockers),
      ...idsOf(task?.dependents)
    ])];

  const resolveContext = async id => {
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
      generation !== runtime.generation ||
      !focal
    ) {
      return null;
    }

    const relatedIds =
      relationIds(focal)
        .filter(
          relatedId =>
            relatedId !== id
        );

    const pairs =
      await Promise.all(
        relatedIds.map(
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
      generation !== runtime.generation
    ) {
      return null;
    }

    if (
      runtime.controller === controller
    ) {
      runtime.controller = null;
    }

    return {
      focal,
      related:
        new Map(pairs)
    };
  };

  const taskLink = id => {
    const task =
      runtime.related.get(id);

    const title =
      first(
        task,
        ["title", "name", "purpose"]
      );

    return `
      <button
        type="button"
        class="niche-causal-lens-task"
        data-causal-lens-task="${
          escapeHtml(id)
        }"
      >
        <span>
          ${escapeHtml(id)}
        </span>
        <small>
          ${escapeHtml(
            title ||
            (
              task
                ? "title not projected"
                : "task unavailable"
            )
          )}
        </small>
      </button>
    `;
  };

  const relationSection = (
    label,
    ids,
    empty
  ) => `
    <section
      class="niche-causal-lens-section"
    >
      <header>
        <span>${escapeHtml(label)}</span>
        <span>${ids.length}</span>
      </header>

      <div
        class="niche-causal-lens-list"
      >
        ${
          ids.length
            ? ids
                .map(taskLink)
                .join("")
            : `
              <div
                class="niche-causal-lens-empty"
              >
                ${escapeHtml(empty)}
              </div>
            `
        }
      </div>
    </section>
  `;

  const fact = (
    label,
    value
  ) => `
    <div
      class="niche-causal-lens-fact"
    >
      <span>${escapeHtml(label)}</span>
      <strong>
        ${escapeHtml(
          represented(value)
            ? (
                typeof value === "object"
                  ? JSON.stringify(value)
                  : value
              )
            : "not projected"
        )}
      </strong>
    </div>
  `;

  const renderCausal = task => {
    const dependencies =
      idsOf(task.dependencies);

    const unsatisfied =
      idsOf(
        task.unsatisfied_dependencies
      );

    const blockers =
      idsOf(task.blockers);

    const dependents =
      idsOf(task.dependents);

    const constraints =
      first(
        task,
        [
          "constraints",
          "constraint",
          "conditions",
          "preconditions"
        ]
      );

    return `
      ${relationSection(
        "DIRECT PREREQUISITES",
        dependencies,
        "No direct prerequisite is represented."
      )}

      ${relationSection(
        "UNSATISFIED PREREQUISITES",
        unsatisfied,
        "No unsatisfied prerequisite is represented."
      )}

      ${relationSection(
        "BLOCKERS",
        blockers,
        "No blocker is represented."
      )}

      ${fact(
        "explicit constraints",
        constraints
      )}

      ${relationSection(
        "DIRECT CONSEQUENCES",
        dependents,
        "No direct dependent is represented."
      )}

      <div
        class="niche-causal-lens-boundary"
      >
        Only represented direct relationships
        are asserted in causal mode. Missing
        relationships remain unknown.
      </div>
    `;
  };

  const renderAuthority = task => `
    ${fact(
      "owner",
      first(
        task,
        [
          "authority_owner",
          "owner"
        ]
      )
    )}

    ${fact(
      "authority effect",
      first(
        task,
        [
          "authority_effect",
          "authorityEffect"
        ]
      )
    )}

    ${fact(
      "classification",
      first(
        task,
        [
          "authority_classification",
          "authority",
          "classification"
        ]
      )
    )}

    ${fact(
      "basis",
      first(
        task,
        [
          "authority_basis",
          "basis"
        ]
      )
    )}

    ${fact(
      "provenance",
      first(
        task,
        ["provenance", "source"]
      )
    )}

    ${fact(
      "lineage",
      first(
        task,
        ["lineage"]
      )
    )}

    ${fact(
      "supersedes",
      first(
        task,
        ["supersedes"]
      )
    )}

    ${fact(
      "superseded by",
      first(
        task,
        [
          "superseded_by",
          "supersededBy"
        ]
      )
    )}

    <div
      class="niche-causal-lens-boundary"
    >
      Missing authority fields are not
      projected. Causal position, filesystem
      location, visual prominence, priority,
      and readiness do not establish
      authority.
    </div>
  `;

  const renderUnlock = task => {
    const direct =
      idsOf(task.dependents);

    const second =
      [...new Set(
        direct.flatMap(id => {
          const related =
            runtime.related.get(id);

          return related
            ? idsOf(
                related.dependents
              )
            : [];
        })
      )]
        .filter(
          id =>
            id !== runtime.taskId &&
            !direct.includes(id)
        );

    return `
      ${relationSection(
        "DIRECT UNLOCK NEIGHBORHOOD",
        direct,
        "No direct dependent is represented."
      )}

      ${relationSection(
        "SECOND-ORDER VISIBLE",
        second,
        "No second-order dependent is derivable from the resolved direct neighborhood."
      )}

      <div
        class="niche-causal-lens-boundary"
      >
        Second-order visibility is a bounded
        graph projection, not a complete
        transitive closure and not a claim
        that those tasks will become ready.
      </div>
    `;
  };

  const renderBlocker = task => {
    const blockers =
      idsOf(task.blockers);

    const unsatisfied =
      idsOf(
        task.unsatisfied_dependencies
      );

    return `
      ${relationSection(
        "REPRESENTED BLOCKERS",
        blockers,
        "No blocker is represented."
      )}

      ${relationSection(
        "UNSATISFIED DEPENDENCIES",
        unsatisfied,
        "No unsatisfied dependency is represented."
      )}

      <div
        class="niche-causal-lens-boundary"
      >
        Blocker mode does not infer severity,
        duration, probability, ownership,
        priority, or resolution method.
      </div>
    `;
  };

  const render = () => {
    const body =
      document.getElementById(
        "niche-causal-lens-body"
      );

    if (!body) {
      return;
    }

    if (!runtime.focal) {
      body.innerHTML = `
        <div
          class="niche-causal-lens-empty"
        >
          Task context is unavailable. No
          causal structure has been inferred.
        </div>
      `;

      return;
    }

    const content =
      runtime.mode === "authority"
        ? renderAuthority(
            runtime.focal
          )
        : runtime.mode === "unlock"
          ? renderUnlock(
              runtime.focal
            )
          : runtime.mode === "blocker"
            ? renderBlocker(
                runtime.focal
              )
            : renderCausal(
                runtime.focal
              );

    body.innerHTML = content;

    document
      .querySelectorAll(
        "[data-causal-lens-mode]"
      )
      .forEach(button => {
        button.setAttribute(
          "aria-pressed",
          String(
            button.dataset
              .causalLensMode ===
              runtime.mode
          )
        );
      });
  };

  const refresh = async id => {
    const resolved =
      id ||
      currentTaskId();

    runtime.taskId =
      resolved;

    if (!resolved) {
      runtime.focal = null;
      runtime.related.clear();
      render();
      return false;
    }

    const result =
      await resolveContext(
        resolved
      );

    if (!result) {
      runtime.focal = null;
      runtime.related.clear();
      render();
      return false;
    }

    runtime.focal =
      result.focal;

    runtime.related =
      result.related;

    render();

    return true;
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
            neighborhood / interpretation
          </p>

          <h2
            class="niche-causal-lens-title"
          >
            CAUSAL LENS
          </h2>
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
        aria-label="Causal Lens mode"
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

    shell.addEventListener(
      "click",
      event => {
        const mode =
          event.target.closest(
            "[data-causal-lens-mode]"
          );

        if (mode) {
          runtime.mode =
            mode.dataset
              .causalLensMode;

          render();
          return;
        }

        const task =
          event.target.closest(
            "[data-causal-lens-task]"
          );

        if (!task) {
          return;
        }

        const id =
          task.dataset
            .causalLensTask;

        window
          .NicheCrossViewContinuity
          ?.select?.(id);

        const existing =
          [...document.querySelectorAll(
            "[data-task-id]"
          )].find(
            node =>
              node.dataset.taskId === id
          );

        existing?.click();

        void refresh(id);
      }
    );
  };

  const open = async (
    id,
    mode = "causal"
  ) => {
    ensureShell();

    const shell =
      document.getElementById(
        "niche-causal-lens"
      );

    if (!shell) {
      return;
    }

    runtime.previousFocus =
      document.activeElement;

    runtime.mode =
      [
        "causal",
        "authority",
        "unlock",
        "blocker"
      ].includes(mode)
        ? mode
        : "causal";

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

        const taskNode =
          trigger.closest(
            "[data-task-id]"
          );

        void open(
          taskNode?.dataset?.taskId ||
          currentTaskId(),
          trigger.dataset
            .causalLensMode ||
            "causal"
        );
      },
      true
    );

    document.addEventListener(
      "keydown",
      event => {
        if (
          event.altKey &&
          event.shiftKey &&
          !event.ctrlKey &&
          !event.metaKey &&
          event.key.toLowerCase() === "c"
        ) {
          event.preventDefault();
          void open();
          return;
        }

        if (
          event.key === "Escape" &&
          runtime.open
        ) {
          close();
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
            currentTaskId()
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
            shortcut:
              "alt+shift+c",
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

      state: () => ({
        schema: SCHEMA,
        open: runtime.open,
        mode: runtime.mode,
        taskId: runtime.taskId,
        relatedCount:
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
