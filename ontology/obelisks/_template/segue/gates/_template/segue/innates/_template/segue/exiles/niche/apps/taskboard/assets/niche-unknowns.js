"use strict";

/*
 * savant / niche
 * unknown-state projection
 *
 * owner: exile:niche
 * authority_effect: none
 *
 * Unknown is preserved as unknown. This module does not infer missing
 * authority, readiness, priority, evidence, dependency, or health state.
 */

(() => {
    "use strict";

    const state = {
        unavailable: new Set(),
        taskAvailable: false,
        livingAvailable: false,
        historyAvailable: false
    };

    const $ = (selector, root = document) =>
        root.querySelector(selector);

    const $$ = (selector, root = document) =>
        Array.from(
            root.querySelectorAll(selector)
        );

    function unavailable(name) {
        return state.unavailable.has(name);
    }

    function mark(
        element,
        reason
    ) {
        if (!element) {
            return;
        }

        element.dataset.nicheUnknown =
            "true";

        element.dataset.nicheUnknownReason =
            reason;

        if (
            !element.getAttribute(
                "title"
            )
        ) {
            element.setAttribute(
                "title",
                reason
            );
        }
    }

    function clear(element) {
        if (!element) {
            return;
        }

        element.removeAttribute(
            "data-niche-unknown"
        );

        element.removeAttribute(
            "data-niche-unknown-reason"
        );
    }

    function projectTaskUnknowns() {
        const selectors = [
            "#execute-heading",
            "#execute-purpose",
            "#execute-priority",
            "#execute-ancestry",
            "#start-next",
            "#frontier-track",
            "#priority-oracle",
            "#flow-board",
            "#graph-stage",
            "#objective-grid",
            "#evidence-grid"
        ];

        selectors.forEach(
            (selector) => {
                const element =
                    $(selector);

                if (
                    state.taskAvailable
                ) {
                    clear(element);
                } else {
                    mark(
                        element,
                        "task projection unavailable"
                    );
                }
            }
        );
    }

    function projectHistoryUnknowns() {
        [
            "#timeline",
            "#history-list"
        ].forEach(
            (selector) => {
                const element =
                    $(selector);

                if (
                    state.historyAvailable
                ) {
                    clear(element);
                } else {
                    mark(
                        element,
                        "history projection unavailable"
                    );
                }
            }
        );
    }

    function projectLivingUnknowns() {
        [
            "#living-summary",
            "#living-grid",
            "#fabric-identity"
        ].forEach(
            (selector) => {
                const element =
                    $(selector);

                if (
                    state.livingAvailable
                ) {
                    clear(element);
                } else {
                    mark(
                        element,
                        "living projection unavailable"
                    );
                }
            }
        );
    }

    function project() {
        projectTaskUnknowns();
        projectHistoryUnknowns();
        projectLivingUnknowns();

        document.documentElement
            .dataset
            .nicheUnknowns =
            state.unavailable.size
                ? "present"
                : "none";
    }

    function ingest(detail) {
        state.unavailable.clear();

        const results =
            detail?.results || {};

        for (
            const [
                name,
                result
            ] of Object.entries(
                results
            )
        ) {
            if (!result?.ok) {
                state.unavailable.add(
                    name
                );
            }
        }

        state.taskAvailable =
            Boolean(
                results.tasks?.ok
            );

        state.historyAvailable =
            Boolean(
                results.history?.ok
            );

        state.livingAvailable =
            Boolean(
                results.living?.ok ||
                results.fabric?.ok
            );

        project();
    }

    function observe() {
        new MutationObserver(
            () => {
                project();
            }
        ).observe(
            document.body,
            {
                childList: true,
                subtree: true
            }
        );
    }

    function initialize() {
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
        }

        observe();
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

    window.NicheUnknowns =
        Object.freeze({
            state() {
                return {
                    unavailable:
                        Array.from(
                            state.unavailable
                        ),
                    taskAvailable:
                        state.taskAvailable,
                    livingAvailable:
                        state.livingAvailable,
                    historyAvailable:
                        state.historyAvailable,
                    authority_effect:
                        "none"
                };
            }
        });
})();
