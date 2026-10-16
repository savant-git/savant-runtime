"use strict";

/*
 * savant / niche
 * frontend bootstrap coordinator
 *
 * owner: exile:niche
 * authority_effect: none
 */

(() => {
    "use strict";

    const state = {
        ready: false,
        initializedAt: null
    };

    function initialize() {
        if (state.ready) {
            return;
        }

        state.ready = true;

        state.initializedAt =
            new Date()
                .toISOString();

        document.documentElement
            .dataset
            .nicheFrontend =
            "ready";

        window.dispatchEvent(
            new CustomEvent(
                "niche:frontend-ready",
                {
                    detail: {
                        initialized_at:
                            state.initializedAt,
                        authority_effect:
                            "none"
                    }
                }
            )
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

    window.NicheBootstrap =
        Object.freeze({
            state() {
                return {
                    ready:
                        state.ready,
                    initializedAt:
                        state.initializedAt
                };
            }
        });
})();
