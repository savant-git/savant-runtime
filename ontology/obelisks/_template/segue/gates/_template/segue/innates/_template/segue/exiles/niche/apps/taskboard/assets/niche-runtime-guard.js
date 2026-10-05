"use strict";

/*
 * savant / niche
 * runtime interaction guard
 *
 * owner: exile:niche
 * authority_effect: none
 *
 * Prevents task-authority mutations when the task projection is
 * unavailable while preserving read-only living and navigation surfaces.
 */

(() => {
    "use strict";

    const state = {
        taskAvailable: false,
        initialized: false
    };

    const mutationSelectors = [
        "#start-next",
        "#transition-confirm",
        "[data-transition]",
        "[data-task-transition]",
        "[data-action='complete']",
        "[data-action='block']",
        "[data-action='defer']",
        "[data-action='start']",
        "[data-action='continue']"
    ].join(",");

    function apply() {
        document.documentElement.dataset.nicheTaskAuthority =
            state.taskAvailable
                ? "available"
                : "unavailable";

        document
            .querySelectorAll(
                mutationSelectors
            )
            .forEach(
                (element) => {
                    if (
                        state.taskAvailable
                    ) {
                        element.removeAttribute(
                            "aria-disabled"
                        );

                        if (
                            "disabled" in
                            element
                        ) {
                            element.disabled =
                                false;
                        }

                        return;
                    }

                    element.setAttribute(
                        "aria-disabled",
                        "true"
                    );

                    if (
                        "disabled" in
                        element
                    ) {
                        element.disabled =
                            true;
                    }
                }
            );
    }

    function ingest(detail) {
        const task =
            detail?.results?.tasks;

        state.taskAvailable =
            Boolean(
                task?.ok
            );

        apply();
    }

    function guard(event) {
        if (state.taskAvailable) {
            return;
        }

        const control =
            event.target.closest?.(
                mutationSelectors
            );

        if (!control) {
            return;
        }

        event.preventDefault();
        event.stopImmediatePropagation();
    }

    function initialize() {
        if (state.initialized) {
            return;
        }

        state.initialized = true;

        document.addEventListener(
            "click",
            guard,
            true
        );

        document.addEventListener(
            "submit",
            guard,
            true
        );

        window.addEventListener(
            "niche:api-status",
            (event) => {
                ingest(
                    event.detail
                );
            }
        );

        const current =
            window.NicheApiResilience
                ?.status?.();

        if (current) {
            ingest(current);
        } else {
            apply();
        }

        new MutationObserver(
            apply
        ).observe(
            document.body,
            {
                childList: true,
                subtree: true
            }
        );
    }

    if (
        document.readyState ===
        "loading"
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

    window.NicheRuntimeGuard =
        Object.freeze({
            state() {
                return {
                    taskAvailable:
                        state.taskAvailable,
                    authority_effect:
                        "none"
                };
            }
        });
})();
