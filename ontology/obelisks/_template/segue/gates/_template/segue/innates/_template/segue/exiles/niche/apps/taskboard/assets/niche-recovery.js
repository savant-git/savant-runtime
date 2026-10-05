"use strict";

/*
 * savant / niche
 * projection recovery
 *
 * owner: exile:niche
 * authority_effect: none
 *
 * Rebuilds only interface projections from already admitted API
 * responses. It never reconstructs task authority from UI state.
 */

(() => {
    "use strict";

    const state = {
        mode: "normal",
        available: new Set(),
        unavailable: new Set(),
        lastChange: null
    };

    const $ = (selector, root = document) =>
        root.querySelector(selector);

    const $$ = (selector, root = document) =>
        Array.from(root.querySelectorAll(selector));

    function setMode(mode) {
        state.mode = mode;
        state.lastChange = new Date().toISOString();

        document.body.dataset.nicheRecovery = mode;

        window.dispatchEvent(
            new CustomEvent("niche:recovery", {
                detail: {
                    mode,
                    available: Array.from(state.available),
                    unavailable: Array.from(state.unavailable),
                    changed_at: state.lastChange,
                    authority_effect: "none"
                }
            })
        );
    }

    function clearUnavailableMarkers() {
        $$("[data-niche-projection-unavailable]")
            .forEach((element) => {
                element.removeAttribute(
                    "data-niche-projection-unavailable"
                );
            });
    }

    function markSurface(surface, unavailable) {
        const element =
            $(`[data-surface="${surface}"]`);

        if (!element) {
            return;
        }

        if (unavailable) {
            element.dataset.nicheProjectionUnavailable = "true";
        } else {
            element.removeAttribute(
                "data-niche-projection-unavailable"
            );
        }
    }

    function reconcile(apiState) {
        clearUnavailableMarkers();

        state.available.clear();
        state.unavailable.clear();

        const results =
            apiState?.results || {};

        for (const [name, result] of Object.entries(results)) {
            if (result?.ok) {
                state.available.add(name);
            } else {
                state.unavailable.add(name);
            }
        }

        const tasksUnavailable =
            state.unavailable.has("tasks");

        const historyUnavailable =
            state.unavailable.has("history");

        const livingUnavailable =
            state.unavailable.has("living") &&
            state.unavailable.has("fabric");

        [
            "execute",
            "flow",
            "constellation",
            "objectives",
            "evidence"
        ].forEach((surface) => {
            markSurface(
                surface,
                tasksUnavailable
            );
        });

        markSurface(
            "timeline",
            historyUnavailable
        );

        markSurface(
            "history",
            historyUnavailable
        );

        markSurface(
            "living",
            livingUnavailable
        );

        if (
            tasksUnavailable &&
            historyUnavailable
        ) {
            setMode("task-core-unavailable");
            return;
        }

        if (state.unavailable.size) {
            setMode("degraded");
            return;
        }

        setMode("normal");
    }

    function installApiBridge() {
        window.addEventListener(
            "niche:api-status",
            (event) => {
                reconcile(
                    event.detail
                );
            }
        );

        const current =
            window.NicheApiResilience
                ?.status?.();

        if (current?.results) {
            reconcile(current);
        }
    }

    function installGuard() {
        document.addEventListener(
            "click",
            (event) => {
                const surface =
                    event.target.closest(
                        "[data-niche-projection-unavailable='true']"
                    );

                if (!surface) {
                    return;
                }

                const mutationControl =
                    event.target.closest(
                        "#start-next, #transition-confirm, [data-transition], [data-task-transition]"
                    );

                if (!mutationControl) {
                    return;
                }

                event.preventDefault();
                event.stopImmediatePropagation();
            },
            true
        );
    }

    function initialize() {
        installApiBridge();
        installGuard();
    }

    if (document.readyState === "loading") {
        document.addEventListener(
            "DOMContentLoaded",
            initialize,
            { once: true }
        );
    } else {
        initialize();
    }

    window.NicheRecovery =
        Object.freeze({
            state() {
                return {
                    mode: state.mode,
                    available: Array.from(state.available),
                    unavailable: Array.from(state.unavailable),
                    lastChange: state.lastChange
                };
            },

            reconcile
        });
})();
