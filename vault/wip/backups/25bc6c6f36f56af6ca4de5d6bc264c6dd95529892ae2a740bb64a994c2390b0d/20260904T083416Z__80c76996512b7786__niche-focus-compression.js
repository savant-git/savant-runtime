(() => {
  "use strict";

  const SCHEMA =
    "savant.niche.focus-compression.v1";

  const runtime = {
    initialized: false,
    active: false,
    taskId: null,
    task: null,
    generation: 0,
    controller: null
  };

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

  const currentTaskId = () => {
    const niche =
      window.Niche?.state?.();

    return (
      runtime.taskId ||
      niche?.selectedTaskId ||
      niche?.recommendedTaskId ||
      null
    );
  };

  const dependencies = task =>
    unique([
      ...array(task?.dependencies),
      ...array(
        task?.unsatisfied_dependencies
      ),
      ...array(task?.blockers)
    ]);

  const dependents = task =>
    unique(
      array(task?.dependents)
    );

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
            signal:
              controller.signal,
            cache: "no-store",
            headers: {
              Accept:
                "application/json"
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

  const ensureConsole = () => {
    if (
      document.getElementById(
        "niche-focus-console"
      )
    ) {
      return;
    }

    const consoleNode =
      document.createElement("section");

    consoleNode.id =
      "niche-focus-console";

    consoleNode.className =
      "niche-focus-console";

    consoleNode.hidden = true;

    consoleNode.setAttribute(
      "aria-live",
      "polite"
    );

    consoleNode.innerHTML = `
      <div class="niche-focus-readout">
        <span class="niche-focus-kicker">
          focus compression / causal neighborhood
        </span>

        <span
          class="niche-focus-task"
          id="niche-focus-task"
        >
          unknown
        </span>

        <span
          class="niche-focus-counts"
          id="niche-focus-counts"
        ></span>
      </div>

      <button
        type="button"
        class="niche-focus-exit"
      >
        exit focus
      </button>
    `;

    document.body.append(
      consoleNode
    );

    consoleNode
      .querySelector(
        ".niche-focus-exit"
      )
      ?.addEventListener(
        "click",
        clear
      );
  };

  const clearClasses = () => {
    document
      .querySelectorAll(
        [
          ".niche-focus-origin",
          ".niche-focus-upstream",
          ".niche-focus-downstream"
        ].join(",")
      )
      .forEach(node => {
        node.classList.remove(
          "niche-focus-origin",
          "niche-focus-upstream",
          "niche-focus-downstream"
        );
      });
  };

  const nodesForTask = taskId =>
    [...document.querySelectorAll(
      "[data-task-id]"
    )].filter(
      node =>
        node.dataset.taskId === taskId
    );

  const mark = (
    taskId,
    className
  ) => {
    nodesForTask(taskId)
      .forEach(node => {
        node.classList.add(
          className
        );
      });
  };

  const renderConsole = (
    taskId,
    upstream,
    downstream
  ) => {
    ensureConsole();

    const consoleNode =
      document.getElementById(
        "niche-focus-console"
      );

    const taskNode =
      document.getElementById(
        "niche-focus-task"
      );

    const countsNode =
      document.getElementById(
        "niche-focus-counts"
      );

    if (
      !consoleNode ||
      !taskNode ||
      !countsNode
    ) {
      return;
    }

    taskNode.textContent =
      taskId || "unknown";

    countsNode.textContent =
      `upstream ${upstream.length} · downstream ${downstream.length}`;

    consoleNode.hidden = false;
  };

  const apply = async taskId => {
    const id =
      taskId ||
      currentTaskId();

    if (!id) {
      clear();
      return false;
    }

    const task =
      await fetchTask(id);

    if (!task) {
      clear();
      return false;
    }

    runtime.taskId = id;
    runtime.task = task;
    runtime.active = true;

    const upstream =
      dependencies(task);

    const downstream =
      dependents(task);

    clearClasses();

    mark(
      id,
      "niche-focus-origin"
    );

    upstream.forEach(
      upstreamId => {
        mark(
          upstreamId,
          "niche-focus-upstream"
        );
      }
    );

    downstream.forEach(
      downstreamId => {
        mark(
          downstreamId,
          "niche-focus-downstream"
        );
      }
    );

    document.body.classList.add(
      "niche-focus-compression-active"
    );

    renderConsole(
      id,
      upstream,
      downstream
    );

    window.dispatchEvent(
      new CustomEvent(
        "niche:focus-compression-change",
        {
          detail: {
            schema: SCHEMA,
            active: true,
            taskId: id,
            upstream:
              [...upstream],
            downstream:
              [...downstream],
            authorityEffect: "none",
            projectionOnly: true
          }
        }
      )
    );

    return true;
  };

  function clear() {
    runtime.controller?.abort();

    runtime.active = false;
    runtime.taskId = null;
    runtime.task = null;

    clearClasses();

    document.body.classList.remove(
      "niche-focus-compression-active"
    );

    const consoleNode =
      document.getElementById(
        "niche-focus-console"
      );

    if (consoleNode) {
      consoleNode.hidden = true;
    }

    window.dispatchEvent(
      new CustomEvent(
        "niche:focus-compression-change",
        {
          detail: {
            schema: SCHEMA,
            active: false,
            taskId: null,
            authorityEffect: "none",
            projectionOnly: true
          }
        }
      )
    );
  }

  const toggle = async taskId => {
    const id =
      taskId ||
      currentTaskId();

    if (
      runtime.active &&
      runtime.taskId === id
    ) {
      clear();
      return false;
    }

    return apply(id);
  };

  const bindTaskSelection = () => {
    document.addEventListener(
      "click",
      event => {
        if (!runtime.active) {
          return;
        }

        const node =
          event.target.closest(
            "[data-task-id]"
          );

        if (!node) {
          return;
        }

        const id =
          node.dataset.taskId;

        if (
          id &&
          id !== runtime.taskId
        ) {
          void apply(id);
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
          runtime.active
        ) {
          event.preventDefault();
          clear();
          return;
        }

        if (
          event.key.toLowerCase() ===
            "f" &&
          !event.altKey &&
          !event.ctrlKey &&
          !event.metaKey
        ) {
          event.preventDefault();
          void toggle();
        }
      }
    );
  };

  const bindCausalEvents = () => {
    window.addEventListener(
      "niche:causal-field-ready",
      () => {
        if (runtime.active) {
          void apply(
            runtime.taskId
          );
        }
      }
    );

    window.addEventListener(
      "niche:semantic-runtime-update",
      event => {
        if (
          runtime.active &&
          event.detail?.changed
        ) {
          void apply(
            runtime.taskId
          );
        }
      }
    );
  };

  const initialize = () => {
    if (runtime.initialized) {
      return;
    }

    runtime.initialized = true;

    ensureConsole();
    bindTaskSelection();
    bindKeyboard();
    bindCausalEvents();

    document.documentElement.dataset
      .nicheFocusCompression =
      "ready";

    window.dispatchEvent(
      new CustomEvent(
        "niche:focus-compression-ready",
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

  window.NicheFocusCompression =
    Object.freeze({
      apply,
      clear,
      toggle,

      state: () => ({
        schema: SCHEMA,
        active: runtime.active,
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
