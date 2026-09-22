"use strict";

/*
 * savant / niche
 * synchronized projection continuity
 *
 * owner: exile:niche
 * authority_effect: none
 *
 * Keeps identity, selection, view, focus, and projection context coherent
 * across Niche surfaces without creating task authority.
 */

(() => {
    "use strict";

    const state = {
        taskId: null,
        view: "execute",
        previousView: null,
        lastTaskByView: new Map(),
        pendingFrame: 0,
        observer: null
    };

    const $ = (selector, root = document) =>
        root.querySelector(selector);

    const $$ = (selector, root = document) =>
        Array.from(root.querySelectorAll(selector));

    function safe(value) {
        return value === undefined || value === null
            ? ""
            : String(value);
    }

    function escapeSelector(value) {
        if (window.CSS?.escape) {
            return CSS.escape(safe(value));
        }

        return safe(value).replace(
            /["\\]/g,
            "\\$&"
        );
    }

    function activeView() {
        return (
            $(".surface.active")?.dataset.surface ||
            $(".nav [aria-current='page']")?.dataset.view ||
            state.view ||
            "execute"
        );
    }

    function taskElements(taskId) {
        if (!taskId) {
            return [];
        }

        const escaped =
            escapeSelector(taskId);

        return $$(
            `[data-task-id="${escaped}"]`
        );
    }

    function clearIdentity() {
        $$(
            ".niche-identity-primary, .niche-identity-related"
        ).forEach((element) => {
            element.classList.remove(
                "niche-identity-primary",
                "niche-identity-related"
            );

            element.removeAttribute(
                "data-niche-selected"
            );
        });
    }

    function relatedIds(taskId) {
        const source =
            taskElements(taskId)[0];

        if (!source) {
            return [];
        }

        const values = new Set();

        [
            "dependencies",
            "dependents",
            "blockers"
        ].forEach((key) => {
            const raw =
                source.dataset[key];

            if (!raw) {
                return;
            }

            raw.split(",")
                .map((value) => value.trim())
                .filter(Boolean)
                .forEach((value) => {
                    values.add(value);
                });
        });

        return Array.from(values);
    }

    function projectIdentity(taskId) {
        clearIdentity();

        if (!taskId) {
            return;
        }

        state.taskId = taskId;

        taskElements(taskId)
            .forEach((element) => {
                element.classList.add(
                    "niche-identity-primary"
                );

                element.dataset.nicheSelected =
                    "true";
            });

        for (
            const relatedId of relatedIds(taskId)
        ) {
            taskElements(relatedId)
                .forEach((element) => {
                    element.classList.add(
                        "niche-identity-related"
                    );
                });
        }

        state.lastTaskByView.set(
            activeView(),
            taskId
        );

        document.body.dataset
            .nicheSelectedTask =
            taskId;
    }

    function inferSelectedTask() {
        const explicit =
            $(
                "[data-task-id][aria-current='true']"
            ) ||
            $(
                "[data-task-id][data-niche-selected='true']"
            );

        if (explicit?.dataset.taskId) {
            return explicit.dataset.taskId;
        }

        const inspector =
            $("#inspector");

        if (
            inspector?.classList.contains(
                "open"
            )
        ) {
            const title =
                $("#inspector-title")
                    ?.textContent
                    ?.trim();

            if (title) {
                const matching =
                    $$("[data-task-id]")
                        .find((element) => {
                            const heading =
                                $("h3", element)
                                    ?.textContent
                                    ?.trim();

                            return heading === title;
                        });

                if (matching?.dataset.taskId) {
                    return matching.dataset.taskId;
                }
            }
        }

        return state.taskId;
    }

    function reconcileIdentity() {
        state.pendingFrame = 0;

        const taskId =
            inferSelectedTask();

        if (taskId) {
            projectIdentity(taskId);
        } else {
            clearIdentity();
        }
    }

    function scheduleReconcile() {
        if (state.pendingFrame) {
            return;
        }

        state.pendingFrame =
            window.requestAnimationFrame(
                reconcileIdentity
            );
    }

    function switchView(view) {
        if (!view) {
            return;
        }

        state.previousView =
            activeView();

        state.view = view;

        if (
            window.Niche?.view
        ) {
            window.Niche.view(view);
        } else {
            $$(".surface")
                .forEach((surface) => {
                    surface.classList.toggle(
                        "active",
                        surface.dataset.surface ===
                            view
                    );
                });

            $$(".nav [data-view]")
                .forEach((button) => {
                    const active =
                        button.dataset.view ===
                        view;

                    button.classList.toggle(
                        "active",
                        active
                    );

                    if (active) {
                        button.setAttribute(
                            "aria-current",
                            "page"
                        );
                    } else {
                        button.removeAttribute(
                            "aria-current"
                        );
                    }
                });
        }

        const taskId =
            state.taskId ||
            state.lastTaskByView.get(view);

        window.requestAnimationFrame(
            () => {
                if (taskId) {
                    projectIdentity(taskId);

                    const target =
                        taskElements(taskId)
                            .find(
                                (element) =>
                                    element.offsetParent !==
                                    null
                            );

                    target?.scrollIntoView({
                        block: "nearest",
                        inline: "nearest",
                        behavior:
                            window.matchMedia(
                                "(prefers-reduced-motion: reduce)"
                            ).matches
                                ? "auto"
                                : "smooth"
                    });
                }
            }
        );
    }

    function returnToPreviousView() {
        switchView(
            state.previousView ||
            "execute"
        );
    }

    function installTaskSelection() {
        document.addEventListener(
            "click",
            (event) => {
                const task =
                    event.target.closest(
                        "[data-task-id]"
                    );

                if (!task?.dataset.taskId) {
                    return;
                }

                projectIdentity(
                    task.dataset.taskId
                );
            },
            true
        );

        document.addEventListener(
            "focusin",
            (event) => {
                const task =
                    event.target.closest?.(
                        "[data-task-id]"
                    );

                if (!task?.dataset.taskId) {
                    return;
                }

                projectIdentity(
                    task.dataset.taskId
                );
            }
        );
    }

    function installNavigationContinuity() {
        $$(".nav [data-view]")
            .forEach((button) => {
                button.addEventListener(
                    "click",
                    () => {
                        state.previousView =
                            activeView();

                        state.view =
                            button.dataset.view;

                        window.setTimeout(
                            reconcileIdentity,
                            0
                        );
                    },
                    true
                );
            });
    }

    function installInspectorContinuity() {
        const inspector =
            $("#inspector");

        if (!inspector) {
            return;
        }

        if (
            "MutationObserver" in window
        ) {
            const observer =
                new MutationObserver(() => {
                    const taskId =
                        inferSelectedTask();

                    if (taskId) {
                        projectIdentity(
                            taskId
                        );
                    }
                });

            observer.observe(
                inspector,
                {
                    childList: true,
                    subtree: true,
                    attributes: true,
                    attributeFilter: [
                        "class",
                        "aria-hidden"
                    ]
                }
            );
        }
    }

    function installProjectionObserver() {
        if (
            !("MutationObserver" in window)
        ) {
            return;
        }

        state.observer =
            new MutationObserver(
                scheduleReconcile
            );

        state.observer.observe(
            $("#main") ||
            document.body,
            {
                childList: true,
                subtree: true
            }
        );
    }

    function installCrossViewControls() {
        document.addEventListener(
            "keydown",
            (event) => {
                const target =
                    event.target;

                if (
                    target instanceof
                        HTMLInputElement ||
                    target instanceof
                        HTMLTextAreaElement ||
                    target instanceof
                        HTMLSelectElement ||
                    target?.isContentEditable
                ) {
                    return;
                }

                if (
                    event.key ===
                    "Backspace" &&
                    event.altKey
                ) {
                    event.preventDefault();
                    returnToPreviousView();
                }

                if (
                    event.key ===
                    "Enter" &&
                    event.altKey &&
                    state.taskId
                ) {
                    event.preventDefault();

                    const task =
                        taskElements(
                            state.taskId
                        )[0];

                    task?.click();
                }
            }
        );
    }

    function installCausalJump() {
        document.addEventListener(
            "dblclick",
            (event) => {
                const task =
                    event.target.closest(
                        "[data-task-id]"
                    );

                if (!task?.dataset.taskId) {
                    return;
                }

                projectIdentity(
                    task.dataset.taskId
                );

                switchView(
                    "constellation"
                );
            }
        );
    }

    function initialize() {
        state.view =
            activeView();

        installTaskSelection();
        installNavigationContinuity();
        installInspectorContinuity();
        installProjectionObserver();
        installCrossViewControls();
        installCausalJump();

        reconcileIdentity();
    }

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

    window.NicheContinuity =
        Object.freeze({
            select(taskId) {
                projectIdentity(
                    safe(taskId)
                );
            },

            view(view) {
                switchView(
                    safe(view)
                );
            },

            back:
                returnToPreviousView,

            reconcile:
                reconcileIdentity,

            state() {
                return {
                    taskId:
                        state.taskId,
                    view:
                        activeView(),
                    previousView:
                        state.previousView
                };
            }
        });
})();
