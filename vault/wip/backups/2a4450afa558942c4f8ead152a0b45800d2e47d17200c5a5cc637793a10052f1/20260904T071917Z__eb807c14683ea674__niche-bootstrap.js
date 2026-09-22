"use strict";

/*
 * savant / niche
 * frontend bootstrap coordinator
 *
 * owner: exile:niche
 * authority_effect: none
 *
 * Loads the optional executable-environment presentation layer.
 * Failure of that layer never prevents the authoritative Niche
 * task interface from booting.
 */

(() => {
    "use strict";

    const state = {
        ready: false,
        initializedAt: null,
        executableEnvironment: "pending"
    };

    const enhancementStylesheet =
        "/assets/niche-executable-environment.css";

    const enhancementScript =
        "/assets/niche-executable-environment.js";

    function loadStylesheet() {
        if (
            document.querySelector(
                `link[href="${enhancementStylesheet}"]`
            )
        ) {
            return;
        }

        const link =
            document.createElement("link");

        link.rel = "stylesheet";
        link.href = enhancementStylesheet;
        link.dataset.nicheProjection =
            "executable-environment";

        link.addEventListener(
            "error",
            () => {
                state.executableEnvironment =
                    "degraded";

                document.documentElement
                    .dataset
                    .nicheExecutableEnvironment =
                    "degraded";
            },
            {
                once: true
            }
        );

        document.head.appendChild(
            link
        );
    }

    function loadScript() {
        if (
            document.querySelector(
                `script[src="${enhancementScript}"]`
            )
        ) {
            return;
        }

        const script =
            document.createElement("script");

        script.src =
            enhancementScript;

        script.defer = true;

        script.dataset.nicheProjection =
            "executable-environment";

        script.addEventListener(
            "load",
            () => {
                state.executableEnvironment =
                    "loaded";

                document.documentElement
                    .dataset
                    .nicheExecutableEnvironment =
                    "loaded";
            },
            {
                once: true
            }
        );

        script.addEventListener(
            "error",
            () => {
                state.executableEnvironment =
                    "degraded";

                document.documentElement
                    .dataset
                    .nicheExecutableEnvironment =
                    "degraded";
            },
            {
                once: true
            }
        );

        document.body.appendChild(
            script
        );
    }

    function loadExecutableEnvironment() {
        try {
            loadStylesheet();
            loadScript();

        } catch (error) {
            state.executableEnvironment =
                "degraded";

            document.documentElement
                .dataset
                .nicheExecutableEnvironment =
                "degraded";

            console.warn(
                "niche executable environment enhancement unavailable",
                error
            );
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

        loadExecutableEnvironment();

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
                        state.initializedAt,
                    executableEnvironment:
                        state.executableEnvironment
                };
            }
        });
})();
