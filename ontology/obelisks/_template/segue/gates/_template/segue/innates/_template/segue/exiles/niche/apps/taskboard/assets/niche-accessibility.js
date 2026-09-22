"use strict";

/*
 * savant / niche
 * accessibility projection
 *
 * owner: exile:niche
 * authority_effect: none
 */

(() => {
    "use strict";

    const state = {
        initialized: false,
        lastAnnouncement: ""
    };

    function createLiveRegion() {
        let region =
            document.getElementById(
                "niche-a11y-live"
            );

        if (region) {
            return region;
        }

        region =
            document.createElement(
                "div"
            );

        region.id =
            "niche-a11y-live";

        region.className =
            "sr-only";

        region.setAttribute(
            "role",
            "status"
        );

        region.setAttribute(
            "aria-live",
            "polite"
        );

        region.setAttribute(
            "aria-atomic",
            "true"
        );

        document.body.append(
            region
        );

        return region;
    }

    function announce(message) {
        if (
            !message ||
            message ===
                state.lastAnnouncement
        ) {
            return;
        }

        state.lastAnnouncement =
            message;

        const region =
            createLiveRegion();

        region.textContent = "";

        requestAnimationFrame(
            () => {
                region.textContent =
                    message;
            }
        );
    }

    function labelTask(element) {
        const title =
            element.querySelector(
                "h1, h2, h3, strong"
            )?.textContent
                ?.trim();

        const id =
            element.dataset.taskId;

        if (
            !element.hasAttribute(
                "tabindex"
            )
        ) {
            element.tabIndex = 0;
        }

        if (
            !element.hasAttribute(
                "role"
            )
        ) {
            element.setAttribute(
                "role",
                "button"
            );
        }

        if (
            !element.hasAttribute(
                "aria-label"
            )
        ) {
            element.setAttribute(
                "aria-label",
                title ||
                id ||
                "Niche task"
            );
        }
    }

    function reconcile() {
        document
            .querySelectorAll(
                "[data-task-id]"
            )
            .forEach(
                labelTask
            );

        document
            .querySelectorAll(
                "[data-view]"
            )
            .forEach(
                (button) => {
                    const selected =
                        button.classList
                            .contains(
                                "active"
                            ) ||
                        button.getAttribute(
                            "aria-current"
                        ) === "page";

                    button.setAttribute(
                        "aria-pressed",
                        selected
                            ? "true"
                            : "false"
                    );
                }
            );
    }

    function installKeyboardActivation() {
        document.addEventListener(
            "keydown",
            (event) => {
                if (
                    event.key !==
                        "Enter" &&
                    event.key !==
                        " "
                ) {
                    return;
                }

                const task =
                    event.target.closest?.(
                        "[data-task-id]"
                    );

                if (!task) {
                    return;
                }

                if (
                    event.target.closest(
                        "button, a, input, textarea, select"
                    )
                ) {
                    return;
                }

                event.preventDefault();

                task.click();
            }
        );
    }

    function installAnnouncements() {
        window.addEventListener(
            "niche:api-status",
            (event) => {
                const results =
                    Object.values(
                        event.detail
                            ?.results ||
                        {}
                    );

                if (!results.length) {
                    return;
                }

                const failed =
                    results.filter(
                        (result) =>
                            !result?.ok
                    ).length;

                announce(
                    failed
                        ? `Niche is degraded. ${failed} projections are unavailable.`
                        : "Niche projections are available."
                );
            }
        );

        window.addEventListener(
            "niche:recovery",
            (event) => {
                if (
                    event.detail?.mode ===
                    "task-core-unavailable"
                ) {
                    announce(
                        "Task projection is unavailable. Task mutations are disabled."
                    );
                }
            }
        );

        window.addEventListener(
            "niche:temporal-ghost",
            (event) => {
                const cursor =
                    Number(
                        event.detail
                            ?.cursor
                    );

                if (
                    Number.isFinite(
                        cursor
                    )
                ) {
                    announce(
                        `Historical replay event ${cursor + 1}.`
                    );
                }
            }
        );
    }

    function initialize() {
        if (state.initialized) {
            return;
        }

        state.initialized = true;

        createLiveRegion();
        reconcile();
        installKeyboardActivation();
        installAnnouncements();

        new MutationObserver(
            reconcile
        ).observe(
            document.body,
            {
                childList: true,
                subtree: true,
                attributes: true,
                attributeFilter: [
                    "class",
                    "aria-current",
                    "data-task-id"
                ]
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

    window.NicheAccessibility =
        Object.freeze({
            announce,
            reconcile
        });
})();
