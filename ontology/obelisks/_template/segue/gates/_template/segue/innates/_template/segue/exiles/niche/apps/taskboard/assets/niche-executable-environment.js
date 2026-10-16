"use strict";

/*
 * savant / niche
 * executable task environment enhancement layer
 *
 * owner: exile:niche
 * authority_effect: none
 * projection_only: true
 *
 * This module does not own task state.
 * It does not perform authoritative mutations.
 * It observes and augments the existing Niche interface.
 */

(() => {
    "use strict";

    const schema =
        "savant.niche.executable-environment.v1";

    const views = Object.freeze([
        "execute",
        "flow",
        "constellation",
        "objectives",
        "timeline",
        "evidence",
        "living",
        "history"
    ]);

    const storageKeys =
        Object.freeze({
            view:
                "savant.niche.interface.view",
            inspectorWidth:
                "savant.niche.interface.inspector-width",
            commandHistory:
                "savant.niche.interface.command-history"
        });

    const runtime = {
        initialized: false,
        observer: null,
        resizeObserver: null,
        selectedTaskId: null,
        previousTaskId: null,
        activeView: "execute",
        lastTaskCount: null,
        lastLivingCount: null,
        commandHistory: [],
        commandSequence: "",
        commandSequenceTimer: null,
        reticle: null,
        deck: null,
        compass: null,
        reducedMotion:
            window.matchMedia(
                "(prefers-reduced-motion: reduce)"
            ).matches,
        coarsePointer:
            window.matchMedia(
                "(pointer: coarse)"
            ).matches
    };

    const $ =
        (selector, root = document) =>
            root.querySelector(selector);

    const $$ =
        (selector, root = document) =>
            Array.from(
                root.querySelectorAll(
                    selector
                )
            );

    function safeStorageGet(
        key,
        fallback = null
    ) {
        try {
            const value =
                window.localStorage
                    .getItem(key);

            return value === null
                ? fallback
                : value;

        } catch (_error) {
            return fallback;
        }
    }

    function safeStorageSet(
        key,
        value
    ) {
        try {
            window.localStorage
                .setItem(
                    key,
                    value
                );

        } catch (_error) {
            /*
             * Interface preferences are optional.
             * Failure has no authority effect.
             */
        }
    }

    function safeJsonParse(
        value,
        fallback
    ) {
        try {
            return JSON.parse(
                value
            );

        } catch (_error) {
            return fallback;
        }
    }

    function normalizedText(
        value,
        fallback = "UNKNOWN"
    ) {
        if (
            value === null ||
            value === undefined
        ) {
            return fallback;
        }

        const text =
            String(value).trim();

        return text || fallback;
    }

    function setDatasetState(
        element,
        state
    ) {
        if (!element) {
            return;
        }

        element.dataset.state =
            normalizedText(
                state,
                "unknown"
            )
                .toLowerCase()
                .replace(
                    /[^a-z0-9_-]+/g,
                    "-"
                );
    }

    function createInstrument(
        label,
        id
    ) {
        const element =
            document.createElement(
                "div"
            );

        element.className =
            "niche-deck-instrument";

        element.id = id;

        element.dataset.state =
            "unknown";

        const labelElement =
            document.createElement(
                "span"
            );

        labelElement.textContent =
            label;

        const lamp =
            document.createElement(
                "i"
            );

        lamp.setAttribute(
            "aria-hidden",
            "true"
        );

        const value =
            document.createElement(
                "strong"
            );

        value.textContent =
            "UNKNOWN";

        element.append(
            labelElement,
            lamp,
            value
        );

        return element;
    }

    function buildDeck() {
        if (
            $("#niche-executable-deck")
        ) {
            runtime.deck =
                $("#niche-executable-deck");

            return;
        }

        const statusrail =
            $("#statusrail");

        if (!statusrail) {
            return;
        }

        const deck =
            document.createElement(
                "section"
            );

        deck.id =
            "niche-executable-deck";

        deck.className =
            "niche-executable-deck";

        deck.setAttribute(
            "aria-label",
            "Niche execution projection status"
        );

        const main =
            document.createElement(
                "div"
            );

        main.className =
            "niche-deck-main";

        const coordinate =
            document.createElement(
                "div"
            );

        coordinate.className =
            "niche-deck-coordinate";

        coordinate.setAttribute(
            "aria-hidden",
            "true"
        );

        const coordinateText =
            document.createElement(
                "span"
            );

        coordinateText.textContent =
            "NX";

        coordinate.appendChild(
            coordinateText
        );

        const readout =
            document.createElement(
                "div"
            );

        readout.className =
            "niche-deck-readout";

        const label =
            document.createElement(
                "div"
            );

        label.className =
            "niche-deck-label";

        label.textContent =
            "CURRENT EXECUTABLE SHAPE";

        const value =
            document.createElement(
                "div"
            );

        value.id =
            "niche-deck-value";

        value.className =
            "niche-deck-value";

        value.textContent =
            "Resolving authoritative task projection";

        readout.append(
            label,
            value
        );

        main.append(
            coordinate,
            readout
        );

        const instruments =
            document.createElement(
                "div"
            );

        instruments.className =
            "niche-deck-instruments";

        instruments.append(
            createInstrument(
                "TASK FIELD",
                "niche-deck-tasks"
            ),
            createInstrument(
                "FRONTIER",
                "niche-deck-frontier"
            ),
            createInstrument(
                "LIVING",
                "niche-deck-living"
            ),
            createInstrument(
                "PROJECTION",
                "niche-deck-projection"
            )
        );

        const compass =
            document.createElement(
                "div"
            );

        compass.className =
            "niche-view-compass";

        compass.setAttribute(
            "aria-hidden",
            "true"
        );

        views.forEach(
            (view) => {
                const segment =
                    document.createElement(
                        "span"
                    );

                segment.dataset.view =
                    view;

                compass.appendChild(
                    segment
                );
            }
        );

        deck.append(
            main,
            instruments,
            compass
        );

        statusrail.insertAdjacentElement(
            "afterend",
            deck
        );

        runtime.deck = deck;
        runtime.compass = compass;
    }

    function buildReticle() {
        if (
            runtime.coarsePointer ||
            runtime.reducedMotion ||
            $(".niche-reticle")
        ) {
            return;
        }

        const reticle =
            document.createElement(
                "div"
            );

        reticle.className =
            "niche-reticle";

        reticle.setAttribute(
            "aria-hidden",
            "true"
        );

        document.body.appendChild(
            reticle
        );

        runtime.reticle =
            reticle;

        document.addEventListener(
            "pointermove",
            (event) => {
                if (
                    event.pointerType ===
                    "touch"
                ) {
                    return;
                }

                reticle.style.transform =
                    `translate3d(${event.clientX - 14}px, ${event.clientY - 14}px, 0)`;

                reticle.classList.add(
                    "visible"
                );
            },
            {
                passive: true
            }
        );

        document.addEventListener(
            "pointerleave",
            () => {
                reticle.classList.remove(
                    "visible"
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
                return (
                    window.Niche.state() ||
                    {}
                );
            }

        } catch (_error) {
            return {};
        }

        return {};
    }

    function updateCompass(
        activeView
    ) {
        const compass =
            runtime.compass ||
            $(".niche-view-compass");

        if (!compass) {
            return;
        }

        $$(
            "[data-view]",
            compass
        ).forEach(
            (segment) => {
                segment.classList.toggle(
                    "active",
                    segment.dataset.view ===
                        activeView
                );
            }
        );
    }

    function updateDeck() {
        const nicheState =
            currentNicheState();

        const activeView =
            normalizedText(
                nicheState.activeView,
                runtime.activeView
            ).toLowerCase();

        runtime.activeView =
            views.includes(activeView)
                ? activeView
                : "execute";

        const selectedTaskId =
            nicheState.selectedTaskId ||
            null;

        const recommendedTaskId =
            nicheState.recommendedTaskId ||
            null;

        const taskCount =
            Number.isFinite(
                Number(
                    nicheState.taskCount
                )
            )
                ? Number(
                    nicheState.taskCount
                )
                : null;

        const livingCount =
            Number.isFinite(
                Number(
                    nicheState.livingSurfaceCount
                )
            )
                ? Number(
                    nicheState.livingSurfaceCount
                )
                : null;

        const readout =
            $("#niche-deck-value");

        if (readout) {
            if (selectedTaskId) {
                readout.textContent =
                    `FOCUS // ${selectedTaskId}`;

            } else if (
                recommendedTaskId
            ) {
                readout.textContent =
                    `NEXT // ${recommendedTaskId}`;

            } else {
                readout.textContent =
                    "EXECUTABLE FRONTIER // BASIS UNRESOLVED";
            }
        }

        const tasks =
            $("#niche-deck-tasks");

        if (tasks) {
            const value =
                $("strong", tasks);

            value.textContent =
                taskCount === null
                    ? "UNKNOWN"
                    : String(taskCount);

            setDatasetState(
                tasks,
                taskCount === null
                    ? "unknown"
                    : "available"
            );
        }

        const frontier =
            $("#niche-deck-frontier");

        if (frontier) {
            const value =
                $("strong", frontier);

            if (recommendedTaskId) {
                value.textContent =
                    "READY";

                setDatasetState(
                    frontier,
                    "ready"
                );

            } else {
                value.textContent =
                    "UNKNOWN";

                setDatasetState(
                    frontier,
                    "unknown"
                );
            }
        }

        const living =
            $("#niche-deck-living");

        if (living) {
            const value =
                $("strong", living);

            value.textContent =
                livingCount === null
                    ? "UNKNOWN"
                    : String(livingCount);

            setDatasetState(
                living,
                livingCount === null
                    ? "unknown"
                    : "available"
            );
        }

        const projection =
            $("#niche-deck-projection");

        if (projection) {
            const apiText =
                normalizedText(
                    $("#api-status-text")
                        ?.textContent,
                    "unknown"
                )
                    .toLowerCase();

            const value =
                $("strong", projection);

            const healthy =
                apiText.includes(
                    "healthy"
                ) ||
                apiText.includes(
                    "available"
                ) ||
                apiText.includes(
                    "connected"
                );

            const degraded =
                apiText.includes(
                    "degraded"
                );

            value.textContent =
                healthy
                    ? "LIVE"
                    : degraded
                        ? "DEGRADED"
                        : "UNKNOWN";

            setDatasetState(
                projection,
                healthy
                    ? "healthy"
                    : degraded
                        ? "degraded"
                        : "unknown"
            );
        }

        updateCompass(
            runtime.activeView
        );

        if (
            runtime.lastTaskCount !== null &&
            taskCount !== null &&
            runtime.lastTaskCount !==
                taskCount
        ) {
            pulse(
                tasks
            );
        }

        if (
            runtime.lastLivingCount !== null &&
            livingCount !== null &&
            runtime.lastLivingCount !==
                livingCount
        ) {
            pulse(
                living
            );
        }

        runtime.lastTaskCount =
            taskCount;

        runtime.lastLivingCount =
            livingCount;

        if (
            selectedTaskId !==
            runtime.selectedTaskId
        ) {
            runtime.previousTaskId =
                runtime.selectedTaskId;

            runtime.selectedTaskId =
                selectedTaskId;

            synchronizeSelection();
        }
    }

    function pulse(
        element
    ) {
        if (
            !element ||
            runtime.reducedMotion
        ) {
            return;
        }

        element.classList.remove(
            "niche-change-trace"
        );

        requestAnimationFrame(
            () => {
                element.classList.add(
                    "niche-change-trace"
                );
            }
        );

        window.setTimeout(
            () => {
                element.classList.remove(
                    "niche-change-trace"
                );
            },
            1000
        );
    }

    function taskElements(
        taskId
    ) {
        if (!taskId) {
            return [];
        }

        return $$(
            "[data-task-id]"
        ).filter(
            (element) =>
                element.dataset.taskId ===
                taskId
        );
    }

    function relatedTaskIds(
        selected
    ) {
        if (!selected) {
            return new Set();
        }

        const related =
            new Set([
                selected
            ]);

        taskElements(
            selected
        ).forEach(
            (element) => {
                [
                    "dependencies",
                    "dependents",
                    "upstream",
                    "downstream"
                ].forEach(
                    (name) => {
                        const raw =
                            element.dataset[
                                name
                            ];

                        if (!raw) {
                            return;
                        }

                        raw
                            .split(/[,\s]+/)
                            .map(
                                (item) =>
                                    item.trim()
                            )
                            .filter(Boolean)
                            .forEach(
                                (item) =>
                                    related.add(
                                        item
                                    )
                            );
                    }
                );
            }
        );

        return related;
    }

    function synchronizeSelection() {
        const selected =
            runtime.selectedTaskId;

        const related =
            relatedTaskIds(
                selected
            );

        $$(
            "[data-task-id]"
        ).forEach(
            (element) => {
                const id =
                    element.dataset.taskId;

                const isSelected =
                    Boolean(
                        selected &&
                        id === selected
                    );

                element.dataset
                    .nicheSelected =
                    isSelected
                        ? "true"
                        : "false";

                if (
                    selected &&
                    related.has(id)
                ) {
                    element.dataset
                        .nicheRelated =
                        "true";

                } else {
                    delete element.dataset
                        .nicheRelated;
                }
            }
        );

        document.body.classList.toggle(
            "niche-focus-compressed",
            Boolean(selected)
        );

        if (selected) {
            taskElements(
                selected
            ).forEach(
                pulse
            );
        }

        updateGraphAlternative();
    }

    function updateGraphAlternative() {
        const stage =
            $("#graph-stage");

        if (!stage) {
            return;
        }

        let companion =
            $(".niche-a11y-graph", stage);

        if (!companion) {
            companion =
                document.createElement(
                    "div"
                );

            companion.className =
                "niche-a11y-graph";

            companion.id =
                "niche-graph-companion";

            stage.appendChild(
                companion
            );

            stage.setAttribute(
                "aria-describedby",
                companion.id
            );
        }

        const nodes =
            $$(
                "[data-task-id]",
                stage
            );

        const selected =
            runtime.selectedTaskId;

        if (!nodes.length) {
            companion.textContent =
                "Dependency graph projection currently has no rendered task nodes.";

            return;
        }

        if (selected) {
            companion.textContent =
                `Dependency graph contains ${nodes.length} rendered task nodes. Selected task ${selected}. Use the task inspector and dependency controls for textual navigation.`;

        } else {
            companion.textContent =
                `Dependency graph contains ${nodes.length} rendered task nodes. No task is currently selected.`;
        }
    }

    function markUnknowns() {
        const unknownPatterns =
            /^(unknown|not projected|unresolved|not available|not authoritative)$/i;

        $$(
            ".fabric-meta, .priority, .oracle-explanation, .compact-list, .metric-grid, .inspector-section"
        ).forEach(
            (container) => {
                if (
                    unknownPatterns.test(
                        normalizedText(
                            container.textContent,
                            ""
                        )
                    )
                ) {
                    container.classList.add(
                        "niche-unknown"
                    );

                } else {
                    container.classList.remove(
                        "niche-unknown"
                    );
                }
            }
        );
    }

    function markProjectionSemantics() {
        const authorityText =
            normalizedText(
                $("#authority-status-text")
                    ?.textContent,
                ""
            ).toLowerCase();

        const deck =
            runtime.deck;

        if (!deck) {
            return;
        }

        let badge =
            $(
                ".niche-projection-badge",
                deck
            );

        if (!badge) {
            badge =
                document.createElement(
                    "span"
                );

            badge.className =
                "niche-projection-badge";

            const readout =
                $(".niche-deck-readout");

            readout?.appendChild(
                badge
            );
        }

        if (
            authorityText.includes(
                "projection"
            )
        ) {
            badge.textContent =
                "INTERFACE PROJECTION";

        } else if (
            authorityText
        ) {
            badge.textContent =
                authorityText.toUpperCase();

        } else {
            badge.textContent =
                "AUTHORITY BASIS UNKNOWN";
        }
    }

    function updateTopOffset() {
        const topbar =
            $(".topbar");

        const status =
            $("#statusrail");

        const deck =
            runtime.deck;

        const height =
            [
                topbar,
                status,
                deck
            ].reduce(
                (
                    total,
                    element
                ) =>
                    total +
                    (
                        element
                            ?.getBoundingClientRect()
                            .height ||
                        0
                    ),
                0
            );

        document.documentElement
            .style
            .setProperty(
                "--niche-top-offset",
                `${Math.ceil(height)}px`
            );
    }

    function persistView() {
        const active =
            $(
                ".nav [data-view].active"
            ) ||
            $(
                ".nav [data-view][aria-current='page']"
            );

        if (
            active?.dataset.view &&
            views.includes(
                active.dataset.view
            )
        ) {
            runtime.activeView =
                active.dataset.view;

            safeStorageSet(
                storageKeys.view,
                runtime.activeView
            );

            updateCompass(
                runtime.activeView
            );
        }
    }

    function restoreView() {
        const saved =
            safeStorageGet(
                storageKeys.view,
                null
            );

        if (
            !saved ||
            !views.includes(saved)
        ) {
            return;
        }

        window.setTimeout(
            () => {
                try {
                    if (
                        window.Niche &&
                        typeof window.Niche.view ===
                            "function"
                    ) {
                        window.Niche.view(
                            saved
                        );
                    }

                } catch (_error) {
                    /*
                     * View persistence is optional.
                     */
                }
            },
            80
        );
    }

    function loadCommandHistory() {
        const raw =
            safeStorageGet(
                storageKeys.commandHistory,
                "[]"
            );

        const parsed =
            safeJsonParse(
                raw,
                []
            );

        runtime.commandHistory =
            Array.isArray(parsed)
                ? parsed
                    .filter(
                        (item) =>
                            typeof item ===
                                "string"
                    )
                    .slice(-20)
                : [];
    }

    function recordCommand(
        command
    ) {
        const normalized =
            normalizedText(
                command,
                ""
            );

        if (!normalized) {
            return;
        }

        runtime.commandHistory =
            runtime.commandHistory
                .filter(
                    (item) =>
                        item !==
                        normalized
                );

        runtime.commandHistory.push(
            normalized
        );

        runtime.commandHistory =
            runtime.commandHistory
                .slice(-20);

        safeStorageSet(
            storageKeys.commandHistory,
            JSON.stringify(
                runtime.commandHistory
            )
        );
    }

    function bindCommandHistory() {
        const input =
            $("#palette-input");

        if (!input) {
            return;
        }

        input.addEventListener(
            "change",
            () => {
                recordCommand(
                    input.value
                );
            }
        );

        input.addEventListener(
            "keydown",
            (event) => {
                if (
                    event.key !==
                    "ArrowUp" ||
                    input.value
                ) {
                    return;
                }

                const previous =
                    runtime.commandHistory[
                        runtime.commandHistory
                            .length -
                        1
                    ];

                if (!previous) {
                    return;
                }

                input.value =
                    previous;

                input.dispatchEvent(
                    new Event(
                        "input",
                        {
                            bubbles: true
                        }
                    )
                );
            }
        );
    }

    function showKeyboardHelp() {
        const informationShell =
            $("#information-shell");

        const title =
            $("#information-title");

        const body =
            $("#information-body");

        if (
            !informationShell ||
            !title ||
            !body
        ) {
            return;
        }

        title.textContent =
            "Niche keyboard environment";

        body.innerHTML = `
            <div class="inspector-section">
                <div class="eyebrow">NAVIGATION</div>
                <p><kbd>⌘/Ctrl K</kbd> command palette</p>
                <p><kbd>/</kbd> search</p>
                <p><kbd>?</kbd> keyboard reference</p>
                <p><kbd>F</kbd> execution focus</p>
                <p><kbd>G E</kbd> Execute</p>
                <p><kbd>G C</kbd> Constellation</p>
                <p><kbd>G L</kbd> Living</p>
                <p><kbd>G H</kbd> History</p>
                <p><kbd>Esc</kbd> progressively close context</p>
            </div>
            <div class="inspector-section">
                <div class="eyebrow">AUTHORITY</div>
                <p>Keyboard navigation changes interface context only. Task mutation remains explicit through Niche transition controls.</p>
            </div>
        `;

        informationShell.hidden =
            false;

        const close =
            $("#information-close");

        close?.focus();
    }

    function routeSequence(
        sequence
    ) {
        const mapping = {
            ge: "execute",
            gf: "flow",
            gc: "constellation",
            go: "objectives",
            gt: "timeline",
            gv: "evidence",
            gl: "living",
            gh: "history"
        };

        const target =
            mapping[sequence];

        if (!target) {
            return false;
        }

        try {
            window.Niche?.view?.(
                target
            );

            safeStorageSet(
                storageKeys.view,
                target
            );

            return true;

        } catch (_error) {
            return false;
        }
    }

    function bindSpatialKeyboard() {
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
                    return;
                }

                if (
                    event.key === "?"
                ) {
                    event.preventDefault();
                    showKeyboardHelp();
                    return;
                }

                if (
                    event.key.toLowerCase() ===
                    "f"
                ) {
                    if (
                        runtime.selectedTaskId
                    ) {
                        document.body
                            .classList
                            .toggle(
                                "niche-focus-compressed"
                            );
                    }

                    return;
                }

                const key =
                    event.key
                        .toLowerCase();

                if (
                    key === "g" &&
                    !runtime.commandSequence
                ) {
                    runtime.commandSequence =
                        "g";

                    clearTimeout(
                        runtime.commandSequenceTimer
                    );

                    runtime.commandSequenceTimer =
                        window.setTimeout(
                            () => {
                                runtime.commandSequence =
                                    "";
                            },
                            900
                        );

                    return;
                }

                if (
                    runtime.commandSequence ===
                    "g"
                ) {
                    const sequence =
                        `g${key}`;

                    runtime.commandSequence =
                        "";

                    clearTimeout(
                        runtime.commandSequenceTimer
                    );

                    if (
                        routeSequence(
                            sequence
                        )
                    ) {
                        event.preventDefault();
                    }
                }
            }
        );
    }

    function bindViewPersistence() {
        $(".nav")?.addEventListener(
            "click",
            (event) => {
                const button =
                    event.target.closest(
                        "[data-view]"
                    );

                if (!button) {
                    return;
                }

                window.setTimeout(
                    persistView,
                    0
                );
            }
        );
    }

    function bindGraphInteractions() {
        const stage =
            $("#graph-stage");

        if (!stage) {
            return;
        }

        stage.addEventListener(
            "dblclick",
            (event) => {
                const node =
                    event.target.closest(
                        "[data-task-id]"
                    );

                if (!node) {
                    return;
                }

                const id =
                    node.dataset.taskId;

                if (!id) {
                    return;
                }

                try {
                    window.Niche?.task?.(
                        id
                    );

                    window.Niche?.view?.(
                        "execute"
                    );

                } catch (_error) {
                    /*
                     * Core Niche remains responsible
                     * for task selection.
                     */
                }
            }
        );

        stage.addEventListener(
            "keydown",
            (event) => {
                if (
                    ![
                        "ArrowLeft",
                        "ArrowRight",
                        "ArrowUp",
                        "ArrowDown"
                    ].includes(
                        event.key
                    )
                ) {
                    return;
                }

                const nodes =
                    $$(
                        "[data-task-id]",
                        stage
                    ).filter(
                        (element) =>
                            !element.hidden
                    );

                if (!nodes.length) {
                    return;
                }

                const active =
                    document.activeElement;

                let index =
                    nodes.indexOf(
                        active
                    );

                if (index < 0) {
                    index = 0;

                } else if (
                    event.key ===
                        "ArrowRight" ||
                    event.key ===
                        "ArrowDown"
                ) {
                    index =
                        Math.min(
                            nodes.length - 1,
                            index + 1
                        );

                } else {
                    index =
                        Math.max(
                            0,
                            index - 1
                        );
                }

                event.preventDefault();

                nodes[index]
                    .focus?.();
            }
        );
    }

    function ensureGraphNodesFocusable() {
        $$(
            "#graph-stage [data-task-id]"
        ).forEach(
            (node) => {
                if (
                    !node.hasAttribute(
                        "tabindex"
                    )
                ) {
                    node.tabIndex = 0;
                }

                if (
                    !node.hasAttribute(
                        "role"
                    )
                ) {
                    node.setAttribute(
                        "role",
                        "button"
                    );
                }
            }
        );
    }

    function constrainInspector() {
        const inspector =
            $("#inspector");

        if (!inspector) {
            return;
        }

        const saved =
            Number(
                safeStorageGet(
                    storageKeys.inspectorWidth,
                    ""
                )
            );

        if (
            Number.isFinite(saved) &&
            saved >= 280 &&
            saved <=
                Math.min(
                    760,
                    window.innerWidth -
                        32
                ) &&
            window.innerWidth >
                700
        ) {
            inspector.style.width =
                `${saved}px`;
        }

        const rect =
            inspector
                .getBoundingClientRect();

        if (
            rect.width >
            window.innerWidth
        ) {
            inspector.style.width =
                "100%";
        }
    }

    function semanticRefresh() {
        updateDeck();
        persistView();
        markUnknowns();
        markProjectionSemantics();
        ensureGraphNodesFocusable();
        updateGraphAlternative();
        constrainInspector();
        updateTopOffset();
    }

    function observeInterface() {
        if (runtime.observer) {
            runtime.observer.disconnect();
        }

        let queued = false;

        runtime.observer =
            new MutationObserver(
                () => {
                    if (queued) {
                        return;
                    }

                    queued = true;

                    requestAnimationFrame(
                        () => {
                            queued = false;
                            semanticRefresh();
                        }
                    );
                }
            );

        runtime.observer.observe(
            document.body,
            {
                subtree: true,
                childList: true,
                attributes: true,
                attributeFilter: [
                    "class",
                    "aria-current",
                    "aria-hidden",
                    "hidden",
                    "data-task-id"
                ]
            }
        );
    }

    function observeGeometry() {
        if (
            typeof ResizeObserver !==
            "function"
        ) {
            window.addEventListener(
                "resize",
                updateTopOffset,
                {
                    passive: true
                }
            );

            return;
        }

        runtime.resizeObserver =
            new ResizeObserver(
                () => {
                    updateTopOffset();
                    constrainInspector();
                }
            );

        [
            $(".topbar"),
            $("#statusrail"),
            runtime.deck,
            $("#inspector")
        ]
            .filter(Boolean)
            .forEach(
                (element) =>
                    runtime.resizeObserver
                        .observe(
                            element
                        )
            );
    }

    function announceReady() {
        document.documentElement
            .dataset
            .nicheExecutableEnvironment =
            "ready";

        window.dispatchEvent(
            new CustomEvent(
                "niche:executable-environment-ready",
                {
                    detail: {
                        schema,
                        authority_effect:
                            "none",
                        projection_only:
                            true,
                        reduced_motion:
                            runtime.reducedMotion
                    }
                }
            )
        );
    }

    function initialize() {
        if (
            runtime.initialized
        ) {
            return;
        }

        runtime.initialized = true;

        loadCommandHistory();

        buildDeck();
        buildReticle();

        bindCommandHistory();
        bindSpatialKeyboard();
        bindViewPersistence();
        bindGraphInteractions();

        observeInterface();
        observeGeometry();

        restoreView();

        semanticRefresh();

        window.setTimeout(
            semanticRefresh,
            250
        );

        window.setTimeout(
            semanticRefresh,
            1000
        );

        announceReady();
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

    window.NicheExecutableEnvironment =
        Object.freeze({
            schema,
            authorityEffect:
                "none",
            projectionOnly:
                true,
            refresh:
                semanticRefresh,
            state() {
                return {
                    initialized:
                        runtime.initialized,
                    activeView:
                        runtime.activeView,
                    selectedTaskId:
                        runtime.selectedTaskId,
                    reducedMotion:
                        runtime.reducedMotion,
                    commandHistoryLength:
                        runtime.commandHistory
                            .length
                };
            }
        });
})();
