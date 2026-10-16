"use strict";

/*
 * savant / niche
 * viewport geometry guard
 *
 * owner: exile:niche
 * authority_effect: none
 *
 * Publishes measured browser geometry so the interface can remain
 * usable across viewport sizes, browser chrome changes, zoom, software
 * keyboards, orientation changes, and safe-area constrained devices.
 */

(() => {
    "use strict";

    const root =
        document.documentElement;

    const state = {
        width: 0,
        height: 0,
        visualWidth: 0,
        visualHeight: 0,
        offsetTop: 0,
        offsetLeft: 0,
        keyboard: 0,
        compactHeight: false,
        narrow: false,
        scheduled: false
    };

    function px(name, value) {
        root.style.setProperty(
            name,
            `${Math.max(0, value)}px`
        );
    }

    function measure() {
        state.scheduled = false;

        const viewport =
            window.visualViewport;

        const layoutWidth =
            Math.max(
                1,
                root.clientWidth,
                window.innerWidth || 0
            );

        const layoutHeight =
            Math.max(
                1,
                root.clientHeight,
                window.innerHeight || 0
            );

        const visualWidth =
            viewport?.width ||
            layoutWidth;

        const visualHeight =
            viewport?.height ||
            layoutHeight;

        const offsetTop =
            viewport?.offsetTop || 0;

        const offsetLeft =
            viewport?.offsetLeft || 0;

        const keyboard =
            Math.max(
                0,
                layoutHeight -
                visualHeight -
                offsetTop
            );

        state.width =
            layoutWidth;

        state.height =
            layoutHeight;

        state.visualWidth =
            visualWidth;

        state.visualHeight =
            visualHeight;

        state.offsetTop =
            offsetTop;

        state.offsetLeft =
            offsetLeft;

        state.keyboard =
            keyboard;

        state.compactHeight =
            visualHeight < 620;

        state.narrow =
            visualWidth < 520;

        px(
            "--niche-layout-width",
            layoutWidth
        );

        px(
            "--niche-layout-height",
            layoutHeight
        );

        px(
            "--niche-visual-width",
            visualWidth
        );

        px(
            "--niche-visual-height",
            visualHeight
        );

        px(
            "--niche-visual-top",
            offsetTop
        );

        px(
            "--niche-visual-left",
            offsetLeft
        );

        px(
            "--niche-keyboard-height",
            keyboard
        );

        root.dataset.nicheKeyboard =
            keyboard > 80
                ? "open"
                : "closed";

        root.dataset.nicheHeight =
            state.compactHeight
                ? "compact"
                : "normal";

        root.dataset.nicheWidth =
            state.narrow
                ? "narrow"
                : "normal";

        window.dispatchEvent(
            new CustomEvent(
                "niche:geometry",
                {
                    detail: {
                        ...state,
                        scheduled:
                            undefined,
                        authority_effect:
                            "none"
                    }
                }
            )
        );
    }

    function schedule() {
        if (state.scheduled) {
            return;
        }

        state.scheduled = true;

        requestAnimationFrame(
            measure
        );
    }

    function initialize() {
        schedule();

        window.addEventListener(
            "resize",
            schedule,
            {
                passive: true
            }
        );

        window.addEventListener(
            "orientationchange",
            schedule,
            {
                passive: true
            }
        );

        window.visualViewport
            ?.addEventListener(
                "resize",
                schedule,
                {
                    passive: true
                }
            );

        window.visualViewport
            ?.addEventListener(
                "scroll",
                schedule,
                {
                    passive: true
                }
            );

        if (
            "ResizeObserver" in
            window
        ) {
            new ResizeObserver(
                schedule
            ).observe(
                root
            );
        }
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

    window.NicheViewportGuard =
        Object.freeze({
            measure,

            state() {
                return {
                    width:
                        state.width,
                    height:
                        state.height,
                    visualWidth:
                        state.visualWidth,
                    visualHeight:
                        state.visualHeight,
                    offsetTop:
                        state.offsetTop,
                    offsetLeft:
                        state.offsetLeft,
                    keyboard:
                        state.keyboard,
                    compactHeight:
                        state.compactHeight,
                    narrow:
                        state.narrow
                };
            }
        });
})();
