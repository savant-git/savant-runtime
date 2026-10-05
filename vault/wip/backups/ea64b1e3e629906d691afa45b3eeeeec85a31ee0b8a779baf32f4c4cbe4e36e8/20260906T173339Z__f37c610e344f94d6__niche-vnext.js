"use strict";

/*
 * savant / niche vnext
 * converged interface coordinator
 *
 * owner: exile:niche
 * authority_effect: none
 *
 * This module owns only non-authoritative interface state.
 * Authoritative task state and mutations remain owned by Niche/backend.
 */

(() => {
    const STORAGE = Object.freeze({
        theme: "savant.niche.ui.theme",
        causalMode: "savant.niche.ui.causal-mode",
        causalZoom: "savant.niche.ui.causal-zoom"
    });

    const THEMES = Object.freeze([
        "nexus",
        "phosphor",
        "volt",
        "ember",
        "ultraviolet",
        "monolith",
        "afterimage"
    ]);

    const CAUSAL_MODES = Object.freeze({
        topology: {
            label: "TOPOLOGY",
            description:
                "Structural dependency projection. Interface geometry is non-authoritative."
        },

        flow: {
            label: "FLOW",
            description:
                "Task execution state projected into one causal workspace."
        },

        dependencies: {
            label: "DEPENDENCIES",
            description:
                "Dependency relationships for represented task state."
        },

        impact: {
            label: "IMPACT",
            description:
                "Represented downstream task consequences and dependents."
        },

        objective: {
            label: "OBJECTIVE",
            description:
                "Objective context where that edifice is represented."
        },

        critical: {
            label: "CRITICAL PATH",
            description:
                "Deterministically derived critical-path information where available."
        },

        blockers: {
            label: "BLOCKERS",
            description:
                "Represented blockers and unsatisfied dependency structure."
        },

        authority: {
            label: "AUTHORITY",
            description:
                "Authority and projection boundaries for represented work."
        }
    });

    const state = {
        ready: false,
        theme: "nexus",
        causalMode: "topology",
        causalZoom: 1,
        selectedTaskId: null
    };

    const $ = (
        selector,
        root = document
    ) => root.querySelector(selector);

    const $$ = (
        selector,
        root = document
    ) => Array.from(
        root.querySelectorAll(selector)
    );

    function safeRead(key) {
        try {
            return window.localStorage
                .getItem(key);
        } catch {
            return null;
        }
    }

    function safeWrite(
        key,
        value
    ) {
        try {
            window.localStorage
                .setItem(
                    key,
                    value
                );
        } catch {
            return;
        }
    }

    function validTheme(value) {
        return THEMES.includes(value)
            ? value
            : "nexus";
    }

    function validCausalMode(value) {
        return Object.prototype
            .hasOwnProperty.call(
                CAUSAL_MODES,
                value
            )
            ? value
            : "topology";
    }

    function applyTheme(
        theme,
        {
            persist = true
        } = {}
    ) {
        const next =
            validTheme(theme);

        state.theme =
            next;

        document.documentElement
            .dataset
            .nicheTheme =
            next;

        const control =
            $("#niche-theme");

        if (
            control &&
            control.value !== next
        ) {
            control.value =
                next;
        }

        if (persist) {
            safeWrite(
                STORAGE.theme,
                next
            );
        }

        window.dispatchEvent(
            new CustomEvent(
                "niche:theme-change",
                {
                    detail: {
                        theme: next,
                        authority_effect:
                            "none"
                    }
                }
            )
        );
    }

    function applyCausalMode(
        mode,
        {
            persist = true
        } = {}
    ) {
        const next =
            validCausalMode(mode);

        state.causalMode =
            next;

        const workspace =
            $(".causal-workspace");

        const graph =
            $("#graph-stage");

        const flow =
            $("#causal-flow");

        if (workspace) {
            workspace.dataset
                .causalActive =
                next;
        }

        const flowActive =
            next === "flow";

        if (graph) {
            graph.hidden =
                flowActive;
        }

        if (flow) {
            flow.hidden =
                !flowActive;
        }

        $$("[data-causal-mode]")
            .forEach(
                (button) => {
                    const active =
                        button.dataset
                            .causalMode === next;

                    button.classList
                        .toggle(
                            "active",
                            active
                        );

                    button.setAttribute(
                        "aria-pressed",
                        active
                            ? "true"
                            : "false"
                    );
                }
            );

        const metadata =
            CAUSAL_MODES[next];

        const label =
            $("#causal-mode-label");

        if (label) {
            label.textContent =
                metadata.label;
        }

        const description =
            $("#causal-mode-description");

        if (description) {
            description.textContent =
                metadata.description;
        }

        if (persist) {
            safeWrite(
                STORAGE.causalMode,
                next
            );
        }

        window.dispatchEvent(
            new CustomEvent(
                "niche:causal-mode-change",
                {
                    detail: {
                        mode: next,
                        authority_effect:
                            "none"
                    }
                }
            )
        );
    }

    function clampZoom(value) {
        return Math.min(
            1.8,
            Math.max(
                0.55,
                value
            )
        );
    }

    function applyCausalZoom(
        value,
        {
            persist = true
        } = {}
    ) {
        const next =
            clampZoom(
                Number(value) || 1
            );

        state.causalZoom =
            next;

        const nodes =
            $("#graph-nodes");

        const edges =
            $("#graph-edges");

        if (nodes) {
            nodes.style
                .transformOrigin =
                "50% 50%";

            nodes.style
                .transform =
                `scale(${next})`;
        }

        if (edges) {
            edges.style
                .transformOrigin =
                "50% 50%";

            edges.style
                .transform =
                `scale(${next})`;
        }

        if (persist) {
            safeWrite(
                STORAGE.causalZoom,
                String(next)
            );
        }
    }

    function bindTheme() {
        const control =
            $("#niche-theme");

        if (!control) {
            return;
        }

        control.addEventListener(
            "change",
            () => {
                applyTheme(
                    control.value
                );
            }
        );
    }

    function bindCausalModes() {
        $$("[data-causal-mode]")
            .forEach(
                (button) => {
                    button.addEventListener(
                        "click",
                        () => {
                            applyCausalMode(
                                button.dataset
                                    .causalMode
                            );
                        }
                    );
                }
            );
    }

    function bindViewport() {
        $$("[data-causal-viewport]")
            .forEach(
                (button) => {
                    button.addEventListener(
                        "click",
                        () => {
                            const action =
                                button.dataset
                                    .causalViewport;

                            if (
                                action ===
                                "zoom-in"
                            ) {
                                applyCausalZoom(
                                    state.causalZoom +
                                    0.1
                                );

                                return;
                            }

                            if (
                                action ===
                                "zoom-out"
                            ) {
                                applyCausalZoom(
                                    state.causalZoom -
                                    0.1
                                );

                                return;
                            }

                            applyCausalZoom(1);
                        }
                    );
                }
            );
    }

    function currentNicheState() {
        try {
            if (
                window.Niche &&
                typeof window.Niche.state ===
                    "function"
            ) {
                return window.Niche
                    .state();
            }
        } catch {
            return null;
        }

        return null;
    }

    function normalizeTaskId(value) {
        if (
            value === null ||
            value === undefined ||
            value === ""
        ) {
            return null;
        }

        return String(value);
    }

    function resolveSelectedTask() {
        const nicheState =
            currentNicheState();

        if (!nicheState) {
            return state.selectedTaskId;
        }

        const selected =
            normalizeTaskId(
                nicheState.selectedTaskId
            );

        if (selected) {
            state.selectedTaskId =
                selected;

            return selected;
        }

        return state.selectedTaskId;
    }

    function refreshSelectionLabel() {
        const target =
            $("#causal-selection");

        if (!target) {
            return;
        }

        const selected =
            resolveSelectedTask();

        target.textContent =
            selected
                ? selected
                : "NO TASK SELECTED";
    }

    function renderCompanionFromDom() {
        const target =
            $("#causal-companion-body");

        if (!target) {
            return;
        }

        const selected =
            resolveSelectedTask();

        if (!selected) {
            target.textContent =
                "Select a represented task to inspect its causal neighborhood.";

            return;
        }

        const inspectorTitle =
            $("#inspector-title");

        const title =
            inspectorTitle &&
            inspectorTitle.textContent &&
            inspectorTitle.textContent !==
                "No task selected"
                ? inspectorTitle.textContent
                : selected;

        target.replaceChildren();

        const dl =
            document.createElement("dl");

        const taskTerm =
            document.createElement("dt");

        taskTerm.textContent =
            "TASK";

        const taskValue =
            document.createElement("dd");

        taskValue.textContent =
            title;

        const idTerm =
            document.createElement("dt");

        idTerm.textContent =
            "IDENTITY";

        const idValue =
            document.createElement("dd");

        idValue.textContent =
            selected;

        const authorityTerm =
            document.createElement("dt");

        authorityTerm.textContent =
            "FIELD AUTHORITY";

        const authorityValue =
            document.createElement("dd");

        authorityValue.textContent =
            "Projection only. Task authority remains outside interface geometry.";

        dl.append(
            taskTerm,
            taskValue,
            idTerm,
            idValue,
            authorityTerm,
            authorityValue
        );

        target.append(dl);
    }

    function syncSelection() {
        refreshSelectionLabel();
        renderCompanionFromDom();
    }

    function bindSelectionSync() {
        const inspector =
            $("#inspector");

        if (!inspector) {
            return;
        }

        const observer =
            new MutationObserver(
                () => {
                    syncSelection();
                }
            );

        observer.observe(
            inspector,
            {
                subtree: true,
                childList: true,
                characterData: true,
                attributes: true,
                attributeFilter: [
                    "aria-hidden"
                ]
            }
        );

        window.addEventListener(
            "niche:task-selected",
            (event) => {
                const detail =
                    event.detail || {};

                const candidate =
                    normalizeTaskId(
                        detail.taskId ??
                        detail.task_id ??
                        detail.id
                    );

                if (candidate) {
                    state.selectedTaskId =
                        candidate;
                }

                syncSelection();
            }
        );
    }

    function bindObjectiveControls() {
        const search =
            $("#objective-search");

        if (search) {
            search.addEventListener(
                "input",
                () => {
                    const query =
                        search.value
                            .trim()
                            .toLocaleLowerCase();

                    $$("#objective-grid > *")
                        .forEach(
                            (element) => {
                                const text =
                                    (
                                        element.textContent ||
                                        ""
                                    )
                                        .toLocaleLowerCase();

                                element.hidden =
                                    Boolean(query) &&
                                    !text.includes(query);
                            }
                        );
                }
            );
        }

        $$("[data-objective-filter]")
            .forEach(
                (button) => {
                    button.addEventListener(
                        "click",
                        () => {
                            $$(
                                "[data-objective-filter]"
                            )
                                .forEach(
                                    (candidate) => {
                                        candidate.classList
                                            .toggle(
                                                "active",
                                                candidate ===
                                                    button
                                            );
                                    }
                                );

                            const filter =
                                button.dataset
                                    .objectiveFilter;

                            const grid =
                                $("#objective-grid");

                            if (grid) {
                                grid.dataset
                                    .objectiveFilter =
                                    filter;
                            }

                            window.dispatchEvent(
                                new CustomEvent(
                                    "niche:objective-filter",
                                    {
                                        detail: {
                                            filter,
                                            authority_effect:
                                                "none"
                                        }
                                    }
                                )
                            );
                        }
                    );
                }
            );
    }

    function bindKeyboard() {
        let pendingGo =
            false;

        let pendingTimer =
            null;

        const destinations =
            Object.freeze({
                e: "execute",
                c: "causal",
                o: "objectives",
                t: "timeline",
                v: "evidence",
                l: "living",
                h: "history"
            });

        function editableTarget(target) {
            if (
                !target ||
                !(target instanceof Element)
            ) {
                return false;
            }

            return Boolean(
                target.closest(
                    "input, textarea, select, [contenteditable='true']"
                )
            );
        }

        function activateView(view) {
            const button =
                $(
                    `.nav [data-view="${view}"]`
                );

            if (button) {
                button.click();
            }
        }

        document.addEventListener(
            "keydown",
            (event) => {
                if (
                    editableTarget(
                        event.target
                    )
                ) {
                    return;
                }

                if (
                    event.key === "g" &&
                    !event.metaKey &&
                    !event.ctrlKey &&
                    !event.altKey
                ) {
                    pendingGo =
                        true;

                    window.clearTimeout(
                        pendingTimer
                    );

                    pendingTimer =
                        window.setTimeout(
                            () => {
                                pendingGo =
                                    false;
                            },
                            900
                        );

                    return;
                }

                if (
                    pendingGo &&
                    destinations[event.key]
                ) {
                    event.preventDefault();

                    pendingGo =
                        false;

                    window.clearTimeout(
                        pendingTimer
                    );

                    activateView(
                        destinations[event.key]
                    );

                    return;
                }

                pendingGo =
                    false;

                if (
                    event.key === "f" &&
                    !event.metaKey &&
                    !event.ctrlKey &&
                    !event.altKey
                ) {
                    event.preventDefault();

                    activateView(
                        "execute"
                    );

                    $("#start-next")
                        ?.focus();
                }
            }
        );
    }

    function restoreState() {
        applyTheme(
            safeRead(
                STORAGE.theme
            ) || "nexus",
            {
                persist: false
            }
        );

        applyCausalMode(
            safeRead(
                STORAGE.causalMode
            ) || "topology",
            {
                persist: false
            }
        );

        applyCausalZoom(
            safeRead(
                STORAGE.causalZoom
            ) || 1,
            {
                persist: false
            }
        );
    }

    function initialize() {
        if (state.ready) {
            return;
        }

        state.ready =
            true;

        restoreState();
        bindTheme();
        bindCausalModes();
        bindViewport();
        bindSelectionSync();
        bindObjectiveControls();
        bindKeyboard();
        syncSelection();

        document.documentElement
            .dataset
            .nicheVnext =
            "ready";

        window.dispatchEvent(
            new CustomEvent(
                "niche:vnext-ready",
                {
                    detail: {
                        authority_effect:
                            "none",
                        visual_system:
                            state.theme,
                        causal_mode:
                            state.causalMode
                    }
                }
            )
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

    window.NicheVnext =
        Object.freeze({
            state() {
                return {
                    ready:
                        state.ready,
                    theme:
                        state.theme,
                    causalMode:
                        state.causalMode,
                    causalZoom:
                        state.causalZoom,
                    selectedTaskId:
                        state.selectedTaskId,
                    authorityEffect:
                        "none"
                };
            },

            theme:
                applyTheme,

            causalMode:
                applyCausalMode,

            causalZoom:
                applyCausalZoom
        });
})();
