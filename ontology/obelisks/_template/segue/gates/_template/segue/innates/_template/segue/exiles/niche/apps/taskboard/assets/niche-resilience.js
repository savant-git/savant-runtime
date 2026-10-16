"use strict";

/*
 * savant / niche
 * browser resilience and interaction continuity
 *
 * owner: exile:niche
 * authority_effect: none
 *
 * Presentation only. This module does not create, alter, infer, or own
 * authoritative Savant task state.
 */

(() => {
    "use strict";

    const state = {
        activeElement: null,
        scroll: new Map(),
        surfaceScroll: new Map(),
        inspectorTask: null,
        refreshPending: false,
        resizeFrame: 0,
        lastWidth: 0,
        lastHeight: 0,
        compact: false,
        narrow: false
    };

    const $ = (selector, root = document) =>
        root.querySelector(selector);

    const $$ = (selector, root = document) =>
        Array.from(root.querySelectorAll(selector));

    function visible(element) {
        if (!element || element.hidden) {
            return false;
        }

        const style =
            window.getComputedStyle(element);

        return (
            style.display !== "none" &&
            style.visibility !== "hidden"
        );
    }

    function elementKey(element) {
        if (!element) {
            return null;
        }

        if (element.id) {
            return `#${element.id}`;
        }

        if (element.dataset?.taskId) {
            return `[data-task-id="${CSS.escape(element.dataset.taskId)}"]`;
        }

        if (element.dataset?.view) {
            return `[data-view="${CSS.escape(element.dataset.view)}"]`;
        }

        return null;
    }

    function rememberFocus() {
        state.activeElement =
            elementKey(
                document.activeElement
            );
    }

    function restoreFocus() {
        if (!state.activeElement) {
            return;
        }

        const element =
            $(state.activeElement);

        if (
            element &&
            visible(element)
        ) {
            try {
                element.focus({
                    preventScroll: true
                });
            } catch {
                element.focus();
            }
        }
    }

    function rememberScroll() {
        state.scroll.set(
            "window",
            {
                x: window.scrollX,
                y: window.scrollY
            }
        );

        [
            "#flow-board",
            "#graph-stage",
            "#living-grid",
            "#timeline",
            "#history-list",
            "#inspector",
            "#palette-results"
        ].forEach((selector) => {
            const element =
                $(selector);

            if (!element) {
                return;
            }

            state.scroll.set(
                selector,
                {
                    x: element.scrollLeft,
                    y: element.scrollTop
                }
            );
        });

        $$(".surface").forEach(
            (surface) => {
                const name =
                    surface.dataset.surface;

                if (!name) {
                    return;
                }

                state.surfaceScroll.set(
                    name,
                    {
                        x: surface.scrollLeft,
                        y: surface.scrollTop
                    }
                );
            }
        );
    }

    function restoreScroll() {
        const windowPosition =
            state.scroll.get("window");

        if (windowPosition) {
            window.scrollTo(
                windowPosition.x,
                windowPosition.y
            );
        }

        for (
            const [selector, position]
            of state.scroll
        ) {
            if (
                selector === "window"
            ) {
                continue;
            }

            const element =
                $(selector);

            if (!element) {
                continue;
            }

            element.scrollLeft =
                position.x;

            element.scrollTop =
                position.y;
        }

        for (
            const [name, position]
            of state.surfaceScroll
        ) {
            const surface =
                $(
                    `[data-surface="${CSS.escape(name)}"]`
                );

            if (!surface) {
                continue;
            }

            surface.scrollLeft =
                position.x;

            surface.scrollTop =
                position.y;
        }
    }

    function rememberInspector() {
        const inspector =
            $("#inspector");

        if (
            !inspector ||
            !inspector.classList.contains(
                "open"
            )
        ) {
            state.inspectorTask = null;
            return;
        }

        const selected =
            $(".task-card[aria-current='true']");

        state.inspectorTask =
            selected?.dataset.taskId ||
            null;
    }

    function preserveWorkspace() {
        rememberFocus();
        rememberScroll();
        rememberInspector();
    }

    function restoreWorkspace() {
        window.requestAnimationFrame(
            () => {
                restoreScroll();
                restoreFocus();
            }
        );
    }

    function usableWidth() {
        return Math.max(
            1,
            window.visualViewport?.width ||
            window.innerWidth ||
            document.documentElement.clientWidth
        );
    }

    function usableHeight() {
        return Math.max(
            1,
            window.visualViewport?.height ||
            window.innerHeight ||
            document.documentElement.clientHeight
        );
    }

    function updateGeometry() {
        state.resizeFrame = 0;

        const width =
            usableWidth();

        const height =
            usableHeight();

        if (
            width === state.lastWidth &&
            height === state.lastHeight
        ) {
            return;
        }

        state.lastWidth = width;
        state.lastHeight = height;

        state.compact =
            width < 1120;

        state.narrow =
            width < 720;

        document.documentElement
            .style
            .setProperty(
                "--niche-safe-width",
                `${width}px`
            );

        document.documentElement
            .style
            .setProperty(
                "--niche-safe-height",
                `${height}px`
            );

        document.body.classList.toggle(
            "niche-compact",
            state.compact
        );

        document.body.classList.toggle(
            "niche-narrow",
            state.narrow
        );

        document.body.classList.toggle(
            "niche-short",
            height < 620
        );

        document.body.classList.toggle(
            "niche-landscape",
            width > height
        );

        normalizePanels();
    }

    function scheduleGeometry() {
        if (state.resizeFrame) {
            return;
        }

        state.resizeFrame =
            window.requestAnimationFrame(
                updateGeometry
            );
    }

    function normalizePanels() {
        const width =
            usableWidth();

        const inspector =
            $("#inspector");

        if (inspector) {
            const maximum =
                Math.max(
                    280,
                    Math.min(
                        560,
                        width - 16
                    )
                );

            inspector.style.setProperty(
                "--niche-inspector-max",
                `${maximum}px`
            );
        }

        const dialogs =
            $$(".dialog");

        for (const dialog of dialogs) {
            dialog.style.maxWidth =
                `${Math.max(
                    280,
                    Math.min(
                        680,
                        width - 20
                    )
                )}px`;
        }

        const palette =
            $(".palette");

        if (palette) {
            palette.style.maxWidth =
                `${Math.max(
                    280,
                    Math.min(
                        760,
                        width - 20
                    )
                )}px`;
        }
    }

    function repairHiddenLayers() {
        $$(
            ".dialog-shell[hidden], .palette-shell[hidden]"
        ).forEach((element) => {
            element.style.setProperty(
                "display",
                "none",
                "important"
            );
        });

        $$(
            ".dialog-shell:not([hidden]), .palette-shell:not([hidden])"
        ).forEach((element) => {
            if (
                element.style.display ===
                "none"
            ) {
                element.style.removeProperty(
                    "display"
                );
            }
        });
    }

    function preventBackgroundInteraction() {
        const modalOpen =
            visible(
                $(".dialog-shell:not([hidden])")
            ) ||
            visible(
                $(".palette-shell:not([hidden])")
            );

        document.body.classList.toggle(
            "niche-modal-open",
            modalOpen
        );

        const main =
            $("#main");

        if (main) {
            if (modalOpen) {
                main.setAttribute(
                    "inert",
                    ""
                );
            } else {
                main.removeAttribute(
                    "inert"
                );
            }
        }
    }

    function updateTransientState() {
        repairHiddenLayers();
        preventBackgroundInteraction();
    }

    function installTransientObserver() {
        if (
            !("MutationObserver" in window)
        ) {
            return;
        }

        const observer =
            new MutationObserver(
                updateTransientState
            );

        observer.observe(
            document.body,
            {
                subtree: true,
                attributes: true,
                attributeFilter: [
                    "hidden"
                ]
            }
        );
    }

    function makeTaskCardsSemantic() {
        $$(".task-card").forEach(
            (card) => {
                if (
                    !card.hasAttribute(
                        "role"
                    )
                ) {
                    card.setAttribute(
                        "role",
                        "button"
                    );
                }

                const title =
                    $("h3", card)
                        ?.textContent
                        ?.trim() ||
                    "Task";

                const stateName =
                    card.dataset.state ||
                    "unknown";

                card.setAttribute(
                    "aria-label",
                    `${title}. State ${stateName}. Open task inspector.`
                );
            }
        );
    }

    function makeLivingSemantic() {
        $$(".living-surface").forEach(
            (surface) => {
                if (
                    !surface.hasAttribute(
                        "role"
                    )
                ) {
                    surface.setAttribute(
                        "role",
                        "button"
                    );
                }

                const name =
                    $("h3", surface)
                        ?.textContent
                        ?.trim() ||
                    "Living surface";

                surface.setAttribute(
                    "aria-label",
                    `${name}. Projected living surface. Open details.`
                );
            }
        );
    }

    function markSelectedTask() {
        const inspector =
            $("#inspector");

        if (
            !inspector ||
            !inspector.classList.contains(
                "open"
            )
        ) {
            $$(".task-card").forEach(
                (card) =>
                    card.removeAttribute(
                        "aria-current"
                    )
            );

            return;
        }

        const title =
            $("#inspector-title")
                ?.textContent
                ?.trim();

        if (!title) {
            return;
        }

        $$(".task-card").forEach(
            (card) => {
                const cardTitle =
                    $("h3", card)
                        ?.textContent
                        ?.trim();

                if (
                    cardTitle === title
                ) {
                    card.setAttribute(
                        "aria-current",
                        "true"
                    );
                } else {
                    card.removeAttribute(
                        "aria-current"
                    );
                }
            }
        );
    }

    function semanticPass() {
        makeTaskCardsSemantic();
        makeLivingSemantic();
        markSelectedTask();
        updateTransientState();
    }

    function installSemanticObserver() {
        if (
            !("MutationObserver" in window)
        ) {
            return;
        }

        const observer =
            new MutationObserver(() => {
                window.clearTimeout(
                    semanticPass.timer
                );

                semanticPass.timer =
                    window.setTimeout(
                        semanticPass,
                        40
                    );
            });

        observer.observe(
            $("#main") ||
            document.body,
            {
                childList: true,
                subtree: true
            }
        );
    }

    function installRefreshContinuity() {
        const refresh =
            $("#refresh");

        if (refresh) {
            refresh.addEventListener(
                "pointerdown",
                preserveWorkspace,
                {
                    capture: true
                }
            );

            refresh.addEventListener(
                "click",
                () => {
                    window.setTimeout(
                        restoreWorkspace,
                        100
                    );
                }
            );
        }

        document.addEventListener(
            "visibilitychange",
            () => {
                if (document.hidden) {
                    preserveWorkspace();
                } else {
                    window.setTimeout(
                        restoreWorkspace,
                        120
                    );
                }
            }
        );
    }

    function installTouchProtection() {
        document.addEventListener(
            "touchstart",
            (event) => {
                const target =
                    event.target.closest(
                        "button, .task-card, .living-surface, .compact-item"
                    );

                if (!target) {
                    return;
                }

                target.classList.add(
                    "niche-touch-active"
                );
            },
            {
                passive: true
            }
        );

        const clear = () => {
            $$(".niche-touch-active")
                .forEach(
                    (element) =>
                        element.classList.remove(
                            "niche-touch-active"
                        )
                );
        };

        document.addEventListener(
            "touchend",
            clear,
            {
                passive: true
            }
        );

        document.addEventListener(
            "touchcancel",
            clear,
            {
                passive: true
            }
        );
    }

    function installSafeArea() {
        document.body.classList.add(
            "niche-safe-area"
        );
    }

    function installKeyboardNavigation() {
        document.addEventListener(
            "keydown",
            (event) => {
                const target =
                    event.target;

                if (
                    target instanceof
                        HTMLInputElement ||
                    target instanceof
                        HTMLTextAreaElement ||
                    target instanceof
                        HTMLSelectElement ||
                    target?.isContentEditable
                ) {
                    return;
                }

                if (
                    event.key ===
                    "Home" &&
                    event.altKey
                ) {
                    event.preventDefault();

                    window.Niche?.view?.(
                        "execute"
                    );

                    window.scrollTo(
                        0,
                        0
                    );

                    $("#start-next")
                        ?.focus();
                }

                if (
                    event.key ===
                    "r" &&
                    event.altKey
                ) {
                    event.preventDefault();

                    preserveWorkspace();

                    Promise.resolve(
                        window.Niche
                            ?.refresh?.()
                    ).finally(
                        restoreWorkspace
                    );
                }
            }
        );
    }

    function initialize() {
        installSafeArea();
        updateGeometry();
        updateTransientState();
        semanticPass();

        installTransientObserver();
        installSemanticObserver();
        installRefreshContinuity();
        installTouchProtection();
        installKeyboardNavigation();

        window.addEventListener(
            "resize",
            scheduleGeometry,
            {
                passive: true
            }
        );

        window.addEventListener(
            "orientationchange",
            scheduleGeometry,
            {
                passive: true
            }
        );

        if (
            window.visualViewport
        ) {
            window.visualViewport
                .addEventListener(
                    "resize",
                    scheduleGeometry,
                    {
                        passive: true
                    }
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

    window.NicheResilience =
        Object.freeze({
            preserve:
                preserveWorkspace,
            restore:
                restoreWorkspace,
            geometry:
                updateGeometry,
            semantics:
                semanticPass
        });
})();
