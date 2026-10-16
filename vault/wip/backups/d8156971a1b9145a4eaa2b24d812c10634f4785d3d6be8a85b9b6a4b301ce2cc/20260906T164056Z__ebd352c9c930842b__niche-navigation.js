"use strict";

/*
 * savant / niche / navigation
 *
 * owner: exile:niche
 * semantic_role: represented task-topology navigation controller
 * authority_effect: none
 * projection_only: true
 *
 * substance:
 *   authoritative task data is read through the established niche api.
 *
 * projection:
 *   navigation geometry, territories, routes, viewport state, search
 *   results, selection emphasis and local preferences are non-authoritative.
 *
 * mutation:
 *   none.
 */

(() => {
    "use strict";

    const SVG_NS = "http://www.w3.org/2000/svg";

    const TASK_ENDPOINT =
        "/api/tasks?include_terminal=true";

    const STORAGE_KEY =
        "savant.niche.navigation.v3";

    const EVENT_PREFIX =
        "niche:navigation";

    const WORLD = Object.freeze({
        padding: 90,
        territoryWidth: 900,
        territoryHeight: 680,
        territoryGapX: 120,
        territoryGapY: 130,
        columns: 4,
        nodeWidth: 188,
        nodeHeight: 58,
        nodeGapX: 64,
        nodeGapY: 34,
        nodeColumns: 4,
    });

    const VIEWPORT = Object.freeze({
        minScale: 0.18,
        maxScale: 3.8,
        wheelFactor: 0.00135,
        keyboardPan: 90,
        zoomStep: 1.22,
    });

    const KNOWN_STATES = new Set([
        "ready",
        "active",
        "review",
        "waiting",
        "blocked",
        "complete",
    ]);

    const FILTERS = Object.freeze([
        "all",
        "ready",
        "active",
        "review",
        "waiting",
        "blocked",
        "complete",
        "unknown",
    ]);

    const LENSES = Object.freeze([
        "structure",
        "dependencies",
        "objectives",
        "status",
    ]);

    const state = {
        installed: false,
        loaded: false,
        loading: false,
        loadPromise: null,
        generation: 0,
        fetchController: null,
        resizeObserver: null,
        renderQueued: false,
        transformQueued: false,

        tasks: [],
        nodes: [],
        territories: [],
        edges: [],
        nodeById: new Map(),
        taskById: new Map(),
        childrenById: new Map(),
        dependentsById: new Map(),

        selectedId: "",
        lens: "structure",
        filter: "all",
        isolate: false,
        route: [],

        viewport: {
            x: 0,
            y: 0,
            scale: 1,
        },

        world: {
            width: 1600,
            height: 1000,
        },

        pointer: {
            mode: "",
            x: 0,
            y: 0,
            originX: 0,
            originY: 0,
            viewportX: 0,
            viewportY: 0,
            active: new Map(),
            pinchDistance: 0,
            pinchScale: 1,
            pinchCenterX: 0,
            pinchCenterY: 0,
        },

        selectionHistory: [],
    };

    const dom = Object.create(null);

    function q(selector, root = document) {
        return root.querySelector(selector);
    }

    function qa(selector, root = document) {
        return Array.from(root.querySelectorAll(selector));
    }

    function createSvg(name, attributes = {}) {
        const element =
            document.createElementNS(
                SVG_NS,
                name,
            );

        for (const [key, value] of
            Object.entries(attributes)) {
            element.setAttribute(
                key,
                String(value),
            );
        }

        return element;
    }

    function asText(value, fallback = "") {
        if (
            value === null ||
            value === undefined
        ) {
            return fallback;
        }

        const normalized =
            String(value).trim();

        return normalized || fallback;
    }

    function lower(value) {
        return asText(value).toLowerCase();
    }

    function firstRepresented(...values) {
        for (const value of values) {
            if (
                value !== undefined &&
                value !== null &&
                value !== ""
            ) {
                return value;
            }
        }

        return undefined;
    }

    function clamp(value, minimum, maximum) {
        return Math.min(
            maximum,
            Math.max(minimum, value),
        );
    }

    function escapeHtml(value) {
        return asText(value)
            .replaceAll("&", "&amp;")
            .replaceAll("<", "&lt;")
            .replaceAll(">", "&gt;")
            .replaceAll('"', "&quot;")
            .replaceAll("'", "&#039;");
    }

    function truncate(value, maximum = 46) {
        const source =
            asText(value);

        if (source.length <= maximum) {
            return source;
        }

        return `${source.slice(
            0,
            Math.max(1, maximum - 1),
        )}…`;
    }

    function emit(type, detail = {}) {
        window.dispatchEvent(
            new CustomEvent(
                `${EVENT_PREFIX}:${type}`,
                {
                    detail: {
                        ...detail,
                        authority_effect:
                            "none",
                        projection_only:
                            true,
                    },
                },
            ),
        );
    }

    function taskId(task) {
        return asText(
            firstRepresented(
                task?.id,
                task?.task_id,
                task?.identity,
                task?.key,
            ),
        );
    }

    function taskTitle(task) {
        return asText(
            firstRepresented(
                task?.title,
                task?.name,
                task?.action,
                task?.summary,
                taskId(task),
            ),
            "untitled task",
        );
    }

    function taskReady(task) {
        const value =
            firstRepresented(
                task?.ready,
                task?.is_ready,
                task?.readiness,
            );

        if (typeof value === "boolean") {
            return value;
        }

        const normalized =
            lower(value);

        return (
            normalized === "ready" ||
            normalized === "true" ||
            normalized === "yes"
        );
    }

    function taskState(task) {
        const raw =
            lower(
                firstRepresented(
                    task?.state,
                    task?.status,
                    task?.lifecycle_state,
                ),
            );

        if (
            raw.includes("complete") ||
            raw.includes("done") ||
            raw.includes("closed")
        ) {
            return "complete";
        }

        if (
            raw.includes("block") ||
            raw.includes("failed")
        ) {
            return "blocked";
        }

        if (
            raw.includes("active") ||
            raw.includes("progress") ||
            raw.includes("started") ||
            raw.includes("leased")
        ) {
            return "active";
        }

        if (
            raw.includes("review") ||
            raw.includes("evidence") ||
            raw.includes("verify")
        ) {
            return "review";
        }

        if (
            raw.includes("wait") ||
            raw.includes("defer") ||
            raw.includes("pending")
        ) {
            return "waiting";
        }

        if (taskReady(task)) {
            return "ready";
        }

        return raw || "waiting";
    }

    function taskPriority(task) {
        return asText(
            firstRepresented(
                task?.priority,
                task?.authoritative_priority,
                task?.rank,
            ),
            "unknown",
        );
    }

    function taskObjective(task) {
        return asText(
            firstRepresented(
                task?.objective,
                task?.objective_id,
                task?.root_objective,
                task?.ancestry?.objective,
            ),
            "unknown objective",
        );
    }

    function taskParent(task) {
        return asText(
            firstRepresented(
                task?.parent,
                task?.parent_id,
                task?.parent_task_id,
                task?.ancestry?.parent,
            ),
        );
    }

    function taskDependencies(task) {
        const candidate =
            firstRepresented(
                task?.dependencies,
                task?.depends_on,
                task?.prerequisites,
                task?.requires,
            );

        if (!Array.isArray(candidate)) {
            return [];
        }

        return candidate
            .map((item) => {
                if (
                    typeof item ===
                    "string"
                ) {
                    return item.trim();
                }

                return asText(
                    firstRepresented(
                        item?.id,
                        item?.task_id,
                        item?.key,
                    ),
                );
            })
            .filter(Boolean);
    }

    function normalizeTask(task) {
        const id =
            taskId(task);

        if (!id) {
            return null;
        }

        const stateValue =
            taskState(task);

        return Object.freeze({
            id,
            title:
                taskTitle(task),
            state:
                stateValue,
            ready:
                taskReady(task),
            objective:
                taskObjective(task),
            parent:
                taskParent(task),
            dependencies:
                Object.freeze(
                    taskDependencies(task),
                ),
            priority:
                taskPriority(task),
            raw:
                task,
        });
    }

    function normalizePayload(payload) {
        const candidate =
            Array.isArray(payload)
                ? payload
                : Array.isArray(
                      payload?.tasks,
                  )
                  ? payload.tasks
                  : Array.isArray(
                        payload?.items,
                    )
                    ? payload.items
                    : [];

        const normalized =
            candidate
                .map(normalizeTask)
                .filter(Boolean);

        normalized.sort((a, b) => {
            const objective =
                a.objective.localeCompare(
                    b.objective,
                );

            if (objective !== 0) {
                return objective;
            }

            return (
                a.title.localeCompare(
                    b.title,
                ) ||
                a.id.localeCompare(b.id)
            );
        });

        return normalized;
    }

    function unknownState(node) {
        return !KNOWN_STATES.has(
            node.state,
        );
    }

    function buildRelationships(tasks) {
        const taskById =
            new Map();

        const childrenById =
            new Map();

        const dependentsById =
            new Map();

        for (const task of tasks) {
            taskById.set(
                task.id,
                task,
            );

            childrenById.set(
                task.id,
                [],
            );

            dependentsById.set(
                task.id,
                [],
            );
        }

        for (const task of tasks) {
            if (
                task.parent &&
                taskById.has(task.parent)
            ) {
                childrenById
                    .get(task.parent)
                    .push(task.id);
            }

            for (
                const dependency
                of task.dependencies
            ) {
                if (
                    dependentsById.has(
                        dependency,
                    )
                ) {
                    dependentsById
                        .get(dependency)
                        .push(task.id);
                }
            }
        }

        for (const values of [
            ...childrenById.values(),
            ...dependentsById.values(),
        ]) {
            values.sort(
                (a, b) =>
                    a.localeCompare(b),
            );
        }

        return {
            taskById,
            childrenById,
            dependentsById,
        };
    }

    function projectModel(tasks) {
        const relationships =
            buildRelationships(tasks);

        const objectiveGroups =
            new Map();

        for (const task of tasks) {
            const key =
                task.objective ||
                "unknown objective";

            if (
                !objectiveGroups.has(key)
            ) {
                objectiveGroups.set(
                    key,
                    [],
                );
            }

            objectiveGroups
                .get(key)
                .push(task);
        }

        const objectiveNames =
            Array.from(
                objectiveGroups.keys(),
            ).sort((a, b) =>
                a.localeCompare(b),
            );

        const territories = [];
        const nodes = [];
        const edges = [];
        const nodeById =
            new Map();

        let maximumRight = 0;
        let maximumBottom = 0;

        objectiveNames.forEach(
            (objective, objectiveIndex) => {
                const territoryColumn =
                    objectiveIndex %
                    WORLD.columns;

                const territoryRow =
                    Math.floor(
                        objectiveIndex /
                            WORLD.columns,
                    );

                const territoryX =
                    WORLD.padding +
                    territoryColumn *
                        (
                            WORLD.territoryWidth +
                            WORLD.territoryGapX
                        );

                const territoryY =
                    WORLD.padding +
                    territoryRow *
                        (
                            WORLD.territoryHeight +
                            WORLD.territoryGapY
                        );

                const tasksInObjective =
                    objectiveGroups
                        .get(objective)
                        .slice()
                        .sort(
                            (a, b) =>
                                a.title.localeCompare(
                                    b.title,
                                ) ||
                                a.id.localeCompare(
                                    b.id,
                                ),
                        );

                const rows =
                    Math.max(
                        1,
                        Math.ceil(
                            tasksInObjective
                                .length /
                                WORLD.nodeColumns,
                        ),
                    );

                const territoryHeight =
                    Math.max(
                        WORLD.territoryHeight,
                        150 +
                            rows *
                                (
                                    WORLD.nodeHeight +
                                    WORLD.nodeGapY
                                ),
                    );

                const territory =
                    Object.freeze({
                        id:
                            `objective:${objective}`,
                        objective,
                        x:
                            territoryX,
                        y:
                            territoryY,
                        width:
                            WORLD.territoryWidth,
                        height:
                            territoryHeight,
                        count:
                            tasksInObjective.length,
                    });

                territories.push(
                    territory,
                );

                tasksInObjective.forEach(
                    (task, index) => {
                        const column =
                            index %
                            WORLD.nodeColumns;

                        const row =
                            Math.floor(
                                index /
                                    WORLD.nodeColumns,
                            );

                        const x =
                            territoryX +
                            60 +
                            column *
                                (
                                    WORLD.nodeWidth +
                                    WORLD.nodeGapX
                                );

                        const y =
                            territoryY +
                            110 +
                            row *
                                (
                                    WORLD.nodeHeight +
                                    WORLD.nodeGapY
                                );

                        const node =
                            Object.freeze({
                                ...task,
                                x,
                                y,
                                width:
                                    WORLD.nodeWidth,
                                height:
                                    WORLD.nodeHeight,
                                territoryId:
                                    territory.id,
                            });

                        nodes.push(node);
                        nodeById.set(
                            node.id,
                            node,
                        );
                    },
                );

                maximumRight =
                    Math.max(
                        maximumRight,
                        territoryX +
                            WORLD.territoryWidth,
                    );

                maximumBottom =
                    Math.max(
                        maximumBottom,
                        territoryY +
                            territoryHeight,
                    );
            },
        );

        for (const node of nodes) {
            if (
                node.parent &&
                nodeById.has(node.parent)
            ) {
                edges.push(
                    Object.freeze({
                        id:
                            `edifice:${node.parent}:${node.id}`,
                        type:
                            "edifice",
                        source:
                            node.parent,
                        target:
                            node.id,
                    }),
                );
            }

            for (
                const dependency
                of node.dependencies
            ) {
                if (
                    nodeById.has(
                        dependency,
                    )
                ) {
                    edges.push(
                        Object.freeze({
                            id:
                                `dependency:${dependency}:${node.id}`,
                            type:
                                "dependency",
                            source:
                                dependency,
                            target:
                                node.id,
                        }),
                    );
                }
            }
        }

        edges.sort(
            (a, b) =>
                a.type.localeCompare(
                    b.type,
                ) ||
                a.source.localeCompare(
                    b.source,
                ) ||
                a.target.localeCompare(
                    b.target,
                ),
        );

        return {
            tasks,
            nodes,
            territories,
            edges,
            nodeById,
            taskById:
                relationships.taskById,
            childrenById:
                relationships.childrenById,
            dependentsById:
                relationships.dependentsById,
            world: {
                width:
                    Math.max(
                        1200,
                        maximumRight +
                            WORLD.padding,
                    ),
                height:
                    Math.max(
                        800,
                        maximumBottom +
                            WORLD.padding,
                    ),
            },
        };
    }

    function applyModel(model) {
        state.tasks =
            model.tasks;

        state.nodes =
            model.nodes;

        state.territories =
            model.territories;

        state.edges =
            model.edges;

        state.nodeById =
            model.nodeById;

        state.taskById =
            model.taskById;

        state.childrenById =
            model.childrenById;

        state.dependentsById =
            model.dependentsById;

        state.world =
            model.world;

        if (
            state.selectedId &&
            !state.nodeById.has(
                state.selectedId,
            )
        ) {
            state.selectedId = "";
            state.route = [];
        }
    }

    function neighborhoodIds(id) {
        const result =
            new Set();

        if (
            !id ||
            !state.nodeById.has(id)
        ) {
            return result;
        }

        result.add(id);

        const node =
            state.nodeById.get(id);

        if (
            node.parent &&
            state.nodeById.has(
                node.parent,
            )
        ) {
            result.add(node.parent);
        }

        for (
            const child
            of state.childrenById.get(
                id,
            ) || []
        ) {
            result.add(child);
        }

        for (
            const dependency
            of node.dependencies
        ) {
            if (
                state.nodeById.has(
                    dependency,
                )
            ) {
                result.add(dependency);
            }
        }

        for (
            const dependent
            of state.dependentsById.get(
                id,
            ) || []
        ) {
            result.add(dependent);
        }

        return result;
    }

    function visibleNodes() {
        const neighborhood =
            state.isolate &&
            state.selectedId
                ? neighborhoodIds(
                      state.selectedId,
                  )
                : null;

        return state.nodes.filter(
            (node) => {
                if (
                    neighborhood &&
                    !neighborhood.has(node.id)
                ) {
                    return false;
                }

                if (
                    state.filter ===
                    "all"
                ) {
                    return true;
                }

                if (
                    state.filter ===
                    "unknown"
                ) {
                    return unknownState(
                        node,
                    );
                }

                return (
                    node.state ===
                    state.filter
                );
            },
        );
    }

    function adjacency() {
        const graph =
            new Map();

        for (
            const node
            of state.nodes
        ) {
            graph.set(
                node.id,
                new Set(),
            );
        }

        for (
            const edge
            of state.edges
        ) {
            graph
                .get(edge.source)
                ?.add(edge.target);

            graph
                .get(edge.target)
                ?.add(edge.source);
        }

        return graph;
    }

    function representedRoute(
        sourceId,
        targetId,
    ) {
        if (
            !state.nodeById.has(
                sourceId,
            ) ||
            !state.nodeById.has(
                targetId,
            )
        ) {
            return [];
        }

        if (
            sourceId === targetId
        ) {
            return [sourceId];
        }

        const graph =
            adjacency();

        const queue =
            [sourceId];

        const previous =
            new Map([
                [sourceId, null],
            ]);

        while (queue.length) {
            const current =
                queue.shift();

            const neighbors =
                Array.from(
                    graph.get(
                        current,
                    ) || [],
                ).sort(
                    (a, b) =>
                        a.localeCompare(b),
                );

            for (
                const neighbor
                of neighbors
            ) {
                if (
                    previous.has(
                        neighbor,
                    )
                ) {
                    continue;
                }

                previous.set(
                    neighbor,
                    current,
                );

                if (
                    neighbor ===
                    targetId
                ) {
                    const route = [];
                    let cursor =
                        targetId;

                    while (
                        cursor !== null
                    ) {
                        route.push(
                            cursor,
                        );

                        cursor =
                            previous.get(
                                cursor,
                            );
                    }

                    return route.reverse();
                }

                queue.push(neighbor);
            }
        }

        return [];
    }

    function relationshipBetween(
        sourceId,
        targetId,
    ) {
        for (
            const edge
            of state.edges
        ) {
            if (
                edge.source ===
                    sourceId &&
                edge.target ===
                    targetId
            ) {
                return edge.type ===
                    "edifice"
                    ? "contains"
                    : "is required by";
            }

            if (
                edge.source ===
                    targetId &&
                edge.target ===
                    sourceId
            ) {
                return edge.type ===
                    "edifice"
                    ? "within"
                    : "requires";
            }
        }

        return "connected";
    }

    function preferenceSnapshot() {
        return {
            lens:
                state.lens,
            filter:
                state.filter,
            isolate:
                state.isolate,
            selectedId:
                state.selectedId,
            viewport: {
                ...state.viewport,
            },
        };
    }

    function savePreferences() {
        try {
            localStorage.setItem(
                STORAGE_KEY,
                JSON.stringify(
                    preferenceSnapshot(),
                ),
            );
        } catch {
            /*
             * local preferences are optional
             * and non-authoritative.
             */
        }
    }

    function restorePreferences() {
        try {
            const raw =
                localStorage.getItem(
                    STORAGE_KEY,
                );

            if (!raw) {
                return;
            }

            const parsed =
                JSON.parse(raw);

            if (
                LENSES.includes(
                    parsed?.lens,
                )
            ) {
                state.lens =
                    parsed.lens;
            }

            if (
                FILTERS.includes(
                    parsed?.filter,
                )
            ) {
                state.filter =
                    parsed.filter;
            }

            state.isolate =
                Boolean(
                    parsed?.isolate,
                );

            state.selectedId =
                asText(
                    parsed?.selectedId,
                );

            const viewport =
                parsed?.viewport;

            if (
                viewport &&
                Number.isFinite(
                    viewport.x,
                ) &&
                Number.isFinite(
                    viewport.y,
                ) &&
                Number.isFinite(
                    viewport.scale,
                )
            ) {
                state.viewport = {
                    x:
                        viewport.x,
                    y:
                        viewport.y,
                    scale:
                        clamp(
                            viewport.scale,
                            VIEWPORT.minScale,
                            VIEWPORT.maxScale,
                        ),
                };
            }
        } catch {
            /*
             * malformed preferences are ignored.
             */
        }
    }

    function ensureNavigationButton() {
        const existing =
            q(
                '.nav [data-view="navigation"]',
            );

        if (existing) {
            return existing;
        }

        const nav =
            q(".nav");

        if (!nav) {
            return null;
        }

        const button =
            document.createElement(
                "button",
            );

        button.type =
            "button";

        button.dataset.view =
            "navigation";

        button.textContent =
            "Navigation";

        const causal =
            q(
                '.nav [data-view="causal"]',
            );

        if (causal) {
            nav.insertBefore(
                button,
                causal,
            );
        } else {
            nav.append(button);
        }

        return button;
    }

    function createSurface() {
        const existing =
            q(
                "#surface-navigation",
            );

        if (existing) {
            return existing;
        }

        const surfaces =
            q(".surfaces") ||
            q("main") ||
            document.body;

        const section =
            document.createElement(
                "section",
            );

        section.id =
            "surface-navigation";

        section.className =
            "surface niche-navigation-surface";

        section.dataset.surface =
            "navigation";

        section.hidden =
            true;

        section.innerHTML = `
            <div class="navigation-heading">
                <div>
                    <div class="navigation-eyebrow">
                        REPRESENTED NICHE TASK TOPOLOGY
                    </div>
                    <h1>Navigation</h1>
                    <p>
                        Spatial orientation through represented task,
                        objective, edifice and dependency relationships.
                        Geometry is a non-authoritative projection.
                    </p>
                </div>

                <div class="navigation-location">
                    <span class="navigation-location-label">
                        YOU ARE HERE
                    </span>
                    <strong
                        id="navigation-location-value"
                        class="navigation-location-value"
                    >
                        overview
                    </strong>
                </div>
            </div>

            <div class="navigation-commandbar">
                <div class="navigation-search-shell">
                    <input
                        id="navigation-search"
                        class="navigation-input"
                        type="search"
                        autocomplete="off"
                        spellcheck="false"
                        placeholder="Find represented task…"
                        aria-label="Search represented tasks"
                    >
                    <div
                        id="navigation-search-results"
                        class="navigation-search-results"
                        role="listbox"
                    ></div>
                </div>

                <select
                    id="navigation-lens"
                    class="navigation-select"
                    aria-label="Navigation lens"
                >
                    <option value="structure">
                        Structure
                    </option>
                    <option value="dependencies">
                        Dependencies
                    </option>
                    <option value="objectives">
                        Objectives
                    </option>
                    <option value="status">
                        Status
                    </option>
                </select>

                <select
                    id="navigation-status-filter"
                    class="navigation-select"
                    aria-label="Task state filter"
                >
                    <option value="all">
                        All states
                    </option>
                    <option value="ready">
                        Ready
                    </option>
                    <option value="active">
                        Active
                    </option>
                    <option value="review">
                        Review
                    </option>
                    <option value="waiting">
                        Waiting
                    </option>
                    <option value="blocked">
                        Blocked
                    </option>
                    <option value="complete">
                        Complete
                    </option>
                    <option value="unknown">
                        Unknown
                    </option>
                </select>

                <button
                    id="navigation-isolate"
                    class="navigation-action"
                    type="button"
                    aria-pressed="false"
                >
                    Focus neighborhood
                </button>
            </div>

            <nav
                id="navigation-breadcrumb"
                class="navigation-breadcrumb"
                aria-label="Navigation breadcrumb"
            ></nav>

            <div class="navigation-shell">
                <div class="navigation-map-column">
                    <div
                        id="navigation-map-frame"
                        class="navigation-map-frame"
                        data-lens="structure"
                        data-semantic-zoom="medium"
                    >
                        <svg
                            id="navigation-map"
                            class="navigation-map"
                            tabindex="0"
                            role="application"
                            aria-label="Represented Niche task topology"
                        >
                            <defs>
                                <marker
                                    id="navigation-arrow"
                                    markerWidth="8"
                                    markerHeight="8"
                                    refX="7"
                                    refY="4"
                                    orient="auto"
                                    markerUnits="strokeWidth"
                                >
                                    <path
                                        d="M0,0 L8,4 L0,8 z"
                                        fill="currentColor"
                                    ></path>
                                </marker>
                            </defs>

                            <g id="navigation-world"></g>
                        </svg>

                        <div class="navigation-controls">
                            <button
                                id="navigation-zoom-in"
                                type="button"
                                aria-label="Zoom in"
                                title="Zoom in"
                            >
                                +
                            </button>
                            <button
                                id="navigation-zoom-out"
                                type="button"
                                aria-label="Zoom out"
                                title="Zoom out"
                            >
                                −
                            </button>
                            <button
                                id="navigation-home"
                                type="button"
                                aria-label="Fit all"
                                title="Fit all"
                            >
                                ⌂
                            </button>
                        </div>

                        <div class="navigation-zoom-meter">
                            <span id="navigation-zoom-label">
                                100%
                            </span>
                            <span class="navigation-scale-bar"></span>
                        </div>

                        <div class="navigation-minimap">
                            <svg
                                id="navigation-minimap"
                                aria-hidden="true"
                            ></svg>
                        </div>
                    </div>
                </div>

                <aside class="navigation-side">
                    <section
                        id="navigation-inspector"
                        class="navigation-panel"
                    >
                        <h2>Location</h2>
                        <p>
                            Select a represented task to inspect its
                            immediate structural neighborhood.
                        </p>
                    </section>

                    <section class="navigation-panel">
                        <h2>Route</h2>

                        <div class="navigation-route-shell">
                            <input
                                id="navigation-route-input"
                                class="navigation-input"
                                type="search"
                                autocomplete="off"
                                spellcheck="false"
                                placeholder="Destination task id or title"
                                aria-label="Navigation destination"
                            >
                        </div>

                        <button
                            id="navigation-route-button"
                            class="navigation-action"
                            type="button"
                        >
                            Find represented route
                        </button>

                        <div
                            id="navigation-route"
                            class="navigation-route"
                        ></div>
                    </section>

                    <section class="navigation-panel">
                        <h2>Projection</h2>
                        <div
                            id="navigation-stats"
                            class="navigation-stats"
                        ></div>
                    </section>

                    <section class="navigation-panel">
                        <h2>Accessible index</h2>
                        <div
                            id="navigation-text-index"
                            class="navigation-text-index"
                        ></div>
                    </section>
                </aside>
            </div>

            <div
                id="navigation-live"
                class="navigation-live"
                aria-live="polite"
                aria-atomic="true"
            ></div>
        `;

        const causal =
            q(
                '#surface-causal, [data-surface="causal"]',
            );

        if (
            causal &&
            causal.parentElement ===
                surfaces
        ) {
            surfaces.insertBefore(
                section,
                causal,
            );
        } else {
            surfaces.append(section);
        }

        return section;
    }

    function cacheDom() {
        dom.surface =
            q(
                "#surface-navigation",
            );

        dom.navButton =
            q(
                '.nav [data-view="navigation"]',
            );

        dom.location =
            q(
                "#navigation-location-value",
            );

        dom.search =
            q(
                "#navigation-search",
            );

        dom.searchResults =
            q(
                "#navigation-search-results",
            );

        dom.lens =
            q(
                "#navigation-lens",
            );

        dom.filter =
            q(
                "#navigation-status-filter",
            );

        dom.isolate =
            q(
                "#navigation-isolate",
            );

        dom.breadcrumb =
            q(
                "#navigation-breadcrumb",
            );

        dom.mapFrame =
            q(
                "#navigation-map-frame",
            );

        dom.map =
            q(
                "#navigation-map",
            );

        dom.world =
            q(
                "#navigation-world",
            );

        dom.zoomIn =
            q(
                "#navigation-zoom-in",
            );

        dom.zoomOut =
            q(
                "#navigation-zoom-out",
            );

        dom.home =
            q(
                "#navigation-home",
            );

        dom.zoomLabel =
            q(
                "#navigation-zoom-label",
            );

        dom.minimap =
            q(
                "#navigation-minimap",
            );

        dom.inspector =
            q(
                "#navigation-inspector",
            );

        dom.routeInput =
            q(
                "#navigation-route-input",
            );

        dom.routeButton =
            q(
                "#navigation-route-button",
            );

        dom.route =
            q(
                "#navigation-route",
            );

        dom.stats =
            q(
                "#navigation-stats",
            );

        dom.textIndex =
            q(
                "#navigation-text-index",
            );

        dom.live =
            q(
                "#navigation-live",
            );
    }

    function setLive(message) {
        if (dom.live) {
            dom.live.textContent =
                message;
        }
    }

    function activate() {
        install();

        if (!dom.surface) {
            return;
        }

        if (
            window.Niche &&
            typeof window.Niche.view ===
                "function"
        ) {
            try {
                window.Niche.view(
                    "navigation",
                );
            } catch {
                fallbackActivate();
            }
        } else {
            fallbackActivate();
        }

        dom.surface.hidden =
            false;

        void load();

        requestAnimationFrame(
            () => {
                dom.surface?.scrollIntoView(
                    {
                        block:
                            "start",
                    },
                );
            },
        );
    }

    function fallbackActivate() {
        for (
            const surface
            of qa(".surface")
        ) {
            const active =
                surface ===
                dom.surface;

            surface.classList.toggle(
                "active",
                active,
            );

            surface.hidden =
                !active;
        }

        for (
            const button
            of qa(
                ".nav [data-view]",
            )
        ) {
            const active =
                button ===
                dom.navButton;

            button.classList.toggle(
                "active",
                active,
            );

            button.setAttribute(
                "aria-current",
                active
                    ? "page"
                    : "false",
            );
        }
    }

    async function fetchTaskProjection() {
        state.generation += 1;

        const generation =
            state.generation;

        state.fetchController?.abort();

        const controller =
            new AbortController();

        state.fetchController =
            controller;

        const response =
            await fetch(
                TASK_ENDPOINT,
                {
                    method:
                        "GET",
                    headers: {
                        Accept:
                            "application/json",
                    },
                    cache:
                        "no-store",
                    signal:
                        controller.signal,
                },
            );

        if (!response.ok) {
            throw new Error(
                `tasks http ${response.status}`,
            );
        }

        const payload =
            await response.json();

        if (
            generation !==
            state.generation
        ) {
            throw new DOMException(
                "stale navigation projection",
                "AbortError",
            );
        }

        return normalizePayload(
            payload,
        );
    }

    function clearError() {
        const error =
            q(
                "#navigation-error",
                dom.surface,
            );

        error?.remove();
    }

    function renderError(error) {
        clearError();

        const panel =
            document.createElement(
                "div",
            );

        panel.id =
            "navigation-error";

        panel.className =
            "navigation-error";

        panel.innerHTML = `
            <strong>
                Navigation projection unavailable
            </strong>
            <p>
                Execute remains independent. No task authority was changed.
            </p>
            <button
                id="navigation-retry"
                class="navigation-action"
                type="button"
            >
                Retry Navigation
            </button>
        `;

        dom.mapFrame?.insertAdjacentElement(
            "afterend",
            panel,
        );

        q(
            "#navigation-retry",
            panel,
        )?.addEventListener(
            "click",
            () => {
                void load({
                    force:
                        true,
                });
            },
            {
                once:
                    true,
            },
        );

        setLive(
            "Navigation projection unavailable.",
        );

        emit(
            "degraded",
            {
                error:
                    asText(
                        error?.message,
                        "unknown error",
                    ),
            },
        );
    }

    async function load(
        {
            force = false,
        } = {},
    ) {
        install();

        if (
            state.loaded &&
            !force
        ) {
            return;
        }

        if (
            state.loading &&
            state.loadPromise &&
            !force
        ) {
            return state.loadPromise;
        }

        state.loading =
            true;

        dom.surface?.setAttribute(
            "aria-busy",
            "true",
        );

        state.loadPromise =
            (async () => {
                try {
                    clearError();

                    const tasks =
                        await fetchTaskProjection();

                    const model =
                        projectModel(
                            tasks,
                        );

                    applyModel(model);

                    if (
                        state.selectedId &&
                        !state.nodeById.has(
                            state.selectedId,
                        )
                    ) {
                        state.selectedId =
                            "";
                    }

                    state.loaded =
                        true;

                    render();

                    if (
                        state.viewport.scale ===
                            1 &&
                        state.viewport.x ===
                            0 &&
                        state.viewport.y ===
                            0
                    ) {
                        fitAll({
                            persist:
                                false,
                        });
                    }

                    emit(
                        "available",
                        {
                            task_count:
                                state.tasks
                                    .length,
                            represented_node_count:
                                state.nodes
                                    .length,
                        },
                    );

                    setLive(
                        `Navigation available. ${state.nodes.length} represented tasks.`,
                    );
                } catch (error) {
                    if (
                        error?.name ===
                        "AbortError"
                    ) {
                        return;
                    }

                    renderError(
                        error,
                    );
                } finally {
                    state.loading =
                        false;

                    dom.surface?.setAttribute(
                        "aria-busy",
                        "false",
                    );
                }
            })();

        return state.loadPromise;
    }

    function render() {
        if (!state.loaded) {
            return;
        }

        renderMap();
        renderBreadcrumb();
        renderInspector();
        renderRoute();
        renderStats();
        renderTextIndex();
        renderMinimap();
        applyTransform();
        updateControlState();
    }

    function queueRender() {
        if (
            state.renderQueued
        ) {
            return;
        }

        state.renderQueued =
            true;

        requestAnimationFrame(
            () => {
                state.renderQueued =
                    false;

                render();
            },
        );
    }

    function edgePath(
        source,
        target,
    ) {
        const sx =
            source.x +
            source.width / 2;

        const sy =
            source.y +
            source.height / 2;

        const tx =
            target.x +
            target.width / 2;

        const ty =
            target.y +
            target.height / 2;

        const dx =
            Math.max(
                70,
                Math.abs(tx - sx) *
                    0.42,
            );

        return [
            `M ${sx} ${sy}`,
            `C ${sx + dx} ${sy}`,
            `${tx - dx} ${ty}`,
            `${tx} ${ty}`,
        ].join(" ");
    }

    function renderMap() {
        if (!dom.world) {
            return;
        }

        dom.world.replaceChildren();

        const visible =
            visibleNodes();

        const visibleIds =
            new Set(
                visible.map(
                    (node) =>
                        node.id,
                ),
            );

        const routeIds =
            new Set(
                state.route,
            );

        const relatedIds =
            state.selectedId
                ? neighborhoodIds(
                      state.selectedId,
                  )
                : new Set();

        const territoryLayer =
            createSvg("g", {
                class:
                    "navigation-territories",
            });

        for (
            const territory
            of state.territories
        ) {
            const group =
                createSvg("g", {
                    class:
                        "nav-territory-group",
                    "data-territory-id":
                        territory.id,
                });

            const rectangle =
                createSvg("rect", {
                    class:
                        "nav-territory",
                    x:
                        territory.x,
                    y:
                        territory.y,
                    width:
                        territory.width,
                    height:
                        territory.height,
                    rx:
                        8,
                });

            rectangle.dataset.objective =
                territory.objective;

            rectangle.setAttribute(
                "tabindex",
                "0",
            );

            rectangle.setAttribute(
                "role",
                "button",
            );

            rectangle.setAttribute(
                "aria-label",
                `Fit objective ${territory.objective}`,
            );

            const band =
                createSvg("rect", {
                    class:
                        "nav-territory-band",
                    x:
                        territory.x,
                    y:
                        territory.y,
                    width:
                        territory.width,
                    height:
                        52,
                });

            const title =
                createSvg("text", {
                    class:
                        "nav-territory-title",
                    x:
                        territory.x +
                        20,
                    y:
                        territory.y +
                        32,
                });

            title.textContent =
                truncate(
                    territory.objective,
                    58,
                );

            const meta =
                createSvg("text", {
                    class:
                        "nav-territory-meta",
                    x:
                        territory.x +
                        territory.width -
                        20,
                    y:
                        territory.y +
                        31,
                    "text-anchor":
                        "end",
                });

            meta.textContent =
                `${territory.count} represented`;

            group.append(
                rectangle,
                band,
                title,
                meta,
            );

            territoryLayer.append(
                group,
            );
        }

        const edgeLayer =
            createSvg("g", {
                class:
                    "navigation-edges",
            });

        for (
            const edge
            of state.edges
        ) {
            const source =
                state.nodeById.get(
                    edge.source,
                );

            const target =
                state.nodeById.get(
                    edge.target,
                );

            if (
                !source ||
                !target
            ) {
                continue;
            }

            const routeEdge =
                state.route.some(
                    (
                        id,
                        index,
                    ) =>
                        index <
                            state.route
                                .length -
                                1 &&
                        (
                            (
                                id ===
                                    edge.source &&
                                state.route[
                                    index +
                                        1
                                ] ===
                                    edge.target
                            ) ||
                            (
                                id ===
                                    edge.target &&
                                state.route[
                                    index +
                                        1
                                ] ===
                                    edge.source
                            )
                        ),
                );

            const selectedRelated =
                state.selectedId &&
                (
                    edge.source ===
                        state.selectedId ||
                    edge.target ===
                        state.selectedId
                );

            const visibleEdge =
                visibleIds.has(
                    edge.source,
                ) &&
                visibleIds.has(
                    edge.target,
                );

            const classes = [
                "nav-edge",
                `nav-edge-${edge.type}`,
            ];

            if (routeEdge) {
                classes.push(
                    "route",
                );
            } else if (
                selectedRelated
            ) {
                classes.push(
                    "related",
                );
            }

            if (!visibleEdge) {
                classes.push(
                    "dimmed",
                );
            }

            const path =
                createSvg("path", {
                    class:
                        classes.join(
                            " ",
                        ),
                    d:
                        edgePath(
                            source,
                            target,
                        ),
                    "data-edge-id":
                        edge.id,
                });

            edgeLayer.append(
                path,
            );
        }

        const nodeLayer =
            createSvg("g", {
                class:
                    "navigation-nodes",
            });

        state.nodes.forEach(
            (
                node,
                index,
            ) => {
                const visibleNode =
                    visibleIds.has(
                        node.id,
                    );

                const classes = [
                    "nav-map-node",
                    KNOWN_STATES.has(
                        node.state,
                    )
                        ? `nav-node-state-${node.state}`
                        : "nav-node-state-unknown",
                ];

                if (
                    node.id ===
                    state.selectedId
                ) {
                    classes.push(
                        "selected",
                    );
                }

                if (
                    routeIds.has(
                        node.id,
                    )
                ) {
                    classes.push(
                        "route",
                    );
                }

                if (
                    state.selectedId &&
                    !relatedIds.has(
                        node.id,
                    ) &&
                    node.id !==
                        state.selectedId
                ) {
                    classes.push(
                        "dimmed",
                    );
                }

                if (!visibleNode) {
                    classes.push(
                        "dimmed",
                    );
                }

                const group =
                    createSvg("g", {
                        class:
                            classes.join(
                                " ",
                            ),
                        transform:
                            `translate(${node.x} ${node.y})`,
                        tabindex:
                            visibleNode
                                ? "0"
                                : "-1",
                        role:
                            "button",
                        "aria-label":
                            `${node.title}. State ${KNOWN_STATES.has(node.state) ? node.state : "unknown"}. Objective ${node.objective}.`,
                        "data-task-id":
                            node.id,
                    });

                const body =
                    createSvg("rect", {
                        class:
                            "nav-node-body",
                        width:
                            node.width,
                        height:
                            node.height,
                        rx:
                            4,
                    });

                const rail =
                    createSvg("rect", {
                        class:
                            "nav-node-rail",
                        width:
                            5,
                        height:
                            node.height,
                    });

                const title =
                    createSvg("text", {
                        class:
                            "nav-node-title",
                        x:
                            15,
                        y:
                            23,
                    });

                title.textContent =
                    truncate(
                        node.title,
                        28,
                    );

                const meta =
                    createSvg("text", {
                        class:
                            "nav-node-meta",
                        x:
                            15,
                        y:
                            43,
                    });

                const displayedState =
                    KNOWN_STATES.has(
                        node.state,
                    )
                        ? node.state
                        : "unknown";

                meta.textContent =
                    `${displayedState} · ${truncate(node.priority, 14)}`;

                const ordinal =
                    createSvg("text", {
                        class:
                            "nav-node-index",
                        x:
                            node.width -
                            10,
                        y:
                            15,
                        "text-anchor":
                            "end",
                    });

                ordinal.textContent =
                    String(
                        index + 1,
                    ).padStart(
                        3,
                        "0",
                    );

                group.append(
                    body,
                    rail,
                    title,
                    meta,
                    ordinal,
                );

                if (
                    node.id ===
                    state.selectedId
                ) {
                    const ring =
                        createSvg(
                            "rect",
                            {
                                class:
                                    "nav-you-are-here",
                                x:
                                    -7,
                                y:
                                    -7,
                                width:
                                    node.width +
                                    14,
                                height:
                                    node.height +
                                    14,
                                rx:
                                    8,
                            },
                        );

                    const outerRing =
                        createSvg(
                            "rect",
                            {
                                class:
                                    "nav-you-are-here-ring",
                                x:
                                    -14,
                                y:
                                    -14,
                                width:
                                    node.width +
                                    28,
                                height:
                                    node.height +
                                    28,
                                rx:
                                    12,
                            },
                        );

                    const label =
                        createSvg(
                            "text",
                            {
                                class:
                                    "nav-you-are-here-text",
                                x:
                                    0,
                                y:
                                    -22,
                            },
                        );

                    label.textContent =
                        "YOU ARE HERE";

                    group.append(
                        ring,
                        outerRing,
                        label,
                    );
                }

                nodeLayer.append(
                    group,
                );
            },
        );

        dom.world.append(
            territoryLayer,
            edgeLayer,
            nodeLayer,
        );

        dom.mapFrame.dataset.lens =
            state.lens;

        updateSemanticZoom();
    }

    function renderBreadcrumb() {
        if (!dom.breadcrumb) {
            return;
        }

        dom.breadcrumb.replaceChildren();

        const overview =
            document.createElement(
                "button",
            );

        overview.type =
            "button";

        overview.textContent =
            "overview";

        overview.addEventListener(
            "click",
            () => {
                clearSelection();
                fitAll();
            },
        );

        dom.breadcrumb.append(
            overview,
        );

        if (!state.selectedId) {
            return;
        }

        const selected =
            state.nodeById.get(
                state.selectedId,
            );

        if (!selected) {
            return;
        }

        const separator =
            document.createElement(
                "span",
            );

        separator.textContent =
            "›";

        dom.breadcrumb.append(
            separator,
        );

        const objective =
            document.createElement(
                "button",
            );

        objective.type =
            "button";

        objective.textContent =
            selected.objective;

        objective.addEventListener(
            "click",
            () =>
                fitObjective(
                    selected.objective,
                ),
        );

        dom.breadcrumb.append(
            objective,
        );

        if (
            selected.parent &&
            state.nodeById.has(
                selected.parent,
            )
        ) {
            const parentSeparator =
                document.createElement(
                    "span",
                );

            parentSeparator.textContent =
                "›";

            const parentButton =
                document.createElement(
                    "button",
                );

            parentButton.type =
                "button";

            parentButton.textContent =
                truncate(
                    state.nodeById.get(
                        selected.parent,
                    ).title,
                    30,
                );

            parentButton.addEventListener(
                "click",
                () =>
                    select(
                        selected.parent,
                        {
                            focus:
                                true,
                        },
                    ),
            );

            dom.breadcrumb.append(
                parentSeparator,
                parentButton,
            );
        }

        const finalSeparator =
            document.createElement(
                "span",
            );

        finalSeparator.textContent =
            "›";

        const current =
            document.createElement(
                "strong",
            );

        current.textContent =
            truncate(
                selected.title,
                38,
            );

        dom.breadcrumb.append(
            finalSeparator,
            current,
        );
    }

    function renderInspector() {
        if (!dom.inspector) {
            return;
        }

        if (!state.selectedId) {
            dom.inspector.innerHTML = `
                <h2>Location</h2>
                <p>
                    Select a represented task to inspect its structural
                    neighborhood. No graph geometry is authoritative.
                </p>
            `;

            if (dom.location) {
                dom.location.textContent =
                    "overview";
            }

            return;
        }

        const node =
            state.nodeById.get(
                state.selectedId,
            );

        if (!node) {
            return;
        }

        if (dom.location) {
            dom.location.textContent =
                node.title;
        }

        const dependencies =
            node.dependencies.filter(
                (id) =>
                    state.nodeById.has(
                        id,
                    ),
            );

        const dependents =
            state.dependentsById.get(
                node.id,
            ) || [];

        const children =
            state.childrenById.get(
                node.id,
            ) || [];

        const displayedState =
            KNOWN_STATES.has(
                node.state,
            )
                ? node.state
                : "unknown";

        dom.inspector.innerHTML = `
            <div class="navigation-eyebrow">
                YOU ARE HERE
            </div>

            <h2>
                ${escapeHtml(node.title)}
            </h2>

            <dl class="navigation-detail-grid">
                <dt>task</dt>
                <dd>${escapeHtml(node.id)}</dd>

                <dt>objective</dt>
                <dd>${escapeHtml(node.objective)}</dd>

                <dt>state</dt>
                <dd>${escapeHtml(displayedState)}</dd>

                <dt>priority</dt>
                <dd>${escapeHtml(node.priority)}</dd>

                <dt>parent</dt>
                <dd>
                    ${
                        node.parent
                            ? escapeHtml(
                                  node.parent,
                              )
                            : "not represented"
                    }
                </dd>

                <dt>requires</dt>
                <dd>${dependencies.length}</dd>

                <dt>dependents</dt>
                <dd>${dependents.length}</dd>

                <dt>children</dt>
                <dd>${children.length}</dd>

                <dt>geometry</dt>
                <dd>projection only</dd>
            </dl>

            <div>
                ${dependencies
                    .map((id) => {
                        const dependency =
                            state.nodeById.get(
                                id,
                            );

                        return `
                            <button
                                class="navigation-pill"
                                type="button"
                                data-nav-jump="${escapeHtml(id)}"
                            >
                                requires:
                                ${escapeHtml(
                                    truncate(
                                        dependency?.title ||
                                            id,
                                        24,
                                    ),
                                )}
                            </button>
                        `;
                    })
                    .join("")}

                ${dependents
                    .map((id) => {
                        const dependent =
                            state.nodeById.get(
                                id,
                            );

                        return `
                            <button
                                class="navigation-pill"
                                type="button"
                                data-nav-jump="${escapeHtml(id)}"
                            >
                                dependent:
                                ${escapeHtml(
                                    truncate(
                                        dependent?.title ||
                                            id,
                                        24,
                                    ),
                                )}
                            </button>
                        `;
                    })
                    .join("")}
            </div>
        `;

        for (
            const button
            of qa(
                "[data-nav-jump]",
                dom.inspector,
            )
        ) {
            button.addEventListener(
                "click",
                () =>
                    select(
                        button.dataset
                            .navJump,
                        {
                            focus:
                                true,
                        },
                    ),
            );
        }
    }

    function renderRoute() {
        if (!dom.route) {
            return;
        }

        dom.route.replaceChildren();

        if (
            state.route.length <
            1
        ) {
            const message =
                document.createElement(
                    "p",
                );

            message.textContent =
                state.selectedId
                    ? "Choose a represented destination."
                    : "Select a starting task first.";

            dom.route.append(
                message,
            );

            return;
        }

        state.route.forEach(
            (
                id,
                index,
            ) => {
                const node =
                    state.nodeById.get(
                        id,
                    );

                if (!node) {
                    return;
                }

                const button =
                    document.createElement(
                        "button",
                    );

                button.type =
                    "button";

                button.className =
                    "navigation-route-step";

                const relation =
                    index === 0
                        ? "start"
                        : relationshipBetween(
                              state.route[
                                  index - 1
                              ],
                              id,
                          );

                button.innerHTML = `
                    <span
                        class="navigation-route-step-number"
                    >
                        ${index + 1}
                    </span>
                    <span>
                        ${escapeHtml(node.title)}
                        <small>
                            ${escapeHtml(relation)}
                        </small>
                    </span>
                `;

                button.addEventListener(
                    "click",
                    () =>
                        select(
                            id,
                            {
                                focus:
                                    true,
                                preserveRoute:
                                    true,
                            },
                        ),
                );

                dom.route.append(
                    button,
                );
            },
        );
    }

    function renderStats() {
        if (!dom.stats) {
            return;
        }

        const visible =
            visibleNodes();

        const ready =
            state.nodes.filter(
                (node) =>
                    node.state ===
                    "ready",
            ).length;

        const blocked =
            state.nodes.filter(
                (node) =>
                    node.state ===
                    "blocked",
            ).length;

        const unknown =
            state.nodes.filter(
                unknownState,
            ).length;

        dom.stats.innerHTML = `
            <div class="navigation-stat">
                <strong>
                    ${state.nodes.length}
                </strong>
                <span>represented</span>
            </div>

            <div class="navigation-stat">
                <strong>
                    ${visible.length}
                </strong>
                <span>visible</span>
            </div>

            <div class="navigation-stat">
                <strong>
                    ${ready}
                </strong>
                <span>ready</span>
            </div>

            <div class="navigation-stat">
                <strong>
                    ${blocked}
                </strong>
                <span>blocked</span>
            </div>

            <div class="navigation-stat">
                <strong>
                    ${state.territories.length}
                </strong>
                <span>objectives</span>
            </div>

            <div class="navigation-stat">
                <strong>
                    ${unknown}
                </strong>
                <span>unknown state</span>
            </div>
        `;
    }

    function renderTextIndex() {
        if (!dom.textIndex) {
            return;
        }

        const fragment =
            document.createDocumentFragment();

        for (
            const node
            of visibleNodes()
        ) {
            const button =
                document.createElement(
                    "button",
                );

            button.type =
                "button";

            button.innerHTML = `
                <strong>
                    ${escapeHtml(node.title)}
                </strong>
                <small>
                    ${escapeHtml(node.objective)}
                    ·
                    ${escapeHtml(
                        KNOWN_STATES.has(
                            node.state,
                        )
                            ? node.state
                            : "unknown",
                    )}
                </small>
            `;

            button.addEventListener(
                "click",
                () =>
                    select(
                        node.id,
                        {
                            focus:
                                true,
                        },
                    ),
            );

            fragment.append(
                button,
            );
        }

        dom.textIndex.replaceChildren(
            fragment,
        );
    }

    function renderMinimap() {
        if (!dom.minimap) {
            return;
        }

        dom.minimap.replaceChildren();

        dom.minimap.setAttribute(
            "viewBox",
            `0 0 ${state.world.width} ${state.world.height}`,
        );

        for (
            const territory
            of state.territories
        ) {
            dom.minimap.append(
                createSvg(
                    "rect",
                    {
                        class:
                            "nav-mini-territory",
                        x:
                            territory.x,
                        y:
                            territory.y,
                        width:
                            territory.width,
                        height:
                            territory.height,
                    },
                ),
            );
        }

        const frame =
            mapDimensions();

        const scale =
            state.viewport.scale;

        const viewportX =
            -state.viewport.x /
            scale;

        const viewportY =
            -state.viewport.y /
            scale;

        const viewportWidth =
            frame.width /
            scale;

        const viewportHeight =
            frame.height /
            scale;

        dom.minimap.append(
            createSvg(
                "rect",
                {
                    class:
                        "nav-mini-viewport",
                    x:
                        viewportX,
                    y:
                        viewportY,
                    width:
                        viewportWidth,
                    height:
                        viewportHeight,
                },
            ),
        );
    }

    function searchMatches(query) {
        const normalized =
            lower(query);

        if (!normalized) {
            return [];
        }

        const prefix = [];
        const contains = [];

        for (
            const node
            of state.nodes
        ) {
            const id =
                lower(node.id);

            const title =
                lower(node.title);

            const objective =
                lower(
                    node.objective,
                );

            if (
                id.startsWith(
                    normalized,
                ) ||
                title.startsWith(
                    normalized,
                )
            ) {
                prefix.push(node);
                continue;
            }

            if (
                id.includes(
                    normalized,
                ) ||
                title.includes(
                    normalized,
                ) ||
                objective.includes(
                    normalized,
                )
            ) {
                contains.push(
                    node,
                );
            }
        }

        return [
            ...prefix,
            ...contains,
        ].slice(0, 14);
    }

    function renderSearchResults() {
        if (
            !dom.search ||
            !dom.searchResults
        ) {
            return;
        }

        const matches =
            searchMatches(
                dom.search.value,
            );

        dom.searchResults.replaceChildren();

        if (!matches.length) {
            dom.searchResults.classList.remove(
                "open",
            );

            return;
        }

        const fragment =
            document.createDocumentFragment();

        for (
            const node
            of matches
        ) {
            const button =
                document.createElement(
                    "button",
                );

            button.type =
                "button";

            button.className =
                "navigation-result";

            button.setAttribute(
                "role",
                "option",
            );

            button.innerHTML = `
                <strong>
                    ${escapeHtml(node.title)}
                </strong>
                <small>
                    ${escapeHtml(node.id)}
                </small>
            `;

            button.addEventListener(
                "click",
                () => {
                    dom.search.value =
                        node.title;

                    dom.searchResults.classList.remove(
                        "open",
                    );

                    select(
                        node.id,
                        {
                            focus:
                                true,
                        },
                    );
                },
            );

            fragment.append(
                button,
            );
        }

        dom.searchResults.append(
            fragment,
        );

        dom.searchResults.classList.add(
            "open",
        );
    }

    function resolveDestination(
        value,
    ) {
        const normalized =
            lower(value);

        if (!normalized) {
            return null;
        }

        if (
            state.nodeById.has(
                asText(value),
            )
        ) {
            return state.nodeById.get(
                asText(value),
            );
        }

        return (
            state.nodes.find(
                (node) =>
                    lower(node.id) ===
                        normalized ||
                    lower(node.title) ===
                        normalized,
            ) ||
            searchMatches(
                value,
            )[0] ||
            null
        );
    }

    function routeToInput() {
        if (!state.selectedId) {
            setLive(
                "Select a starting task before finding a route.",
            );

            return;
        }

        const destination =
            resolveDestination(
                dom.routeInput?.value,
            );

        if (!destination) {
            state.route = [];
            renderRoute();

            setLive(
                "Destination is not represented.",
            );

            return;
        }

        state.route =
            representedRoute(
                state.selectedId,
                destination.id,
            );

        renderRoute();
        renderMap();
        renderMinimap();

        if (
            state.route.length
        ) {
            setLive(
                `Represented route contains ${state.route.length} task locations. It is not an execution order.`,
            );
        } else {
            setLive(
                "No represented route connects those task locations.",
            );
        }
    }

    function select(
        id,
        {
            focus = false,
            preserveRoute = false,
        } = {},
    ) {
        install();

        if (!state.loaded) {
            activate();

            return void load().then(
                () => {
                    if (
                        state.nodeById.has(
                            id,
                        )
                    ) {
                        select(
                            id,
                            {
                                focus,
                                preserveRoute,
                            },
                        );
                    }
                },
            );
        }

        if (
            !state.nodeById.has(id)
        ) {
            return;
        }

        if (
            state.selectedId &&
            state.selectedId !== id
        ) {
            state.selectionHistory.push(
                state.selectedId,
            );

            if (
                state.selectionHistory
                    .length > 50
            ) {
                state.selectionHistory.shift();
            }
        }

        state.selectedId =
            id;

        if (!preserveRoute) {
            state.route = [];
        }

        savePreferences();

        queueRender();

        if (focus) {
            requestAnimationFrame(
                () =>
                    focusNode(id),
            );
        }

        emit(
            "selection",
            {
                task_id:
                    id,
            },
        );
    }

    function clearSelection() {
        state.selectedId =
            "";

        state.route = [];

        savePreferences();

        queueRender();

        emit(
            "selection",
            {
                task_id:
                    null,
            },
        );
    }

    function mapDimensions() {
        const rectangle =
            dom.mapFrame?.getBoundingClientRect();

        return {
            width:
                Math.max(
                    1,
                    rectangle?.width ||
                        1,
                ),
            height:
                Math.max(
                    1,
                    rectangle?.height ||
                        1,
                ),
        };
    }

    function updateViewBox() {
        if (!dom.map) {
            return;
        }

        const dimensions =
            mapDimensions();

        dom.map.setAttribute(
            "viewBox",
            `0 0 ${dimensions.width} ${dimensions.height}`,
        );

        dom.map.setAttribute(
            "preserveAspectRatio",
            "xMinYMin meet",
        );

        applyTransform();
        renderMinimap();
    }

    function updateSemanticZoom() {
        if (!dom.mapFrame) {
            return;
        }

        const scale =
            state.viewport.scale;

        dom.mapFrame.dataset.semanticZoom =
            scale < 0.44
                ? "far"
                : scale < 0.88
                  ? "medium"
                  : "near";
    }

    function applyTransform() {
        if (
            !dom.world ||
            !dom.mapFrame
        ) {
            return;
        }

        const {
            x,
            y,
            scale,
        } = state.viewport;

        dom.world.setAttribute(
            "transform",
            `translate(${x} ${y}) scale(${scale})`,
        );

        if (dom.zoomLabel) {
            dom.zoomLabel.textContent =
                `${Math.round(
                    scale * 100,
                )}%`;
        }

        updateSemanticZoom();
    }

    function queueTransform() {
        if (
            state.transformQueued
        ) {
            return;
        }

        state.transformQueued =
            true;

        requestAnimationFrame(
            () => {
                state.transformQueued =
                    false;

                applyTransform();
                renderMinimap();
            },
        );
    }

    function setViewport(
        viewport,
        {
            persist = true,
        } = {},
    ) {
        state.viewport = {
            x:
                Number.isFinite(
                    viewport.x,
                )
                    ? viewport.x
                    : state.viewport.x,
            y:
                Number.isFinite(
                    viewport.y,
                )
                    ? viewport.y
                    : state.viewport.y,
            scale:
                clamp(
                    Number.isFinite(
                        viewport.scale,
                    )
                        ? viewport.scale
                        : state.viewport
                              .scale,
                    VIEWPORT.minScale,
                    VIEWPORT.maxScale,
                ),
        };

        if (persist) {
            savePreferences();
        }

        queueTransform();
    }

    function zoomAt(
        factor,
        clientX,
        clientY,
    ) {
        if (!dom.mapFrame) {
            return;
        }

        const rectangle =
            dom.mapFrame.getBoundingClientRect();

        const localX =
            clientX -
            rectangle.left;

        const localY =
            clientY -
            rectangle.top;

        const oldScale =
            state.viewport.scale;

        const nextScale =
            clamp(
                oldScale * factor,
                VIEWPORT.minScale,
                VIEWPORT.maxScale,
            );

        const worldX =
            (
                localX -
                state.viewport.x
            ) /
            oldScale;

        const worldY =
            (
                localY -
                state.viewport.y
            ) /
            oldScale;

        setViewport({
            x:
                localX -
                worldX *
                    nextScale,
            y:
                localY -
                worldY *
                    nextScale,
            scale:
                nextScale,
        });
    }

    function zoomCentered(
        factor,
    ) {
        const rectangle =
            dom.mapFrame?.getBoundingClientRect();

        if (!rectangle) {
            return;
        }

        zoomAt(
            factor,
            rectangle.left +
                rectangle.width / 2,
            rectangle.top +
                rectangle.height /
                    2,
        );
    }

    function fitBounds(
        bounds,
        {
            persist = true,
        } = {},
    ) {
        const frame =
            mapDimensions();

        const padding =
            42;

        const width =
            Math.max(
                1,
                bounds.width,
            );

        const height =
            Math.max(
                1,
                bounds.height,
            );

        const scale =
            clamp(
                Math.min(
                    (
                        frame.width -
                        padding * 2
                    ) / width,
                    (
                        frame.height -
                        padding * 2
                    ) / height,
                ),
                VIEWPORT.minScale,
                VIEWPORT.maxScale,
            );

        const x =
            (
                frame.width -
                width * scale
            ) /
                2 -
            bounds.x * scale;

        const y =
            (
                frame.height -
                height * scale
            ) /
                2 -
            bounds.y * scale;

        setViewport(
            {
                x,
                y,
                scale,
            },
            {
                persist,
            },
        );
