"use strict";

/*
 * savant / niche
 * rendering coordinator
 *
 * owner: exile:niche
 * authority_effect: none
 */

(() => {
    "use strict";

    const state = {
        visible: true,
        frame: null,
        queued: new Map()
    };

    function flush() {
        state.frame = null;

        if (!state.visible) {
            return;
        }

        const work =
            Array.from(
                state.queued.values()
            );

        state.queued.clear();

        for (const callback of work) {
            try {
                callback();
            } catch (error) {
                window.dispatchEvent(
                    new CustomEvent(
                        "niche:render-error",
                        {
                            detail: {
                                message:
                                    String(
                                        error?.message ||
                                        error
                                    ),
                                authority_effect:
                                    "none"
                            }
                        }
                    )
                );
            }
        }
    }

    function schedule(
        key,
        callback
    ) {
        if (
            typeof callback !==
            "function"
        ) {
            return;
        }

        state.queued.set(
            String(key),
            callback
        );

        if (
            !state.visible ||
            state.frame !== null
        ) {
            return;
        }

        state.frame =
            requestAnimationFrame(
                flush
            );
    }

    function cancel(key) {
        state.queued.delete(
            String(key)
        );
    }

    function initialize() {
        document.addEventListener(
            "visibilitychange",
            () => {
                state.visible =
                    document.visibilityState !==
                    "hidden";

                if (
                    state.visible &&
                    state.queued.size &&
                    state.frame ===
                        null
                ) {
                    state.frame =
                        requestAnimationFrame(
                            flush
                        );
                }
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

    window.NichePerformance =
        Object.freeze({
            schedule,
            cancel,

            state() {
                return {
                    visible:
                        state.visible,
                    queued:
                        state.queued.size
                };
            }
        });
})();
