(() => {
  "use strict";

  const SCHEMA =
    "savant.niche.focus-compression.v1";

  const runtime = {
    initialized: false,
    active: false,
    taskId: null,
    focal: null,
    upstream: new Set(),
    downstream: new Set(),
    generation: 0,
    controller: null
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
          [
            "task_id",
            "taskId",
            "id"
          ]
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

  const clearClasses = () => {
    document
      .querySelectorAll(
        "[data-task-id]"
      )
      .forEach(node => {
        node.classList.remove(
          "niche-focus-origin",
          "niche-focus-upstream",
          "niche-focus-downstream",
          "niche-focus-muted"
        );
      });

    document.documentElement
      .classList.remove(
        "niche-focus-compression-active"
      );
  };

  const classifyNodes = () => {
    clearClasses();

    if (
      !runtime.active ||
      !runtime.taskId
    ) {
      return;
    }

    document.documentElement
      .classList.add(
        "niche-focus-compression-active"
      );

    document
      .querySelectorAll(
        "[data-task-id]"
      )
      .forEach(node => {
        const id =
          node.dataset.taskId;

        if (id === runtime.taskId) {
          node.classList.add(
            "niche-focus-origin"
          );
          return;
        }

        if (
          runtime.upstream.has(id)
        ) {
          node.classList.add(
            "niche-focus-upstream"
          );
          return;
        }

        if (
          runtime.downstream.has(id)
        ) {
          node.classList.add(
            "niche-focus-downstream"
          );
          return;
        }

        node.classList.add(
          "niche-focus-muted"
        );
      });
  };

  const publish = () => {
    window.dispatchEvent(
      new CustomEvent(
        "niche:focus-compression-change",
        {
          detail: {
            schema: SCHEMA,
            active: runtime.active,
            taskId: runtime.taskId,
            upstream:
              [...runtime.upstream],
            downstream:
              [...runtime.downstream],
            authorityEffect: "none",
            projectionOnly: true
          }
        }
      )
    );
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

    const task =
      await fetchTask(
        id,
        controller
      );

    if (
      generation !==
      runtime.generation
    ) {
      return false;
    }

    if (!task) {
      runtime.focal = null;
      runtime.upstream.clear();
      runtime.downstream.clear();
      classifyNodes();
      publish();
      return false;
    }

    runtime.focal = task;

    runtime.upstream =
      new Set([
        ...idsOf(
          task.dependencies
        ),
        ...idsOf(
          task.unsatisfied_dependencies
        ),
        ...idsOf(
          task.blockers
        )
      ]);

    runtime.downstream =
      new Set(
        idsOf(task.dependents)
      );

    if (
      runtime.controller ===
      controller
    ) {
      runtime.controller = null;
    }

    classifyNodes();
    publish();

    return true;
  };

  const select = async id => {
    const resolved =
      id ||
      currentTaskId();

    runtime.taskId =
      resolved;

    if (!resolved) {
      runtime.focal = null;
      runtime.upstream.clear();
      runtime.downstream.clear();
      classifyNodes();
      publish();
      return false;
    }

    return resolve(resolved);
  };

  const activate = async id => {
    runtime.active = true;

    await select(
      id ||
      currentTaskId()
    );

    classifyNodes();
    publish();

    return runtime.active;
  };

  const deactivate = () => {
    runtime.active = false;

    runtime.controller?.abort();

    clearClasses();
    publish();

    return false;
  };

  const toggle = async id => {
    if (runtime.active) {
      return deactivate();
    }

    return activate(id);
  };

  const bindSelection = () => {
    document.addEventListener(
      "click",
      event => {
        const task =
          event.target.closest(
            "[data-task-id]"
          );

        if (
          !task ||
          !runtime.active
        ) {
          return;
        }

        const id =
          task.dataset.taskId;

        if (
          id &&
          id !== runtime.taskId
        ) {
          void select(id);
        }
      },
      true
    );

    document.addEventListener(
      "focusin",
      event => {
        const task =
          event.target.closest?.(
            "[data-task-id]"
          );

        if (
          !task ||
          !runtime.active
        ) {
          return;
        }

        const id =
          task.dataset.taskId;

        if (
          id &&
          id !== runtime.taskId
        ) {
          void select(id);
        }
      }
    );
  };

  const bindTriggers = () => {
    /*
    No bare "f" keyboard listener lives here.

    The established executable-environment
    layer already owns that keyboard gesture.
    This module exposes explicit methods and
    data-action hooks so only one layer owns
    the global key binding.
    */

    document.addEventListener(
      "click",
      event => {
        const trigger =
          event.target.closest(
            [
              "[data-action='focus-compression']",
              "[data-command='focus-compression']",
              "[data-focus-compression]"
            ].join(",")
          );

        if (!trigger) {
          return;
        }

        const task =
          trigger.closest(
            "[data-task-id]"
          );

        void toggle(
          task?.dataset?.taskId ||
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
          runtime.active &&
          event.detail?.changed
        ) {
          void select(
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
          runtime.active &&
          id &&
          id !== runtime.taskId
        ) {
          void select(id);
        }
      }
    );

    window.addEventListener(
      "niche:frontend-focus-compression",
      event => {
        const requested =
          event.detail?.active;

        const id =
          event.detail?.taskId ||
          currentTaskId();

        if (requested === false) {
          deactivate();
          return;
        }

        if (requested === true) {
          void activate(id);
          return;
        }

        void toggle(id);
      }
    );
  };

  const initialize = () => {
    if (runtime.initialized) {
      return;
    }

    runtime.initialized = true;

    bindSelection();
    bindTriggers();
    bindRuntime();

    document.documentElement.dataset
      .nicheFocusCompression =
      "ready";

    window.dispatchEvent(
      new CustomEvent(
        "niche:focus-compression-ready",
        {
          detail: {
            schema: SCHEMA,
            keyboardOwner:
              "executable-environment",
            authorityEffect: "none",
            projectionOnly: true
          }
        }
      )
    );
  };

  window.NicheFocusCompression =
    Object.freeze({
      activate,
      deactivate,
      toggle,
      select,

      state: () => ({
        schema: SCHEMA,
        active: runtime.active,
        taskId: runtime.taskId,
        upstream:
          [...runtime.upstream],
        downstream:
          [...runtime.downstream],
        keyboardOwner:
          "executable-environment",
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
