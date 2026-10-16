"use strict";

/*
 * savant / niche
 * load finalizer
 *
 * owner: exile:niche
 * authority_effect: none
 */

(() => {
    "use strict";

    function finalize() {
        const modules = {
            bootstrap:
                Boolean(
                    window.NicheBootstrap
                ),
            safe_selector:
                Boolean(
                    window.NicheSafeSelector
                ),
            responsive:
                Boolean(
                    window.NicheResponsive
                ),
            viewport_guard:
                Boolean(
                    window.NicheViewportGuard
                ),
            core:
                Boolean(
                    window.Niche
                ),
            enhancements:
                Boolean(
                    window.NicheEnhancements
                ),
            resilience:
                Boolean(
                    window.NicheResilience
                ),
            continuity:
                Boolean(
                    window.NicheContinuity
                ),
            spatial_state:
                Boolean(
                    window.NicheSpatialState
                ),
            focus:
                Boolean(
                    window.NicheFocus
                ),
            api_resilience:
                Boolean(
                    window.NicheApiResilience
                ),
            recovery:
                Boolean(
                    window.NicheRecovery
                ),
            unknowns:
                Boolean(
                    window.NicheUnknowns
                ),
            replay:
                Boolean(
                    window.NicheReplay
                ),
            diagnostics:
                Boolean(
                    window.NicheDiagnostics
                ),
            runtime_guard:
                Boolean(
                    window.NicheRuntimeGuard
                ),
            command_extensions:
                Boolean(
                    window.NicheCommandExtensions
                ),
            accessibility:
                Boolean(
                    window.NicheAccessibility
                ),
            performance:
                Boolean(
                    window.NichePerformance
                ),
            motion:
                Boolean(
                    window.NicheMotion
                ),
            health_wave:
                Boolean(
                    window.NicheHealthWave
                )
        };

        const missing =
            Object.entries(
                modules
            )
                .filter(
                    ([, loaded]) =>
                        !loaded
                )
                .map(
                    ([name]) =>
                        name
                );

        document.documentElement
            .dataset
            .nicheModules =
            missing.length
                ? "degraded"
                : "loaded";

        window.dispatchEvent(
            new CustomEvent(
                "niche:modules-ready",
                {
                    detail: {
                        modules,
                        missing,
                        authority_effect:
                            "none"
                    }
                }
            )
        );
    }

    if (
        document.readyState ===
        "complete"
    ) {
        finalize();
    } else {
        window.addEventListener(
            "load",
            finalize,
            {
                once: true
            }
        );
    }

    window.NicheLoadFinalizer =
        Object.freeze({
            finalize
        });
})();
