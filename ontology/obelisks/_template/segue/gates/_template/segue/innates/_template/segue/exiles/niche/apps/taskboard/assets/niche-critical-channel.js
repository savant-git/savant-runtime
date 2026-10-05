(() => {
  "use strict";

  const SCHEMA =
    "savant.niche.critical-channel.v1";

  const runtime = {
    initialized: false,
    open: false,
    taskId: null,
    focal: null,
    upstream: new Map(),
    downstream: new Map(),
    generation: 0,
    controller: null,
    previousFocus: null
  };

  const array = value =>
    Array.isArray(value)
      ? value
      : [];

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

  const upstreamIds = task =>
    [...new Set([
      ...idsOf(task?.dependencies),
      ...idsOf(
        task?.unsatisfied_dependencies
      ),
      ...idsOf(task?.blockers)
    ])];

  const downstreamIds = task =>
    idsOf(task?.dependents);

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

    const upstream =
      upstreamIds(focal);

    const downstream =
      downstreamIds(focal);

    const relationIds =
      [...new Set([
        ...upstream,
        ...downstream
      ])].filter(
        relatedId =>
          relatedId !== id
      );

    const pairs =
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
      generation !== runtime.generation
    ) {
      return null;
    }

    const resolved =
      new Map(pairs);

    const upstreamMap =
      new Map(
        upstream.map(
          relatedId => [
            relatedId,
            resolved.get(relatedId) || null
          ]
        )
      );

    const downstreamMap =
      new Map(
        downstream.map(
          relatedId => [
            relatedId,
            resolved.get(relatedId) || null
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
      upstream: upstreamMap,
      downstream: downstreamMap
    };
  };

  const node = (
    id,
    task,
    relation
  ) => `
    <button
      type="button"
      class="niche-critical-channel-node"
      data-critical-channel-task="${
        escapeHtml(id)
      }"
      data-critical-channel-relation="${
        escapeHtml(relation)
      }"
    >
      <span
        class="niche-critical-channel-node-id"
      >
        ${escapeHtml(id)}
      </span>

      <span
        class="niche-critical-channel-node-title"
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

  const band = (
    label,
    key,
    values,
    emptyMessage
  ) => `
    <section
      class="niche-critical-channel-band"
      data-band="${escapeHtml(key)}"
    >
      <header
        class="niche-critical-channel-band-head"
      >
        <span>${escapeHtml(label)}</span>
        <span>${values.size}</span>
      </header>

      <div
        class="niche-critical-channel-list"
      >
        ${
          values.size
            ? [...values.entries()]
                .map(
                  ([id, task]) =>
                    node(
                      id,
                      task,
                      key
                    )
                )
                .join("")
            : `
              <div
                class="niche-critical-channel-empty"
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
        "niche-critical-channel-body"
      );

    if (!body) {
      return;
    }

    if (!runtime.focal) {
      body.innerHTML = `
        <div
          class="niche-critical-channel-empty"
        >
          No focal task is resolved. No
          critical channel is inferred.
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
        class="niche-critical-channel-summary"
      >
        <span
          class="niche-critical-channel-chip"
        >
          origin:${escapeHtml(originId)}
        </span>

        <span
          class="niche-critical-channel-chip"
        >
          upstream:${runtime.upstream.size}
        </span>

        <span
          class="niche-critical-channel-chip"
        >
          downstream:${runtime.downstream.size}
        </span>

        <span
          class="niche-critical-channel-chip"
        >
          basis:represented relations
        </span>
      </div>

      <div
        class="niche-critical-channel-bands"
      >
        ${band(
          "REPRESENTED UPSTREAM",
          "upstream",
          runtime.upstream,
          "No dependency, unsatisfied dependency, or blocker is represented."
        )}

        ${band(
          "FOCAL TASK",
          "origin",
          origin,
          "No focal task is represented."
        )}

        ${band(
          "REPRESENTED DOWNSTREAM",
          "downstream",
          runtime.downstream,
          "No direct dependent is represented."
        )}

        <section
          class="niche-critical-channel-band"
          data-band="boundary"
        >
          <header
            class="niche-critical-channel-band-head"
          >
            <span>CRITICALITY BOUNDARY</span>
            <span>unknown</span>
          </header>

          <div
            class="niche-critical-channel-list"
          >
            <div
              class="niche-critical-channel-empty"
            >
              This instrument does not
              calculate or invent a critical
              path. A task appears here
              because a represented direct
              causal relation connects it to
              the focal task.
            </div>
          </div>
        </section>
      </div>

      <div
        class="niche-critical-channel-note"
      >
        "Critical Channel" is a navigation
        projection over the represented
        local causal neighborhood. It does
        not assert scheduling criticality,
        priority, urgency, bottleneck status,
        duration, execution order, or
        authority unless a separate
        authoritative source explicitly
        projects such a claim.
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
      runtime.upstream.clear();
      runtime.downstream.clear();
      render();
      return false;
    }

    const result =
      await resolve(resolvedId);

    if (!result) {
      runtime.focal = null;
      runtime.upstream.clear();
      runtime.downstream.clear();
      render();
      return false;
    }

    runtime.focal =
      result.focal;

    runtime.upstream =
      result.upstream;

    runtime.downstream =
      result.downstream;

    render();

    window.dispatchEvent(
      new CustomEvent(
        "niche:critical-channel-update",
        {
          detail: {
            schema: SCHEMA,
            taskId: resolvedId,
            upstreamCount:
              runtime.upstream.size,
            downstreamCount:
              runtime.downstream.size,
            criticalPathAsserted: false,
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
        "niche-critical-channel"
      )
    ) {
      return;
    }

    const shell =
      document.createElement("aside");

    shell.id =
      "niche-critical-channel";

    shell.className =
      "niche-critical-channel";

    shell.hidden = true;

    shell.setAttribute(
      "aria-label",
      "Critical Channel"
    );

    shell.innerHTML = `
      <header
        class="niche-critical-channel-head"
      >
        <div>
          <p
            class="niche-critical-channel-kicker"
          >
            causal channel / local topology
          </p>

          <h2
            class="niche-critical-channel-title"
          >
            CRITICAL CHANNEL
          </h2>
        </div>

        <button
          type="button"
          class="niche-critical-channel-close"
          aria-label="Close Critical Channel"
        >
          ×
        </button>
      </header>

      <div
        class="niche-critical-channel-body"
        id="niche-critical-channel-body"
      ></div>
    `;

    document.body.append(shell);

    shell
      .querySelector(
        ".niche-critical-channel-close"
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
            "[data-critical-channel-task]"
          );

        if (!button) {
          return;
        }

        const id =
          button.dataset
            .criticalChannelTask;

        window
          .NicheCrossViewContinuity
          ?.select?.(id);

        const existing =
          [...document.querySelectorAll(
            "[data-task-id]"
          )].find(
            candidate =>
              candidate.dataset.taskId === id
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
        "niche-critical-channel"
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
        ".niche-critical-channel-close"
      )
      ?.focus();
  };

  const close = () => {
    runtime.open = false;

    runtime.controller?.abort();

    const shell =
      document.getElementById(
        "niche-critical-channel"
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
              "[data-action='critical-channel']",
              "[data-command='critical-channel']",
              "[data-critical-channel]"
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
      .nicheCriticalChannel =
      "ready";

    window.dispatchEvent(
      new CustomEvent(
        "niche:critical-channel-ready",
        {
          detail: {
            schema: SCHEMA,
            criticalPathAsserted: false,
            authorityEffect: "none",
            projectionOnly: true
          }
        }
      )
    );
  };

  window.NicheCriticalChannel =
    Object.freeze({
      open,
      close,
      refresh,

      state: () => ({
        schema: SCHEMA,
        open: runtime.open,
        taskId: runtime.taskId,
        upstreamCount:
          runtime.upstream.size,
        downstreamCount:
          runtime.downstream.size,
        criticalPathAsserted: false,
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
