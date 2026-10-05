(() => {
  "use strict";

  const SCHEMA =
    "savant.niche.semantic-motion.v1";

  const CLASS_NAMES = Object.freeze({
    focus: "niche-motion-focus-enter",
    ready: "niche-motion-ready-enter",
    complete: "niche-motion-complete",
    blocked: "niche-motion-blocked",
    change: "niche-motion-change",
    propagate: "niche-motion-propagate",
    filament: "niche-motion-filament-resolve",
    living: "niche-motion-living-pulse"
  });

  const runtime = {
    initialized: false,
    reduced: false,
    activeAnimations: new Set(),
    taskState: new Map(),
    livingState: new Map(),
    observer: null,
    frame: null
  };

  const prefersReducedMotion = () =>
    window.matchMedia?.(
      "(prefers-reduced-motion: reduce)"
    )?.matches === true;

  const taskId = node =>
    node?.dataset?.taskId || null;

  const taskStatus = node =>
    node?.dataset?.status ||
    node?.dataset?.state ||
    node?.getAttribute?.("data-task-state") ||
    null;

  const taskReady = node => {
    const value =
      node?.dataset?.ready ??
      node?.getAttribute?.("data-ready");

    if (value === "true" || value === true) {
      return true;
    }

    if (value === "false" || value === false) {
      return false;
    }

    return null;
  };

  const signatureForTask = node =>
    JSON.stringify({
      status: taskStatus(node),
      ready: taskReady(node),
      blocked:
        node?.dataset?.blocked ??
        node?.getAttribute?.("data-blocked") ??
        null,
      selected:
        node?.classList?.contains(
          "selected"
        ) ||
        node?.classList?.contains(
          "is-selected"
        ) ||
        node?.getAttribute?.(
          "aria-selected"
        ) === "true"
    });

  const animationEnd = (
    node,
    className
  ) => {
    node.classList.remove(className);
    runtime.activeAnimations.delete(node);
  };

  const animateClass = (
    node,
    className
  ) => {
    if (
      !node ||
      !className
    ) {
      return;
    }

    if (runtime.reduced) {
      node.classList.add(className);

      window.requestAnimationFrame(
        () => {
          node.classList.remove(
            className
          );
        }
      );

      return;
    }

    node.classList.remove(className);

    void node.offsetWidth;

    node.classList.add(className);
    runtime.activeAnimations.add(node);

    node.addEventListener(
      "animationend",
      () => {
        animationEnd(
          node,
          className
        );
      },
      {
        once: true
      }
    );
  };

  const classifyTaskChange = (
    previous,
    current
  ) => {
    if (!previous) {
      return null;
    }

    let before;
    let after;

    try {
      before = JSON.parse(previous);
      after = JSON.parse(current);
    } catch {
      return "change";
    }

    if (
      before.ready !== true &&
      after.ready === true
    ) {
      return "ready";
    }

    if (
      before.status !== after.status &&
      [
        "completed",
        "complete",
        "done"
      ].includes(
        String(
          after.status || ""
        ).toLowerCase()
      )
    ) {
      return "complete";
    }

    if (
      before.blocked !== after.blocked &&
      (
        after.blocked === true ||
        after.blocked === "true"
      )
    ) {
      return "blocked";
    }

    if (
      before.selected !== true &&
      after.selected === true
    ) {
      return "focus";
    }

    if (previous !== current) {
      return "change";
    }

    return null;
  };

  const reconcileTasks = () => {
    const seen = new Set();

    document
      .querySelectorAll("[data-task-id]")
      .forEach(node => {
        const id = taskId(node);

        if (!id) {
          return;
        }

        seen.add(id);

        const signature =
          signatureForTask(node);

        const previous =
          runtime.taskState.get(id);

        runtime.taskState.set(
          id,
          signature
        );

        const change =
          classifyTaskChange(
            previous,
            signature
          );

        if (change) {
          animateClass(
            node,
            CLASS_NAMES[change]
          );
        }
      });

    for (
      const id of runtime.taskState.keys()
    ) {
      if (!seen.has(id)) {
        runtime.taskState.delete(id);
      }
    }
  };

  const livingId = node =>
    node?.dataset?.surfaceId ||
    node?.dataset?.livingSurface ||
    node?.dataset?.surface ||
    null;

  const livingSignature = node =>
    JSON.stringify({
      sequence:
        node?.dataset?.sequence ||
        null,
      changed:
        node?.dataset?.changed ||
        null,
      health:
        node?.dataset?.health ||
        node?.dataset?.state ||
        null,
      freshness:
        node?.dataset?.freshness ||
        null
    });

  const reconcileLiving = () => {
    const candidates =
      document.querySelectorAll(
        [
          "[data-surface-id]",
          "[data-living-surface]",
          "[data-surface]"
        ].join(",")
      );

    const seen = new Set();

    candidates.forEach(node => {
      const id = livingId(node);

      if (!id) {
        return;
      }

      seen.add(id);

      const signature =
        livingSignature(node);

      const previous =
        runtime.livingState.get(id);

      runtime.livingState.set(
        id,
        signature
      );

      if (
        previous &&
        previous !== signature
      ) {
        animateClass(
          node,
          CLASS_NAMES.living
        );
      }
    });

    for (
      const id of runtime.livingState.keys()
    ) {
      if (!seen.has(id)) {
        runtime.livingState.delete(id);
      }
    }
  };

  const reconcileFilaments = () => {
    document
      .querySelectorAll(
        [
          "[data-dependency-resolved='true']",
          "[data-resolved='true'][data-dependency]",
          ".dependency-filament[data-resolved='true']"
        ].join(",")
      )
      .forEach(node => {
        if (
          node.dataset
            .nicheMotionResolved ===
          "true"
        ) {
          return;
        }

        node.dataset
          .nicheMotionResolved =
          "true";

        animateClass(
          node,
          CLASS_NAMES.filament
        );
      });
  };

  const reconcile = () => {
    runtime.frame = null;

    reconcileTasks();
    reconcileLiving();
    reconcileFilaments();
  };

  const scheduleReconcile = () => {
    if (
      runtime.frame !== null
    ) {
      return;
    }

    runtime.frame =
      window.requestAnimationFrame(
        reconcile
      );
  };

  const bindObserver = () => {
    runtime.observer =
      new MutationObserver(
        records => {
          const meaningful =
            records.some(record => {
              if (
                record.type ===
                "childList"
              ) {
                return (
                  record.addedNodes.length >
                    0 ||
                  record.removedNodes.length >
                    0
                );
              }

              if (
                record.type ===
                "attributes"
              ) {
                return [
                  "class",
                  "aria-selected",
                  "data-status",
                  "data-state",
                  "data-task-state",
                  "data-ready",
                  "data-blocked",
                  "data-sequence",
                  "data-changed",
                  "data-health",
                  "data-freshness",
                  "data-resolved"
                ].includes(
                  record.attributeName
                );
              }

              return false;
            });

          if (meaningful) {
            scheduleReconcile();
          }
        }
      );

    runtime.observer.observe(
      document.body,
      {
        subtree: true,
        childList: true,
        attributes: true,
        attributeFilter: [
          "class",
          "aria-selected",
          "data-status",
          "data-state",
          "data-task-state",
          "data-ready",
          "data-blocked",
          "data-sequence",
          "data-changed",
          "data-health",
          "data-freshness",
          "data-resolved"
        ]
      }
    );
  };

  const bindReducedMotion = () => {
    const media =
      window.matchMedia?.(
        "(prefers-reduced-motion: reduce)"
      );

    if (!media) {
      return;
    }

    runtime.reduced =
      media.matches;

    const update = event => {
      runtime.reduced =
        event.matches;
    };

    if (media.addEventListener) {
      media.addEventListener(
        "change",
        update
      );
    } else {
      media.addListener?.(update);
    }
  };

  const animatePropagation = (
    nodes,
    interval = 65
  ) => {
    if (!Array.isArray(nodes)) {
      return;
    }

    nodes.forEach(
      (node, index) => {
        window.setTimeout(
          () => {
            animateClass(
              node,
              CLASS_NAMES.propagate
            );
          },
          runtime.reduced
            ? 0
            : index * interval
        );
      }
    );
  };

  const animateTask = (
    taskIdentifier,
    kind = "change"
  ) => {
    const className =
      CLASS_NAMES[kind];

    if (!className) {
      return false;
    }

    const node =
      [...document.querySelectorAll(
        "[data-task-id]"
      )].find(
        candidate =>
          candidate.dataset.taskId ===
          taskIdentifier
      );

    if (!node) {
      return false;
    }

    animateClass(
      node,
      className
    );

    return true;
  };

  const initialize = () => {
    if (runtime.initialized) {
      return;
    }

    runtime.initialized = true;

    bindReducedMotion();
    reconcile();
    bindObserver();

    document.documentElement.dataset
      .nicheMotion = "ready";

    window.dispatchEvent(
      new CustomEvent(
        "niche:motion-ready",
        {
          detail: {
            schema: SCHEMA,
            authorityEffect: "none",
            projectionOnly: true,
            engine: "native-css"
          }
        }
      )
    );
  };

  window.NicheMotion =
    Object.freeze({
      animateTask,
      animatePropagation,
      reconcile,

      state: () => ({
        schema: SCHEMA,
        reducedMotion:
          runtime.reduced,
        trackedTasks:
          runtime.taskState.size,
        trackedLivingSurfaces:
          runtime.livingState.size,
        authorityEffect: "none",
        projectionOnly: true,
        engine: "native-css"
      })
    });

  if (
    document.readyState === "loading"
  ) {
    document.addEventListener(
      "DOMContentLoaded",
      initialize,
      {
        once: true
      }
    );
  } else {
    initialize();
  }
})();
