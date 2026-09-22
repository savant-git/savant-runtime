"use strict";

/*
 * savant / niche
 * spatial continuity
 *
 * owner: exile:niche
 * authority_effect: none
 *
 * Preserves interface position only. No task state is persisted here.
 */

(() => {
    "use strict";

    const KEY =
        "savant.niche.spatial.v1";

    const state = {
        views: Object.create(null)
    };

    function read() {
        try {
            const parsed =
                JSON.parse(
                    sessionStorage
                        .getItem(KEY) ||
                    "{}"
                );

            if (
                parsed &&
                typeof parsed ===
                    "object" &&
                parsed.views &&
                typeof parsed.views ===
                    "object"
            ) {
                state.views =
                    parsed.views;
            }
        } catch {
            state.views =
                Object.create(null);
        }
    }

    function write() {
        try {
            sessionStorage.setItem(
                KEY,
                JSON.stringify({
                    views:
                        state.views
                })
            );
        } catch {
            /* projection continuity is optional */
        }
    }

    function activeSurface() {
        return (
            document.querySelector(
                ".surface.active"
            ) ||
            document.querySelector(
                ".surface:not([hidden])"
            )
        );
    }

    function activeName() {
        return (
            activeSurface()
                ?.dataset
                ?.surface ||
            "execute"
        );
    }

    function capture() {
        const name =
            activeName();

        const surface =
            activeSurface();

        if (!surface) {
            return;
        }

        state.views[name] = {
            windowX:
                window.scrollX,
            windowY:
                window.scrollY,
            surfaceX:
                surface.scrollLeft,
            surfaceY:
                surface.scrollTop
        };

        write();
    }

    function restore(name) {
        const saved =
            state.views[name];

        if (!saved) {
            return;
        }

        requestAnimationFrame(
            () => {
                const surface =
                    document.querySelector(
                        `[data-surface="${CSS.escape(name)}"]`
                    );

                if (surface) {
                    surface.scrollLeft =
                        Number(
                            saved.surfaceX
                        ) || 0;

                    surface.scrollTop =
                        Number(
                            saved.surfaceY
                        ) || 0;
                }

                window.scrollTo(
                    Number(
                        saved.windowX
                    ) || 0,
                    Number(
                        saved.windowY
                    ) || 0
                );
            }
        );
    }

    function initialize() {
        read();

        let previous =
            activeName();

        document.addEventListener(
            "click",
            (event) => {
                const control =
                    event.target.closest(
                        "[data-view]"
                    );

                if (!control) {
                    return;
                }

                capture();

                const next =
                    control.dataset.view;

                previous =
                    next;

                window.setTimeout(
                    () => {
                        restore(next);
                    },
                    0
                );
            },
            true
        );

        window.addEventListener(
            "pagehide",
            capture
        );

        document.addEventListener(
            "visibilitychange",
            () => {
                if (
                    document.visibilityState ===
                    "hidden"
                ) {
                    capture();
                }
            }
        );

        new MutationObserver(
            () => {
                const current =
                    activeName();

                if (
                    current !==
                    previous
                ) {
                    previous =
                        current;

                    restore(current);
                }
            }
        ).observe(
            document.body,
            {
                attributes: true,
                subtree: true,
                attributeFilter: [
                    "class",
                    "hidden"
                ]
            }
        );

        restore(previous);
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

    window.NicheSpatialState =
        Object.freeze({
            capture,
            restore,

            state() {
                return JSON.parse(
                    JSON.stringify(
                        state.views
                    )
                );
            }
        });
})();
