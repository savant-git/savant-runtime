(() => {
    "use strict";

    const SVG_NS =
        "http://www.w3.org/2000/svg";

    const STORAGE_KEY =
        "savant.niche.navigation.v1";

    const WORLD_MARGIN =
        160;

    const TERRITORY_WIDTH =
        920;

    const TERRITORY_GAP =
        110;

    const TERRITORY_HEADER =
        78;

    const NODE_WIDTH =
        188;

    const NODE_HEIGHT =
        58;

    const NODE_GAP_X =
        38;

    const NODE_GAP_Y =
        28;

    const MIN_SCALE =
        0.16;

    const MAX_SCALE =
        3.4;

    const state = {
        installed:
            false,

        loaded:
            false,

        loading:
            false,

        tasks:
            [],

        nodes:
            [],

        nodeById:
            new Map(),

        territories:
            [],

        edges:
            [],

        selectedId:
            null,

        route:
            [],

        routeDestination:
            null,

        lens:
            "structure",

        statusFilter:
            "all",

        isolate:
            false,

        transform: {
            x: 0,
            y: 0,
            k: 1
        },

        world: {
            width: 2400,
            height: 1600
        },

        history:
            [],

        historyIndex:
            -1,

        pointers:
            new Map(),

        drag:
            null,

        pinch:
            null,

        renderScheduled:
            false,

        fetchController:
            null
    };

    const $ = (
        selector,
        root = document
    ) => root.querySelector(
        selector
    );

    const $$ = (
        selector,
        root = document
    ) => Array.from(
        root.querySelectorAll(
            selector
        )
    );

    function svg(
        name,
        attributes = {}
    ) {
        const element =
            document.createElementNS(
                SVG_NS,
                name
            );

        for (
            const [
                key,
                value
            ]
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

    function text(
        value,
        fallback = ""
    ) {
        if (
            value === null ||
            value === undefined
        ) {
            return fallback;
        }

        const result =
            String(value)
                .trim();

        return result ||
            fallback;
    }

    function first(
        ...values
    ) {
        for (
            const value
            of values
        ) {
            if (
                value !== null &&
                value !== undefined &&
                value !== ""
            ) {
                return value;
            }
        }

        return null;
    }

    function lower(
        value
    ) {
        return text(
            value
        ).toLowerCase();
    }

    function clamp(
        value,
        min,
        max
    ) {
        return Math.min(
            max,
            Math.max(
                min,
                value
            )
        );
    }

    function taskId(
        task
    ) {
        return text(
            first(
                task.id,
                task.task_id,
                task.identity,
                task.key
            )
        );
    }

    function taskTitle(
        task
    ) {
        return text(
            first(
                task.title,
                task.name,
                task.action,
                task.summary,
                taskId(task)
            ),
            "untitled task"
        );
    }

    function taskReady(
        task
    ) {
        const value =
            first(
                task.ready,
                task.is_ready,
                task.readiness
            );

        if (
            typeof value ===
            "boolean"
        ) {
            return value;
        }

        const normalized =
            lower(value);

        return (
            normalized ===
                "ready" ||
            normalized ===
                "true" ||
            normalized ===
                "yes"
        );
    }

    function taskState(
        task
    ) {
        const raw =
            lower(
                first(
                    task.state,
                    task.status,
                    task.lifecycle_state
                )
            );

        if (
            raw.includes(
                "complete"
            ) ||
            raw === "done" ||
            raw === "closed"
        ) {
            return "complete";
        }

        if (
            raw.includes(
                "block"
            ) ||
            raw === "failed"
        ) {
            return "blocked";
        }

        if (
            raw.includes(
                "active"
            ) ||
            raw.includes(
                "progress"
            ) ||
            raw === "started" ||
            raw === "leased"
        ) {
            return "active";
        }

        if (
            taskReady(task)
        ) {
            return "ready";
        }

        return raw ||
            "unknown";
    }

    function taskObjective(
        task
    ) {
        return text(
            first(
                task.objective,
                task.objective_id,
                task.root_objective,
                task.ancestry
                    ?.objective
            ),
            "unknown objective"
        );
    }

    function taskParent(
        task
    ) {
        return text(
            first(
                task.parent,
                task.parent_id,
                task.parent_task_id,
                task.ancestry
                    ?.parent
            )
        );
    }

    function taskDependencies(
        task
    ) {
        const candidate =
            first(
                task.dependencies,
                task.depends_on,
                task.prerequisites,
                task.requires
            );

        if (
            !Array.isArray(
                candidate
            )
        ) {
            return [];
        }

        return candidate
            .map(
                item => {
                    if (
                        typeof item ===
                        "string"
                    ) {
                        return item;
                    }

                    return text(
                        first(
                            item.id,
                            item.task_id,
                            item.key
                        )
                    );
                }
            )
            .filter(Boolean);
    }

    function taskPriority(
        task
    ) {
        return text(
            first(
                task.priority,
                task.authoritative_priority,
                task.rank
            ),
            "unknown"
        );
    }

    function normalizeTask(
        task
    ) {
        const id =
            taskId(task);

        return {
            id,

            title:
                taskTitle(task),

            state:
                taskState(task),

            ready:
                taskReady(task),

            objective:
                taskObjective(task),

            parent:
                taskParent(task),

            dependencies:
                taskDependencies(task),

            priority:
                taskPriority(task),

            raw:
                task
        };
    }

    function escapeHtml(
        value
    ) {
        return text(value)
            .replaceAll(
                "&",
                "&amp;"
            )
            .replaceAll(
                "<",
                "&lt;"
            )
            .replaceAll(
                ">",
                "&gt;"
            )
            .replaceAll(
                '"',
                "&quot;"
            )
            .replaceAll(
                "'",
                "&#039;"
            );
    }

    function installShell() {
        if (
            state.installed
        ) {
            return;
        }

        const nav =
            $(".nav");

        const main =
            $("#main");

        if (
            !nav ||
            !main
        ) {
            return;
        }

        let button =
            nav.querySelector(
                '[data-view="navigation"]'
            );

        if (!button) {
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
                nav.querySelector(
                    '[data-view="causal"]'
                );

            nav.insertBefore(
                button,
                causal || null
            );
        }

        if (
            !$("#surface-navigation")
        ) {
            const section =
                document.createElement(
                    "section"
                );

            section.id =
                "surface-navigation";

            section.className =
                "surface niche-navigation-surface";

            section.dataset.surface =
                "navigation";

            section.setAttribute(
                "aria-labelledby",
                "navigation-heading"
            );

            section.innerHTML =
                buildShellMarkup();

            const causalSurface =
                $(
                    "#surface-causal",
                    main
                );

            main.insertBefore(
                section,
                causalSurface || null
            );
        }

        button.addEventListener(
            "click",
            activateNavigation
        );

        bindControls();

        state.installed =
            true;

        restorePreference();

        window.dispatchEvent(
            new CustomEvent(
                "niche:navigation-ready",
                {
                    detail: {
                        owner:
                            "niche:navigation",

                        authority_effect:
                            "none",

                        projection_only:
                            true
                    }
                }
            )
        );
    }

    function buildShellMarkup() {
        return `
            <header class="navigation-heading">
                <div>
                    <div class="navigation-eyebrow">
                        SAVANT SPATIAL NAVIGATOR
                    </div>

                    <h1 id="navigation-heading">
                        Navigation
                    </h1>

                    <p>
                        Find any represented task, understand where it sits,
                        and navigate through represented structure without
                        changing authoritative state.
                    </p>
                </div>

                <div
                    class="navigation-location"
                    aria-live="polite"
                >
                    <span class="navigation-location-label">
                        YOU ARE HERE
                    </span>

                    <strong
                        id="navigation-location-value"
                        class="navigation-location-value"
                    >
                        Savant / overview
                    </strong>
                </div>
            </header>

            <div class="navigation-commandbar">
                <div class="navigation-search-shell">
                    <input
                        id="navigation-search"
                        class="navigation-input"
                        type="search"
                        autocomplete="off"
                        spellcheck="false"
                        placeholder="Find task, objective, state or id"
                        aria-label="Search Navigation"
                        aria-controls="navigation-search-results"
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
                aria-label="Navigation location"
            >
                <span>
                    Savant
                </span>
            </nav>

            <div class="navigation-shell">
                <div class="navigation-map-column">
                    <div
                        id="navigation-map-frame"
                        class="navigation-map-frame"
                        data-semantic-zoom="medium"
                        data-lens="structure"
                    >
                        <svg
                            id="navigation-map"
                            class="navigation-map"
                            tabindex="0"
                            role="application"
                            aria-label="Interactive Savant topology map"
                            viewBox="0 0 1000 700"
                            preserveAspectRatio="xMidYMid meet"
                        >
                            <defs>
                                <marker
                                    id="navigation-arrow-dependency"
                                    viewBox="0 0 8 8"
                                    refX="7"
                                    refY="4"
                                    markerWidth="6"
                                    markerHeight="6"
                                    orient="auto"
                                >
                                    <path
                                        d="M0 0L8 4L0 8L2 4Z"
                                        fill="#62d3ec"
                                        opacity=".68"
                                    ></path>
                                </marker>
                            </defs>

                            <g
                                id="navigation-world"
                                class="navigation-world"
                            ></g>
                        </svg>

                        <div
                            class="navigation-controls"
                            aria-label="Map controls"
                        >
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
                                aria-label="Fit whole map"
                                title="Fit whole map"
                            >
                                ⌂
                            </button>

                            <button
                                id="navigation-zoom-in"
                                type="button"
                                aria-label="Zoom in"
                                title="Zoom in"
                            >
                                +
                            </button>

                            <button
                                id="navigation-back"
                                type="button"
                                aria-label="Previous map location"
                                title="Previous location"
                            >
                                ‹
                            </button>

                            <button
                                id="navigation-focus"
                                type="button"
                                aria-label="Fit selected location"
                                title="Fit selected location"
                            >
                                ◎
                            </button>

                            <button
                                id="navigation-forward"
                                type="button"
                                aria-label="Next map location"
                                title="Next location"
                            >
                                ›
                            </button>
                        </div>

                        <div
                            class="navigation-zoom-meter"
                            aria-hidden="true"
                        >
                            <span id="navigation-zoom-label">
                                100%
                            </span>

                            <span class="navigation-scale-bar"></span>
                        </div>

                        <div
                            id="navigation-minimap"
                            class="navigation-minimap"
                            aria-hidden="true"
                        ></div>
                    </div>
                </div>

                <aside
                    class="navigation-side"
                    aria-label="Navigation details"
                >
                    <section
                        id="navigation-inspector"
                        class="navigation-panel"
                    >
                        <div class="navigation-eyebrow">
                            LOCATION
                        </div>

                        <h2>
                            Savant overview
                        </h2>

                        <p>
                            Select a represented location on the map.
                        </p>
                    </section>

                    <section class="navigation-panel">
                        <div class="navigation-eyebrow">
                            ROUTE
                        </div>

                        <h3>
                            Navigate to
                        </h3>

                        <div class="navigation-route-shell">
                            <input
                                id="navigation-route-input"
                                class="navigation-input"
                                type="search"
                                autocomplete="off"
                                placeholder="Destination task"
                                aria-label="Route destination"
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
                        >
                            <p>
                                Select your current location, then choose a
                                destination.
                            </p>
                        </div>
                    </section>

                    <section class="navigation-panel">
                        <div class="navigation-eyebrow">
                            MAP STATUS
                        </div>

                        <div
                            id="navigation-stats"
                            class="navigation-stats"
                        ></div>
                    </section>

                    <section class="navigation-panel">
                        <div class="navigation-eyebrow">
                            ACCESSIBLE INDEX
                        </div>

                        <h3>
                            Nearby locations
                        </h3>

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
            ></div>
        `;
    }

    function bindControls() {
        const search =
            $("#navigation-search");

        search.addEventListener(
            "input",
            () => {
                renderSearch(
                    search.value
                );
            }
        );

        search.addEventListener(
            "keydown",
            event => {
                if (
                    event.key ===
                    "Escape"
                ) {
                    closeSearch();
                }
            }
        );

        $("#navigation-lens")
            .addEventListener(
                "change",
                event => {
                    state.lens =
                        event.target.value;

                    const frame =
                        $("#navigation-map-frame");

                    frame.dataset.lens =
                        state.lens;

                    applyVisualFocus();

                    savePreference();
                }
            );

        $("#navigation-status-filter")
            .addEventListener(
                "change",
                event => {
                    state.statusFilter =
                        event.target.value;

                    applyVisualFocus();

                    renderTextIndex();

                    savePreference();
                }
            );

        $("#navigation-isolate")
            .addEventListener(
                "click",
                event => {
                    state.isolate =
                        !state.isolate;

                    event
                        .currentTarget
                        .setAttribute(
                            "aria-pressed",
                            String(
                                state.isolate
                            )
                        );

                    applyVisualFocus();

                    savePreference();
                }
            );

        $("#navigation-zoom-in")
            .addEventListener(
                "click",
                () => {
                    zoomBy(
                        1.28
                    );
                }
            );

        $("#navigation-zoom-out")
            .addEventListener(
                "click",
                () => {
                    zoomBy(
                        1 / 1.28
                    );
                }
            );

        $("#navigation-home")
            .addEventListener(
                "click",
                () => {
                    fitAll(true);
                }
            );

        $("#navigation-focus")
            .addEventListener(
                "click",
                () => {
                    fitSelected(true);
                }
            );

        $("#navigation-back")
            .addEventListener(
                "click",
                navigateBack
            );

        $("#navigation-forward")
            .addEventListener(
                "click",
                navigateForward
            );

        $("#navigation-route-button")
            .addEventListener(
                "click",
                routeFromInput
            );

        $("#navigation-route-input")
            .addEventListener(
                "keydown",
                event => {
                    if (
                        event.key ===
                        "Enter"
                    ) {
                        event
                            .preventDefault();

                        routeFromInput();
                    }
                }
            );

        const map =
            $("#navigation-map");

        map.addEventListener(
            "wheel",
            onWheel,
            {
                passive: false
            }
        );

        map.addEventListener(
            "pointerdown",
            onPointerDown
        );

        map.addEventListener(
            "pointermove",
            onPointerMove
        );

        map.addEventListener(
            "pointerup",
            onPointerUp
        );

        map.addEventListener(
            "pointercancel",
            onPointerUp
        );

        map.addEventListener(
            "keydown",
            onMapKeyDown
        );

        document.addEventListener(
            "click",
            event => {
                if (
                    !event.target.closest(
                        ".navigation-search-shell"
                    )
                ) {
                    closeSearch();
                }
            }
        );
    }

    function activateNavigation() {
        for (
            const surface
            of $$(".surface")
        ) {
            surface.classList
                .toggle(
                    "active",
                    surface.id ===
                        "surface-navigation"
                );
        }

        for (
            const button
            of $$(".nav [data-view]")
        ) {
            const active =
                button.dataset.view ===
                "navigation";

            button.classList
                .toggle(
                    "active",
                    active
                );

            if (active) {
                button.setAttribute(
                    "aria-current",
                    "page"
                );
            } else {
                button.removeAttribute(
                    "aria-current"
                );
            }
        }

        const surface =
            $("#surface-navigation");

        surface.scrollIntoView({
            block:
                "start"
        });

        load();
    }

    async function load(
        force = false
    ) {
        if (
            state.loading
        ) {
            return;
        }

        if (
            state.loaded &&
            !force
        ) {
            scheduleRenderTransform();

            return;
        }

        state.loading =
            true;

        const frame =
            $("#navigation-map-frame");

        frame.setAttribute(
            "aria-busy",
            "true"
        );

        state.fetchController
            ?.abort();

        const controller =
            new AbortController();

        state.fetchController =
            controller;

        try {
            const response =
                await fetch(
                    "/api/tasks?include_terminal=true",
                    {
                        headers: {
                            Accept:
                                "application/json"
                        },

                        cache:
                            "no-store",

                        signal:
                            controller.signal
                    }
                );

            if (
                !response.ok
            ) {
                throw new Error(
                    `task projection unavailable (${response.status})`
                );
            }

            const payload =
                await response.json();

            const candidate =
                Array.isArray(payload)
                    ? payload
                    : first(
                        payload.tasks,
                        payload.items,
                        payload.results,
                        []
                    );

            if (
                !Array.isArray(
                    candidate
                )
            ) {
                throw new Error(
                    "task projection did not contain a represented task array"
                );
            }

            const tasks =
                candidate
                    .map(
                        normalizeTask
                    )
                    .filter(
                        task =>
                            Boolean(
                                task.id
                            )
                    );

            state.tasks =
                tasks;

            buildModel();

            state.loaded =
                true;

            render();

            if (
                state.selectedId &&
                state.nodeById.has(
                    state.selectedId
                )
            ) {
                selectNode(
                    state.selectedId,
                    {
                        navigate:
                            false,

                        fit:
                            false,

                        announce:
                            false
                    }
                );
            } else {
                fitAll(false);
            }

            announce(
                `Navigation loaded ${state.nodes.length} represented locations across ${state.territories.length} objective territories.`
            );
        } catch (error) {
            if (
                error.name ===
                "AbortError"
            ) {
                return;
            }

            renderFailure(
                error.message
            );
        } finally {
            if (
                state.fetchController ===
                controller
            ) {
                state.loading =
                    false;

                frame.removeAttribute(
                    "aria-busy"
                );
            }
        }
    }

    function buildModel() {
        const nodeById =
            new Map();

        for (
            const task
            of state.tasks
        ) {
            nodeById.set(
                task.id,
                {
                    ...task,

                    x: 0,
                    y: 0,

                    width:
                        NODE_WIDTH,

                    height:
                        NODE_HEIGHT,

                    territory:
                        null,

                    children:
                        [],

                    dependents:
                        []
                }
            );
        }

        for (
            const node
            of nodeById.values()
        ) {
            if (
                node.parent &&
                nodeById.has(
                    node.parent
                )
            ) {
                nodeById
                    .get(
                        node.parent
                    )
                    .children
                    .push(
                        node.id
                    );
            }

            for (
                const dependency
                of node.dependencies
            ) {
                if (
                    nodeById.has(
                        dependency
                    )
                ) {
                    nodeById
                        .get(
                            dependency
                        )
                        .dependents
                        .push(
                            node.id
                        );
                }
            }
        }

        const groups =
            new Map();

        for (
            const node
            of nodeById.values()
        ) {
            const key =
                node.objective;

            if (
                !groups.has(key)
            ) {
                groups.set(
                    key,
                    []
                );
            }

            groups
                .get(key)
                .push(node);
        }

        const territoryEntries =
            Array.from(
                groups.entries()
            )
                .sort(
                    (
                        [a],
                        [b]
                    ) =>
                        a.localeCompare(
                            b,
                            undefined,
                            {
                                numeric:
                                    true,

                                sensitivity:
                                    "base"
                            }
                        )
                );

        const territoryColumns =
            Math.max(
                1,
                Math.ceil(
                    Math.sqrt(
                        territoryEntries
                            .length *
                        1.35
                    )
                )
            );

        const territories =
            [];

        let worldHeight =
            WORLD_MARGIN * 2;

        const rowHeights =
            [];

        territoryEntries.forEach(
            (
                [
                    objective,
                    nodes
                ],
                territoryIndex
            ) => {
                nodes.sort(
                    (a, b) => {
                        const parentA =
                            a.parent || "";

                        const parentB =
                            b.parent || "";

                        return (
                            parentA.localeCompare(
                                parentB
                            ) ||
                            a.title.localeCompare(
                                b.title
                            ) ||
                            a.id.localeCompare(
                                b.id
                            )
                        );
                    }
                );

                const internalColumns =
                    clamp(
                        Math.ceil(
                            Math.sqrt(
                                nodes.length *
                                1.8
                            )
                        ),
                        2,
                        5
                    );

                const internalRows =
                    Math.ceil(
                        nodes.length /
                        internalColumns
                    );

                const territoryHeight =
                    TERRITORY_HEADER +
                    72 +
                    internalRows *
                        (
                            NODE_HEIGHT +
                            NODE_GAP_Y
                        );

                const column =
                    territoryIndex %
                    territoryColumns;

                const row =
                    Math.floor(
                        territoryIndex /
                        territoryColumns
                    );

                rowHeights[row] =
                    Math.max(
                        rowHeights[row] ||
                            0,
                        territoryHeight
                    );

                territories.push({
                    id:
                        `territory-${territoryIndex}`,

                    objective,

                    nodes,

                    row,
                    column,

                    width:
                        TERRITORY_WIDTH,

                    height:
                        territoryHeight,

                    x: 0,
                    y: 0,

                    internalColumns
                });
            }
        );

        const rowOffsets =
            [];

        let cursorY =
            WORLD_MARGIN;

        for (
            let row = 0;
            row <
            rowHeights.length;
            row += 1
        ) {
            rowOffsets[row] =
                cursorY;

            cursorY +=
                rowHeights[row] +
                TERRITORY_GAP;
        }

        worldHeight =
            cursorY +
            WORLD_MARGIN -
            TERRITORY_GAP;

        for (
            const territory
            of territories
        ) {
            territory.x =
                WORLD_MARGIN +
                territory.column *
                (
                    TERRITORY_WIDTH +
                    TERRITORY_GAP
                );

            territory.y =
                rowOffsets[
                    territory.row
                ];

            const usableWidth =
                TERRITORY_WIDTH -
                100;

            const columnSpacing =
                territory.internalColumns >
                    1
                    ? (
                        usableWidth -
                        NODE_WIDTH
                    ) /
                    (
                        territory
                            .internalColumns -
                        1
                    )
                    : 0;

            territory.nodes
                .forEach(
                    (
                        node,
                        index
                    ) => {
                        const column =
                            index %
                            territory
                                .internalColumns;

                        const row =
                            Math.floor(
                                index /
                                territory
                                    .internalColumns
                            );

                        node.x =
                            territory.x +
                            50 +
                            column *
                                columnSpacing;

                        node.y =
                            territory.y +
                            TERRITORY_HEADER +
                            48 +
                            row *
                                (
                                    NODE_HEIGHT +
                                    NODE_GAP_Y
                                );

                        node.territory =
                            territory.id;
                    }
                );
        }

        const edges =
            [];

        for (
            const node
            of nodeById.values()
        ) {
            if (
                node.parent &&
                nodeById.has(
                    node.parent
                )
            ) {
                edges.push({
                    id:
                        `edifice:${node.parent}:${node.id}`,

                    type:
                        "edifice",

                    source:
                        node.parent,

                    target:
                        node.id
                });
            }

            for (
                const dependency
                of node.dependencies
            ) {
                if (
                    nodeById.has(
                        dependency
                    )
                ) {
                    edges.push({
                        id:
                            `dependency:${dependency}:${node.id}`,

                        type:
                            "dependency",

                        source:
                            dependency,

                        target:
                            node.id
                    });
                }
            }
        }

        state.nodeById =
            nodeById;

        state.nodes =
            Array.from(
                nodeById.values()
            );

        state.territories =
            territories;

        state.edges =
            edges;

        state.world.width =
            WORLD_MARGIN * 2 +
            territoryColumns *
                TERRITORY_WIDTH +
            Math.max(
                0,
                territoryColumns - 1
            ) *
                TERRITORY_GAP;

        state.world.height =
            Math.max(
                worldHeight,
                1100
            );
    }

    function render() {
        renderMap();
        renderMinimap();
        renderStats();
        renderInspector();
        renderBreadcrumb();
        renderTextIndex();

        applyVisualFocus();

        scheduleRenderTransform();
    }

    function renderMap() {
        const world =
            $("#navigation-world");

        world.replaceChildren();

        const territoryLayer =
            svg(
                "g",
                {
                    class:
                        "nav-territory-layer"
                }
            );

        const edgeLayer =
            svg(
                "g",
                {
                    class:
                        "nav-edge-layer"
                }
            );

        const nodeLayer =
            svg(
                "g",
                {
                    class:
                        "nav-node-layer"
                }
            );

        const interactionLayer =
            svg(
                "g",
                {
                    class:
                        "nav-interaction-layer"
                }
            );

        for (
            const territory
            of state.territories
        ) {
            const group =
                svg(
                    "g",
                    {
                        "data-territory":
                            territory.id
                    }
                );

            const rect =
                svg(
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
                            14,

                        ry:
                            14
                    }
                );

            const band =
                svg(
                    "rect",
                    {
                        class:
                            "nav-territory-band",

                        x:
                            territory.x,

                        y:
                            territory.y,

                        width:
                            territory.width,

                        height:
                            TERRITORY_HEADER,

                        rx:
                            14,

                        ry:
                            14
                    }
                );

            const title =
                svg(
                    "text",
                    {
                        class:
                            "nav-territory-title",

                        x:
                            territory.x +
                            24,

                        y:
                            territory.y +
                            34
                    }
                );

            title.textContent =
                territory.objective;

            const meta =
                svg(
                    "text",
                    {
                        class:
                            "nav-territory-meta",

                        x:
                            territory.x +
                            24,

                        y:
                            territory.y +
                            56
                    }
                );

            meta.textContent =
                `${territory.nodes.length} represented location${territory.nodes.length === 1 ? "" : "s"}`;

            group.append(
                rect,
                band,
                title,
                meta
            );

            territoryLayer.append(
                group
            );
        }

        for (
            const edge
            of state.edges
        ) {
            const source =
                state.nodeById.get(
                    edge.source
                );

            const target =
                state.nodeById.get(
                    edge.target
                );

            if (
                !source ||
                !target
            ) {
                continue;
            }

            const path =
                svg(
                    "path",
                    {
                        class:
                            `nav-edge nav-edge-${edge.type}`,

                        "data-edge-id":
                            edge.id,

                        "data-source":
                            edge.source,

                        "data-target":
                            edge.target,

                        d:
                            edgePath(
                                source,
                                target
                            )
                    }
                );

            if (
                edge.type ===
                "dependency"
            ) {
                path.setAttribute(
                    "marker-end",
                    "url(#navigation-arrow-dependency)"
                );
            }

            edgeLayer.append(
                path
            );
        }

        for (
            const [
                index,
                node
            ]
            of state.nodes.entries()
        ) {
            nodeLayer.append(
                renderNode(
                    node,
                    index
                )
            );
        }

        world.append(
            territoryLayer,
            edgeLayer,
            nodeLayer,
            interactionLayer
        );
    }

    function renderNode(
        node,
        index
    ) {
        const group =
            svg(
                "g",
                {
                    class:
                        `nav-map-node nav-node-state-${node.state}`,

                    tabindex:
                        "0",

                    role:
                        "button",

                    "aria-label":
                        `${node.title}. ${node.state}. Objective ${node.objective}.`,

                    "data-node-id":
                        node.id,

                    transform:
                        `translate(${node.x} ${node.y})`
                }
            );

        const body =
            svg(
                "rect",
                {
                    class:
                        "nav-node-body",

                    width:
                        NODE_WIDTH,

                    height:
                        NODE_HEIGHT,

                    rx:
                        5,

                    ry:
                        5
                }
            );

        const rail =
            svg(
                "rect",
                {
                    class:
                        "nav-node-rail",

                    width:
                        4,

                    height:
                        NODE_HEIGHT,

                    rx:
                        2
                }
            );

        const title =
            svg(
                "text",
                {
                    class:
                        "nav-node-title",

                    x:
                        16,

                    y:
                        23
                }
            );

        title.textContent =
            truncate(
                node.title,
                26
            );

        const meta =
            svg(
                "text",
                {
                    class:
                        "nav-node-meta",

                    x:
                        16,

                    y:
                        43
                }
            );

        meta.textContent =
            `${node.state} · ${node.id}`;

        const ordinal =
            svg(
                "text",
                {
                    class:
                        "nav-node-index",

                    x:
                        NODE_WIDTH -
                        8,

                    y:
                        13,

                    "text-anchor":
                        "end"
                }
            );

        ordinal.textContent =
            String(
                index + 1
            ).padStart(
                3,
                "0"
            );

        group.append(
            body,
            rail,
            title,
            meta,
            ordinal
        );

        group.addEventListener(
            "click",
            event => {
                event.stopPropagation();

                selectNode(
                    node.id,
                    {
                        fit: false
                    }
                );
            }
        );

        group.addEventListener(
            "keydown",
            event => {
                if (
                    event.key ===
                        "Enter" ||
                    event.key ===
                        " "
                ) {
                    event
                        .preventDefault();

                    selectNode(
                        node.id,
                        {
                            fit:
                                false
                        }
                    );
                }
            }
        );

        return group;
    }

    function edgePath(
        source,
        target
    ) {
        const sx =
            source.x +
            NODE_WIDTH / 2;

        const sy =
            source.y +
            NODE_HEIGHT / 2;

        const tx =
            target.x +
            NODE_WIDTH / 2;

        const ty =
            target.y +
            NODE_HEIGHT / 2;

        const horizontal =
            Math.abs(
                tx - sx
            ) >
            Math.abs(
                ty - sy
            );

        if (horizontal) {
            const mx =
                (
                    sx +
                    tx
                ) /
                2;

            return (
                `M${sx},${sy}` +
                ` C${mx},${sy}` +
                ` ${mx},${ty}` +
                ` ${tx},${ty}`
            );
        }

        const my =
            (
                sy +
                ty
            ) /
                2;

        return (
            `M${sx},${sy}` +
            ` C${sx},${my}` +
            ` ${tx},${my}` +
            ` ${tx},${ty}`
        );
    }

    function truncate(
        value,
        length
    ) {
        const normalized =
            text(value);

        if (
            normalized.length <=
            length
        ) {
            return normalized;
        }

        return (
            normalized.slice(
                0,
                Math.max(
                    0,
                    length - 1
                )
            ) +
            "…"
        );
    }

    function renderMinimap() {
        const host =
            $("#navigation-minimap");

        host.replaceChildren();

        const map =
            svg(
                "svg",
                {
                    viewBox:
                        `0 0 ${state.world.width} ${state.world.height}`,

                    preserveAspectRatio:
                        "xMidYMid meet"
                }
            );

        for (
            const territory
            of state.territories
        ) {
            map.append(
                svg(
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

        const viewport =
            svg(
                "rect",
                {
                    id:
                        "navigation-mini-viewport",

                    class:
                        "nav-mini-viewport",

                    x: 0,
                    y: 0,
                    width: 100,
                    height: 100
                }
            );

        map.append(
            viewport
        );

        host.append(
            map
        );

        updateMinimapViewport();
    }

    function renderStats() {
        const host =
            $("#navigation-stats");

        const counts =
            {
                ready: 0,
                active: 0,
                blocked: 0,
                complete: 0,
                unknown: 0
            };

        for (
            const node
            of state.nodes
        ) {
            if (
                Object.prototype
                    .hasOwnProperty
                    .call(
                        counts,
                        node.state
                    )
            ) {
                counts[
                    node.state
                ] += 1;
            } else {
                counts.unknown +=
                    1;
            }
        }

        host.innerHTML = `
            <div class="navigation-stat">
                <strong>
                    ${state.nodes.length}
                </strong>
                <span>LOCATIONS</span>
            </div>

            <div class="navigation-stat">
                <strong>
                    ${state.territories.length}
                </strong>
                <span>TERRITORIES</span>
            </div>

            <div class="navigation-stat">
                <strong>
                    ${counts.ready}
                </strong>
                <span>READY</span>
            </div>

            <div class="navigation-stat">
                <strong>
                    ${counts.blocked}
                </strong>
                <span>BLOCKED</span>
            </div>
        `;
    }

    function selectNode(
        id,
        {
            navigate = true,
            fit = false,
            announce:
                shouldAnnounce = true
        } = {}
    ) {
        const node =
            state.nodeById.get(id);

        if (!node) {
            return;
        }

        state.selectedId =
            id;

        if (navigate) {
            pushHistory(id);
        }

        renderInspector();
        renderBreadcrumb();
        renderTextIndex();

        applyVisualFocus();

        if (fit) {
            fitSelected(true);
        }

        savePreference();

        if (shouldAnnounce) {
            announce(
                `You are here: ${node.title}.`
            );
        }
    }

    function renderInspector() {
        const host =
            $("#navigation-inspector");

        const location =
            $("#navigation-location-value");

        const node =
            state.selectedId
                ? state.nodeById.get(
                    state.selectedId
                )
                : null;

        if (!node) {
            location.textContent =
                "Savant / overview";

            host.innerHTML = `
                <div class="navigation-eyebrow">
                    LOCATION
                </div>

                <h2>
                    Savant overview
                </h2>

                <p>
                    Select a represented location on the map.
                    Map geometry is a navigation projection and
                    does not alter Savant authority.
                </p>
            `;

            return;
        }

        location.textContent =
            node.title;

        const dependencies =
            node.dependencies
                .filter(
                    id =>
                        state.nodeById.has(
                            id
                        )
                );

        const children =
            node.children
                .filter(
                    id =>
                        state.nodeById.has(
                            id
                        )
                );

        const dependents =
            node.dependents
                .filter(
                    id =>
                        state.nodeById.has(
                            id
                        )
                );

        host.innerHTML = `
            <div class="navigation-eyebrow">
                YOU ARE HERE
            </div>

            <h2>
                ${escapeHtml(node.title)}
            </h2>

            <p>
                ${escapeHtml(node.id)}
            </p>

            <dl class="navigation-detail-grid">
                <dt>STATE</dt>
                <dd>
                    ${escapeHtml(node.state)}
                </dd>

                <dt>OBJECTIVE</dt>
                <dd>
                    ${escapeHtml(node.objective)}
                </dd>

                <dt>PRIORITY</dt>
                <dd>
                    ${escapeHtml(node.priority)}
                </dd>

                <dt>PARENT</dt>
                <dd>
                    ${
                        node.parent
                            ? escapeHtml(
                                node.parent
                            )
                            : "not represented"
                    }
                </dd>

                <dt>REQUIRES</dt>
                <dd>
                    ${dependencies.length}
                </dd>

                <dt>DEPENDENTS</dt>
                <dd>
                    ${dependents.length}
                </dd>

                <dt>CHILDREN</dt>
                <dd>
                    ${children.length}
                </dd>
            </dl>

            <div>
                ${dependencies
                    .slice(0, 8)
                    .map(
                        id => `
                            <button
                                type="button"
                                class="navigation-pill"
                                data-nav-jump="${escapeHtml(id)}"
                            >
                                requires:
                                ${escapeHtml(
                                    state.nodeById
                                        .get(id)
                                        ?.title ||
                                    id
                                )}
                            </button>
                        `
                    )
                    .join("")}

                ${dependents
                    .slice(0, 8)
                    .map(
                        id => `
                            <button
                                type="button"
                                class="navigation-pill"
                                data-nav-jump="${escapeHtml(id)}"
                            >
                                leads to:
                                ${escapeHtml(
                                    state.nodeById
                                        .get(id)
                                        ?.title ||
                                    id
                                )}
                            </button>
                        `
                    )
                    .join("")}
            </div>
        `;

        for (
            const button
            of $$(
                "[data-nav-jump]",
                host
            )
        ) {
            button.addEventListener(
                "click",
                () => {
                    selectNode(
                        button.dataset
                            .navJump,

                        {
                            fit: true
                        }
                    );
                }
            );
        }
    }

    function parentChain(
        node
    ) {
        const result =
            [];

        const visited =
            new Set();

        let cursor =
            node;

        while (
            cursor &&
            cursor.parent &&
            state.nodeById.has(
                cursor.parent
            ) &&
            !visited.has(
                cursor.parent
            )
        ) {
            visited.add(
                cursor.parent
            );

            cursor =
                state.nodeById.get(
                    cursor.parent
                );

            result.unshift(
                cursor
            );
        }

        return result;
    }

    function renderBreadcrumb() {
        const host =
            $("#navigation-breadcrumb");

        host.replaceChildren();

        const overview =
            document.createElement(
                "button"
            );

        overview.type =
            "button";

        overview.textContent =
            "Savant";

        overview.addEventListener(
            "click",
            () => {
                state.selectedId =
                    null;

                state.route =
                    [];

                renderInspector();
                renderBreadcrumb();
                applyVisualFocus();
                fitAll(true);
            }
        );

        host.append(
            overview
        );

        const node =
            state.selectedId
                ? state.nodeById.get(
                    state.selectedId
                )
                : null;

        if (!node) {
            return;
        }

        const objective =
            document.createElement(
                "span"
            );

        objective.textContent =
            `› ${node.objective}`;

        host.append(
            objective
        );

        for (
            const ancestor
            of parentChain(node)
        ) {
            const separator =
                document.createElement(
                    "span"
                );

            separator.textContent =
                "›";

            const button =
                document.createElement(
                    "button"
                );

            button.type =
                "button";

            button.textContent =
                ancestor.title;

            button.addEventListener(
                "click",
                () => {
                    selectNode(
                        ancestor.id,
                        {
                            fit: true
                        }
                    );
                }
            );

            host.append(
                separator,
                button
            );
        }

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
            node.title;

        host.append(
            separator,
            current
        );
    }

    function renderTextIndex() {
        const host =
            $("#navigation-text-index");

        const visible =
            getVisibleNodes()
                .slice()
                .sort(
                    (a, b) =>
                        a.title.localeCompare(
                            b.title
                        )
                );

        const selected =
            state.selectedId
                ? state.nodeById.get(
                    state.selectedId
                )
                : null;

        let nodes =
            visible;

        if (selected) {
            const neighborhood =
                neighborhoodIds(
                    selected.id
                );

            const near =
                visible.filter(
                    node =>
                        neighborhood.has(
                            node.id
                        )
                );

            if (near.length) {
                nodes =
                    near;
            }
        }

        host.replaceChildren();

        for (
            const node
            of nodes.slice(
                0,
                30
            )
        ) {
            const button =
                document.createElement(
                    "button"
                );

            button.type =
                "button";

            const strong =
                document.createElement(
                    "strong"
                );

            strong.textContent =
                node.title;

            const small =
                document.createElement(
                    "small"
                );

            small.textContent =
                `${node.state} · ${node.objective}`;

            button.append(
                strong,
                small
            );

            button.addEventListener(
                "click",
                () => {
                    selectNode(
                        node.id,
                        {
                            fit: true
                        }
                    );
                }
            );

            host.append(
                button
            );
        }

        if (!nodes.length) {
            const empty =
                document.createElement(
                    "p"
                );

            empty.textContent =
                "No represented locations match this filter.";

            host.append(
                empty
            );
        }
    }

    function getVisibleNodes() {
        if (
            state.statusFilter ===
            "all"
        ) {
            return state.nodes;
        }

        return state.nodes
            .filter(
                node =>
                    node.state ===
                    state.statusFilter
            );
    }

    function neighborhoodIds(
        id
    ) {
        const result =
            new Set([
                id
            ]);

        const node =
            state.nodeById.get(id);

        if (!node) {
            return result;
        }

        if (
            node.parent &&
            state.nodeById.has(
                node.parent
            )
        ) {
            result.add(
                node.parent
            );
        }

        for (
            const child
            of node.children
        ) {
            result.add(
                child
            );
        }

        for (
            const dependency
            of node.dependencies
        ) {
            if (
                state.nodeById.has(
                    dependency
                )
            ) {
                result.add(
                    dependency
                );
            }
        }

        for (
            const dependent
            of node.dependents
        ) {
            result.add(
                dependent
            );
        }

        return result;
    }

    function applyVisualFocus() {
        const allowedByStatus =
            new Set(
                getVisibleNodes()
                    .map(
                        node =>
                            node.id
                    )
            );

        const neighborhood =
            state.selectedId
                ? neighborhoodIds(
                    state.selectedId
                )
                : new Set();

        const routeIds =
            new Set(
                state.route
            );

        for (
            const element
            of $$(
                ".nav-map-node",
                $("#navigation-world")
            )
        ) {
            const id =
                element.dataset
                    .nodeId;

            const statusAllowed =
                allowedByStatus.has(
                    id
                );

            const isolateAllowed =
                !state.isolate ||
                !state.selectedId ||
                neighborhood.has(id);

            element.classList
                .toggle(
                    "selected",
                    id ===
                        state.selectedId
                );

            element.classList
                .toggle(
                    "route",
                    routeIds.has(id)
                );

            element.classList
                .toggle(
                    "dimmed",
                    !statusAllowed ||
                    !isolateAllowed
                );
        }

        for (
            const edge
            of $$(
                ".nav-edge",
                $("#navigation-world")
            )
        ) {
            const source =
                edge.dataset.source;

            const target =
                edge.dataset.target;

            const related =
                state.selectedId &&
                (
                    source ===
                        state.selectedId ||
                    target ===
                        state.selectedId
                );

            const route =
                isRouteEdge(
                    source,
                    target
                );

            const allowed =
                allowedByStatus.has(
                    source
                ) &&
                allowedByStatus.has(
                    target
                );

            const isolateAllowed =
                !state.isolate ||
                !state.selectedId ||
                (
                    neighborhood.has(
                        source
                    ) &&
                    neighborhood.has(
                        target
                    )
                );

            edge.classList
                .toggle(
                    "related",
                    Boolean(
                        related
                    )
                );

            edge.classList
                .toggle(
                    "route",
                    route
                );

            edge.classList
                .toggle(
                    "dimmed",
                    !route &&
                    (
                        !allowed ||
                        !isolateAllowed
                    )
                );
        }

        renderYouAreHere();
    }

    function isRouteEdge(
        source,
        target
    ) {
        if (
            state.route.length <
            2
        ) {
            return false;
        }

        for (
            let i = 0;
            i <
            state.route.length - 1;
            i += 1
        ) {
            const a =
                state.route[i];

            const b =
                state.route[
                    i + 1
                ];

            if (
                (
                    a === source &&
                    b === target
                ) ||
                (
                    a === target &&
                    b === source
                )
            ) {
                return true;
            }
        }

        return false;
    }

    function renderYouAreHere() {
        const layer =
            $(
                ".nav-interaction-layer",
                $("#navigation-world")
            );

        if (!layer) {
            return;
        }

        layer.replaceChildren();

        if (
            !state.selectedId
        ) {
            return;
        }

        const node =
            state.nodeById.get(
                state.selectedId
            );

        if (!node) {
            return;
        }

        const centerX =
            node.x +
            NODE_WIDTH / 2;

        const centerY =
            node.y +
            NODE_HEIGHT / 2;

        const ring =
            svg(
                "rect",
                {
                    class:
                        "nav-you-are-here",

                    x:
                        node.x - 10,

                    y:
                        node.y - 10,

                    width:
                        NODE_WIDTH + 20,

                    height:
                        NODE_HEIGHT + 20,

                    rx:
                        9
                }
            );

        const outer =
            svg(
                "circle",
                {
                    class:
                        "nav-you-are-here-ring",

                    cx:
                        centerX,

                    cy:
                        centerY,

                    r:
                        Math.max(
                            NODE_WIDTH,
                            NODE_HEIGHT
                        ) /
                            1.55
                }
            );

        const label =
            svg(
                "text",
                {
                    class:
                        "nav-you-are-here-text",

                    x:
                        centerX,

                    y:
                        node.y - 18,

                    "text-anchor":
                        "middle"
                }
            );

        label.textContent =
            "YOU ARE HERE";

        layer.append(
            outer,
            ring,
            label
        );
    }

    function renderSearch(
        query
    ) {
        const host =
            $("#navigation-search-results");

        const normalized =
            lower(query);

        if (
            normalized.length <
            2
        ) {
            closeSearch();

            return;
        }

        const tokens =
            normalized
                .split(/\s+/)
                .filter(Boolean);

        const matches =
            state.nodes
                .map(
                    node => {
                        const haystack =
                            lower(
                                [
                                    node.title,
                                    node.id,
                                    node.objective,
                                    node.state,
                                    node.priority
                                ].join(" ")
                            );

                        const matched =
                            tokens.every(
                                token =>
                                    haystack.includes(
                                        token
                                    )
                            );

                        if (!matched) {
                            return null;
                        }

                        let score = 0;

                        if (
                            lower(
                                node.title
                            ).startsWith(
                                normalized
                            )
                        ) {
                            score += 20;
                        }

                        if (
                            lower(
                                node.id
                            ) ===
                            normalized
                        ) {
                            score += 30;
                        }

                        if (
                            haystack.includes(
                                normalized
                            )
                        ) {
                            score += 10;
                        }

                        return {
                            node,
                            score
                        };
                    }
                )
                .filter(Boolean)
                .sort(
                    (a, b) =>
                        b.score -
                            a.score ||
                        a.node.title
                            .localeCompare(
                                b.node.title
                            )
                )
                .slice(
                    0,
                    12
                );

        host.replaceChildren();

        for (
            const match
            of matches
        ) {
            const button =
                document.createElement(
                    "button"
                );

            button.type =
                "button";

            button.className =
                "navigation-result";

            button.setAttribute(
                "role",
                "option"
            );

            const strong =
                document.createElement(
                    "strong"
                );

            strong.textContent =
                match.node.title;

            const small =
                document.createElement(
                    "small"
                );

            small.textContent =
                `${match.node.state} · ${match.node.objective}`;

            button.append(
                strong,
                small
            );

            button.addEventListener(
                "click",
                () => {
                    selectNode(
                        match.node.id,
                        {
                            fit: true
                        }
                    );

                    $("#navigation-search")
                        .value =
                        match.node.title;

                    closeSearch();
                }
            );

            host.append(
                button
            );
        }

        if (
            !matches.length
        ) {
            const empty =
                document.createElement(
                    "div"
                );

            empty.className =
                "navigation-result";

            empty.textContent =
                "No represented location matches this search.";

            host.append(
                empty
            );
        }

        host.classList
            .add(
                "open"
            );
    }

    function closeSearch() {
        $("#navigation-search-results")
            ?.classList
            .remove(
                "open"
            );
    }

    function findDestination(
        query
    ) {
        const normalized =
            lower(query);

        if (!normalized) {
            return null;
        }

        const exact =
            state.nodes.find(
                node =>
                    lower(
                        node.id
                    ) ===
                        normalized ||
                    lower(
                        node.title
                    ) ===
                        normalized
            );

        if (exact) {
            return exact;
        }

        return (
            state.nodes.find(
                node =>
                    lower(
                        node.title
                    ).includes(
                        normalized
                    )
            ) ||
            state.nodes.find(
                node =>
                    lower(
                        node.id
                    ).includes(
                        normalized
                    )
            ) ||
            null
        );
    }

    function routeFromInput() {
        const source =
            state.selectedId
                ? state.nodeById.get(
                    state.selectedId
                )
                : null;

        if (!source) {
            renderRouteMessage(
                "Select your current location first."
            );

            return;
        }

        const query =
            $("#navigation-route-input")
                .value;

        const destination =
            findDestination(
                query
            );

        if (!destination) {
            renderRouteMessage(
                "No represented destination matches that value."
            );

            return;
        }

        const route =
            shortestRepresentedRoute(
                source.id,
                destination.id
            );

        state.routeDestination =
            destination.id;

        state.route =
            route;

        renderRoute();
        applyVisualFocus();

        if (route.length) {
            fitRoute(
                route,
                true
            );
        }
    }

    function adjacency() {
        const map =
            new Map();

        for (
            const node
            of state.nodes
        ) {
            map.set(
                node.id,
                new Set()
            );
        }

        for (
            const edge
            of state.edges
        ) {
            if (
                !map.has(
                    edge.source
                ) ||
                !map.has(
                    edge.target
                )
            ) {
                continue;
            }

            map.get(
                edge.source
            ).add(
                edge.target
            );

            /*
             * Navigation routes are structural
             * traversal routes, not execution-order
             * claims, so represented relationships
             * are traversable in either direction.
             */
            map.get(
                edge.target
            ).add(
                edge.source
            );
        }

        return map;
    }

    function shortestRepresentedRoute(
        source,
        destination
    ) {
        if (
            source ===
            destination
        ) {
            return [
                source
            ];
        }

        const graph =
            adjacency();

        const queue =
            [
                source
            ];

        const previous =
            new Map([
                [
                    source,
                    null
                ]
            ]);

        while (
            queue.length
        ) {
            const current =
                queue.shift();

            for (
                const next
                of graph.get(
                    current
                ) || []
            ) {
                if (
                    previous.has(
                        next
                    )
                ) {
                    continue;
                }

                previous.set(
                    next,
                    current
                );

                if (
                    next ===
                    destination
                ) {
                    const result =
                        [
                            destination
                        ];

                    let cursor =
                        current;

                    while (
                        cursor
                    ) {
                        result.push(
                            cursor
                        );

                        cursor =
                            previous.get(
                                cursor
                            );
                    }

                    return result
                        .reverse();
                }

                queue.push(
                    next
                );
            }
        }

        return [];
    }

    function renderRoute() {
        const host =
            $("#navigation-route");

        if (
            !state.route.length
        ) {
            renderRouteMessage(
                "No represented structural route was found."
            );

            return;
        }

        host.replaceChildren();

        state.route
            .forEach(
                (
                    id,
                    index
                ) => {
                    const node =
                        state.nodeById.get(
                            id
                        );

                    if (!node) {
                        return;
                    }

                    const step =
                        document.createElement(
                            "button"
                        );

                    step.type =
                        "button";

                    step.className =
                        "navigation-route-step";

                    const number =
                        document.createElement(
                            "span"
                        );

                    number.className =
                        "navigation-route-step-number";

                    number.textContent =
                        String(
                            index + 1
                        );

                    const body =
                        document.createElement(
                            "span"
                        );

                    const strong =
                        document.createElement(
                            "strong"
                        );

                    strong.textContent =
                        node.title;

                    const small =
                        document.createElement(
                            "small"
                        );

                    small.textContent =
                        `${node.state} · ${node.objective}`;

                    body.append(
                        strong,
                        small
                    );

                    step.append(
                        number,
                        body
                    );

                    step.addEventListener(
                        "click",
                        () => {
                            selectNode(
                                id,
                                {
                                    fit:
                                        true
                                }
                            );
                        }
                    );

                    host.append(
                        step
                    );
                }
            );

        announce(
            `Represented route contains ${state.route.length} locations.`
        );
    }

    function renderRouteMessage(
        message
    ) {
        $("#navigation-route")
            .innerHTML =
            `<p>${escapeHtml(message)}</p>`;
    }

    function pushHistory(
        id
    ) {
        if (
            state.history[
                state.historyIndex
            ] === id
        ) {
            return;
        }

        state.history =
            state.history.slice(
                0,
                state.historyIndex +
                    1
            );

        state.history.push(
            id
        );

        if (
            state.history.length >
            50
        ) {
            state.history.shift();
        }

        state.historyIndex =
            state.history.length -
            1;
    }

    function navigateBack() {
        if (
            state.historyIndex <=
            0
        ) {
            return;
        }

        state.historyIndex -=
            1;

        selectNode(
            state.history[
                state.historyIndex
            ],
            {
                navigate:
                    false,

                fit:
                    true
            }
        );
    }

    function navigateForward() {
        if (
            state.historyIndex >=
            state.history.length -
                1
        ) {
            return;
        }

        state.historyIndex +=
            1;

        selectNode(
            state.history[
                state.historyIndex
            ],
            {
                navigate:
                    false,

                fit:
                    true
            }
        );
    }

    function zoomBy(
        factor,
        clientX = null,
        clientY = null
    ) {
        const frame =
            $("#navigation-map-frame");

        const rect =
            frame
                .getBoundingClientRect();

        const cx =
            clientX ??
            (
                rect.left +
                rect.width /
                    2
            );

        const cy =
            clientY ??
            (
                rect.top +
                rect.height /
                    2
            );

        zoomAt(
            cx,
            cy,
            state.transform.k *
                factor
        );
    }

    function zoomAt(
        clientX,
        clientY,
        nextScale
    ) {
        const frame =
            $("#navigation-map-frame");

        const rect =
            frame
                .getBoundingClientRect();

        const nextK =
            clamp(
                nextScale,
                MIN_SCALE,
                MAX_SCALE
            );

        const localX =
            clientX -
            rect.left;

        const localY =
            clientY -
            rect.top;

        const worldX =
            (
                localX -
                state.transform.x
            ) /
            state.transform.k;

        const worldY =
            (
                localY -
                state.transform.y
            ) /
            state.transform.k;

        state.transform.x =
            localX -
            worldX *
                nextK;

        state.transform.y =
            localY -
            worldY *
                nextK;

        state.transform.k =
            nextK;

        scheduleRenderTransform();
    }

    function onWheel(
        event
    ) {
        event.preventDefault();

        const factor =
            Math.exp(
                -event.deltaY *
                .0014
            );

        zoomAt(
            event.clientX,
            event.clientY,
            state.transform.k *
                factor
        );
    }

    function onPointerDown(
        event
    ) {
        const map =
            $("#navigation-map");

        map.setPointerCapture(
            event.pointerId
        );

        state.pointers.set(
            event.pointerId,
            {
                x:
                    event.clientX,

                y:
                    event.clientY
            }
        );

        if (
            state.pointers.size ===
            1
        ) {
            state.drag = {
                pointerId:
                    event.pointerId,

                x:
                    event.clientX,

                y:
                    event.clientY,

                originX:
                    state.transform.x,

                originY:
                    state.transform.y
            };

            state.pinch =
                null;
        } else if (
            state.pointers.size ===
            2
        ) {
            const points =
                Array.from(
                    state.pointers
                        .values()
                );

            state.pinch = {
                distance:
                    pointerDistance(
                        points[0],
                        points[1]
                    ),

                scale:
                    state.transform.k,

                center:
                    pointerCenter(
                        points[0],
                        points[1]
                    )
            };

            state.drag =
                null;
        }
    }

    function onPointerMove(
        event
    ) {
        if (
            !state.pointers.has(
                event.pointerId
            )
        ) {
            return;
        }

        state.pointers.set(
            event.pointerId,
            {
                x:
                    event.clientX,

                y:
                    event.clientY
            }
        );

        if (
            state.pointers.size ===
            1 &&
            state.drag &&
            state.drag.pointerId ===
                event.pointerId
        ) {
            state.transform.x =
                state.drag.originX +
                (
                    event.clientX -
                    state.drag.x
                );

            state.transform.y =
                state.drag.originY +
                (
                    event.clientY -
                    state.drag.y
                );

            scheduleRenderTransform();

            return;
        }

        if (
            state.pointers.size ===
            2
        ) {
            const points =
                Array.from(
                    state.pointers
                        .values()
                );

            const distance =
                pointerDistance(
                    points[0],
                    points[1]
                );

            const center =
                pointerCenter(
                    points[0],
                    points[1]
                );

            if (!state.pinch) {
                state.pinch = {
                    distance,

                    scale:
                        state.transform.k,

                    center
                };

                return;
            }

            const ratio =
                distance /
                Math.max(
                    1,
                    state.pinch
                        .distance
                );

            zoomAt(
                center.x,
                center.y,
                state.pinch.scale *
                    ratio
            );
        }
    }

    function onPointerUp(
        event
    ) {
        state.pointers.delete(
            event.pointerId
        );

        if (
            state.pointers.size <
            2
        ) {
            state.pinch =
                null;
        }

        if (
            state.pointers.size ===
            0
        ) {
            state.drag =
                null;

            savePreference();
        }
    }

    function pointerDistance(
        a,
        b
    ) {
        return Math.hypot(
            b.x - a.x,
            b.y - a.y
        );
    }

    function pointerCenter(
        a,
        b
    ) {
        return {
            x:
                (
                    a.x +
                    b.x
                ) /
                2,

            y:
                (
                    a.y +
                    b.y
                ) /
                2
        };
    }

    function onMapKeyDown(
        event
    ) {
        if (
            event.target.closest(
                "input, select, textarea"
            )
        ) {
            return;
        }

        if (
            event.key === "+" ||
            event.key === "="
        ) {
            event
                .preventDefault();

            zoomBy(
                1.25
            );

            return;
        }

        if (
            event.key === "-"
        ) {
            event
                .preventDefault();

            zoomBy(
                .8
            );

            return;
        }

        if (
            event.key === "0"
        ) {
            event
                .preventDefault();

            fitAll(true);

            return;
        }

        if (
            event.key === "f" ||
            event.key === "F"
        ) {
            if (
                state.selectedId
            ) {
                event
                    .preventDefault();

                fitSelected(true);
            }

            return;
        }

        if (
            [
                "ArrowUp",
                "ArrowDown",
                "ArrowLeft",
                "ArrowRight"
            ].includes(
                event.key
            )
        ) {
            event
                .preventDefault();

            navigateSpatially(
                event.key
            );
        }
    }

    function navigateSpatially(
        direction
    ) {
        if (
            !state.nodes.length
        ) {
            return;
        }

        let current =
            state.selectedId
                ? state.nodeById.get(
                    state.selectedId
                )
                : state.nodes[0];

        if (!current) {
            return;
        }

        const origin = {
            x:
                current.x +
                NODE_WIDTH /
                    2,

            y:
                current.y +
                NODE_HEIGHT /
                    2
        };

        let best =
            null;

        let bestScore =
            Infinity;

        for (
            const candidate
            of getVisibleNodes()
        ) {
            if (
                candidate.id ===
                current.id
            ) {
                continue;
            }

            const target = {
                x:
                    candidate.x +
                    NODE_WIDTH /
                        2,

                y:
                    candidate.y +
                    NODE_HEIGHT /
                        2
            };

            const dx =
                target.x -
                origin.x;

            const dy =
                target.y -
                origin.y;

            const valid =
                (
                    direction ===
                        "ArrowRight" &&
                    dx > 0 &&
                    Math.abs(dx) >=
                        Math.abs(dy) *
                        .35
                ) ||
                (
                    direction ===
                        "ArrowLeft" &&
                    dx < 0 &&
                    Math.abs(dx) >=
                        Math.abs(dy) *
                        .35
                ) ||
                (
                    direction ===
                        "ArrowDown" &&
                    dy > 0 &&
                    Math.abs(dy) >=
                        Math.abs(dx) *
                        .35
                ) ||
                (
                    direction ===
                        "ArrowUp" &&
                    dy < 0 &&
                    Math.abs(dy) >=
                        Math.abs(dx) *
                        .35
                );

            if (!valid) {
                continue;
            }

            const distance =
                Math.hypot(
                    dx,
                    dy
                );

            const axisPenalty =
                (
                    direction ===
                        "ArrowLeft" ||
                    direction ===
                        "ArrowRight"
                )
                    ? Math.abs(dy) *
                        .65
                    : Math.abs(dx) *
                        .65;

            const score =
                distance +
                axisPenalty;

            if (
                score <
                bestScore
            ) {
                best =
                    candidate;

                bestScore =
                    score;
            }
        }

        if (best) {
            selectNode(
                best.id,
                {
                    fit: false
                }
            );

            const element =
                $(
                    `[data-node-id="${CSS.escape(best.id)}"]`,
                    $("#navigation-world")
                );

            element?.focus();
        }
    }

    function scheduleRenderTransform() {
        if (
            state.renderScheduled
        ) {
            return;
        }

        state.renderScheduled =
            true;

        requestAnimationFrame(
            () => {
                state.renderScheduled =
                    false;

                renderTransform();
            }
        );
    }

    function renderTransform() {
        const world =
            $("#navigation-world");

        if (!world) {
            return;
        }

        world.setAttribute(
            "transform",
            `translate(${state.transform.x} ${state.transform.y}) scale(${state.transform.k})`
        );

        const frame =
            $("#navigation-map-frame");

        frame.dataset.semanticZoom =
            state.transform.k <
                .42
                ? "far"
                : state.transform.k <
                    .95
                    ? "medium"
                    : "near";

        $("#navigation-zoom-label")
            .textContent =
            `${Math.round(state.transform.k * 100)}%`;

        updateMinimapViewport();
    }

    function fitAll(
        persist = true
    ) {
        const frame =
            $("#navigation-map-frame");

        if (
            !frame ||
            !state.world.width ||
            !state.world.height
        ) {
            return;
        }

        const rect =
            frame
                .getBoundingClientRect();

        const padding =
            36;

        const scale =
            clamp(
                Math.min(
                    (
                        rect.width -
                        padding * 2
                    ) /
                        state.world.width,

                    (
                        rect.height -
                        padding * 2
                    ) /
                        state.world.height
                ),
                MIN_SCALE,
                1
            );

        state.transform.k =
            scale;

        state.transform.x =
            (
                rect.width -
                state.world.width *
                    scale
            ) /
                2;

        state.transform.y =
            (
                rect.height -
                state.world.height *
                    scale
            ) /
                2;

        scheduleRenderTransform();

        if (persist) {
            savePreference();
        }
    }

    function fitSelected(
        persist = true
    ) {
        const node =
            state.selectedId
                ? state.nodeById.get(
                    state.selectedId
                )
                : null;

        if (!node) {
            fitAll(
                persist
            );

            return;
        }

        fitBounds(
            {
                x:
                    node.x - 160,

                y:
                    node.y - 150,

                width:
                    NODE_WIDTH + 320,

                height:
                    NODE_HEIGHT + 300
            },
            persist
        );
    }

    function fitRoute(
        route,
        persist = true
    ) {
        const nodes =
            route
                .map(
                    id =>
                        state.nodeById.get(
                            id
                        )
                )
                .filter(Boolean);

        if (!nodes.length) {
            return;
        }

        const minX =
            Math.min(
                ...nodes.map(
                    node =>
                        node.x
                )
            );

        const minY =
            Math.min(
                ...nodes.map(
                    node =>
                        node.y
                )
            );

        const maxX =
            Math.max(
                ...nodes.map(
                    node =>
                        node.x +
                        NODE_WIDTH
                )
            );

        const maxY =
            Math.max(
                ...nodes.map(
                    node =>
                        node.y +
                        NODE_HEIGHT
                )
            );

        fitBounds(
            {
                x:
                    minX - 120,

                y:
                    minY - 120,

                width:
                    maxX -
                    minX +
                    240,

                height:
                    maxY -
                    minY +
                    240
            },
            persist
        );
    }

    function fitBounds(
        bounds,
        persist = true
    ) {
        const frame =
            $("#navigation-map-frame");

        const rect =
            frame
                .getBoundingClientRect();

        const scale =
            clamp(
                Math.min(
                    rect.width /
                        bounds.width,

                    rect.height /
                        bounds.height
                ) *
                    .86,
                MIN_SCALE,
                MAX_SCALE
            );

        state.transform.k =
            scale;

        state.transform.x =
            (
                rect.width -
                bounds.width *
                    scale
            ) /
                2 -
            bounds.x *
                scale;

        state.transform.y =
            (
                rect.height -
                bounds.height *
                    scale
            ) /
                2 -
            bounds.y *
                scale;

        scheduleRenderTransform();

        if (persist) {
            savePreference();
        }
    }

    function updateMinimapViewport() {
        const viewport =
            $("#navigation-mini-viewport");

        const frame =
            $("#navigation-map-frame");

        if (
            !viewport ||
            !frame ||
            !state.transform.k
        ) {
            return;
        }

        const rect =
            frame
                .getBoundingClientRect();

        const x =
            -state.transform.x /
            state.transform.k;

        const y =
            -state.transform.y /
            state.transform.k;

        const width =
            rect.width /
            state.transform.k;

        const height =
            rect.height /
            state.transform.k;

        viewport.setAttribute(
            "x",
            String(x)
        );

        viewport.setAttribute(
            "y",
            String(y)
        );

        viewport.setAttribute(
            "width",
            String(width)
        );

        viewport.setAttribute(
            "height",
            String(height)
        );
    }

    function renderFailure(
        message
    ) {
        const frame =
            $("#navigation-map-frame");

        frame.innerHTML = `
            <div class="navigation-error">
                <strong>
                    Navigation projection unavailable
                </strong>

                <p>
                    ${escapeHtml(message)}
                </p>

                <p>
                    This does not change authoritative Savant state.
                </p>
            </div>
        `;
    }

    function announce(
        message
    ) {
        const live =
            $("#navigation-live");

        if (!live) {
            return;
        }

        live.textContent =
            "";

        requestAnimationFrame(
            () => {
                live.textContent =
                    message;
            }
        );
    }

    function savePreference() {
        try {
            localStorage.setItem(
                STORAGE_KEY,
                JSON.stringify({
                    selectedId:
                        state.selectedId,

                    lens:
                        state.lens,

                    statusFilter:
                        state.statusFilter,

                    isolate:
                        state.isolate,

                    transform:
                        state.transform
                })
            );
        } catch {
            return;
        }
    }

    function restorePreference() {
        try {
            const raw =
                localStorage.getItem(
                    STORAGE_KEY
                );

            if (!raw) {
                return;
            }

            const value =
                JSON.parse(raw);

            if (
                typeof value.selectedId ===
                "string"
            ) {
                state.selectedId =
                    value.selectedId;
            }

            if (
                [
                    "structure",
                    "dependencies",
                    "objectives",
                    "status"
                ].includes(
                    value.lens
                )
            ) {
                state.lens =
                    value.lens;
            }

            if (
                [
                    "all",
                    "ready",
                    "active",
                    "blocked",
                    "complete",
                    "unknown"
                ].includes(
                    value.statusFilter
                )
            ) {
                state.statusFilter =
                    value.statusFilter;
            }

            state.isolate =
                value.isolate ===
                true;

            const transform =
                value.transform;

            if (
                transform &&
                Number.isFinite(
                    transform.x
                ) &&
                Number.isFinite(
                    transform.y
                ) &&
                Number.isFinite(
                    transform.k
                )
            ) {
                state.transform = {
                    x:
                        transform.x,

                    y:
                        transform.y,

                    k:
                        clamp(
                            transform.k,
                            MIN_SCALE,
                            MAX_SCALE
                        )
                };
            }

            const lens =
                $("#navigation-lens");

            const filter =
                $("#navigation-status-filter");

            const isolate =
                $("#navigation-isolate");

            if (lens) {
                lens.value =
                    state.lens;
            }

            if (filter) {
                filter.value =
                    state.statusFilter;
            }

            if (isolate) {
                isolate.setAttribute(
                    "aria-pressed",
                    String(
                        state.isolate
                    )
                );
            }

            const frame =
                $("#navigation-map-frame");

            if (frame) {
                frame.dataset.lens =
                    state.lens;
            }
        } catch {
            return;
        }
    }

    function start() {
        installShell();

        window.addEventListener(
            "niche:frontend-ready",
            installShell
        );
    }

    if (
        document.readyState ===
        "loading"
    ) {
        document.addEventListener(
            "DOMContentLoaded",
            start,
            {
                once: true
            }
        );
    } else {
        start();
    }

    window.NicheNavigation =
        Object.freeze({
            open:
                activateNavigation,

            reload() {
                return load(
                    true
                );
            },

            select(id) {
                if (
                    !state.loaded
                ) {
                    activateNavigation();

                    const wait =
                        setInterval(
                            () => {
                                if (
                                    state.loaded
                                ) {
                                    clearInterval(
                                        wait
                                    );

                                    selectNode(
                                        id,
                                        {
                                            fit:
                                                true
                                        }
                                    );
                                }
                            },
                            50
                        );

                    setTimeout(
                        () => {
                            clearInterval(
                                wait
                            );
                        },
                        8000
                    );

                    return;
                }

                selectNode(
                    id,
                    {
                        fit: true
                    }
                );
            },

            state() {
                return {
                    loaded:
                        state.loaded,

                    taskCount:
                        state.nodes.length,

                    territoryCount:
                        state.territories
                            .length,

                    selectedId:
                        state.selectedId,

                    lens:
                        state.lens,

                    statusFilter:
                        state.statusFilter,

                    isolate:
                        state.isolate,

                    routeLength:
                        state.route.length,

                    authorityEffect:
                        "none",

                    projectionOnly:
                        true
                };
            }
        });
})();
