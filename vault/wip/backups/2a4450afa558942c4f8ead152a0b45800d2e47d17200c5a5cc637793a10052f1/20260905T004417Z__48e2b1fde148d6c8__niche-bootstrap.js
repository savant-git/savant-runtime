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

    const ASSETS = Object.freeze([
        ["stylesheet", "/assets/niche-graphics.css", "nicheGraphics"],
        ["stylesheet", "/assets/niche-themes.css", "nicheThemes"],
        ["script", "/assets/niche-graphics.js", "nicheGraphics"],
        ["script", "/assets/niche-themes.js", "nicheThemes"]
    ]);

    const state = {
        ready: false,
        initializedAt: null,
        assetsRequested: false
    };

    function requestAssets() {
        if (state.assetsRequested) {
            return;
        }

        state.assetsRequested = true;

        for (const [kind, href, datasetKey] of ASSETS) {
            if (kind === "stylesheet") {
                if (document.querySelector(`link[href="${href}"]`)) {
                    continue;
                }

                const style = document.createElement("link");

                style.rel = "stylesheet";
                style.href = href;
                style.dataset[datasetKey] = "stylesheet";

                document.head.append(style);

                continue;
            }

            if (document.querySelector(`script[src="${href}"]`)) {
                continue;
            }

            const script = document.createElement("script");

            script.src = href;
            script.defer = true;
            script.dataset[datasetKey] = "controller";

            document.head.append(script);
        }
    }

    function initialize() {
        if (state.ready) {
            return;
        }

        state.ready = true;
        state.initializedAt = new Date().toISOString();

        document.documentElement.dataset.nicheFrontend = "ready";

        window.dispatchEvent(
            new CustomEvent(
                "niche:frontend-ready",
                {
                    detail: {
                        initialized_at: state.initializedAt,
                        authority_effect: "none"
                    }
                }
            )
        );

        requestAssets();
    }

    if (document.readyState === "loading") {
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

    window.NicheBootstrap = Object.freeze({
        state() {
            return {
                ready: state.ready,
                initializedAt: state.initializedAt,
                assetsRequested: state.assetsRequested
            };
        }
    });
})();
