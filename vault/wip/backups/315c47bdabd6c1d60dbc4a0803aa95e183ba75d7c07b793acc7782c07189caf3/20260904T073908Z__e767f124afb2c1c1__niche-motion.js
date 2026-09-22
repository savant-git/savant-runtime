"use strict";

/*
 * savant / niche
 * semantic motion coordinator
 *
 * owner: exile:niche
 * authority_effect: none
 *
 * Motion communicates projection change only.
 */

(() => {
    "use strict";

    const state = {
        reduced: false,
        previous: new Map(),
        initialized: false
    };

    const query =
        window.matchMedia?.(
            "(prefers-reduced-motion: reduce)"
        );

    function reduced() {
        return Boolean(
            query?.matches
        );
    }

    function snapshot() {
        const current =
            new Map();

        document
            .querySelectorAll(
                "[data-task-id]"
            )
            .forEach(
                (element) => {
                    const id =
                        element.dataset
                            .taskId;

                    if (!id) {
                        return;
                    }

                    current.set(
                        id,
                        {
                            state:
                                element.dataset
                                    .state ||
                                "unknown",
                            ready:
                                element.dataset
                                    .ready ||
                                "unknown",
                            blocked:
                                element.dataset
                                    .blocked ||
                                "unknown"
                        }
                    );
                }
            );

        return current;
    }

    function pulse(element) {
        if (
            state.reduced ||
            !element
        ) {
            return;
        }

        element.classList.remove(
            "niche-semantic-change"
        );

        void element.offsetWidth;

        element.classList.add(
            "niche-semantic-change"
        );

        window.setTimeout(
            () => {
                element.classList.remove(
                    "niche-semantic-change"
                );
            },
            720
        );
    }

    function reconcile() {
        const current =
            snapshot();

        for (
            const [
                id,
                value
            ] of current
        ) {
            const previous =
                state.previous.get(id);

            if (!previous) {
                continue;
            }

            if (
                previous.state !==
                    value.state ||
                previous.ready !==
                    value.ready ||
                previous.blocked !==
                    value.blocked
            ) {
                const selector =
                    window
                        .NicheSafeSelector
                        ?.task?.(id);

                if (!selector) {
                    continue;
                }

                document
                    .querySelectorAll(
                        selector
                    )
                    .forEach(
                        pulse
                    );
            }
        }

        state.previous =
            current;
    }

    function schedule() {
        if (
            window.NichePerformance
                ?.schedule
        ) {
            window.NichePerformance
                .schedule(
                    "semantic-motion",
                    reconcile
                );

            return;
        }

        requestAnimationFrame(
            reconcile
        );
    }

    function initialize() {
        if (state.initialized) {
            return;
        }

        state.initialized = true;
        state.reduced =
            reduced();

        state.previous =
            snapshot();

        query?.addEventListener?.(
            "change",
            () => {
                state.reduced =
                    reduced();
            }
        );

        new MutationObserver(
            schedule
        ).observe(
            document.body,
            {
                childList: true,
                subtree: true,
                attributes: true,
                attributeFilter: [
                    "data-state",
                    "data-ready",
                    "data-blocked"
                ]
            }
        );

        window.addEventListener(
            "niche:api-status",
            schedule
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

    window.NicheMotion =
        Object.freeze({
            reconcile,

            state() {
                return {
                    reduced:
                        state.reduced,
                    tracked:
                        state.previous.size,
                    authority_effect:
                        "none"
                };
            }
        });
})();
