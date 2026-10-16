(() => {
  "use strict";

  const SCHEMA =
    "savant.niche.cross-view-continuity.v1";

  const runtime = {
    initialized: false,
    taskId: null,
    observer: null,
    frame: null
  };

  const taskIdFromNode = node => {
    if (!(node instanceof Element)) {
      return null;
    }

    return (
      node.closest("[data-task-id]")
        ?.dataset?.taskId ||
      null
    );
  };

  const nicheState = () => {
    try {
      return (
        window.Niche?.state?.() ||
        {}
      );
    } catch {
      return {};
    }
  };

  const resolvedTaskId = () => {
    const state =
      nicheState();

    return (
      state.selectedTaskId ||
      runtime.taskId ||
      state.recommendedTaskId ||
      null
    );
  };

  const ensureBeacon = () => {
    if (
      document.getElementById(
        "niche-continuity-beacon"
      )
    ) {
      return;
    }

    const beacon =
      document.createElement("div");

    beacon.id =
      "niche-continuity-beacon";

    beacon.className =
      "niche-continuity-beacon";

    beacon.hidden = true;

    beacon.setAttribute(
      "aria-live",
      "polite"
    );

    beacon.innerHTML = `
      <span
        class="niche-continuity-copy"
        id="niche-continuity-copy"
      ></span>

      <span
        class="niche-continuity-count"
        id="niche-continuity-count"
      ></span>
    `;

    document.body.append(beacon);
  };

  const clearMarks = () => {
    document
      .querySelectorAll(
        ".niche-continuity-current"
      )
      .forEach(node => {
        node.classList.remove(
          "niche-continuity-current"
        );

        node.removeAttribute(
          "data-continuity-current"
        );
      });
  };

  const matchingNodes = taskId => {
    if (!taskId) {
      return [];
    }

    return [
      ...document.querySelectorAll(
        "[data-task-id]"
      )
    ].filter(
      node =>
        node.dataset.taskId === taskId
    );
  };

  const render = () => {
    runtime.frame = null;

    ensureBeacon();
    clearMarks();

    const taskId =
      resolvedTaskId();

    runtime.taskId =
      taskId;

    const beacon =
      document.getElementById(
        "niche-continuity-beacon"
      );

    const copy =
      document.getElementById(
        "niche-continuity-copy"
      );

    const count =
      document.getElementById(
        "niche-continuity-count"
      );

    if (
      !taskId ||
      !beacon ||
      !copy ||
      !count
    ) {
      if (beacon) {
        beacon.hidden = true;
      }

      return;
    }

    const nodes =
      matchingNodes(taskId);

    nodes.forEach(node => {
      node.classList.add(
        "niche-continuity-current"
      );

      node.setAttribute(
        "data-continuity-current",
        "true"
      );
    });

    copy.textContent =
      taskId;

    count.textContent =
      `${nodes.length} projection${
        nodes.length === 1
          ? ""
          : "s"
      }`;

    beacon.hidden = false;

    document.documentElement.dataset
      .nicheContinuityTask =
      taskId;
  };

  const scheduleRender = () => {
    if (runtime.frame !== null) {
      return;
    }

    runtime.frame =
      requestAnimationFrame(render);
  };

  const select = taskId => {
    if (
      typeof taskId !== "string" ||
      !taskId
    ) {
      return false;
    }

    runtime.taskId =
      taskId;

    scheduleRender();

    window.dispatchEvent(
      new CustomEvent(
        "niche:continuity-selection",
        {
          detail: {
            schema: SCHEMA,
            taskId,
            authorityEffect: "none",
            projectionOnly: true
          }
        }
      )
    );

    return true;
  };

  const bindPointerSelection = () => {
    document.addEventListener(
      "click",
      event => {
        const taskId =
          taskIdFromNode(
            event.target
          );

        if (taskId) {
          select(taskId);
        }
      },
      true
    );
  };

  const bindKeyboardSelection = () => {
    document.addEventListener(
      "focusin",
      event => {
        const taskId =
          taskIdFromNode(
            event.target
          );

        if (taskId) {
          select(taskId);
        }
      }
    );
  };

  const bindKnownEvents = () => {
    [
      "niche:frontend-ready",
      "niche:semantic-runtime-update",
      "niche:focus-compression-change",
      "niche:living-pulse"
    ].forEach(name => {
      window.addEventListener(
        name,
        scheduleRender
      );
    });
  };

  const bindDomProjection = () => {
    runtime.observer =
      new MutationObserver(
        mutations => {
          const relevant =
            mutations.some(
              mutation =>
                mutation.type ===
                  "childList" ||
                (
                  mutation.type ===
                    "attributes" &&
                  mutation.attributeName ===
                    "data-task-id"
                )
            );

          if (relevant) {
            scheduleRender();
          }
        }
      );

    runtime.observer.observe(
      document.body,
      {
        childList: true,
        subtree: true,
        attributes: true,
        attributeFilter: [
          "data-task-id"
        ]
      }
    );
  };

  const focusVisibleProjection = () => {
    const taskId =
      resolvedTaskId();

    if (!taskId) {
      return false;
    }

    const nodes =
      matchingNodes(taskId);

    const visible =
      nodes.find(node => {
        const rect =
          node.getBoundingClientRect();

        return (
          rect.width > 0 &&
          rect.height > 0 &&
          rect.bottom >= 0 &&
          rect.right >= 0 &&
          rect.top <=
            window.innerHeight &&
          rect.left <=
            window.innerWidth
        );
      });

    if (!visible) {
      return false;
    }

    visible.scrollIntoView({
      block: "nearest",
      inline: "nearest",
      behavior:
        matchMedia(
          "(prefers-reduced-motion: reduce)"
        ).matches
          ? "auto"
          : "smooth"
    });

    if (
      visible instanceof
      HTMLElement
    ) {
      if (
        !visible.hasAttribute(
          "tabindex"
        )
      ) {
        visible.tabIndex = -1;
      }

      visible.focus({
        preventScroll: true
      });
    }

    return true;
  };

  const initialize = () => {
    if (runtime.initialized) {
      return;
    }

    runtime.initialized = true;

    ensureBeacon();
    bindPointerSelection();
    bindKeyboardSelection();
    bindKnownEvents();
    bindDomProjection();

    scheduleRender();

    document.documentElement.dataset
      .nicheCrossViewContinuity =
      "ready";

    window.dispatchEvent(
      new CustomEvent(
        "niche:cross-view-continuity-ready",
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

  window.NicheCrossViewContinuity =
    Object.freeze({
      select,
      refresh:
        scheduleRender,
      focusVisibleProjection,

      state: () => ({
        schema: SCHEMA,
        taskId:
          resolvedTaskId(),
        projectionCount:
          matchingNodes(
            resolvedTaskId()
          ).length,
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
