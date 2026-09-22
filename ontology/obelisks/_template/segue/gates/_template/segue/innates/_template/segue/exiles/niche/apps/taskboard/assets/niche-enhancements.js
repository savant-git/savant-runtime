"use strict";

/*
 * savant / niche
 * advanced interaction projections
 *
 * owner: exile:niche
 * authority_effect: none
 *
 * This module adds projection-only interaction instruments over the
 * established Niche frontend. It never writes authoritative task state.
 */

(() => {
    "use strict";

    const state = {
        filter: "",
        tokens: [],
        focus: false,
        lens: "causal",
        selected: null,
        previous: new Map(),
        changed: new Set(),
        observer: null,
        graphFrame: 0
    };

    const $ = (selector, root = document) =>
        root.querySelector(selector);

    const $$ = (selector, root = document) =>
        Array.from(root.querySelectorAll(selector));

    function safe(value, fallback = "") {
        if (
            value === undefined ||
            value === null
        ) {
            return fallback;
        }

        return String(value);
    }

    function normalize(value) {
        return safe(value)
            .trim()
            .toLowerCase();
    }

    function currentTasks() {
        const cards = $$(".task-card");

        return cards.map((card) => ({
            element: card,
            id: safe(card.dataset.taskId),
            state: normalize(card.dataset.state),
            text: normalize(card.textContent),
            changed:
                card.dataset.changed === "true"
        }));
    }

    function parseFilter(value) {
        const source = safe(value).trim();

        if (!source) {
            return [];
        }

        const parts =
            source.match(
                /(?:[^\s"]+|"[^"]*")+/g
            ) || [];

        return parts.map((part) => {
            const clean =
                part.replace(/^"|"$/g, "");

            const index =
                clean.indexOf(":");

            if (index < 1) {
                return {
                    field: "text",
                    value: normalize(clean),
                    raw: clean
                };
            }

            return {
                field: normalize(
                    clean.slice(0, index)
                ),
                value: normalize(
                    clean.slice(index + 1)
                ),
                raw: clean
            };
        }).filter((token) => token.value);
    }

    function matchesToken(task, token) {
        if (token.field === "text") {
            return task.text.includes(
                token.value
            );
        }

        if (token.field === "state") {
            return task.state === token.value;
        }

        if (token.field === "ready") {
            const ready =
                task.state === "ready";

            return token.value === "true"
                ? ready
                : !ready;
        }

        if (token.field === "blocked") {
            const blocked =
                task.state === "blocked";

            return token.value === "true"
                ? blocked
                : !blocked;
        }

        if (token.field === "changed") {
            const changed =
                task.changed ||
                state.changed.has(task.id);

            if (
                token.value === "true" ||
                token.value === "recent"
            ) {
                return changed;
            }

            return !changed;
        }

        /*
         * Unknown grammar fields degrade to a text search instead of
         * fabricating task metadata that is not exposed in the DOM.
         */
        return task.text.includes(
            `${token.field}:${token.value}`
        ) ||
            task.text.includes(token.value);
    }

    function applyFilter() {
        const tasks = currentTasks();

        for (const task of tasks) {
            const visible =
                state.tokens.every(
                    (token) =>
                        matchesToken(
                            task,
                            token
                        )
                );

            task.element.hidden =
                !visible;
        }

        $$(".lane").forEach((lane) => {
            const cards =
                $$(".task-card", lane);

            const visible =
                cards.filter(
                    (card) => !card.hidden
                ).length;

            lane.dataset.filteredEmpty =
                visible === 0
                    ? "true"
                    : "false";
        });

        renderTokens();
        updateFilterCount();
    }

    function renderTokens() {
        const host =
            $("#niche-filter-tokens");

        if (!host) {
            return;
        }

        host.replaceChildren();

        for (
            let index = 0;
            index < state.tokens.length;
            index += 1
        ) {
            const token =
                state.tokens[index];

            const button =
                document.createElement(
                    "button"
                );

            button.type = "button";
            button.className =
                "niche-filter-token";

            button.textContent =
                `${token.raw} ×`;

            button.setAttribute(
                "aria-label",
                `Remove filter ${token.raw}`
            );

            button.addEventListener(
                "click",
                () => {
                    state.tokens.splice(
                        index,
                        1
                    );

                    const input =
                        $("#niche-filter-input");

                    input.value =
                        state.tokens
                            .map(
                                (item) =>
                                    item.raw
                            )
                            .join(" ");

                    applyFilter();
                }
            );

            host.append(button);
        }
    }

    function updateFilterCount() {
        const output =
            $("#niche-filter-count");

        if (!output) {
            return;
        }

        const tasks =
            currentTasks();

        const visible =
            tasks.filter(
                (task) =>
                    !task.element.hidden
            ).length;

        output.textContent =
            state.tokens.length
                ? `${visible}/${tasks.length} visible`
                : `${tasks.length} tasks`;
    }

    function installFilterBar() {
        if ($("#niche-filter-bar")) {
            return;
        }

        const bar =
            document.createElement("section");

        bar.id = "niche-filter-bar";
        bar.className =
            "niche-filter-bar";

        bar.setAttribute(
            "aria-label",
            "Task projection filters"
        );

        const prefix =
            document.createElement("span");

        prefix.className =
            "niche-filter-prefix";

        prefix.textContent = "FILTER";

        const input =
            document.createElement("input");

        input.id =
            "niche-filter-input";

        input.type = "search";
        input.autocomplete = "off";
        input.spellcheck = false;

        input.placeholder =
            "state:ready  blocked:true  changed:recent  task text";

        input.setAttribute(
            "aria-label",
            "Filter task projections"
        );

        const tokens =
            document.createElement("div");

        tokens.id =
            "niche-filter-tokens";

        tokens.className =
            "niche-filter-tokens";

        const count =
            document.createElement("output");

        count.id =
            "niche-filter-count";

        count.className =
            "niche-filter-count";

        const clear =
            document.createElement("button");

        clear.type = "button";
        clear.className =
            "niche-filter-clear";

        clear.textContent = "CLEAR";

        clear.addEventListener(
            "click",
            () => {
                input.value = "";
                state.tokens = [];
                applyFilter();
                input.focus();
            }
        );

        input.addEventListener(
            "input",
            () => {
                state.filter =
                    input.value;

                state.tokens =
                    parseFilter(
                        input.value
                    );

                applyFilter();
            }
        );

        input.addEventListener(
            "keydown",
            (event) => {
                if (
                    event.key === "Escape"
                ) {
                    input.value = "";
                    state.tokens = [];
                    applyFilter();
                    input.blur();
                }
            }
        );

        bar.append(
            prefix,
            input,
            tokens,
            count,
            clear
        );

        const main = $("main");

        if (main) {
            main.before(bar);
        }
    }

    function installExecutionControls() {
        if ($("#niche-mode-controls")) {
            return;
        }

        const host =
            $(".top-actions");

        if (!host) {
            return;
        }

        const controls =
            document.createElement("div");

        controls.id =
            "niche-mode-controls";

        controls.className =
            "niche-mode-controls";

        const focus =
            document.createElement("button");

        focus.type = "button";
        focus.id =
            "niche-focus-toggle";

        focus.textContent =
            "EXECUTION TUNNEL";

        focus.title =
            "Compress Niche around the current executable action";

        focus.addEventListener(
            "click",
            toggleFocus
        );

        const lens =
            document.createElement("button");

        lens.type = "button";
        lens.id =
            "niche-lens-toggle";

        lens.textContent =
            "CAUSAL LENS";

        lens.title =
            "Cycle causal, authority, and change lenses";

        lens.addEventListener(
            "click",
            cycleLens
        );

        controls.append(
            focus,
            lens
        );

        host.prepend(controls);
    }

    function toggleFocus() {
        state.focus = !state.focus;

        document.body.classList.toggle(
            "niche-execution-tunnel",
            state.focus
        );

        const button =
            $("#niche-focus-toggle");

        if (button) {
            button.classList.toggle(
                "active",
                state.focus
            );

            button.textContent =
                state.focus
                    ? "RETURN TO FIELD"
                    : "EXECUTION TUNNEL";
        }

        if (state.focus) {
            window.Niche?.view?.(
                "execute"
            );

            $("#start-next")?.focus();
        }
    }

    function cycleLens() {
        const lenses = [
            "causal",
            "authority",
            "change"
        ];

        const current =
            lenses.indexOf(state.lens);

        state.lens =
            lenses[
                (current + 1) %
                lenses.length
            ];

        document.body.dataset.nicheLens =
            state.lens;

        const button =
            $("#niche-lens-toggle");

        if (button) {
            button.textContent =
                `${state.lens.toUpperCase()} LENS`;
        }

        applyLens();
    }

    function applyLens() {
        const cards =
            currentTasks();

        for (const task of cards) {
            task.element.classList.remove(
                "lens-emphasis",
                "lens-muted"
            );

            if (
                state.lens === "change"
            ) {
                const changed =
                    task.changed ||
                    state.changed.has(task.id);

                task.element.classList.add(
                    changed
                        ? "lens-emphasis"
                        : "lens-muted"
                );

                continue;
            }

            if (
                state.lens === "causal"
            ) {
                const important =
                    task.state === "ready" ||
                    task.state === "active" ||
                    task.state === "blocked";

                task.element.classList.add(
                    important
                        ? "lens-emphasis"
                        : "lens-muted"
                );

                continue;
            }

            /*
             * The task card DOM does not establish authority metadata.
             * Authority Lens therefore does not invent an authoritative
             * classification. It visually marks the projection boundary.
             */
            task.element.classList.add(
                "authority-projection"
            );
        }

        document.body.dataset.nicheLens =
            state.lens;
    }

    function detectChanges() {
        const next = new Map();

        for (const task of currentTasks()) {
            const signature =
                `${task.state}|${task.text}`;

            next.set(
                task.id,
                signature
            );

            if (
                state.previous.has(task.id) &&
                state.previous.get(task.id) !==
                    signature
            ) {
                state.changed.add(
                    task.id
                );

                task.element.classList.add(
                    "living-pulse"
                );

                window.setTimeout(
                    () => {
                        task.element.classList.remove(
                            "living-pulse"
                        );
                    },
                    1500
                );
            }
        }

        state.previous = next;

        applyFilter();
        applyLens();
    }

    function installObserver() {
        const board =
            $("#flow-board");

        if (
            !board ||
            !("MutationObserver" in window)
        ) {
            return;
        }

        state.observer =
            new MutationObserver(() => {
                window.clearTimeout(
                    installObserver.timer
                );

                installObserver.timer =
                    window.setTimeout(
                        detectChanges,
                        60
                    );
            });

        state.observer.observe(
            board,
            {
                childList: true,
                subtree: true,
                attributes: true,
                attributeFilter: [
                    "data-state",
                    "data-changed"
                ]
            }
        );
    }

    function installGraphControls() {
        const stage =
            $("#graph-stage");

        if (
            !stage ||
            $("#niche-graph-controls")
        ) {
            return;
        }

        const controls =
            document.createElement("div");

        controls.id =
            "niche-graph-controls";

        controls.className =
            "niche-graph-controls";

        const commands = [
            ["−", () => zoomGraph(-0.1), "Zoom out"],
            ["1:1", resetGraph, "Reset graph"],
            ["+", () => zoomGraph(0.1), "Zoom in"]
        ];

        for (
            const [label, action, title]
            of commands
        ) {
            const button =
                document.createElement("button");

            button.type = "button";
            button.textContent = label;
            button.title = title;
            button.setAttribute(
                "aria-label",
                title
            );

            button.addEventListener(
                "click",
                action
            );

            controls.append(button);
        }

        stage.append(controls);

        stage.addEventListener(
            "wheel",
            (event) => {
                if (
                    !event.ctrlKey &&
                    !event.metaKey
                ) {
                    return;
                }

                event.preventDefault();

                zoomGraph(
                    event.deltaY < 0
                        ? 0.08
                        : -0.08
                );
            },
            {
                passive: false
            }
        );
    }

    function graphNodeLayer() {
        return $("#graph-nodes");
    }

    function zoomGraph(delta) {
        const layer =
            graphNodeLayer();

        if (!layer) {
            return;
        }

        const current =
            Number(
                layer.dataset.zoom || "1"
            );

        const next =
            Math.min(
                1.8,
                Math.max(
                    0.55,
                    current + delta
                )
            );

        layer.dataset.zoom =
            String(next);

        layer.style.transform =
            `scale(${next})`;

        layer.style.transformOrigin =
            "50% 50%";

        const edges =
            $("#graph-edges");

        if (edges) {
            edges.style.transform =
                `scale(${next})`;

            edges.style.transformOrigin =
                "50% 50%";
        }
    }

    function resetGraph() {
        const layer =
            graphNodeLayer();

        const edges =
            $("#graph-edges");

        if (layer) {
            layer.dataset.zoom = "1";
            layer.style.transform =
                "scale(1)";
        }

        if (edges) {
            edges.style.transform =
                "scale(1)";
        }
    }

    function installShortcuts() {
        document.addEventListener(
            "keydown",
            (event) => {
                const target =
                    event.target;

                const editing =
                    target instanceof
                        HTMLInputElement ||
                    target instanceof
                        HTMLTextAreaElement ||
                    target instanceof
                        HTMLSelectElement ||
                    target?.isContentEditable;

                if (editing) {
                    if (
                        event.key === "/" &&
                        target !==
                            $("#niche-filter-input")
                    ) {
                        return;
                    }

                    return;
                }

                if (event.key === "/") {
                    event.preventDefault();

                    $("#niche-filter-input")
                        ?.focus();

                    return;
                }

                if (
                    event.key.toLowerCase() ===
                    "x"
                ) {
                    toggleFocus();
                    return;
                }

                if (
                    event.key.toLowerCase() ===
                    "l"
                ) {
                    cycleLens();
                    return;
                }

                if (
                    event.key.toLowerCase() ===
                    "g"
                ) {
                    window.Niche?.view?.(
                        "constellation"
                    );

                    return;
                }

                if (
                    event.key.toLowerCase() ===
                    "f"
                ) {
                    window.Niche?.view?.(
                        "flow"
                    );

                    return;
                }

                if (
                    event.key.toLowerCase() ===
                    "e"
                ) {
                    window.Niche?.view?.(
                        "execute"
                    );

                    return;
                }

                if (
                    event.key.toLowerCase() ===
                    "v"
                ) {
                    window.Niche?.view?.(
                        "living"
                    );
                }
            }
        );
    }

    function installViewportIntelligence() {
        window.addEventListener(
            "niche:viewport",
            (event) => {
                const detail =
                    event.detail || {};

                document.body.dataset
                    .nicheViewportMode =
                    safe(
                        detail.mode,
                        "unknown"
                    );

                if (
                    detail.mode ===
                        "phone-narrow" ||
                    detail.mode ===
                        "phone"
                ) {
                    document.body.classList.add(
                        "niche-mobile-execution"
                    );
                } else {
                    document.body.classList.remove(
                        "niche-mobile-execution"
                    );
                }
            }
        );
    }

    function installFrontierSemantics() {
        const track =
            $("#frontier-track");

        if (!track) {
            return;
        }

        const observer =
            new MutationObserver(() => {
                const dots =
                    $$(".frontier-dot", track);

                dots.forEach(
                    (dot, index) => {
                        dot.style.setProperty(
                            "--frontier-index",
                            String(index)
                        );
                    }
                );
            });

        observer.observe(
            track,
            {
                childList: true
            }
        );
    }

    function installLivingSemantics() {
        const grid =
            $("#living-grid");

        if (
            !grid ||
            !("MutationObserver" in window)
        ) {
            return;
        }

        const classify = () => {
            $$(".living-surface", grid)
                .forEach((surface) => {
                    const content =
                        normalize(
                            surface.textContent
                        );

                    let kind =
                        "general";

                    if (
                        /authority|canon|rules|decisions|permissions|invariants|supersession/.test(
                            content
                        )
                    ) {
                        kind =
                            "authority";
                    } else if (
                        /health|assurance|integrity|readiness|freshness|staleness/.test(
                            content
                        )
                    ) {
                        kind =
                            "assurance";
                    } else if (
                        /history|change|evolution|replay|receipt/.test(
                            content
                        )
                    ) {
                        kind =
                            "temporal";
                    } else if (
                        /dependency|dependent|lineage|provenance/.test(
                            content
                        )
                    ) {
                        kind =
                            "graph";
                    } else if (
                        /persona/.test(
                            content
                        )
                    ) {
                        kind =
                            "persona";
                    } else if (
                        /filesystem|services|processes|network|system|packages|git|datastore|environment|capabilities|implementation/.test(
                            content
                        )
                    ) {
                        kind =
                            "runtime";
                    }

                    surface.dataset
                        .surfaceKind =
                        kind;
                });
        };

        const observer =
            new MutationObserver(
                classify
            );

        observer.observe(
            grid,
            {
                childList: true,
                subtree: true
            }
        );

        classify();
    }

    function installConnectionHealth() {
        window.addEventListener(
            "offline",
            () => {
                document.body.classList.add(
                    "niche-offline"
                );
            }
        );

        window.addEventListener(
            "online",
            () => {
                document.body.classList.remove(
                    "niche-offline"
                );
            }
        );

        document.body.classList.toggle(
            "niche-offline",
            !navigator.onLine
        );
    }

    function initialize() {
        installFilterBar();
        installExecutionControls();
        installObserver();
        installGraphControls();
        installShortcuts();
        installViewportIntelligence();
        installFrontierSemantics();
        installLivingSemantics();
        installConnectionHealth();

        detectChanges();
        applyLens();
    }

    if (
        document.readyState === "loading"
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

    window.NicheEnhancements =
        Object.freeze({
            filter(value) {
                const input =
                    $("#niche-filter-input");

                if (!input) {
                    return;
                }

                input.value =
                    safe(value);

                state.tokens =
                    parseFilter(
                        input.value
                    );

                applyFilter();
            },

            focus: toggleFocus,
            lens: cycleLens,

            state() {
                return {
                    filter:
                        state.filter,
                    tokens:
                        state.tokens.map(
                            (token) =>
                                token.raw
                        ),
                    focus:
                        state.focus,
                    lens:
                        state.lens,
                    changed:
                        Array.from(
                            state.changed
                        )
                };
            }
        });
})();
