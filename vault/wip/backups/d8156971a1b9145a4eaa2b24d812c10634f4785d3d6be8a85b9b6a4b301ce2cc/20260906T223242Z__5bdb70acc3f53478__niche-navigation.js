"use strict";

/*
 * savant / niche / navigation
 *
 * owner: exile:niche
 * semantic_role: represented task-space navigation projection
 * authority_effect: none
 * projection_only: true
 *
 * Core task substance, recommendation, selection, refresh, and active-view
 * semantics are delegated to window.Niche. This file owns only Navigation:
 * non-authoritative geometry, semantic zoom, represented routes, viewport
 * state, local focus, and accessibility companions.
 */

(() => {
    "use strict";

    const SVG_NS = "http://www.w3.org/2000/svg";

    const STORAGE_KEY =
        "savant.niche.navigation.v4";

    const EVENT_PREFIX =
        "niche:navigation";

    const ZOOM = Object.freeze({
        minimum: 0.2,
        maximum: 3.6,
        farMaximum: 0.56,
        mediumMaximum: 1.08,
        step: 1.22,
        wheelFactor: 0.0013
    });

    const GEOMETRY = Object.freeze({
        outerPadding: 72,
        territoryGap: 54,
        territoryHeader: 60,
        territoryPadding: 26,
        taskWidth: 220,
        taskHeight: 64,
        taskGapX: 26,
        taskGapY: 20,
        minimumTerritoryWidth: 560,
        maximumColumns: 4
    });

    const state = {
        installed: false,
        active: false,
        projectionGeneration: -1,
        firstMeaningfulFit: false,
        semanticLevel: "far",
        selectedTaskId: null,
        objectiveFocus: null,
        filter: "all",
        query: "",
        route: [],
        selectionHistory: [],
        viewport: {
            x: 0,
            y: 0,
            scale: 1
        },
        world: {
            width: 1,
            height: 1
        },
        model: {
            tasks: [],
            taskById: new Map(),
            dependents: new Map(),
            objectives: [],
            territoryByObjective: new Map(),
            nodeById: new Map(),
            edges: []
        },
        pointer: {
            active: new Map(),
            mode: "",
            startX: 0,
            startY: 0,
            viewportX: 0,
            viewportY: 0,
            pinchDistance: 0,
            pinchScale: 1,
            pinchCenterX: 0,
            pinchCenterY: 0
        },
        resizeObserver: null,
        renderQueued: false,
        transformQueued: false,
        lastDimensions: {
            width: 0,
            height: 0
        }
    };

    const dom = Object.create(null);

    const $ = (
        selector,
        root = document
    ) => root.querySelector(selector);

    const $$ = (
        selector,
        root = document
    ) => Array.from(root.querySelectorAll(selector));

    function asText(
        value,
        fallback = ""
    ) {
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
        return asText(
            value
        ).toLocaleLowerCase();
    }

    function clamp(
        value,
        minimum,
        maximum
    ) {
        return Math.min(
            maximum,
            Math.max(
                minimum,
                value
            )
        );
    }

    function safeRead() {
        try {
            const raw =
                localStorage.getItem(
                    STORAGE_KEY
                );

            return raw
                ? JSON.parse(raw)
                : null;
        } catch {
            return null;
        }
    }

    function safeWrite() {
        try {
            localStorage.setItem(
                STORAGE_KEY,
                JSON.stringify({
                    viewport: {
                        ...state.viewport
                    },
                    objectiveFocus:
                        state.objectiveFocus,
                    filter:
                        state.filter,
                    query:
                        state.query
                })
            );
        } catch {
            return;
        }
    }

    function emit(
        type,
        detail = {}
    ) {
        window.dispatchEvent(
            new CustomEvent(
                `${EVENT_PREFIX}:${type}`,
                {
                    detail: {
                        ...detail,
                        authority_effect:
                            "none",
                        projection_only:
                            true
                    }
                }
            )
        );
    }

    function coreProjection() {
        if (
            !window.Niche ||
            typeof window.Niche.projection !==
                "function"
        ) {
            return null;
        }

        try {
            return window.Niche.projection();
        } catch {
            return null;
        }
    }

    function taskId(task) {
        return asText(
            task?.id ??
            task?.task_id ??
            task?.identity ??
            task?.key
        );
    }

    function taskTitle(task) {
        return asText(
            task?.title ??
            task?.name ??
            task?.action ??
            task?.summary ??
            taskId(task),
            "untitled task"
        );
    }

    function taskObjective(task) {
        return asText(
            task?.objective ??
            task?.objective_id ??
            task?.root_objective ??
            task?.ancestry?.objective,
            "unknown objective"
        );
    }

    function taskParent(task) {
        return asText(
            task?.parent ??
            task?.parent_id ??
            task?.parent_task_id ??
            task?.ancestry?.parent
        );
    }

    function taskDependencies(task) {
        const source =
            task?.dependencies ??
            task?.depends_on ??
            task?.prerequisites ??
            task?.requires;

        if (!Array.isArray(source)) {
            return [];
        }

        return source
            .map((entry) => {
                if (
                    typeof entry ===
                    "string"
                ) {
                    return entry.trim();
                }

                return asText(
                    entry?.id ??
                    entry?.task_id ??
                    entry?.key
                );
            })
            .filter(Boolean);
    }

    function taskState(task) {
        const raw =
            lower(
                task?.state ??
                task?.status ??
                task?.lifecycle_state
            );

        if (
            raw.includes("complete") ||
            raw === "done" ||
            raw === "closed"
        ) {
            return "complete";
        }

        if (
            raw.includes("block") ||
            raw === "failed"
        ) {
            return "blocked";
        }

        if (
            raw.includes("active") ||
            raw.includes("progress") ||
            raw === "started" ||
            raw === "leased"
        ) {
            return "active";
        }

        if (
            raw.includes("review") ||
            raw.includes("verify") ||
            raw.includes("evidence")
        ) {
            return "review";
        }

        if (
            raw.includes("wait") ||
            raw.includes("pending") ||
            raw.includes("defer")
        ) {
            return "waiting";
        }

        if (
            task?.ready === true ||
            task?.is_ready === true
        ) {
            return "ready";
        }

        return raw || "unknown";
    }

    function taskPriority(task) {
        return asText(
            task?.priority ??
            task?.authoritative_priority ??
            task?.rank,
            "unknown"
        );
    }

    function taskMapFromProjection(
        projection
    ) {
        const candidate =
            projection?.normalized?.taskById;

        if (
            candidate instanceof Map
        ) {
            return candidate;
        }

        return new Map(
            (
                projection?.source?.tasks ??
                []
            )
                .map((task) => [
                    taskId(task),
                    task
                ])
                .filter(([id]) =>
                    Boolean(id)
                )
        );
    }

    function dependentsFromProjection(
        projection,
        tasks
    ) {
        const candidate =
            projection?.normalized?.dependents;

        if (
            candidate instanceof Map
        ) {
            return new Map(
                Array.from(
                    candidate.entries(),
                    ([key, values]) => [
                        key,
                        Array.isArray(values)
                            ? values.slice()
                            : []
                    ]
                )
            );
        }

        const result =
            new Map(
                tasks.map((task) => [
                    taskId(task),
                    []
                ])
            );

        for (const task of tasks) {
            const id =
                taskId(task);

            for (
                const dependency
                of taskDependencies(task)
            ) {
                if (
                    result.has(
                        dependency
                    )
                ) {
                    result.get(
                        dependency
                    ).push(id);
                }
            }
        }

        for (
            const values
            of result.values()
        ) {
            values.sort(
                (a, b) =>
                    a.localeCompare(b)
            );
        }

        return result;
    }

    function normalizeProjection(
        projection
    ) {
        const source =
            Array.isArray(
                projection?.source?.tasks
            )
                ? projection.source.tasks
                : [];

        const tasks =
            source
                .filter((task) =>
                    Boolean(taskId(task))
                )
                .slice()
                .sort(
                    (a, b) =>
                        taskObjective(a)
                            .localeCompare(
                                taskObjective(b)
                            ) ||
                        taskTitle(a)
                            .localeCompare(
                                taskTitle(b)
                            ) ||
                        taskId(a)
                            .localeCompare(
                                taskId(b)
                            )
                );

        return {
            tasks,
            taskById:
                taskMapFromProjection(
                    projection
                ),
            dependents:
                dependentsFromProjection(
                    projection,
                    tasks
                ),
            selectedTaskId:
                asText(
                    projection
                        ?.normalized
                        ?.selectedTaskId
                ) ||
                null,
            generation:
                Number(
                    projection
                        ?.requestGeneration
                )
        };
    }

    function objectiveStatistics(
        tasks
    ) {
        const total =
            tasks.length;

        const complete =
            tasks.filter(
                (task) =>
                    taskState(task) ===
                    "complete"
            ).length;

        const ready =
            tasks.filter(
                (task) =>
                    taskState(task) ===
                    "ready"
            ).length;

        const blocked =
            tasks.filter(
                (task) =>
                    taskState(task) ===
                    "blocked"
            ).length;

        return {
            total,
            complete,
            ready,
            blocked,
            ratio:
                total
                    ? complete / total
                    : 0
        };
    }

    function buildModel(
        normalized
    ) {
        const grouped =
            new Map();

        for (
            const task
            of normalized.tasks
        ) {
            const objective =
                taskObjective(task);

            if (
                !grouped.has(
                    objective
                )
            ) {
                grouped.set(
                    objective,
                    []
                );
            }

            grouped
                .get(objective)
                .push(task);
        }

        const objectives =
            Array.from(
                grouped.entries()
            )
                .map(
                    ([name, tasks]) => ({
                        name,
                        tasks,
                        statistics:
                            objectiveStatistics(
                                tasks
                            )
                    })
                )
                .sort(
                    (a, b) =>
                        a.name.localeCompare(
                            b.name
                        )
                );

        const viewportWidth =
            Math.max(
                320,
                state.lastDimensions.width
            );

        const preferredColumns =
            viewportWidth < 560
                ? 1
                : viewportWidth < 960
                    ? 2
                    : Math.min(
                        GEOMETRY.maximumColumns,
                        Math.max(
                            2,
                            Math.floor(
                                viewportWidth /
                                520
                            )
                        )
                    );

        const territoryWidth =
            Math.max(
                GEOMETRY.minimumTerritoryWidth,
                (
                    state.lastDimensions.width -
                    GEOMETRY.outerPadding * 2 -
                    GEOMETRY.territoryGap *
                        Math.max(
                            0,
                            preferredColumns - 1
                        )
                ) /
                    preferredColumns
            );

        const territoryByObjective =
            new Map();

        const nodeById =
            new Map();

        let maxRight = 1;
        let maxBottom = 1;

        objectives.forEach(
            (
                objective,
                objectiveIndex
            ) => {
                const column =
                    objectiveIndex %
                    preferredColumns;

                const row =
                    Math.floor(
                        objectiveIndex /
                        preferredColumns
                    );

                const innerWidth =
                    territoryWidth -
                    GEOMETRY.territoryPadding *
                        2;

                const taskColumns =
                    Math.max(
                        1,
                        Math.floor(
                            (
                                innerWidth +
                                GEOMETRY.taskGapX
                            ) /
                            (
                                GEOMETRY.taskWidth +
                                GEOMETRY.taskGapX
                            )
                        )
                    );

                const rows =
                    Math.max(
                        1,
                        Math.ceil(
                            objective.tasks.length /
                            taskColumns
                        )
                    );

                const territoryHeight =
                    GEOMETRY.territoryHeader +
                    GEOMETRY.territoryPadding *
                        2 +
                    rows *
                        GEOMETRY.taskHeight +
                    Math.max(
                        0,
                        rows - 1
                    ) *
                        GEOMETRY.taskGapY;

                const x =
                    GEOMETRY.outerPadding +
                    column *
                        (
                            territoryWidth +
                            GEOMETRY.territoryGap
                        );

                const precedingRows =
                    objectives
                        .slice(
                            0,
                            row *
                                preferredColumns
                        )
                        .reduce(
                            (
                                heights,
                                candidate,
                                index
                            ) => {
                                const candidateColumn =
                                    index %
                                    preferredColumns;

                                const inner =
                                    territoryWidth -
                                    GEOMETRY.territoryPadding *
                                        2;

                                const columns =
                                    Math.max(
                                        1,
                                        Math.floor(
                                            (
                                                inner +
                                                GEOMETRY.taskGapX
                                            ) /
                                            (
                                                GEOMETRY.taskWidth +
                                                GEOMETRY.taskGapX
                                            )
                                        )
                                    );

                                const candidateRows =
                                    Math.max(
                                        1,
                                        Math.ceil(
                                            candidate.tasks.length /
                                            columns
                                        )
                                    );

                                const height =
                                    GEOMETRY.territoryHeader +
                                    GEOMETRY.territoryPadding *
                                        2 +
                                    candidateRows *
                                        GEOMETRY.taskHeight +
                                    Math.max(
                                        0,
                                        candidateRows - 1
                                    ) *
                                        GEOMETRY.taskGapY;

                                heights[
                                    candidateColumn
                                ] =
                                    Math.max(
                                        heights[
                                            candidateColumn
                                        ] || 0,
                                        height
                                    );

                                return heights;
                            },
                            {}
                        );

                let y =
                    GEOMETRY.outerPadding;

                for (
                    let previousRow = 0;
                    previousRow < row;
                    previousRow += 1
                ) {
                    const rowItems =
                        objectives.slice(
                            previousRow *
                                preferredColumns,
                            (
                                previousRow + 1
                            ) *
                                preferredColumns
                        );

                    let rowHeight =
                        0;

                    for (
                        const item
                        of rowItems
                    ) {
                        const inner =
                            territoryWidth -
                            GEOMETRY.territoryPadding *
                                2;

                        const columns =
                            Math.max(
                                1,
                                Math.floor(
                                    (
                                        inner +
                                        GEOMETRY.taskGapX
                                    ) /
                                    (
                                        GEOMETRY.taskWidth +
                                        GEOMETRY.taskGapX
                                    )
                                )
                            );

                        const itemRows =
                            Math.max(
                                1,
                                Math.ceil(
                                    item.tasks.length /
                                    columns
                                )
                            );

                        const height =
                            GEOMETRY.territoryHeader +
                            GEOMETRY.territoryPadding *
                                2 +
                            itemRows *
                                GEOMETRY.taskHeight +
                            Math.max(
                                0,
                                itemRows - 1
                            ) *
                                GEOMETRY.taskGapY;

                        rowHeight =
                            Math.max(
                                rowHeight,
                                height
                            );
                    }

                    y +=
                        rowHeight +
                        GEOMETRY.territoryGap;
                }

                const territory = {
                    objective:
                        objective.name,
                    tasks:
                        objective.tasks,
                    statistics:
                        objective.statistics,
                    x,
                    y,
                    width:
                        territoryWidth,
                    height:
                        territoryHeight,
                    taskColumns
                };

                territoryByObjective.set(
                    objective.name,
                    territory
                );

                objective.tasks.forEach(
                    (
                        task,
                        taskIndex
                    ) => {
                        const taskColumn =
                            taskIndex %
                            taskColumns;

                        const taskRow =
                            Math.floor(
                                taskIndex /
                                taskColumns
                            );

                        const node = {
                            id:
                                taskId(task),
                            task,
                            objective:
                                objective.name,
                            x:
                                x +
                                GEOMETRY.territoryPadding +
                                taskColumn *
                                    (
                                        GEOMETRY.taskWidth +
                                        GEOMETRY.taskGapX
                                    ),
                            y:
                                y +
                                GEOMETRY.territoryHeader +
                                GEOMETRY.territoryPadding +
                                taskRow *
                                    (
                                        GEOMETRY.taskHeight +
                                        GEOMETRY.taskGapY
                                    ),
                            width:
                                GEOMETRY.taskWidth,
                            height:
                                GEOMETRY.taskHeight
                        };

                        nodeById.set(
                            node.id,
                            node
                        );
                    }
                );

                maxRight =
                    Math.max(
                        maxRight,
                        x +
                        territoryWidth
                    );

                maxBottom =
                    Math.max(
                        maxBottom,
                        y +
                        territoryHeight
                    );
            }
        );

        const edges = [];

        for (
            const task
            of normalized.tasks
        ) {
            const targetId =
                taskId(task);

            for (
                const dependencyId
                of taskDependencies(task)
            ) {
                if (
                    nodeById.has(
                        dependencyId
                    ) &&
                    nodeById.has(
                        targetId
                    )
                ) {
                    edges.push({
                        type:
                            "dependency",
                        source:
                            dependencyId,
                        target:
                            targetId
                    });
                }
            }

            const parent =
                taskParent(task);

            if (
                parent &&
                nodeById.has(parent)
            ) {
                edges.push({
                    type:
                        "edifice",
                    source:
                        parent,
                    target:
                        targetId
                });
            }
        }

        edges.sort(
            (a, b) =>
                a.type.localeCompare(
                    b.type
                ) ||
                a.source.localeCompare(
                    b.source
                ) ||
                a.target.localeCompare(
                    b.target
                )
        );

        state.world = {
            width:
                maxRight +
                GEOMETRY.outerPadding,
            height:
                maxBottom +
                GEOMETRY.outerPadding
        };

        return {
            tasks:
                normalized.tasks,
            taskById:
                normalized.taskById,
            dependents:
                normalized.dependents,
            objectives,
            territoryByObjective,
            nodeById,
            edges
        };
    }

    function ensureSurface() {
        let surface =
            $("#surface-navigation");

        if (surface) {
            return surface;
        }

        const parent =
            $(".surfaces") ??
            $("main") ??
            document.body;

        surface =
            document.createElement(
                "section"
            );

        surface.id =
            "surface-navigation";

        surface.className =
            "surface niche-navigation-surface";

        surface.dataset.surface =
            "navigation";

        surface.hidden =
            true;

        surface.innerHTML = `
            <div class="navigation-heading">
                <div>
                    <div class="navigation-eyebrow">
                        REPRESENTED NICHE TASK TOPOLOGY
                    </div>
                    <h1>Navigation</h1>
                    <p>
                        Find represented work, understand where it sits,
                        and move through explicit task relationships.
                        Geometry is projection-only.
                    </p>
                </div>

                <div class="navigation-location">
                    <span class="navigation-location-label">
                        YOU ARE HERE
                    </span>
                    <strong id="navigation-location-value">
                        overview
                    </strong>
                </div>
            </div>

            <div class="navigation-commandbar">
                <input
                    id="navigation-search"
                    class="navigation-input"
                    type="search"
                    autocomplete="off"
                    placeholder="Find represented task or objective…"
                    aria-label="Search represented tasks and objectives"
                >

                <select
                    id="navigation-status-filter"
                    class="navigation-select"
                    aria-label="Navigation state filter"
                >
                    <option value="all">All states</option>
                    <option value="ready">Ready</option>
                    <option value="active">Active</option>
                    <option value="review">Review</option>
                    <option value="waiting">Waiting</option>
                    <option value="blocked">Blocked</option>
                    <option value="complete">Complete</option>
                    <option value="unknown">Unknown</option>
                </select>

                <button
                    id="navigation-back"
                    class="navigation-action"
                    type="button"
                    disabled
                >
                    Back
                </button>

                <button
                    id="navigation-overview"
                    class="navigation-action"
                    type="button"
                >
                    Overview
                </button>
            </div>

            <div
                id="navigation-breadcrumb"
                class="navigation-breadcrumb"
                aria-label="Navigation breadcrumb"
            ></div>

            <div class="navigation-shell">
                <div class="navigation-map-column">
                    <div
                        id="navigation-map-frame"
                        class="navigation-map-frame"
                        data-semantic-zoom="far"
                    >
                        <svg
                            id="navigation-map"
                            class="navigation-map"
                            tabindex="0"
                            role="application"
                            aria-label="Represented Niche task navigation map"
                        >
                            <g id="navigation-world"></g>
                        </svg>

                        <div class="navigation-controls">
                            <button
                                id="navigation-zoom-in"
                                type="button"
                                aria-label="Zoom in"
                            >
                                +
                            </button>
                            <button
                                id="navigation-zoom-out"
                                type="button"
                                aria-label="Zoom out"
                            >
                                −
                            </button>
                            <button
                                id="navigation-fit"
                                type="button"
                                aria-label="Fit current navigation context"
                            >
                                ⌂
                            </button>
                        </div>

                        <div class="navigation-zoom-meter">
                            <span id="navigation-zoom-label">
                                100%
                            </span>
                            <span id="navigation-level-label">
                                overview
                            </span>
                        </div>

                        <div class="navigation-minimap">
                            <svg
                                id="navigation-minimap"
                                aria-label="Navigation minimap"
                            ></svg>
                        </div>

                        <div
                            id="navigation-loading"
                            class="navigation-overlay"
                            hidden
                        >
                            LOADING NAVIGATION PROJECTION
                        </div>

                        <div
                            id="navigation-error"
                            class="navigation-overlay"
                            hidden
                        >
                            <strong>
                                NAVIGATION DEGRADED
                            </strong>
                            <span>
                                Execute remains available.
                            </span>
                        </div>
                    </div>
                </div>

                <aside class="navigation-side">
                    <section
                        id="navigation-context"
                        class="navigation-panel"
                    ></section>

                    <section class="navigation-panel">
                        <h2>Represented route</h2>

                        <input
                            id="navigation-route-input"
                            class="navigation-input"
                            type="search"
                            autocomplete="off"
                            placeholder="Destination task…"
                            aria-label="Route destination"
                        >

                        <button
                            id="navigation-route-button"
                            class="navigation-action"
                            type="button"
                        >
                            Find route
                        </button>

                        <div
                            id="navigation-route"
                            class="navigation-route"
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
                class="sr-only"
                aria-live="polite"
                aria-atomic="true"
            ></div>
        `;

        const causal =
            $("#surface-causal");

        if (
            causal &&
            causal.parentElement ===
                parent
        ) {
            parent.insertBefore(
                surface,
                causal
            );
        } else {
            parent.append(surface);
        }

        return surface;
    }

    function ensureNavButton() {
        let button =
            $('.nav [data-view="navigation"]');

        if (button) {
            return button;
        }

        const nav =
            $(".nav");

        if (!nav) {
            return null;
        }

        button =
            document.createElement(
                "button"
            );

        button.type =
            "button";

        button.dataset.view =
            "navigation";

        button.textContent =
            "Navigation";

        const causal =
            $('.nav [data-view="causal"]');

        if (causal) {
            nav.insertBefore(
                button,
                causal
            );
        } else {
            nav.append(button);
        }

        return button;
    }

    function cacheDom() {
        dom.surface =
            $("#surface-navigation");
        dom.navButton =
            $('.nav [data-view="navigation"]');
        dom.location =
            $("#navigation-location-value");
        dom.search =
            $("#navigation-search");
        dom.filter =
            $("#navigation-status-filter");
        dom.back =
            $("#navigation-back");
        dom.overview =
            $("#navigation-overview");
        dom.breadcrumb =
            $("#navigation-breadcrumb");
        dom.mapFrame =
            $("#navigation-map-frame");
        dom.map =
            $("#navigation-map");
        dom.world =
            $("#navigation-world");
        dom.zoomIn =
            $("#navigation-zoom-in");
        dom.zoomOut =
            $("#navigation-zoom-out");
        dom.fit =
            $("#navigation-fit");
        dom.zoomLabel =
            $("#navigation-zoom-label");
        dom.levelLabel =
            $("#navigation-level-label");
        dom.minimap =
            $("#navigation-minimap");
        dom.context =
            $("#navigation-context");
        dom.routeInput =
            $("#navigation-route-input");
        dom.routeButton =
            $("#navigation-route-button");
        dom.route =
            $("#navigation-route");
        dom.textIndex =
            $("#navigation-text-index");
        dom.loading =
            $("#navigation-loading");
        dom.error =
            $("#navigation-error");
        dom.live =
            $("#navigation-live");
    }

    function meaningfulDimensions() {
        const rectangle =
            dom.mapFrame
                ?.getBoundingClientRect();

        return Boolean(
            rectangle &&
            rectangle.width >= 160 &&
            rectangle.height >= 180
        );
    }

    function measure() {
        const rectangle =
            dom.mapFrame
                ?.getBoundingClientRect();

        if (!rectangle) {
            return false;
        }

        state.lastDimensions = {
            width:
                Math.max(
                    1,
                    rectangle.width
                ),
            height:
                Math.max(
                    1,
                    rectangle.height
                )
        };

        if (dom.map) {
            dom.map.setAttribute(
                "viewBox",
                `0 0 ${state.lastDimensions.width} ${state.lastDimensions.height}`
            );
        }

        return meaningfulDimensions();
    }

    function semanticLevelForScale(
        scale
    ) {
        if (
            scale <=
            ZOOM.farMaximum
        ) {
            return "far";
        }

        if (
            scale <=
            ZOOM.mediumMaximum
        ) {
            return "medium";
        }

        return "near";
    }

    function updateSemanticLevel() {
        const next =
            semanticLevelForScale(
                state.viewport.scale
            );

        if (
            state.semanticLevel !==
            next
        ) {
            state.semanticLevel =
                next;

            renderMap();

            emit(
                "semantic-zoom",
                {
                    level:
                        next
                }
            );
        }

        if (dom.mapFrame) {
            dom.mapFrame
                .dataset
                .semanticZoom =
                state.semanticLevel;
        }

        if (dom.levelLabel) {
            dom.levelLabel.textContent =
                state.semanticLevel ===
                    "far"
                    ? "objective overview"
                    : state.semanticLevel ===
                        "medium"
                        ? "task clusters"
                        : "task locality";
        }
    }

    function applyTransform() {
        if (!dom.world) {
            return;
        }

        dom.world.setAttribute(
            "transform",
            `translate(${state.viewport.x} ${state.viewport.y}) scale(${state.viewport.scale})`
        );

        if (dom.zoomLabel) {
            dom.zoomLabel.textContent =
                `${Math.round(
                    state.viewport.scale *
                    100
                )}%`;
        }

        if (dom.mapFrame) {
            dom.mapFrame
                .dataset
                .semanticZoom =
                state.semanticLevel;
        }
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
            }
        );
    }

    function setViewport(
        next,
        {
            persist = true
        } = {}
    ) {
        const previousLevel =
            state.semanticLevel;

        state.viewport = {
            x:
                Number.isFinite(
                    next.x
                )
                    ? next.x
                    : state.viewport.x,
            y:
                Number.isFinite(
                    next.y
                )
                    ? next.y
                    : state.viewport.y,
            scale:
                clamp(
                    Number.isFinite(
                        next.scale
                    )
                        ? next.scale
                        : state.viewport.scale,
                    ZOOM.minimum,
                    ZOOM.maximum
                )
        };

        state.semanticLevel =
            semanticLevelForScale(
                state.viewport.scale
            );

        if (
            previousLevel !==
            state.semanticLevel
        ) {
            renderMap();
        }

        if (persist) {
            safeWrite();
        }

        queueTransform();
    }

    function visibleBoundsInWorld() {
        const scale =
            state.viewport.scale;

        return {
            left:
                -state.viewport.x /
                scale,
            top:
                -state.viewport.y /
                scale,
            right:
                (
                    state.lastDimensions.width -
                    state.viewport.x
                ) /
                scale,
            bottom:
                (
                    state.lastDimensions.height -
                    state.viewport.y
                ) /
                scale
        };
    }

    function intersectsViewport(
        x,
        y,
        width,
        height
    ) {
        const bounds =
            visibleBoundsInWorld();

        const margin =
            200 /
            state.viewport.scale;

        return !(
            x + width <
                bounds.left -
                margin ||
            x >
                bounds.right +
                margin ||
            y + height <
                bounds.top -
                margin ||
            y >
                bounds.bottom +
                margin
        );
    }

    function filteredTask(task) {
        if (
            state.filter !==
            "all" &&
            taskState(task) !==
            state.filter
        ) {
            return false;
        }

        const query =
            lower(
                state.query
            );

        if (!query) {
            return true;
        }

        return (
            lower(
                taskTitle(task)
            ).includes(query) ||
            lower(
                taskId(task)
            ).includes(query) ||
            lower(
                taskObjective(task)
            ).includes(query)
        );
    }

    function objectiveVisible(
        objective
    ) {
        if (
            state.objectiveFocus &&
            objective.name !==
                state.objectiveFocus
        ) {
            return false;
        }

        if (!state.query) {
            return objective.tasks.some(
                filteredTask
            );
        }

        return (
            lower(
                objective.name
            ).includes(
                lower(
                    state.query
                )
            ) ||
            objective.tasks.some(
                filteredTask
            )
        );
    }

    function createSvg(
        name,
        attributes = {}
    ) {
        const element =
            document.createElementNS(
                SVG_NS,
                name
            );

        for (
            const [key, value]
            of Object.entries(
                attributes
            )
        ) {
            element.setAttribute(
                key,
                String(value)
            );
        }

        return element;
    }

    function renderTerritory(
        objective,
        territory,
        {
            detailed = false
        } = {}
    ) {
        const group =
            createSvg(
                "g",
                {
                    class:
                        "nav-territory-group",
                    "data-objective":
                        objective.name
                }
            );

        const body =
            createSvg(
                "rect",
                {
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
                        8
                }
            );

        body.setAttribute(
            "tabindex",
            "0"
        );

        body.setAttribute(
            "role",
            "button"
        );

        body.setAttribute(
            "aria-label",
            `Objective ${objective.name}. ${objective.statistics.total} represented tasks. ${objective.statistics.ready} ready. ${objective.statistics.blocked} blocked.`
        );

        const title =
            createSvg(
                "text",
                {
                    class:
                        "nav-territory-title",
                    x:
                        territory.x +
                        20,
                    y:
                        territory.y +
                        30
                }
            );

        title.textContent =
            objective.name;

        const meta =
            createSvg(
                "text",
                {
                    class:
                        "nav-territory-meta",
                    x:
                        territory.x +
                        20,
                    y:
                        territory.y +
                        49
                }
            );

        meta.textContent =
            `${objective.statistics.total} tasks · ${objective.statistics.ready} ready · ${objective.statistics.blocked} blocked · ${Math.round(objective.statistics.ratio * 100)}% complete`;

        group.append(
            body,
            title,
            meta
        );

        if (detailed) {
            const progressTrack =
                createSvg(
                    "rect",
                    {
                        class:
                            "nav-territory-progress-track",
                        x:
                            territory.x +
                            20,
                        y:
                            territory.y +
                            territory.height -
                            16,
                        width:
                            Math.max(
                                40,
                                territory.width -
                                40
                            ),
                        height:
                            3
                    }
                );

            const progress =
                createSvg(
                    "rect",
                    {
                        class:
                            "nav-territory-progress",
                        x:
                            territory.x +
                            20,
                        y:
                            territory.y +
                            territory.height -
                            16,
                        width:
                            Math.max(
                                0,
                                (
                                    territory.width -
                                    40
                                ) *
                                objective.statistics.ratio
                            ),
                        height:
                            3
                    }
                );

            group.append(
                progressTrack,
                progress
            );
        }

        return group;
    }

    function renderNode(
        node,
        {
            label = true,
            metadata = false
        } = {}
    ) {
        const task =
            node.task;

        const group =
            createSvg(
                "g",
                {
                    class:
                        `nav-map-node nav-node-state-${taskState(task)}`,
                    transform:
                        `translate(${node.x} ${node.y})`,
                    "data-task-id":
                        node.id,
                    tabindex:
                        "0",
                    role:
                        "button",
                    "aria-label":
                        `${taskTitle(task)}. ${taskState(task)}. Objective ${taskObjective(task)}.`
                }
            );

        if (
            node.id ===
            state.selectedTaskId
        ) {
            group.classList.add(
                "selected"
            );
        }

        if (
            state.route.includes(
                node.id
            )
        ) {
            group.classList.add(
                "route"
            );
        }

        const body =
            createSvg(
                "rect",
                {
                    class:
                        "nav-node-body",
                    width:
                        node.width,
                    height:
                        node.height,
                    rx:
                        5
                }
            );

        group.append(body);

        if (label) {
            const title =
                createSvg(
                    "text",
                    {
                        class:
                            "nav-node-title",
                        x:
                            14,
                        y:
                            metadata
                                ? 23
                                : 35
                    }
                );

            title.textContent =
                taskTitle(task)
                    .slice(
                        0,
                        38
                    );

            group.append(title);
        }

        if (metadata) {
            const meta =
                createSvg(
                    "text",
                    {
                        class:
                            "nav-node-meta",
                        x:
                            14,
                        y:
                            45
                    }
                );

            meta.textContent =
                `${taskState(task)} · ${taskPriority(task)}`;

            group.append(meta);
        }

        if (
            node.id ===
            state.selectedTaskId
        ) {
            const location =
                createSvg(
                    "text",
                    {
                        class:
                            "nav-you-are-here-text",
                        x:
                            0,
                        y:
                            -10
                    }
                );

            location.textContent =
                "YOU ARE HERE";

            group.append(location);
        }

        return group;
    }

    function edgePath(
        source,
        target
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

        const middle =
            sx +
            (
                tx - sx
            ) *
            0.5;

        return (
            `M ${sx} ${sy} ` +
            `C ${middle} ${sy}, ` +
            `${middle} ${ty}, ` +
            `${tx} ${ty}`
        );
    }

    function localNeighborhoodIds() {
        const result =
            new Set();

        const selected =
            state.model
                .taskById
                .get(
                    state.selectedTaskId
                );

        if (!selected) {
            return result;
        }

        const id =
            taskId(selected);

        result.add(id);

        for (
            const dependency
            of taskDependencies(
                selected
            )
        ) {
            result.add(
                dependency
            );
        }

        for (
            const dependent
            of state.model
                .dependents
                .get(id) ??
                []
        ) {
            result.add(
                dependent
            );
        }

        const parent =
            taskParent(
                selected
            );

        if (parent) {
            result.add(parent);
        }

        for (
            const task
            of state.model.tasks
        ) {
            if (
                taskParent(task) ===
                id
            ) {
                result.add(
                    taskId(task)
                );
            }
        }

        return result;
    }

    function renderMap() {
        if (
            !dom.world ||
            !state.model.objectives.length
        ) {
            return;
        }

        const fragment =
            document.createDocumentFragment();

        const territoryLayer =
            createSvg(
                "g",
                {
                    class:
                        "navigation-territories"
                }
            );

        const edgeLayer =
            createSvg(
                "g",
                {
                    class:
                        "navigation-edges"
                }
            );

        const nodeLayer =
            createSvg(
                "g",
                {
                    class:
                        "navigation-nodes"
                }
            );

        const neighborhood =
            state.semanticLevel ===
                "near" &&
            state.selectedTaskId
                ? localNeighborhoodIds()
                : null;

        for (
            const objective
            of state.model.objectives
        ) {
            if (
                !objectiveVisible(
                    objective
                )
            ) {
                continue;
            }

            const territory =
                state.model
                    .territoryByObjective
                    .get(
                        objective.name
                    );

            if (
                !territory ||
                !intersectsViewport(
                    territory.x,
                    territory.y,
                    territory.width,
                    territory.height
                )
            ) {
                continue;
            }

            territoryLayer.append(
                renderTerritory(
                    objective,
                    territory,
                    {
                        detailed:
                            state.semanticLevel !==
                            "far"
                    }
                )
            );

            if (
                state.semanticLevel ===
                "far"
            ) {
                continue;
            }

            for (
                const task
                of objective.tasks
            ) {
                if (
                    !filteredTask(
                        task
                    )
                ) {
                    continue;
                }

                const id =
                    taskId(task);

                const node =
                    state.model
                        .nodeById
                        .get(id);

                if (!node) {
                    continue;
                }

                if (
                    neighborhood &&
                    !neighborhood.has(id)
                ) {
                    continue;
                }

                if (
                    !intersectsViewport(
                        node.x,
                        node.y,
                        node.width,
                        node.height
                    )
                ) {
                    continue;
                }

                nodeLayer.append(
                    renderNode(
                        node,
                        {
                            label:
                                true,
                            metadata:
                                state.semanticLevel ===
                                "near"
                        }
                    )
                );
            }
        }

        if (
            state.semanticLevel ===
            "near"
        ) {
            const visibleNodeIds =
                neighborhood ??
                new Set(
                    Array.from(
                        state.model
                            .nodeById
                            .keys()
                    )
                );

            for (
                const edge
                of state.model.edges
            ) {
                if (
                    !visibleNodeIds.has(
                        edge.source
                    ) ||
                    !visibleNodeIds.has(
                        edge.target
                    )
                ) {
                    continue;
                }

                const source =
                    state.model
                        .nodeById
                        .get(
                            edge.source
                        );

                const target =
                    state.model
                        .nodeById
                        .get(
                            edge.target
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
                            index
                        ) =>
                            index <
                            state.route.length -
                                1 &&
                            (
                                (
                                    id ===
                                    edge.source &&
                                    state.route[
                                        index + 1
                                    ] ===
                                    edge.target
                                ) ||
                                (
                                    id ===
                                    edge.target &&
                                    state.route[
                                        index + 1
                                    ] ===
                                    edge.source
                                )
                            )
                    );

                const path =
                    createSvg(
                        "path",
                        {
                            class:
                                `nav-edge nav-edge-${edge.type}${routeEdge ? " route" : ""}`,
                            d:
                                edgePath(
                                    source,
                                    target
                                ),
                            "vector-effect":
                                "non-scaling-stroke"
                        }
                    );

                edgeLayer.append(
                    path
                );
            }
        }

        fragment.append(
            territoryLayer,
            edgeLayer,
            nodeLayer
        );

        dom.world.replaceChildren(
            fragment
        );

        applyTransform();
        renderMinimap();
    }

    function renderContext() {
        if (!dom.context) {
            return;
        }

        const task =
            state.model
                .taskById
                .get(
                    state.selectedTaskId
                );

        if (!task) {
            dom.context.innerHTML = `
                <h2>Current location</h2>
                <p>
                    Overview. Select an objective territory or represented
                    task to move into local context.
                </p>
            `;

            if (dom.location) {
                dom.location.textContent =
                    state.objectiveFocus ??
                    "overview";
            }

            return;
        }

        const id =
            taskId(task);

        const dependencies =
            taskDependencies(task)
                .filter((candidate) =>
                    state.model
                        .taskById
                        .has(candidate)
                );

        const dependents =
            state.model
                .dependents
                .get(id) ??
            [];

        const parent =
            taskParent(task);

        const children =
            state.model.tasks
                .filter(
                    (candidate) =>
                        taskParent(
                            candidate
                        ) === id
                )
                .map(
                    taskId
                );

        if (dom.location) {
            dom.location.textContent =
                taskTitle(task);
        }

        dom.context.replaceChildren();

        const heading =
            document.createElement(
                "h2"
            );

        heading.textContent =
            taskTitle(task);

        const list =
            document.createElement(
                "dl"
            );

        const rows = [
            [
                "state",
                taskState(task)
            ],
            [
                "objective",
                taskObjective(task)
            ],
            [
                "parent",
                parent ||
                "not represented"
            ],
            [
                "requires",
                String(
                    dependencies.length
                )
            ],
            [
                "dependents",
                String(
                    dependents.length
                )
            ],
            [
                "children",
                String(
                    children.length
                )
            ],
            [
                "geometry",
                "projection only"
            ]
        ];

        for (
            const [term, value]
            of rows
        ) {
            const dt =
                document.createElement(
                    "dt"
                );

            const dd =
                document.createElement(
                    "dd"
                );

            dt.textContent =
                term;

            dd.textContent =
                value;

            list.append(
                dt,
                dd
            );
        }

        dom.context.append(
            heading,
            list
        );
    }

    function renderBreadcrumb() {
        if (!dom.breadcrumb) {
            return;
        }

        dom.breadcrumb.replaceChildren();

        const overview =
            document.createElement(
                "button"
            );

        overview.type =
            "button";

        overview.textContent =
            "overview";

        overview.addEventListener(
            "click",
            clearObjectiveFocus
        );

        dom.breadcrumb.append(
            overview
        );

        if (
            state.objectiveFocus
        ) {
            const separator =
                document.createElement(
                    "span"
                );

            separator.textContent =
                "›";

            const objective =
                document.createElement(
                    "button"
                );

            objective.type =
                "button";

            objective.textContent =
                state.objectiveFocus;

            objective.addEventListener(
                "click",
                () =>
                    focusObjective(
                        state.objectiveFocus
                    )
            );

            dom.breadcrumb.append(
                separator,
                objective
            );
        }

        const task =
            state.model
                .taskById
                .get(
                    state.selectedTaskId
                );

        if (task) {
            const separator =
                document.createElement(
                    "span"
                );

            separator.textContent =
                "›";

            const current =
                document.createElement(
                    "strong"
                );

            current.textContent =
                taskTitle(task);

            dom.breadcrumb.append(
                separator,
                current
            );
        }
    }

    function renderTextIndex() {
        if (!dom.textIndex) {
            return;
        }

        const fragment =
            document.createDocumentFragment();

        for (
            const objective
            of state.model.objectives
        ) {
            if (
                !objectiveVisible(
                    objective
                )
            ) {
                continue;
            }

            const section =
                document.createElement(
                    "section"
                );

            const heading =
                document.createElement(
                    "button"
                );

            heading.type =
                "button";

            heading.className =
                "navigation-index-objective";

            heading.textContent =
                `${objective.name} · ${objective.statistics.total} tasks`;

            heading.addEventListener(
                "click",
                () =>
                    focusObjective(
                        objective.name
                    )
            );

            section.append(
                heading
            );

            if (
                state.semanticLevel !==
                "far"
            ) {
                for (
                    const task
                    of objective.tasks
                ) {
                    if (
                        !filteredTask(
                            task
                        )
                    ) {
                        continue;
                    }

                    const button =
                        document.createElement(
                            "button"
                        );

                    button.type =
                        "button";

                    button.className =
                        "navigation-index-task";

                    button.textContent =
                        `${taskTitle(task)} · ${taskState(task)}`;

                    button.addEventListener(
                        "click",
                        () =>
                            selectTask(
                                taskId(task),
                                {
                                    focus:
                                        true,
                                    source:
                                        "text-index"
                                }
                            )
                    );

                    section.append(
                        button
                    );
                }
            }

            fragment.append(
                section
            );
        }

        dom.textIndex.replaceChildren(
            fragment
        );
    }

    function renderMinimap() {
        if (!dom.minimap) {
            return;
        }

        dom.minimap.replaceChildren();

        dom.minimap.setAttribute(
            "viewBox",
            `0 0 ${state.world.width} ${state.world.height}`
        );

        for (
            const objective
            of state.model.objectives
        ) {
            if (
                !objectiveVisible(
                    objective
                )
            ) {
                continue;
            }

            const territory =
                state.model
                    .territoryByObjective
                    .get(
                        objective.name
                    );

            if (!territory) {
                continue;
            }

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
                            territory.height
                    }
                )
            );
        }

        const scale =
            state.viewport.scale;

        dom.minimap.append(
            createSvg(
                "rect",
                {
                    class:
                        "nav-mini-viewport",
                    x:
                        -state.viewport.x /
                        scale,
                    y:
                        -state.viewport.y /
                        scale,
                    width:
                        state.lastDimensions.width /
                        scale,
                    height:
                        state.lastDimensions.height /
                        scale
                }
            )
        );
    }

    function routeGraph() {
        const graph =
            new Map(
                state.model.tasks.map(
                    (task) => [
                        taskId(task),
                        new Set()
                    ]
                )
            );

        for (
            const edge
            of state.model.edges
        ) {
            graph
                .get(edge.source)
                ?.add(
                    edge.target
                );

            graph
                .get(edge.target)
                ?.add(
                    edge.source
                );
        }

        return graph;
    }

    function representedRoute(
        source,
        destination
    ) {
        if (
            !state.model.taskById.has(
                source
            ) ||
            !state.model.taskById.has(
                destination
            )
        ) {
            return [];
        }

        const graph =
            routeGraph();

        const previous =
            new Map([
                [
                    source,
                    null
                ]
            ]);

        const queue = [
            source
        ];

        while (
            queue.length
        ) {
            const current =
                queue.shift();

            if (
                current ===
                destination
            ) {
                const path = [];

                let cursor =
                    destination;

                while (
                    cursor !==
                    null
                ) {
                    path.push(
                        cursor
                    );

                    cursor =
                        previous.get(
                            cursor
                        );
                }

                return path.reverse();
            }

            const neighbors =
                Array.from(
                    graph.get(current) ??
                    []
                )
                    .sort(
                        (a, b) =>
                            a.localeCompare(
                                b
                            )
                    );

            for (
                const neighbor
                of neighbors
            ) {
                if (
                    previous.has(
                        neighbor
                    )
                ) {
                    continue;
                }

                previous.set(
                    neighbor,
                    current
                );

                queue.push(
                    neighbor
                );
            }
        }

        return [];
    }

    function resolveTask(
        value
    ) {
        const normalized =
            lower(value);

        if (!normalized) {
            return null;
        }

        for (
            const task
            of state.model.tasks
        ) {
            if (
                lower(
                    taskId(task)
                ) === normalized ||
                lower(
                    taskTitle(task)
                ) === normalized
            ) {
                return task;
            }
        }

        return (
            state.model.tasks
                .find(
                    (task) =>
                        lower(
                            taskTitle(task)
                        ).includes(
                            normalized
                        ) ||
                        lower(
                            taskId(task)
                        ).includes(
                            normalized
                        )
                ) ??
            null
        );
    }

    function renderRoute() {
        if (!dom.route) {
            return;
        }

        dom.route.replaceChildren();

        if (
            state.route.length ===
            0
        ) {
            const text =
                document.createElement(
                    "p"
                );

            text.textContent =
                state.selectedTaskId
                    ? "Choose a represented destination."
                    : "Select a starting task first.";

            dom.route.append(
                text
            );

            return;
        }

        state.route.forEach(
            (
                id,
                index
            ) => {
                const task =
                    state.model
                        .taskById
                        .get(id);

                if (!task) {
                    return;
                }

                const button =
                    document.createElement(
                        "button"
                    );

                button.type =
                    "button";

                button.className =
                    "navigation-route-step";

                button.textContent =
                    `${index + 1}. ${taskTitle(task)}`;

                button.addEventListener(
                    "click",
                    () =>
                        selectTask(
                            id,
                            {
                                focus:
                                    true,
                                source:
                                    "route"
                            }
                        )
                );

                dom.route.append(
                    button
                );
            }
        );
    }

    function selectTask(
        id,
        {
            focus = false,
            source = "navigation"
        } = {}
    ) {
        if (
            !state.model
                .taskById
                .has(id)
        ) {
            return;
        }

        if (
            state.selectedTaskId &&
            state.selectedTaskId !==
                id
        ) {
            state.selectionHistory.push(
                state.selectedTaskId
            );

            if (
                state.selectionHistory.length >
                50
            ) {
                state.selectionHistory.shift();
            }
        }

        state.selectedTaskId =
            id;

        const task =
            state.model
                .taskById
                .get(id);

        state.objectiveFocus =
            taskObjective(task);

        state.route = [];

        updateBackState();
        renderContext();
        renderBreadcrumb();
        renderRoute();
        renderMap();
        renderTextIndex();

        if (focus) {
            focusTask(id);
        }

        if (
            window.Niche &&
            typeof window.Niche.task ===
                "function"
        ) {
            window.Niche.task(id);
        }

        emit(
            "selection",
            {
                task_id:
                    id,
                source
            }
        );
    }

    function updateBackState() {
        if (dom.back) {
            dom.back.disabled =
                state.selectionHistory.length ===
                0;
        }
    }

    function back() {
        const previous =
            state.selectionHistory.pop();

        if (!previous) {
            return;
        }

        state.selectedTaskId =
            previous;

        const task =
            state.model
                .taskById
                .get(previous);

        state.objectiveFocus =
            task
                ? taskObjective(task)
                : null;

        updateBackState();
        renderContext();
        renderBreadcrumb();
        renderMap();
        renderTextIndex();
        focusTask(previous);

        if (
            window.Niche &&
            typeof window.Niche.task ===
                "function"
        ) {
            window.Niche.task(
                previous
            );
        }
    }

    function focusTask(id) {
        const node =
            state.model
                .nodeById
                .get(id);

        if (!node) {
            return;
        }

        const scale =
            clamp(
                Math.max(
                    state.viewport.scale,
                    1.2
                ),
                ZOOM.minimum,
                ZOOM.maximum
            );

        setViewport({
            x:
                state.lastDimensions.width /
                    2 -
                (
                    node.x +
                    node.width / 2
                ) *
                    scale,
            y:
                state.lastDimensions.height /
                    2 -
                (
                    node.y +
                    node.height / 2
                ) *
                    scale,
            scale
        });
    }

    function fitBounds(bounds) {
        const width =
            Math.max(
                1,
                bounds.width
            );

        const height =
            Math.max(
                1,
                bounds.height
            );

        const padding =
            state.lastDimensions.width <
            560
                ? 26
                : 44;

        const scale =
            clamp(
                Math.min(
                    (
                        state.lastDimensions.width -
                        padding * 2
                    ) /
                        width,
                    (
                        state.lastDimensions.height -
                        padding * 2
                    ) /
                        height
                ),
                ZOOM.minimum,
                ZOOM.maximum
            );

        setViewport({
            x:
                (
                    state.lastDimensions.width -
                    width * scale
                ) /
                    2 -
                bounds.x * scale,
            y:
                (
                    state.lastDimensions.height -
                    height * scale
                ) /
                    2 -
                bounds.y * scale,
            scale
        });
    }

    function fitAll() {
        fitBounds({
            x: 0,
            y: 0,
            width:
                state.world.width,
            height:
                state.world.height
        });
    }

    function focusObjective(
        objective
    ) {
        const territory =
            state.model
                .territoryByObjective
                .get(objective);

        if (!territory) {
            return;
        }

        state.objectiveFocus =
            objective;

        state.selectedTaskId =
            null;

        state.route = [];

        renderContext();
        renderBreadcrumb();
        renderRoute();
        renderTextIndex();
        renderMap();

        fitBounds({
            x:
                territory.x -
                20,
            y:
                territory.y -
                20,
            width:
                territory.width +
                40,
            height:
                territory.height +
                40
        });
    }

    function clearObjectiveFocus() {
        state.objectiveFocus =
            null;

        state.selectedTaskId =
            null;

        state.route = [];

        renderContext();
        renderBreadcrumb();
        renderRoute();
        renderTextIndex();
        renderMap();
        fitAll();
    }

    function zoomAt(
        factor,
        clientX,
        clientY
    ) {
        const rectangle =
            dom.mapFrame
                ?.getBoundingClientRect();

        if (!rectangle) {
            return;
        }

        const localX =
            clientX -
            rectangle.left;

        const localY =
            clientY -
            rectangle.top;

        const oldScale =
            state.viewport.scale;

        const newScale =
            clamp(
                oldScale *
                    factor,
                ZOOM.minimum,
                ZOOM.maximum
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
                    newScale,
            y:
                localY -
                worldY *
                    newScale,
            scale:
                newScale
        });
    }

    function zoomCentered(
        factor
    ) {
        const rectangle =
            dom.mapFrame
                ?.getBoundingClientRect();

        if (!rectangle) {
            return;
        }

        zoomAt(
            factor,
            rectangle.left +
                rectangle.width / 2,
            rectangle.top +
                rectangle.height / 2
        );
    }

    function routeToInput() {
        if (
            !state.selectedTaskId
        ) {
            announce(
                "Select a starting task first."
            );

            return;
        }

        const task =
            resolveTask(
                dom.routeInput
                    ?.value
            );

        if (!task) {
            state.route = [];
            renderRoute();
            announce(
                "Destination is not represented."
            );

            return;
        }

        state.route =
            representedRoute(
                state.selectedTaskId,
                taskId(task)
            );

        renderRoute();
        renderMap();

        announce(
            state.route.length
                ? `Represented relationship route contains ${state.route.length} locations. It is not execution order.`
                : "No represented relationship route was found."
        );
    }

    function announce(
        message
    ) {
        if (!dom.live) {
            return;
        }

        dom.live.textContent =
            "";

        requestAnimationFrame(
            () => {
                dom.live.textContent =
                    message;
            }
        );
    }

    function activateSurfaceFallback() {
        for (
            const surface
            of $$(".surface")
        ) {
            const active =
                surface ===
                dom.surface;

            surface.hidden =
                !active;

            surface.classList.toggle(
                "active",
                active
            );
        }

        for (
            const button
            of $$(".nav [data-view]")
        ) {
            button.classList.toggle(
                "active",
                button ===
                    dom.navButton
            );
        }
    }

    function activate() {
        install();

        state.active =
            true;

        if (
            window.Niche &&
            typeof window.Niche.view ===
                "function"
        ) {
            try {
                window.Niche.view(
                    "navigation"
                );
            } catch {
                activateSurfaceFallback();
            }
        } else {
            activateSurfaceFallback();
        }

        if (dom.surface) {
            dom.surface.hidden =
                false;
        }

        requestAnimationFrame(
            () => {
                onActivate();
            }
        );
    }

    function onActivate() {
        state.active =
            true;

        if (!measure()) {
            requestAnimationFrame(
                onActivate
            );

            return;
        }

        syncFromCore();

        if (
            !state.firstMeaningfulFit
        ) {
            state.firstMeaningfulFit =
                true;

            if (
                state.objectiveFocus
            ) {
                focusObjective(
                    state.objectiveFocus
                );
            } else {
                fitAll();
            }
        } else {
            applyTransform();
            renderMap();
        }

        emit(
            "activated"
        );
    }

    function onDeactivate() {
        state.active =
            false;

        safeWrite();

        emit(
            "deactivated"
        );
    }

    function onResize() {
        const previous =
            {
                ...state.lastDimensions
            };

        if (!measure()) {
            return;
        }

        if (
            previous.width ===
                state.lastDimensions.width &&
            previous.height ===
                state.lastDimensions.height
        ) {
            return;
        }

        const projection =
            coreProjection();

        if (projection) {
            const normalized =
                normalizeProjection(
                    projection
                );

            state.model =
                buildModel(
                    normalized
                );
        }

        if (
            state.active &&
            !state.firstMeaningfulFit
        ) {
            state.firstMeaningfulFit =
                true;

            fitAll();
        } else {
            renderAll();
        }
    }

    function syncFromCore() {
        const projection =
            coreProjection();

        if (!projection) {
            setError(
                "Navigation cannot read the current core projection."
            );

            return;
        }

        clearError();

        const normalized =
            normalizeProjection(
                projection
            );

        if (
            Number.isFinite(
                normalized.generation
            ) &&
            normalized.generation <
                state.projectionGeneration
        ) {
            return;
        }

        if (
            Number.isFinite(
                normalized.generation
            )
        ) {
            state.projectionGeneration =
                normalized.generation;
        }

        const selectionChanged =
            normalized.selectedTaskId !==
            state.selectedTaskId;

        state.selectedTaskId =
            normalized.selectedTaskId;

        state.model =
            buildModel(
                normalized
            );

        if (
            state.selectedTaskId
        ) {
            const task =
                state.model
                    .taskById
                    .get(
                        state.selectedTaskId
                    );

            if (task) {
                state.objectiveFocus =
                    taskObjective(task);
            }
        }

        renderAll();

        if (
            selectionChanged &&
            state.active &&
            state.selectedTaskId
        ) {
            focusTask(
                state.selectedTaskId
            );
        }
    }

    function renderAll() {
        renderContext();
        renderBreadcrumb();
        renderRoute();
        renderTextIndex();
        renderMap();
        updateBackState();
    }

    function setError(message) {
        if (dom.error) {
            dom.error.hidden =
                false;

            const text =
                $("span", dom.error);

            if (text) {
                text.textContent =
                    message;
            }
        }

        emit(
            "degraded",
            {
                message
            }
        );
    }

    function clearError() {
        if (dom.error) {
            dom.error.hidden =
                true;
        }
    }

    function bindMapInteraction() {
        dom.map?.addEventListener(
            "wheel",
            (event) => {
                event.preventDefault();

                zoomAt(
                    Math.exp(
                        -event.deltaY *
                        ZOOM.wheelFactor
                    ),
                    event.clientX,
                    event.clientY
                );
            },
            {
                passive:
                    false
            }
        );

        dom.map?.addEventListener(
            "click",
            (event) => {
                const taskElement =
                    event.target
                        .closest?.(
                            "[data-task-id]"
                        );

                if (
                    taskElement
                        ?.dataset
                        .taskId
                ) {
                    selectTask(
                        taskElement.dataset.taskId,
                        {
                            source:
                                "map"
                        }
                    );

                    return;
                }

                const objectiveElement =
                    event.target
                        .closest?.(
                            "[data-objective]"
                        );

                if (
                    objectiveElement
                        ?.dataset
                        .objective
                ) {
                    focusObjective(
                        objectiveElement
                            .dataset
                            .objective
                    );
                }
            }
        );

        dom.map?.addEventListener(
            "dblclick",
            (event) => {
                const taskElement =
                    event.target
                        .closest?.(
                            "[data-task-id]"
                        );

                if (
                    taskElement
                        ?.dataset
                        .taskId
                ) {
                    selectTask(
                        taskElement
                            .dataset
                            .taskId,
                        {
                            focus:
                                true,
                            source:
                                "double-click"
                        }
                    );
                }
            }
        );

        dom.map?.addEventListener(
            "pointerdown",
            (event) => {
                dom.map
                    .setPointerCapture?.(
                        event.pointerId
                    );

                state.pointer.active.set(
                    event.pointerId,
                    {
                        x:
                            event.clientX,
                        y:
                            event.clientY
                    }
                );

                if (
                    state.pointer.active.size ===
                    1
                ) {
                    state.pointer.mode =
                        "pan";

                    state.pointer.startX =
                        event.clientX;

                    state.pointer.startY =
                        event.clientY;

                    state.pointer.viewportX =
                        state.viewport.x;

                    state.pointer.viewportY =
                        state.viewport.y;
                } else if (
                    state.pointer.active.size ===
                    2
                ) {
                    const points =
                        Array.from(
                            state.pointer.active.values()
                        );

                    state.pointer.mode =
                        "pinch";

                    state.pointer.pinchDistance =
                        Math.hypot(
                            points[1].x -
                                points[0].x,
                            points[1].y -
                                points[0].y
                        );

                    state.pointer.pinchScale =
                        state.viewport.scale;

                    state.pointer.pinchCenterX =
                        (
                            points[0].x +
                            points[1].x
                        ) /
                        2;

                    state.pointer.pinchCenterY =
                        (
                            points[0].y +
                            points[1].y
                        ) /
                        2;
                }
            }
        );

        dom.map?.addEventListener(
            "pointermove",
            (event) => {
                if (
                    !state.pointer.active.has(
                        event.pointerId
                    )
                ) {
                    return;
                }

                state.pointer.active.set(
                    event.pointerId,
                    {
                        x:
                            event.clientX,
                        y:
                            event.clientY
                    }
                );

                if (
                    state.pointer.mode ===
                        "pan" &&
                    state.pointer.active.size ===
                        1
                ) {
                    setViewport({
                        x:
                            state.pointer.viewportX +
                            (
                                event.clientX -
                                state.pointer.startX
                            ),
                        y:
                            state.pointer.viewportY +
                            (
                                event.clientY -
                                state.pointer.startY
                            ),
                        scale:
                            state.viewport.scale
                    });

                    return;
                }

                if (
                    state.pointer.active.size ===
                    2
                ) {
                    const points =
                        Array.from(
                            state.pointer.active.values()
                        );

                    const distance =
                        Math.max(
                            1,
                            Math.hypot(
                                points[1].x -
                                    points[0].x,
                                points[1].y -
                                    points[0].y
                            )
                        );

                    const targetScale =
                        clamp(
                            state.pointer.pinchScale *
                            (
                                distance /
                                Math.max(
                                    1,
                                    state.pointer.pinchDistance
                                )
                            ),
                            ZOOM.minimum,
                            ZOOM.maximum
                        );

                    zoomAt(
                        targetScale /
                        state.viewport.scale,
                        state.pointer.pinchCenterX,
                        state.pointer.pinchCenterY
                    );
                }
            }
        );

        const finishPointer =
            (event) => {
                state.pointer.active.delete(
                    event.pointerId
                );

                if (
                    state.pointer.active.size ===
                    0
                ) {
                    state.pointer.mode =
                        "";
                }
            };

        dom.map?.addEventListener(
            "pointerup",
            finishPointer
        );

        dom.map?.addEventListener(
            "pointercancel",
            finishPointer
        );

        dom.map?.addEventListener(
            "keydown",
            (event) => {
                if (
                    event.key === "+"
                ) {
                    event.preventDefault();
                    zoomCentered(
                        ZOOM.step
                    );
                } else if (
                    event.key === "-"
                ) {
                    event.preventDefault();
                    zoomCentered(
                        1 / ZOOM.step
                    );
                } else if (
                    event.key === "0"
                ) {
                    event.preventDefault();
                    fitCurrentContext();
                } else if (
                    event.key === "Escape"
                ) {
                    event.preventDefault();

                    if (
                        state.selectedTaskId
                    ) {
                        state.selectedTaskId =
                            null;

                        renderAll();
                    } else if (
                        state.objectiveFocus
                    ) {
                        clearObjectiveFocus();
                    }
                }
            }
        );
    }

    function bindMinimap() {
        dom.minimap?.addEventListener(
            "click",
            (event) => {
                const rectangle =
                    dom.minimap
                        .getBoundingClientRect();

                if (
                    rectangle.width <=
                        0 ||
                    rectangle.height <=
                        0
                ) {
                    return;
                }

                const worldX =
                    (
                        event.clientX -
                        rectangle.left
                    ) /
                    rectangle.width *
                    state.world.width;

                const worldY =
                    (
                        event.clientY -
                        rectangle.top
                    ) /
                    rectangle.height *
                    state.world.height;

                setViewport({
                    x:
                        state.lastDimensions.width /
                            2 -
                        worldX *
                            state.viewport.scale,
                    y:
                        state.lastDimensions.height /
                            2 -
                        worldY *
                            state.viewport.scale,
                    scale:
                        state.viewport.scale
                });
            }
        );
    }

    function fitCurrentContext() {
        if (
            state.selectedTaskId
        ) {
            focusTask(
                state.selectedTaskId
            );

            return;
        }

        if (
            state.objectiveFocus
        ) {
            focusObjective(
                state.objectiveFocus
            );

            return;
        }

        fitAll();
    }

    function bindControls() {
        dom.navButton?.addEventListener(
            "click",
            activate
        );

        dom.zoomIn?.addEventListener(
            "click",
            () =>
                zoomCentered(
                    ZOOM.step
                )
        );

        dom.zoomOut?.addEventListener(
            "click",
            () =>
                zoomCentered(
                    1 / ZOOM.step
                )
        );

        dom.fit?.addEventListener(
            "click",
            fitCurrentContext
        );

        dom.back?.addEventListener(
            "click",
            back
        );

        dom.overview?.addEventListener(
            "click",
            clearObjectiveFocus
        );

        dom.search?.addEventListener(
            "input",
            () => {
                state.query =
                    dom.search.value.trim();

                safeWrite();
                renderAll();
            }
        );

        dom.search?.addEventListener(
            "keydown",
            (event) => {
                if (
                    event.key !==
                    "Enter"
                ) {
                    return;
                }

                const task =
                    resolveTask(
                        dom.search.value
                    );

                if (task) {
                    event.preventDefault();

                    selectTask(
                        taskId(task),
                        {
                            focus:
                                true,
                            source:
                                "search"
                        }
                    );

                    return;
                }

                const objective =
                    state.model.objectives
                        .find(
                            (candidate) =>
                                lower(
                                    candidate.name
                                ).includes(
                                    lower(
                                        dom.search.value
                                    )
                                )
                        );

                if (objective) {
                    event.preventDefault();

                    focusObjective(
                        objective.name
                    );
                }
            }
        );

        dom.filter?.addEventListener(
            "change",
            () => {
                state.filter =
                    asText(
                        dom.filter.value,
                        "all"
                    );

                safeWrite();
                renderAll();
            }
        );

        dom.routeButton?.addEventListener(
            "click",
            routeToInput
        );

        dom.routeInput?.addEventListener(
            "keydown",
            (event) => {
                if (
                    event.key ===
                    "Enter"
                ) {
                    event.preventDefault();
                    routeToInput();
                }
            }
        );

        bindMapInteraction();
        bindMinimap();
    }

    function bindCoreEvents() {
        for (
            const name
            of [
                "niche:projection",
                "niche:task-selected"
            ]
        ) {
            window.addEventListener(
                name,
                syncFromCore
            );
        }

        window.addEventListener(
            "niche:view",
            (event) => {
                const view =
                    asText(
                        event.detail?.view
                    );

                if (
                    view ===
                    "navigation"
                ) {
                    state.active =
                        true;

                    requestAnimationFrame(
                        onActivate
                    );
                } else if (
                    state.active
                ) {
                    onDeactivate();
                }
            }
        );
    }

    function restorePreferences() {
        const saved =
            safeRead();

        if (!saved) {
            return;
        }

        if (
            saved.viewport &&
            Number.isFinite(
                saved.viewport.x
            ) &&
            Number.isFinite(
                saved.viewport.y
            ) &&
            Number.isFinite(
                saved.viewport.scale
            )
        ) {
            state.viewport = {
                x:
                    saved.viewport.x,
                y:
                    saved.viewport.y,
                scale:
                    clamp(
                        saved.viewport.scale,
                        ZOOM.minimum,
                        ZOOM.maximum
                    )
            };

            state.semanticLevel =
                semanticLevelForScale(
                    state.viewport.scale
                );
        }

        state.objectiveFocus =
            asText(
                saved.objectiveFocus
            ) ||
            null;

        state.filter =
            asText(
                saved.filter,
                "all"
            );

        state.query =
            asText(
                saved.query
            );
    }

    function installResizeObserver() {
        if (
            state.resizeObserver ||
            !dom.mapFrame
        ) {
            return;
        }

        if (
            "ResizeObserver" in
            window
        ) {
            state.resizeObserver =
                new ResizeObserver(
                    () => {
                        requestAnimationFrame(
                            onResize
                        );
                    }
                );

            state.resizeObserver.observe(
                dom.mapFrame
            );
        } else {
            window.addEventListener(
                "resize",
                onResize,
                {
                    passive:
                        true
                }
            );
        }
    }

    function install() {
        if (
            state.installed
        ) {
            return true;
        }

        restorePreferences();
        ensureSurface();
        ensureNavButton();
        cacheDom();

        if (
            !dom.surface ||
            !dom.map ||
            !dom.world
        ) {
            return false;
        }

        if (dom.search) {
            dom.search.value =
                state.query;
        }

        if (dom.filter) {
            dom.filter.value =
                state.filter;
        }

        bindControls();
        bindCoreEvents();
        installResizeObserver();

        state.installed =
            true;

        syncFromCore();

        emit(
            "installed"
        );

        return true;
    }

    window.NicheNavigation =
        Object.freeze({
            open:
                activate,

            select(
                id,
                options = {}
            ) {
                install();

                selectTask(
                    asText(id),
                    options
                );
            },

            fit:
                fitCurrentContext,

            back,

            overview:
                clearObjectiveFocus,

            sync:
                syncFromCore,

            state() {
                return Object.freeze({
                    installed:
                        state.installed,
                    active:
                        state.active,
                    selectedTaskId:
                        state.selectedTaskId,
                    objectiveFocus:
                        state.objectiveFocus,
                    semanticLevel:
                        state.semanticLevel,
                    representedTaskCount:
                        state.model.tasks.length,
                    representedObjectiveCount:
                        state.model.objectives.length,
                    viewport:
                        Object.freeze({
                            ...state.viewport
                        }),
                    projectionGeneration:
                        state.projectionGeneration,
                    authorityEffect:
                        "none",
                    projectionOnly:
                        true
                });
            }
        });

    function start() {
        install();
    }

    if (
        document.readyState ===
        "loading"
    ) {
        document.addEventListener(
            "DOMContentLoaded",
            start,
            {
                once:
                    true
            }
        );
    } else {
        start();
    }
})();
