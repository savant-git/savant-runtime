"use strict";

/*
 * savant / niche
 * api failure containment
 *
 * owner: exile:niche
 * authority_effect: none
 *
 * This module prevents unavailable derived projections from collapsing
 * the executable interface. It does not synthesize missing task state,
 * convert unknowns into facts, or mutate authoritative task storage.
 */

(() => {
    "use strict";

    const endpoints = Object.freeze({
        health: "/api/health",
        tasks: "/api/tasks?include_terminal=true",
        dashboard: "/api/dashboard",
        state: "/api/state",
        living: "/api/living",
        fabric: "/api/living/fabric",
        history: "/api/history"
    });

    const state = {
        results: new Map(),
        failures: new Map(),
        lastProbe: null,
        probing: false,
        timer: null
    };

    const $ = (selector, root = document) =>
        root.querySelector(selector);

    function text(selector, value) {
        const element = $(selector);

        if (element) {
            element.textContent = value;
        }
    }

    function setIndicator(selector, status) {
        const element = $(selector);

        if (!element) {
            return;
        }

        element.dataset.status = status;
    }

    async function request(name, url) {
        const controller =
            new AbortController();

        const timeout =
            window.setTimeout(
                () => controller.abort(),
                8000
            );

        try {
            const response =
                await fetch(
                    url,
                    {
                        method: "GET",
                        headers: {
                            Accept: "application/json"
                        },
                        cache: "no-store",
                        signal: controller.signal
                    }
                );

            const contentType =
                response.headers.get(
                    "content-type"
                ) || "";

            let body = null;

            if (
                contentType.includes(
                    "application/json"
                )
            ) {
                try {
                    body =
                        await response.json();
                } catch {
                    body = null;
                }
            } else {
                try {
                    body =
                        await response.text();
                } catch {
                    body = null;
                }
            }

            const result = {
                name,
                url,
                ok: response.ok,
                status: response.status,
                body,
                checked_at:
                    new Date().toISOString()
            };

            state.results.set(
                name,
                result
            );

            if (response.ok) {
                state.failures.delete(
                    name
                );
            } else {
                state.failures.set(
                    name,
                    result
                );
            }

            return result;
        } catch (error) {
            const result = {
                name,
                url,
                ok: false,
                status: 0,
                body: null,
                error:
                    error?.name ===
                    "AbortError"
                        ? "timeout"
                        : String(
                            error?.message ||
                            error
                        ),
                checked_at:
                    new Date().toISOString()
            };

            state.results.set(
                name,
                result
            );

            state.failures.set(
                name,
                result
            );

            return result;
        } finally {
            window.clearTimeout(
                timeout
            );
        }
    }

    function renderStatus() {
        const results =
            Array.from(
                state.results.values()
            );

        if (!results.length) {
            return;
        }

        const healthy =
            results.filter(
                (result) =>
                    result.ok
            );

        const failed =
            results.filter(
                (result) =>
                    !result.ok
            );

        const task =
            state.results.get(
                "tasks"
            );

        const living =
            state.results.get(
                "living"
            );

        const fabric =
            state.results.get(
                "fabric"
            );

        if (task) {
            setIndicator(
                "#task-status",
                task.ok
                    ? "healthy"
                    : "unavailable"
            );

            text(
                "#task-status-text",
                task.ok
                    ? "available"
                    : "unavailable"
            );
        }

        if (living || fabric) {
            const livingHealthy =
                Boolean(
                    living?.ok ||
                    fabric?.ok
                );

            setIndicator(
                "#fabric-status",
                livingHealthy
                    ? "healthy"
                    : "unavailable"
            );

            text(
                "#fabric-status-text",
                livingHealthy
                    ? "available"
                    : "unavailable"
            );
        }

        if (healthy.length) {
            setIndicator(
                "#api-status",
                failed.length
                    ? "degraded"
                    : "healthy"
            );

            text(
                "#api-status-text",
                failed.length
                    ? "degraded"
                    : "connected"
            );
        } else {
            setIndicator(
                "#api-status",
                "unavailable"
            );

            text(
                "#api-status-text",
                "unavailable"
            );
        }

        if (!failed.length) {
            text(
                "#projection-status",
                `${healthy.length} projections available`
            );

            return;
        }

        const names =
            failed
                .map(
                    (result) =>
                        `${result.name}:${result.status || "offline"}`
                )
                .join(" · ");

        text(
            "#projection-status",
            `${failed.length} unavailable · ${names}`
        );
    }

    function renderFailureSurface() {
        const task =
            state.results.get(
                "tasks"
            );

        if (!task || task.ok) {
            return;
        }

        const heading =
            $("#execute-heading");

        const purpose =
            $("#execute-purpose");

        const detail =
            $("#start-next-detail");

        const start =
            $("#start-next");

        if (heading) {
            heading.textContent =
                "Task projection unavailable";
        }

        if (purpose) {
            purpose.textContent =
                "Niche cannot establish an executable frontier while the authoritative task projection is unavailable.";
        }

        if (detail) {
            detail.textContent =
                task.status
                    ? `Task endpoint returned HTTP ${task.status}`
                    : "Task endpoint could not be reached";
        }

        if (start) {
            start.disabled = true;

            start.setAttribute(
                "aria-disabled",
                "true"
            );
        }

        text(
            "#execute-priority",
            "PRIORITY UNKNOWN"
        );

        text(
            "#oracle-explanation",
            "Priority is intentionally unresolved because the task projection is unavailable. Niche will not manufacture a recommendation."
        );
    }

    function recoverFailureSurface() {
        const task =
            state.results.get(
                "tasks"
            );

        if (!task?.ok) {
            return;
        }

        const start =
            $("#start-next");

        if (start) {
            start.disabled = false;

            start.removeAttribute(
                "aria-disabled"
            );
        }
    }

    function dispatch() {
        window.dispatchEvent(
            new CustomEvent(
                "niche:api-status",
                {
                    detail: {
                        checked_at:
                            state.lastProbe,
                        results:
                            Object.fromEntries(
                                state.results
                            ),
                        failures:
                            Object.fromEntries(
                                state.failures
                            )
                    }
                }
            )
        );
    }

    async function probe() {
        if (state.probing) {
            return;
        }

        state.probing = true;

        try {
            await Promise.all(
                Object.entries(
                    endpoints
                ).map(
                    ([name, url]) =>
                        request(
                            name,
                            url
                        )
                )
            );

            state.lastProbe =
                new Date().toISOString();

            renderStatus();
            renderFailureSurface();
            recoverFailureSurface();
            dispatch();
        } finally {
            state.probing = false;
        }
    }

    function schedule() {
        window.clearInterval(
            state.timer
        );

        state.timer =
            window.setInterval(
                probe,
                10000
            );
    }

    function installRefresh() {
        $("#refresh")
            ?.addEventListener(
                "click",
                () => {
                    window.setTimeout(
                        probe,
                        0
                    );
                }
            );
    }

    function initialize() {
        installRefresh();
        probe();
        schedule();
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

    window.NicheApiResilience =
        Object.freeze({
            probe,

            status() {
                return {
                    checked_at:
                        state.lastProbe,
                    results:
                        Object.fromEntries(
                            state.results
                        ),
                    failures:
                        Object.fromEntries(
                            state.failures
                        )
                };
            }
        });
})();
