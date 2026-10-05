(() => {
  "use strict";

  const SCHEMA =
    "savant.niche.constraint-field.v1";

  const runtime = {
    initialized: false,
    open: false,
    taskId: null,
    focal: null,
    blockers: new Map(),
    unsatisfied: new Map(),
    explicit: [],
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

  const titleOf = task =>
    first(
      task,
      ["title", "name", "purpose"]
    );

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
      runtime.taskId ||
      state.selectedTaskId ||
      state.recommendedTaskId ||
      null
    );
  };

  const explicitConstraints = task => {
    const result = [];

    const append = (
      source,
      value
    ) => {
      if (!represented(value)) {
        return;
      }

      if (Array.isArray(value)) {
        value.forEach(item =>
          append(source, item)
        );
        return;
      }

      if (
        value &&
        typeof value === "object"
      ) {
        try {
          result.push({
            source,
            value:
              JSON.stringify(value)
          });
        } catch {
          result.push({
            source,
            value:
              "represented object"
          });
        }

        return;
      }

      result.push({
        source,
        value: String(value)
      });
    };

    [
      "constraints",
      "constraint",
      "conditions",
      "preconditions"
    ].forEach(key => {
      if (
        Object.prototype.hasOwnProperty.call(
          task || {},
          key
        )
      ) {
        append(
          key,
          task[key]
        );
      }
    });

    return result;
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

      const payload =
        await response.json();

      return (
        payload?.task ||
        payload
      );
    } catch (error) {
      if (
        error?.name === "AbortError"
      ) {
        return null;
      }

      return null;
    }
  };

  const resolve = async id => {
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

    const blockerIds =
      idsOf(focal.blockers);

    const unsatisfiedIds =
      idsOf(
        focal.unsatisfied_dependencies
      );

    const relatedIds =
      [...new Set([
        ...blockerIds,
        ...unsatisfiedIds
      ])].filter(
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
      generation !==
      runtime.generation
    ) {
      return null;
    }

    const resolved =
      new Map(pairs);

    const blockers =
      new Map(
        blockerIds.map(
          relatedId => [
            relatedId,
            resolved.get(
              relatedId
            ) || null
          ]
        )
      );

    const unsatisfied =
      new Map(
        unsatisfiedIds.map(
          relatedId => [
            relatedId,
            resolved.get(
              relatedId
            ) || null
          ]
        )
      );

    if (
      runtime.controller ===
      controller
    ) {
      runtime.controller = null;
    }

    return {
      focal,
      blockers,
      unsatisfied,
      explicit:
        explicitConstraints(focal)
    };
  };

  const taskNode = (
    id,
    task
  ) => `
    <button
      type="button"
      class="niche-constraint-field-node"
      data-constraint-task="${
        escapeHtml(id)
      }"
    >
      <span
        class="niche-constraint-field-node-id"
      >
        ${escapeHtml(id)}
      </span>

      <span
        class="niche-constraint-field-node-title"
      >
        ${escapeHtml(
          titleOf(task) ||
          (
            task
              ? "title not projected"
              : "task payload unavailable"
          )
        )}
      </span>
    </button>
  `;

  const relationSection = (
    label,
    kind,
    values,
    emptyMessage
  ) => `
    <section
      class="niche-constraint-field-section"
      data-kind="${escapeHtml(kind)}"
    >
      <header
        class="
          niche-constraint-field-section-head
        "
      >
        <span>${escapeHtml(label)}</span>
        <span>${values.size}</span>
      </header>

      <div
        class="niche-constraint-field-list"
      >
        ${
          values.size
            ? [...values.entries()]
                .map(
                  ([id, task]) =>
                    taskNode(
                      id,
                      task
                    )
                )
                .join("")
            : `
              <div
                class="
                  niche-constraint-field-empty
                "
              >
                ${escapeHtml(emptyMessage)}
              </div>
            `
        }
      </div>
    </section>
  `;

  const explicitSection = () => `
    <section
      class="niche-constraint-field-section"
      data-kind="explicit"
    >
      <header
        class="
          niche-constraint-field-section-head
        "
      >
        <span>EXPLICIT CONSTRAINT FIELDS</span>
        <span>${runtime.explicit.length}</span>
      </header>

      <div
        class="niche-constraint-field-list"
      >
        ${
          runtime.explicit.length
            ? runtime.explicit
                .map(
                  item => `
                    <div
                      class="
                        niche-constraint-field-fact
                      "
                    >
                      <strong>
                        ${escapeHtml(item.source)}
                      </strong>
                      <br>
                      ${escapeHtml(item.value)}
                    </div>
                  `
                )
                .join("")
            : `
              <div
                class="
                  niche-constraint-field-empty
                "
              >
                No explicit constraint,
                condition, or precondition
                field is represented.
              </div>
            `
        }
      </div>
    </section>
  `;

  const render = () => {
    const body =
      document.getElementById(
        "niche-constraint-field-body"
      );

    if (!body) {
      return;
    }

    if (!runtime.focal) {
      body.innerHTML = `
        <div
          class="niche-constraint-field-empty"
        >
          No focal task is resolved.
          Constraint state is unavailable
          and has not been reconstructed.
        </div>
      `;

      return;
    }

    const id =
      idOf(runtime.focal) ||
      runtime.taskId ||
      "unknown";

    body.innerHTML = `
      <div
        class="niche-constraint-field-summary"
      >
        <span
          class="niche-constraint-field-chip"
        >
          origin:${escapeHtml(id)}
        </span>

        <span
          class="niche-constraint-field-chip"
        >
          blockers:${runtime.blockers.size}
        </span>

        <span
          class="niche-constraint-field-chip"
        >
          unsatisfied:${
            runtime.unsatisfied.size
          }
        </span>

        <span
          class="niche-constraint-field-chip"
        >
          explicit:${runtime.explicit.length}
        </span>
      </div>

      <div
        class="niche-constraint-field-sections"
      >
        ${relationSection(
          "EXPLICIT BLOCKERS",
          "blocker",
          runtime.blockers,
          "No explicit blocker is represented."
        )}

        ${relationSection(
          "UNSATISFIED DEPENDENCIES",
          "unsatisfied",
          runtime.unsatisfied,
          "No unsatisfied dependency is represented."
        )}

        ${explicitSection()}

        <section
          class="niche-constraint-field-section"
          data-kind="boundary"
        >
          <header
            class="
              niche-constraint-field-section-head
            "
          >
            <span>UNKNOWN CONSTRAINT SPACE</span>
            <span>not inferred</span>
          </header>

          <div
            class="niche-constraint-field-list"
          >
            <div
              class="
                niche-constraint-field-empty
              "
            >
              Constraints not represented by
              the task payload remain
              unknown. This instrument does
              not derive hidden constraints
              from state, priority, topology,
              timing, visual placement, or
              missing evidence.
            </div>
          </div>
        </section>
      </div>

      <div
        class="niche-constraint-field-note"
      >
        Constraint Field is a read-only
        projection. A represented blocker,
        unsatisfied dependency, condition,
        or precondition is displayed as
        source-derived task data. Its
        severity, duration, probability,
        authority, ownership, and resolution
        method remain unknown unless those
        properties are explicitly projected.
      </div>
    `;
  };

  const refresh = async id => {
    const resolvedId =
      id ||
      currentTaskId();

    runtime.taskId =
      resolvedId;

    if (!resolvedId) {
      runtime.focal = null;
      runtime.blockers.clear();
      runtime.unsatisfied.clear();
      runtime.explicit = [];
      render();
      return false;
    }

    const result =
      await resolve(resolvedId);

    if (!result) {
      runtime.focal = null;
      runtime.blockers.clear();
      runtime.unsatisfied.clear();
      runtime.explicit = [];
      render();
      return false;
    }

    runtime.focal =
      result.focal;

    runtime.blockers =
      result.blockers;

    runtime.unsatisfied =
      result.unsatisfied;

    runtime.explicit =
      result.explicit;

    render();

    window.dispatchEvent(
      new CustomEvent(
        "niche:constraint-field-update",
        {
          detail: {
            schema: SCHEMA,
            taskId: resolvedId,
            blockerCount:
              runtime.blockers.size,
            unsatisfiedDependencyCount:
              runtime.unsatisfied.size,
            explicitConstraintCount:
              runtime.explicit.length,
            authorityEffect: "none",
            projectionOnly: true
          }
        }
      )
    );

    return true;
  };

  const ensureShell = () => {
    if (
      document.getElementById(
        "niche-constraint-field"
      )
    ) {
      return;
    }

    const shell =
      document.createElement("aside");

    shell.id =
      "niche-constraint-field";

    shell.className =
      "niche-constraint-field";

    shell.hidden = true;

    shell.setAttribute(
      "aria-label",
      "Constraint Field"
    );

    shell.innerHTML = `
      <header
        class="niche-constraint-field-head"
      >
        <div>
          <p
            class="
              niche-constraint-field-kicker
            "
          >
            blockers / conditions /
            prerequisites
          </p>

          <h2
            class="
              niche-constraint-field-title
            "
          >
            CONSTRAINT FIELD
          </h2>
        </div>

        <button
          type="button"
          class="
            niche-constraint-field-close
          "
          aria-label="
            Close Constraint Field
          "
        >
          ×
        </button>
      </header>

      <div
        class="
          niche-constraint-field-body
        "
        id="
          niche-constraint-field-body
        "
      ></div>
    `;

    document.body.append(shell);

    shell
      .querySelector(
        ".niche-constraint-field-close"
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
            "[data-constraint-task]"
          );

        if (!button) {
          return;
        }

        const id =
          button.dataset
            .constraintTask;

        window
          .NicheCrossViewContinuity
          ?.select?.(id);

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

        void refresh(id);
      }
    );
  };

  const open = async id => {
    ensureShell();

    const shell =
      document.getElementById(
        "niche-constraint-field"
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
        ".niche-constraint-field-close"
      )
      ?.focus();
  };

  const close = () => {
    runtime.open = false;

    runtime.controller?.abort();

    const shell =
      document.getElementById(
        "niche-constraint-field"
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
              "[data-action='constraint-field']",
              "[data-command='constraint-field']",
              "[data-constraint-field]"
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
    bindRuntime();

    document.documentElement.dataset
      .nicheConstraintField =
      "ready";

    window.dispatchEvent(
      new CustomEvent(
        "niche:constraint-field-ready",
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

  window.NicheConstraintField =
    Object.freeze({
      open,
      close,
      refresh,

      state: () => ({
        schema: SCHEMA,
        open: runtime.open,
        taskId: runtime.taskId,
        blockerCount:
          runtime.blockers.size,
        unsatisfiedDependencyCount:
          runtime.unsatisfied.size,
        explicitConstraintCount:
          runtime.explicit.length,
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
