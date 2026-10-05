"use strict";

/*
 * savant / niche
 * bounded runtime diagnostics
 *
 * owner: exile:niche
 * authority_effect: none
 *
 * Captures concrete request failures already observable by the browser.
 * It does not infer backend causes, reconstruct task authority, mutate
 * task state, or convert failure evidence into authority.
 */

(() => {
    "use strict";

    const state = {
        failures: new Map(),
        requests: new Map(),
        lastChange: null,
        visible: false
    };

    const $ = (selector, root = document) =>
        root.querySelector(selector);

    function safe(value) {
        return value === undefined ||
            value === null
            ? ""
            : String(value);
    }

    function createElement(
        tag,
        className,
        text
    ) {
        const element =
            document.createElement(tag);

        if (className) {
            element.className =
                className;
        }

        if (
            text !== undefined &&
            text !== null
        ) {
            element.textContent =
                safe(text);
        }

        return element;
    }

    function createPanel() {
        if ($("#niche-diagnostics")) {
            return $(
                "#niche-diagnostics"
            );
        }

        const panel =
            createElement(
                "aside",
                "niche-diagnostics"
            );

        panel.id =
            "niche-diagnostics";

        panel.hidden = true;

        panel.setAttribute(
            "aria-hidden",
            "true"
        );

        panel.setAttribute(
            "aria-labelledby",
            "niche-diagnostics-title"
        );

        const head =
            createElement(
                "header",
                "niche-diagnostics-head"
            );

        const title =
            createElement(
                "div"
            );

        title.append(
            createElement(
                "div",
                "eyebrow",
                "RUNTIME EVIDENCE"
            ),
            createElement(
                "h2",
                "",
                "Projection diagnostics"
            )
        );

        title.lastChild.id =
            "niche-diagnostics-title";

        const close =
            createElement(
                "button",
                "icon-button",
                "×"
            );

        close.type = "button";

        close.setAttribute(
            "aria-label",
            "Close runtime diagnostics"
        );

        close.addEventListener(
            "click",
            hide
        );

        head.append(
            title,
            close
        );

        const summary =
            createElement(
                "div",
                "niche-diagnostics-summary"
            );

        summary.id =
            "niche-diagnostics-summary";

        const body =
            createElement(
                "div",
                "niche-diagnostics-body"
            );

        body.id =
            "niche-diagnostics-body";

        panel.append(
            head,
            summary,
            body
        );

        document.body.append(
            panel
        );

        return panel;
    }

    function failureKey(result) {
        return [
            result?.name || "unknown",
            result?.status ?? "unknown",
            result?.checked_at || ""
        ].join(":");
    }

    function normalizeResult(
        name,
        result
    ) {
        return {
            name:
                safe(
                    result?.name ||
                    name ||
                    "unknown"
                ),
            url:
                safe(
                    result?.url ||
                    "unknown"
                ),
            ok:
                Boolean(
                    result?.ok
                ),
            status:
                Number.isFinite(
                    Number(
                        result?.status
                    )
                )
                    ? Number(
                        result.status
                    )
                    : null,
            error:
                result?.error
                    ? safe(
                        result.error
                    )
                    : null,
            checked_at:
                safe(
                    result?.checked_at ||
                    new Date()
                        .toISOString()
                )
        };
    }

    function ingest(detail) {
        const results =
            detail?.results || {};

        state.requests.clear();

        for (
            const [
                name,
                raw
            ] of Object.entries(
                results
            )
        ) {
            const result =
                normalizeResult(
                    name,
                    raw
                );

            state.requests.set(
                name,
                result
            );

            if (!result.ok) {
                state.failures.set(
                    failureKey(
                        result
                    ),
                    result
                );
            }
        }

        if (
            state.failures.size >
            100
        ) {
            const retained =
                Array.from(
                    state.failures
                        .entries()
                ).slice(-100);

            state.failures =
                new Map(
                    retained
                );
        }

        state.lastChange =
            new Date()
                .toISOString();

        render();
    }

    function statusLabel(result) {
        if (result.ok) {
            return "available";
        }

        if (
            result.status !== null &&
            result.status !== 0
        ) {
            return `http ${result.status}`;
        }

        return (
            result.error ||
            "unavailable"
        );
    }

    function renderSummary() {
        const summary =
            $(
                "#niche-diagnostics-summary"
            );

        if (!summary) {
            return;
        }

        const current =
            Array.from(
                state.requests.values()
            );

        const healthy =
            current.filter(
                (result) =>
                    result.ok
            ).length;

        const failed =
            current.length -
            healthy;

        summary.replaceChildren(
            createElement(
                "span",
                "",
                `${healthy} available`
            ),
            createElement(
                "span",
                "",
                `${failed} unavailable`
            ),
            createElement(
                "span",
                "",
                "authority effect: none"
            )
        );
    }

    function renderCurrent() {
        const body =
            $(
                "#niche-diagnostics-body"
            );

        if (!body) {
            return;
        }

        body.replaceChildren();

        const currentSection =
            createElement(
                "section",
                "niche-diagnostics-section"
            );

        currentSection.append(
            createElement(
                "h3",
                "",
                "Current request state"
            )
        );

        const grid =
            createElement(
                "div",
                "niche-diagnostics-grid"
            );

        const current =
            Array.from(
                state.requests.values()
            );

        if (!current.length) {
            grid.append(
                createElement(
                    "p",
                    "niche-diagnostics-empty",
                    "No request evidence has been observed."
                )
            );
        } else {
            current
                .sort(
                    (left, right) =>
                        left.name.localeCompare(
                            right.name
                        )
                )
                .forEach(
                    (result) => {
                        const item =
                            createElement(
                                "article",
                                "niche-diagnostic"
                            );

                        item.dataset.ok =
                            result.ok
                                ? "true"
                                : "false";

                        const top =
                            createElement(
                                "div",
                                "niche-diagnostic-top"
                            );

                        top.append(
                            createElement(
                                "strong",
                                "",
                                result.name
                            ),
                            createElement(
                                "span",
                                "",
                                statusLabel(
                                    result
                                )
                            )
                        );

                        const url =
                            createElement(
                                "code",
                                "",
                                result.url
                            );

                        item.append(
                            top,
                            url
                        );

                        if (
                            result.error
                        ) {
                            item.append(
                                createElement(
                                    "p",
                                    "",
                                    result.error
                                )
                            );
                        }

                        grid.append(
                            item
                        );
                    }
                );
        }

        currentSection.append(
            grid
        );

        body.append(
            currentSection
        );

        const evidenceSection =
            createElement(
                "section",
                "niche-diagnostics-section"
            );

        evidenceSection.append(
            createElement(
                "h3",
                "",
                "Observed failures"
            )
        );

        const evidence =
            createElement(
                "div",
                "niche-diagnostics-evidence"
            );

        const failures =
            Array.from(
                state.failures.values()
            ).slice(-30);

        if (!failures.length) {
            evidence.append(
                createElement(
                    "p",
                    "niche-diagnostics-empty",
                    "No HTTP or transport failure has been observed."
                )
            );
        } else {
            failures
                .reverse()
                .forEach(
                    (result) => {
                        const line =
                            createElement(
                                "div",
                                "niche-diagnostics-line"
                            );

                        line.append(
                            createElement(
                                "time",
                                "",
                                result.checked_at
                            ),
                            createElement(
                                "strong",
                                "",
                                result.name
                            ),
                            createElement(
                                "span",
                                "",
                                statusLabel(
                                    result
                                )
                            )
                        );

                        evidence.append(
                            line
                        );
                    }
                );
        }

        evidenceSection.append(
            evidence
        );

        body.append(
            evidenceSection
        );
    }

    function render() {
        renderSummary();
        renderCurrent();
    }

    function show() {
        const panel =
            createPanel();

        panel.hidden = false;

        panel.setAttribute(
            "aria-hidden",
            "false"
        );

        state.visible = true;

        render();
    }

    function hide() {
        const panel =
            createPanel();

        panel.hidden = true;

        panel.setAttribute(
            "aria-hidden",
            "true"
        );

        state.visible = false;
    }

    function toggle() {
        if (state.visible) {
            hide();
        } else {
            show();
        }
    }

    function installEvents() {
        window.addEventListener(
            "niche:api-status",
            (event) => {
                ingest(
                    event.detail
                );
            }
        );

        window.addEventListener(
            "error",
            (event) => {
                const result = {
                    name:
                        "frontend",
                    url:
                        event.filename ||
                        "browser",
                    ok: false,
                    status: null,
                    error:
                        event.message ||
                        "javascript error",
                    checked_at:
                        new Date()
                            .toISOString()
                };

                state.failures.set(
                    failureKey(
                        result
                    ),
                    result
                );

                state.lastChange =
                    result.checked_at;

                render();
            }
        );

        window.addEventListener(
            "unhandledrejection",
            (event) => {
                const result = {
                    name:
                        "frontend-promise",
                    url:
                        "browser",
                    ok: false,
                    status: null,
                    error:
                        safe(
                            event.reason
                                ?.message ||
                            event.reason ||
                            "unhandled rejection"
                        ),
                    checked_at:
                        new Date()
                            .toISOString()
                };

                state.failures.set(
                    failureKey(
                        result
                    ),
                    result
                );

                state.lastChange =
                    result.checked_at;

                render();
            }
        );

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
                    event.altKey &&
                    event.key.toLowerCase() ===
                        "d"
                ) {
                    event.preventDefault();
                    toggle();
                }

                if (
                    event.key ===
                        "Escape" &&
                    state.visible
                ) {
                    hide();
                }
            }
        );
    }

    function initialize() {
        createPanel();
        installEvents();

        const current =
            window.NicheApiResilience
                ?.status?.();

        if (current) {
            ingest(
                current
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

    window.NicheDiagnostics =
        Object.freeze({
            show,
            hide,
            toggle,

            state() {
                return {
                    visible:
                        state.visible,
                    lastChange:
                        state.lastChange,
                    requests:
                        Object.fromEntries(
                            state.requests
                        ),
                    failures:
                        Array.from(
                            state.failures
                                .values()
                        )
                };
            }
        });
})();
