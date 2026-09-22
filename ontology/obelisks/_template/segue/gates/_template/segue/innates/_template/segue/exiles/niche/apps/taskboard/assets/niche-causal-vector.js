(() => {
  "use strict";

  const SCHEMA =
    "savant.niche.causal-vector.v1";

  const runtime = {
    initialized: false,
    open: false,
    taskId: null,
    focal: null,
    incoming: new Map(),
    outgoing: new Map(),
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

      if (
        typeof id === "string" &&
        id
      ) {
        return id;
      }
    }

    return null;
  };

  const idsOf = values =>
    [...new Set(
      array(values)
        .map(idOf)
        .filter(Boolean)
    )];

  const incomingIds = task =>
    [...new Set([
      ...idsOf(task?.dependencies),
      ...idsOf(
        task?.unsatisfied_dependencies
      ),
      ...idsOf(task?.blockers)
    ])];

  const outgoingIds = task =>
    idsOf(task?.dependents);

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
      generation !== runtime.generation ||
      !focal
    ) {
      return null;
    }

    const incoming =
      incomingIds(focal)
        .filter(
          relatedId =>
            relatedId !== id
        );

    const outgoing =
      outgoingIds(focal)
        .filter(
          relatedId =>
            relatedId !== id
        );

    const relatedIds =
      [...new Set([
        ...incoming,
        ...outgoing
      ])];

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

    const resolved =
      new Map(pairs);

    const incomingMap =
      new Map(
        incoming.map(
          relatedId => [
            relatedId,
            resolved.get(relatedId) ||
              null
          ]
        )
      );

    const outgoingMap =
      new Map(
        outgoing.map(
          relatedId => [
            relatedId,
            resolved.get(relatedId) ||
              null
          ]
        )
      );

    if (
      runtime.controller === controller
    ) {
      runtime.controller = null;
    }

    return {
      focal,
      incoming: incomingMap,
      outgoing: outgoingMap
    };
  };

  const node = (
    id,
    task,
    direction
  ) => `
    <button
      type="button"
      class="niche-causal-vector-node"
      data-causal-vector-task="${
        escapeHtml(id)
      }"
      data-causal-vector-direction="${
        escapeHtml(direction)
      }"
    >
      <span
        class="niche-causal-vector-node-id"
      >
        ${escapeHtml(id)}
      </span>

      <span
        class="niche-causal-vector-node-title"
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

  const column = (
    label,
    zone,
    values,
    emptyMessage
  ) => `
    <section
      class="niche-causal-vector-column"
      data-vector-zone="${
        escapeHtml(zone)
      }"
    >
      <header
        class="
          niche-causal-vector-column-head
        "
      >
        ${escapeHtml(label)}
      </header>

      <div
        class="niche-causal-vector-list"
      >
        ${
          values.size
            ? [...values.entries()]
                .map(
                  ([id, task]) =>
                    node(
                      id,
                      task,
                      zone
                    )
                )
                .join("")
            : `
              <div
                class="niche-causal-vector-empty"
              >
                ${escapeHtml(emptyMessage)}
              </div>
            `
        }
      </div>
    </section>
  `;

  const render = () => {
    const body =
      document.getElementById(
        "niche-causal-vector-body"
      );

    if (!body) {
      return;
    }

    if (!runtime.focal) {
      body.innerHTML = `
        <div
          class="niche-causal-vector-empty"
        >
          No focal task is resolved. No
          relationship direction is inferred.
        </div>
      `;

      return;
    }

    const originId =
      idOf(runtime.focal) ||
      runtime.taskId ||
      "unknown";

    const origin =
      new Map([
        [
          originId,
          runtime.focal
        ]
      ]);

    body.innerHTML = `
      <div
        class="niche-causal-vector-summary"
      >
        <span
          class="niche-causal-vector-chip"
        >
          origin:${escapeHtml(originId)}
        </span>

        <span
          class="niche-causal-vector-chip"
        >
          incoming:${runtime.incoming.size}
        </span>

        <span
          class="niche-causal-vector-chip"
        >
          outgoing:${runtime.outgoing.size}
        </span>

        <span
          class="niche-causal-vector-chip"
        >
          direction:dependency
        </span>
      </div>

      <div
        class="niche-causal-vector-stage"
      >
        ${column(
          "INCOMING CAUSAL RELATIONS",
          "incoming",
          runtime.incoming,
          "No dependency, unsatisfied dependency, or blocker is represented."
        )}

        <div
          class="niche-causal-vector-arrow"
          aria-hidden="true"
        >
          ──▶
        </div>

        ${column(
          "FOCAL TASK",
          "origin",
          origin,
          "No focal task is represented."
        )}

        <div
          class="niche-causal-vector-arrow"
          aria-hidden="true"
        >
          ──▶
        </div>

        ${column(
          "OUTGOING CAUSAL RELATIONS",
          "outgoing",
          runtime.outgoing,
          "No direct dependent is represented."
        )}
      </div>

      <div
        class="niche-causal-vector-note"
      >
        Vector direction represents only the
        dependency orientation exposed by
        the task projection: prerequisite or
        blocker toward focal task, then focal
        task toward represented dependent.
        It does not establish chronology,
        priority, execution order, authority,
        certainty, duration, or causation
        beyond the represented relationship.
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
      runtime.incoming.clear();
      runtime.outgoing.clear();
      render();
      return false;
    }

    const result =
      await resolve(resolvedId);

    if (!result) {
      runtime.focal = null;
      runtime.incoming.clear();
      runtime.outgoing.clear();
      render();
      return false;
    }

    runtime.focal =
      result.focal;

    runtime.incoming =
      result.incoming;

    runtime.outgoing =
      result.outgoing;

    render();

    window.dispatchEvent(
      new CustomEvent(
        "niche:causal-vector-update",
        {
          detail: {
            schema: SCHEMA,
            taskId: resolvedId,
            incomingCount:
              runtime.incoming.size,
            outgoingCount:
              runtime.outgoing.size,
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
        "niche-causal-vector"
      )
    ) {
      return;
    }

    const shell =
      document.createElement("aside");

    shell.id =
      "niche-causal-vector";

    shell.className =
      "niche-causal-vector";

    shell.hidden = true;

    shell.setAttribute(
      "aria-label",
      "Causal Vector"
    );

    shell.innerHTML = `
      <header
        class="niche-causal-vector-head"
      >
        <div>
          <p
            class="niche-causal-vector-kicker"
          >
            direction / represented topology
          </p>

          <h2
            class="niche-causal-vector-title"
          >
            CAUSAL VECTOR
          </h2>
        </div>

        <button
          type="button"
          class="niche-causal-vector-close"
          aria-label="Close Causal Vector"
        >
          ×
        </button>
      </header>

      <div
        class="niche-causal-vector-body"
        id="niche-causal-vector-body"
      ></div>
    `;

    document.body.append(shell);

    shell
      .querySelector(
        ".niche-causal-vector-close"
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
            "[data-causal-vector-task]"
          );

        if (!button) {
          return;
        }

        const id =
          button.dataset
            .causalVectorTask;

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
        "niche-causal-vector"
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
        ".niche-causal-vector-close"
      )
      ?.focus();
  };

  const close = () => {
    runtime.open = false;

    runtime.controller?.abort();

    const shell =
      document.getElementById(
        "niche-causal-vector"
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
              "[data-action='causal-vector']",
              "[data-command='causal-vector']",
              "[data-causal-vector]"
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
      .nicheCausalVector =
      "ready";

    window.dispatchEvent(
      new CustomEvent(
        "niche:causal-vector-ready",
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

  window.NicheCausalVector =
    Object.freeze({
      open,
      close,
      refresh,

      state: () => ({
        schema: SCHEMA,
        open: runtime.open,
        taskId: runtime.taskId,
        incomingCount:
          runtime.incoming.size,
        outgoingCount:
          runtime.outgoing.size,
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
