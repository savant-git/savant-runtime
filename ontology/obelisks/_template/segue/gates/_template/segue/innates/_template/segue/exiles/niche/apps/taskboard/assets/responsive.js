"use strict";

/*
 * savant / niche
 * responsive interaction substrate
 *
 * projection/interface behavior only.
 * authority_effect: none
 *
 * This module does not mutate task state. It observes the browser
 * environment and exposes deterministic presentation state to Niche.
 */

(() => {
    const root = document.documentElement;

    const state = {
        width: 0,
        height: 0,
        visualWidth: 0,
        visualHeight: 0,
        scale: 1,
        orientation: "portrait",
        mode: "desktop",
        pointer: "fine",
        hover: true,
        reducedMotion: false,
        keyboardInset: 0,
        navHeight: 0,
        headerHeight: 0,
        statusHeight: 0
    };

    let frame = 0;
    let lastSignature = "";

    const media = {
        coarse: window.matchMedia("(pointer: coarse)"),
        hover: window.matchMedia("(hover: hover)"),
        reduced: window.matchMedia("(prefers-reduced-motion: reduce)")
    };

    function number(value) {
        return Number.isFinite(value) ? value : 0;
    }

    function px(value) {
        return `${Math.max(0, Math.round(number(value)))}px`;
    }

    function viewport() {
        const vv = window.visualViewport;

        const width = Math.max(
            1,
            number(window.innerWidth),
            number(document.documentElement.clientWidth)
        );

        const height = Math.max(
            1,
            number(window.innerHeight),
            number(document.documentElement.clientHeight)
        );

        const visualWidth = vv ? Math.max(1, number(vv.width)) : width;
        const visualHeight = vv ? Math.max(1, number(vv.height)) : height;
        const scale = vv ? Math.max(0.1, number(vv.scale) || 1) : 1;

        return {
            width,
            height,
            visualWidth,
            visualHeight,
            scale
        };
    }

    function modeFor(width, height) {
        if (width <= 430) {
            return "phone-narrow";
        }

        if (width <= 700) {
            if (height <= 520 && width > height) {
                return "phone-landscape";
            }

            return "phone";
        }

        if (width <= 900) {
            return "tablet";
        }

        if (width <= 1180) {
            return "compact";
        }

        return "desktop";
    }

    function measure(selector) {
        const element = document.querySelector(selector);

        if (!element) {
            return 0;
        }

        const rect = element.getBoundingClientRect();

        return Math.max(0, rect.height);
    }

    function updateState() {
        const next = viewport();

        state.width = next.width;
        state.height = next.height;
        state.visualWidth = next.visualWidth;
        state.visualHeight = next.visualHeight;
        state.scale = next.scale;

        state.orientation =
            next.visualWidth > next.visualHeight
                ? "landscape"
                : "portrait";

        state.mode = modeFor(next.visualWidth, next.visualHeight);
        state.pointer = media.coarse.matches ? "coarse" : "fine";
        state.hover = media.hover.matches;
        state.reducedMotion = media.reduced.matches;

        state.headerHeight = measure(".topbar");
        state.statusHeight = measure(".statusrail");
        state.navHeight =
            next.visualWidth <= 700
                ? measure(".nav")
                : 0;

        /*
         * VisualViewport becomes smaller when many mobile browsers expose
         * their software keyboard. This value is presentation metadata only.
         */
        state.keyboardInset = Math.max(
            0,
            next.height - next.visualHeight
        );
    }

    function publishCss() {
        root.style.setProperty("--niche-vw", px(state.visualWidth));
        root.style.setProperty("--niche-vh", px(state.visualHeight));
        root.style.setProperty("--niche-layout-vh", px(state.height));
        root.style.setProperty("--niche-header-live", px(state.headerHeight));
        root.style.setProperty("--niche-status-live", px(state.statusHeight));
        root.style.setProperty("--niche-nav-live", px(state.navHeight));
        root.style.setProperty(
            "--niche-keyboard-inset",
            px(state.keyboardInset)
        );

        root.dataset.nicheMode = state.mode;
        root.dataset.nicheOrientation = state.orientation;
        root.dataset.nichePointer = state.pointer;
        root.dataset.nicheHover = state.hover ? "true" : "false";
        root.dataset.nicheReducedMotion =
            state.reducedMotion ? "true" : "false";
    }

    function publishEvent() {
        const signature = JSON.stringify(state);

        if (signature === lastSignature) {
            return;
        }

        lastSignature = signature;

        window.dispatchEvent(
            new CustomEvent("niche:viewport", {
                detail: Object.freeze({ ...state })
            })
        );
    }

    function apply() {
        frame = 0;

        updateState();
        publishCss();
        publishEvent();
    }

    function schedule() {
        if (frame) {
            return;
        }

        frame = window.requestAnimationFrame(apply);
    }

    function visible(element) {
        if (!element) {
            return false;
        }

        if (element.hidden) {
            return false;
        }

        const style = window.getComputedStyle(element);

        return (
            style.display !== "none" &&
            style.visibility !== "hidden"
        );
    }

    function focusables(container) {
        if (!container) {
            return [];
        }

        return Array.from(
            container.querySelectorAll(
                [
                    "a[href]",
                    "button:not([disabled])",
                    "input:not([disabled])",
                    "select:not([disabled])",
                    "textarea:not([disabled])",
                    "[tabindex]:not([tabindex='-1'])"
                ].join(",")
            )
        ).filter((element) => {
            if (element.hidden) {
                return false;
            }

            const style = window.getComputedStyle(element);

            return (
                style.display !== "none" &&
                style.visibility !== "hidden"
            );
        });
    }

    function topTransientLayer() {
        const candidates = [
            ...document.querySelectorAll(
                ".dialog-shell, .palette-shell, .inspector.open"
            )
        ].filter(visible);

        if (!candidates.length) {
            return null;
        }

        return candidates[candidates.length - 1];
    }

    function trapTab(event) {
        if (event.key !== "Tab") {
            return;
        }

        const layer = topTransientLayer();

        if (!layer) {
            return;
        }

        const items = focusables(layer);

        if (!items.length) {
            return;
        }

        const first = items[0];
        const last = items[items.length - 1];
        const active = document.activeElement;

        if (event.shiftKey && active === first) {
            event.preventDefault();
            last.focus();
            return;
        }

        if (!event.shiftKey && active === last) {
            event.preventDefault();
            first.focus();
        }
    }

    function closeTransient(event) {
        if (event.key !== "Escape") {
            return;
        }

        const dialog = Array.from(
            document.querySelectorAll(".dialog-shell:not([hidden])")
        ).pop();

        if (dialog) {
            const cancel =
                dialog.querySelector(
                    "[data-dialog-cancel], [data-action='cancel'], .cancel"
                );

            if (cancel instanceof HTMLElement) {
                cancel.click();
                return;
            }

            dialog.hidden = true;
            return;
        }

        const palette = document.querySelector(
            ".palette-shell:not([hidden])"
        );

        if (palette) {
            palette.hidden = true;
            return;
        }

        const inspector = document.querySelector(".inspector.open");

        if (inspector) {
            const close =
                inspector.querySelector(
                    "[data-inspector-close], [data-action='close']"
                );

            if (close instanceof HTMLElement) {
                close.click();
                return;
            }

            inspector.classList.remove("open");
        }
    }

    function repairTransientVisibility() {
        document
            .querySelectorAll("[hidden]")
            .forEach((element) => {
                if (
                    element instanceof HTMLElement &&
                    element.style.display &&
                    element.style.display !== "none"
                ) {
                    element.style.removeProperty("display");
                }
            });
    }

    function observeLayout() {
        if (!("ResizeObserver" in window)) {
            return;
        }

        const observer = new ResizeObserver(schedule);

        [
            ".topbar",
            ".statusrail",
            ".nav",
            "main"
        ].forEach((selector) => {
            const element = document.querySelector(selector);

            if (element) {
                observer.observe(element);
            }
        });
    }

    function observeTransientLayers() {
        if (!("MutationObserver" in window)) {
            return;
        }

        const observer = new MutationObserver(() => {
            repairTransientVisibility();
            schedule();
        });

        observer.observe(document.body, {
            subtree: true,
            attributes: true,
            attributeFilter: [
                "hidden",
                "class",
                "style"
            ]
        });
    }

    function bindMedia(query) {
        if (typeof query.addEventListener === "function") {
            query.addEventListener("change", schedule);
            return;
        }

        if (typeof query.addListener === "function") {
            query.addListener(schedule);
        }
    }

    window.addEventListener("resize", schedule, {
        passive: true
    });

    window.addEventListener("orientationchange", schedule, {
        passive: true
    });

    window.addEventListener("pageshow", schedule, {
        passive: true
    });

    document.addEventListener("keydown", trapTab, true);
    document.addEventListener("keydown", closeTransient, true);

    bindMedia(media.coarse);
    bindMedia(media.hover);
    bindMedia(media.reduced);

    if (window.visualViewport) {
        window.visualViewport.addEventListener(
            "resize",
            schedule,
            { passive: true }
        );

        window.visualViewport.addEventListener(
            "scroll",
            schedule,
            { passive: true }
        );
    }

    document.addEventListener(
        "DOMContentLoaded",
        () => {
            repairTransientVisibility();
            observeLayout();
            observeTransientLayers();
            apply();
        },
        { once: true }
    );

    window.NicheResponsive = Object.freeze({
        state: () => ({ ...state }),
        refresh: schedule
    });
})();
