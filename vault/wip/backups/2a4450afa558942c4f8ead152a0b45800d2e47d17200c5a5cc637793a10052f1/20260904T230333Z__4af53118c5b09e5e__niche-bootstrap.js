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

    const GRAPHICS_CSS = "/assets/niche-graphics.css";
    const GRAPHICS_JS = "/assets/niche-graphics.js";

    const state = {
        ready: false,
        initializedAt: null,
        graphicsRequested: false
    };

    function requestGraphics() {
        if (state.graphicsRequested) {
            return;
        }

        state.graphicsRequested = true;

        if (!document.querySelector(`link[href="${GRAPHICS_CSS}"]`)) {
            const style = document.createElement("link");

            style.rel = "stylesheet";
            style.href = GRAPHICS_CSS;
            style.dataset.nicheGraphics = "stylesheet";

            document.head.append(style);
        }

        if (!document.querySelector(`script[src="${GRAPHICS_JS}"]`)) {
            const script = document.createElement("script");

            script.src = GRAPHICS_JS;
            script.defer = true;
            script.dataset.nicheGraphics = "controller";

            document.head.append(script);
        }
    }

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

        requestGraphics();
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
                        state.initializedAt,
                    graphicsRequested:
                        state.graphicsRequested
                };
            }
        });
})();
