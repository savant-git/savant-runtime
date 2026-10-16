(() => {
    "use strict";

    const SCHEMA =
        "savant.niche.graphics.v1";

    const SVG_NS =
        "http://www.w3.org/2000/svg";

    const runtime = {
        initialized: false,
        generation: 0,
        controller: null,
        tasks: [],
        selectedTaskId: null,
        living: null,
        observer: null,
        refreshTimer: null
    };

    const array = value =>
        Array.isArray(value)
            ? value
            : [];

    const represented = value =>
        value !== null &&
        value !== undefined &&
        value !== "";

    const first = (object, keys) => {
        for (const key of keys) {
            if (
                object &&
                Object.prototype.hasOwnProperty.call(
                    object,
                    key
                ) &&
                represented(object[key])
            ) {
                return object[key];
            }
        }

        return null;
    };

    const idOf = value => {
        if (
            typeof value === "string" &&
            value
        ) {
            return value;
        }

        if (
            value &&
            typeof value === "object"
        ) {
            const id =
                first(
                    value,
                    [
                        "task_id",
                        "taskId",
                        "id"
                    ]
                );

            return (
                typeof id === "string" &&
                id
                    ? id
                    : null
            );
        }

        return null;
    };

    const idsOf = values =>
        [...new Set(
            array(values)
                .map(idOf)
                .filter(Boolean)
        )];

    const taskId = task =>
        idOf(task);

    const stateOf = task =>
        String(
            first(
                task,
                ["state", "status"]
            ) || ""
        ).toLowerCase();

    const readinessOf = task =>
        first(
            task,
            [
                "readiness",
                "ready",
                "is_ready"
            ]
        );

    const blockersOf = task =>
        idsOf(task?.blockers);

    const unsatisfiedOf = task =>
        idsOf(
            task?.unsatisfied_dependencies
        );

    const dependentsOf = task =>
        idsOf(task?.dependents);

    const dependenciesOf = task =>
        idsOf(task?.dependencies);

    const currentTaskId = () => {
        let state = {};

        try {
            state =
                window.Niche?.state?.() ||
                {};
        } catch {
            state = {};
        }

        return (
            state.selectedTaskId ||
            state.recommendedTaskId ||
            runtime.selectedTaskId ||
            null
        );
    };

    const svg = (
        tag,
        attributes = {}
    ) => {
        const element =
            document.createElementNS(
                SVG_NS,
                tag
            );

        Object.entries(attributes)
            .forEach(
                ([key, value]) => {
                    if (
                        value !== null &&
                        value !== undefined
                    ) {
                        element.setAttribute(
                            key,
                            String(value)
                        );
                    }
                }
            );

        return element;
    };

    const fetchJson = async (
        url,
        controller
    ) => {
        try {
            const response =
                await fetch(
                    url,
                    {
                        signal:
                            controller.signal,
                        cache: "no-store",
                        headers: {
                            Accept:
                                "application/json"
                        }
                    }
                );

            if (!response.ok) {
                return null;
            }

            return await response.json();
        } catch (error) {
            if (
                error?.name ===
                "AbortError"
            ) {
                return null;
            }

            return null;
        }
    };

    const normalizeTasks = payload => {
        if (Array.isArray(payload)) {
            return payload;
        }

        for (
            const key of [
                "tasks",
                "items",
                "results"
            ]
        ) {
            if (
                Array.isArray(
                    payload?.[key]
                )
            ) {
                return payload[key];
            }
        }

        return [];
    };

    const classify = task => {
        const state =
            stateOf(task);

        const readiness =
            readinessOf(task);

        if (
            blockersOf(task).length ||
            unsatisfiedOf(task).length ||
            state === "blocked"
        ) {
            return "blocked";
        }

        if (
            readiness === true ||
            String(readiness)
                .toLowerCase() ===
                "ready"
        ) {
            return "ready";
        }

        if (
            [
                "complete",
                "completed",
                "done",
                "active",
                "started",
                "in_progress",
                "in-progress",
                "running"
            ].includes(state)
        ) {
            return "established";
        }

        return "future";
    };

    const installGraphicContainer = (
        parent,
        className,
        before = null
    ) => {
        let element =
            parent.querySelector(
                `:scope > .${className}`
            );

        if (element) {
            return element;
        }

        element =
            document.createElement("div");

        element.className =
            className;

        if (before) {
            parent.insertBefore(
                element,
                before
            );
        } else {
            parent.append(element);
        }

        return element;
    };

    const renderFrontier = () => {
        const host =
            document.getElementById(
                "frontier-track"
            );

        if (!host) {
            return;
        }

        host.textContent = "";

        const wrapper =
            document.createElement("div");

        wrapper.className =
            "niche-frontier-graphic";

        const canvas =
            svg(
                "svg",
                {
                    class:
                        "niche-frontier-svg niche-graphic-layer",
                    viewBox:
                        "0 0 1000 76",
                    preserveAspectRatio:
                        "none",
                    "aria-hidden":
                        "true"
                }
            );

        [
            {
                x: 0,
                width: 330,
                className:
                    "niche-frontier-zone-established"
            },
            {
                x: 330,
                width: 340,
                className:
                    "niche-frontier-zone-ready"
            },
            {
                x: 670,
                width: 330,
                className:
                    "niche-frontier-zone-future"
            }
        ].forEach(zone => {
            canvas.append(
                svg(
                    "rect",
                    {
                        x: zone.x,
                        y: 0,
                        width:
                            zone.width,
                        height: 76,
                        class:
                            `niche-frontier-zone ${zone.className}`
                    }
                )
            );
        });

        canvas.append(
            svg(
                "line",
                {
                    x1: 0,
                    y1: 38,
                    x2: 1000,
                    y2: 38,
                    class:
                        "niche-frontier-axis"
                }
            )
        );

        [330, 670].forEach(x => {
            canvas.append(
                svg(
                    "line",
                    {
                        x1: x,
                        y1: 6,
                        x2: x,
                        y2: 70,
                        class:
                            "niche-frontier-boundary"
                    }
                )
            );
        });

        const groups = {
            established: [],
            ready: [],
            blocked: [],
            future: []
        };

        runtime.tasks.forEach(task => {
            groups[
                classify(task)
            ].push(task);
        });

        const zones = {
            established: [25, 305],
            ready: [355, 645],
            blocked: [355, 645],
            future: [695, 975]
        };

        Object.entries(groups)
            .forEach(
                ([kind, tasks]) => {
                    const [
                        minX,
                        maxX
                    ] = zones[kind];

                    const count =
                        Math.max(
                            tasks.length,
                            1
                        );

                    tasks.forEach(
                        (task, index) => {
                            const id =
                                taskId(task);

                            const x =
                                tasks.length === 1
                                    ? (
                                        minX +
                                        maxX
                                    ) / 2
                                    : (
                                        minX +
                                        (
                                            (
                                                maxX -
                                                minX
                                            ) *
                                            index
                                        ) /
                                        (
                                            count -
                                            1
                                        )
                                    );

                            const y =
                                38 +
                                (
                                    (
                                        index %
                                        3
                                    ) -
                                    1
                                ) *
                                13;

                            const node =
                                svg(
                                    "circle",
                                    {
                                        cx: x,
                                        cy: y,
                                        r:
                                            kind ===
                                            "ready"
                                                ? 5
                                                : 4,
                                        class:
                                            `niche-frontier-node niche-frontier-node-${kind}`
                                    }
                                );

                            canvas.append(node);

                            if (
                                id &&
                                id ===
                                currentTaskId()
                            ) {
                                canvas.append(
                                    svg(
                                        "circle",
                                        {
                                            cx: x,
                                            cy: y,
                                            r: 10,
                                            class:
                                                "niche-frontier-current-ring"
                                        }
                                    )
                                );
                            }
                        }
                    );
                }
            );

        wrapper.append(canvas);
        host.append(wrapper);
    };

    const renderBlockerRadar = () => {
        const list =
            document.getElementById(
                "blocker-list"
            );

        const panel =
            list?.closest(
                ".metric-panel"
            );

        if (!list || !panel) {
            return;
        }

        const host =
            installGraphicContainer(
                panel,
                "niche-blocker-graphic",
                list
            );

        host.textContent = "";

        const currentId =
            currentTaskId();

        const focal =
            runtime.tasks.find(
                task =>
                    taskId(task) ===
                    currentId
            );

        if (!focal) {
            host.innerHTML = `
                <div class="niche-graphic-empty">
                    blocker geometry unavailable
                </div>
            `;
            return;
        }

        const blockers =
            blockersOf(focal);

        const unsatisfied =
            unsatisfiedOf(focal)
                .filter(
                    id =>
                        !blockers.includes(id)
                );

        const points = [
            ...blockers.map(
                id => ({
                    id,
                    kind: "blocker"
                })
            ),
            ...unsatisfied.map(
                id => ({
                    id,
                    kind:
                        "unsatisfied"
                })
            )
        ];

        const canvas =
            svg(
                "svg",
                {
                    class:
                        "niche-blocker-svg niche-graphic-layer",
                    viewBox:
                        "0 0 260 180",
                    "aria-hidden":
                        "true"
                }
            );

        const cx = 130;
        const cy = 90;

        [26, 52, 78]
            .forEach(radius => {
                canvas.append(
                    svg(
                        "circle",
                        {
                            cx,
                            cy,
                            r: radius,
                            class:
                                "niche-radar-ring"
                        }
                    )
                );
            });

        [
            [52, 90, 208, 90],
            [130, 12, 130, 168],
            [75, 35, 185, 145],
            [185, 35, 75, 145]
        ].forEach(
            ([x1, y1, x2, y2]) => {
                canvas.append(
                    svg(
                        "line",
                        {
                            x1,
                            y1,
                            x2,
                            y2,
                            class:
                                "niche-radar-axis"
                        }
                    )
                );
            }
        );

        canvas.append(
            svg(
                "circle",
                {
                    cx,
                    cy,
                    r: 4,
                    class:
                        "niche-radar-origin"
                }
            )
        );

        points.forEach(
            (point, index) => {
                const angle =
                    (
                        Math.PI *
                        2 *
                        index
                    ) /
                    Math.max(
                        points.length,
                        1
                    ) -
                    Math.PI / 2;

                /*
                Radius is intentionally
                uniform. Position does not
                encode severity, probability,
                priority, duration, or authority.
                */
                const radius = 65;

                const x =
                    cx +
                    Math.cos(angle) *
                    radius;

                const y =
                    cy +
                    Math.sin(angle) *
                    radius;

                canvas.append(
                    svg(
                        "line",
                        {
                            x1: cx,
                            y1: cy,
                            x2: x,
                            y2: y,
                            class:
                                "niche-radar-vector"
                        }
                    )
                );

                canvas.append(
                    svg(
                        "circle",
                        {
                            cx: x,
                            cy: y,
                            r: 5,
                            class:
                                point.kind ===
                                "blocker"
                                    ? "niche-radar-blocker"
                                    : "niche-radar-unsatisfied"
                        }
                    )
                );

                const label =
                    svg(
                        "text",
                        {
                            x:
                                x +
                                (
                                    x >= cx
                                        ? 8
                                        : -8
                                ),
                            y:
                                y + 2,
                            "text-anchor":
                                x >= cx
                                    ? "start"
                                    : "end",
                            class:
                                "niche-radar-label"
                        }
                    );

                label.textContent =
                    point.id.length > 18
                        ? `${
                            point.id.slice(
                                0,
                                16
                            )
                        }…`
                        : point.id;

                canvas.append(label);
            }
        );

        host.append(canvas);
    };

    const renderTopology = () => {
        const metrics =
            document.getElementById(
                "topology-metrics"
            );

        const panel =
            metrics?.closest(
                ".metric-panel"
            );

        if (!metrics || !panel) {
            return;
        }

        const host =
            installGraphicContainer(
                panel,
                "niche-topology-graphic",
                metrics
            );

        host.textContent = "";

        const currentId =
            currentTaskId();

        const focal =
            runtime.tasks.find(
                task =>
                    taskId(task) ===
                    currentId
            );

        if (!focal) {
            host.innerHTML = `
                <div class="niche-graphic-empty">
                    topology unavailable
                </div>
            `;
            return;
        }

        const upstream =
            [...new Set([
                ...dependenciesOf(focal),
                ...unsatisfiedOf(focal),
                ...blockersOf(focal)
            ])];

        const downstream =
            dependentsOf(focal);

        const canvas =
            svg(
                "svg",
                {
                    class:
                        "niche-topology-svg niche-graphic-layer",
                    viewBox:
                        "0 0 300 140",
                    "aria-hidden":
                        "true"
                }
            );

        const cx = 150;
        const cy = 70;

        [28, 52]
            .forEach(radius => {
                canvas.append(
                    svg(
                        "circle",
                        {
                            cx,
                            cy,
                            r: radius,
                            class:
                                "niche-topology-orbit"
                        }
                    )
                );
            });

        const place = (
            ids,
            startAngle,
            endAngle,
            kind
        ) => {
            ids.forEach(
                (id, index) => {
                    const ratio =
                        ids.length <= 1
                            ? 0.5
                            : (
                                index /
                                (
                                    ids.length -
                                    1
                                )
                            );

                    const angle =
                        startAngle +
                        (
                            endAngle -
                            startAngle
                        ) *
                        ratio;

                    const radius = 52;

                    const x =
                        cx +
                        Math.cos(angle) *
                        radius;

                    const y =
                        cy +
                        Math.sin(angle) *
                        radius;

                    canvas.append(
                        svg(
                            "line",
                            {
                                x1: cx,
                                y1: cy,
                                x2: x,
                                y2: y,
                                class:
                                    "niche-topology-link"
                            }
                        )
                    );

                    const blocked =
                        blockersOf(focal)
                            .includes(id) ||
                        unsatisfiedOf(focal)
                            .includes(id);

                    canvas.append(
                        svg(
                            "circle",
                            {
                                cx: x,
                                cy: y,
                                r: 4,
                                class:
                                    `niche-topology-node ${
                                        blocked
                                            ? "niche-topology-blocked"
                                            : kind
                                    }`
                            }
                        )
                    );
                }
            );
        };

        place(
            upstream,
            Math.PI * 0.65,
            Math.PI * 1.35,
            "niche-topology-upstream"
        );

        place(
            downstream,
            -Math.PI * 0.35,
            Math.PI * 0.35,
            "niche-topology-downstream"
        );

        canvas.append(
            svg(
                "circle",
                {
                    cx,
                    cy,
                    r: 6,
                    class:
                        "niche-topology-origin"
                }
            )
        );

        host.append(canvas);
    };

    const livingSurfaces = payload => {
        const candidates = [
            payload?.surfaces,
            payload?.fabric?.surfaces,
            payload?.catalog?.surfaces,
            payload?.current?.surfaces
        ];

        for (const candidate of candidates) {
            if (Array.isArray(candidate)) {
                return candidate;
            }

            if (
                candidate &&
                typeof candidate === "object"
            ) {
                return Object.entries(
                    candidate
                ).map(
                    ([id, value]) => ({
                        id,
                        ...(
                            value &&
                            typeof value ===
                            "object"
                                ? value
                                : {
                                    value
                                }
                        )
                    })
                );
            }
        }

        return [];
    };

    const renderLiving = () => {
        const summary =
            document.getElementById(
                "living-summary"
            );

        if (!summary) {
            return;
        }

        const existing =
            document.getElementById(
                "niche-living-map"
            );

        existing?.remove();

        const host =
            document.createElement("div");

        host.id =
            "niche-living-map";

        host.className =
            "niche-living-map";

        summary.before(host);

        const surfaces =
            livingSurfaces(
                runtime.living
            );

        if (!surfaces.length) {
            host.innerHTML = `
                <div class="niche-graphic-empty">
                    living topology not projected
                </div>
            `;
            return;
        }

        const canvas =
            svg(
                "svg",
                {
                    class:
                        "niche-living-svg niche-graphic-layer",
                    viewBox:
                        "0 0 900 320",
                    preserveAspectRatio:
                        "xMidYMid meet",
                    "aria-hidden":
                        "true"
                }
            );

        const cx = 450;
        const cy = 160;

        [62, 108, 145]
            .forEach(radius => {
                canvas.append(
                    svg(
                        "circle",
                        {
                            cx,
                            cy,
                            r: radius,
                            class:
                                "niche-living-ring"
                        }
                    )
                );
            });

        const count =
            surfaces.length;

        surfaces.forEach(
            (surface, index) => {
                const ring =
                    index % 3;

                const radius =
                    [62, 108, 145][ring];

                const ringMembers =
                    surfaces.filter(
                        (_, candidateIndex) =>
                            candidateIndex %
                            3 === ring
                    );

                const ringIndex =
                    ringMembers.indexOf(
                        surface
                    );

                const angle =
                    (
                        Math.PI *
                        2 *
                        ringIndex
                    ) /
                    Math.max(
                        ringMembers.length,
                        1
                    ) -
                    Math.PI / 2;

                const x =
                    cx +
                    Math.cos(angle) *
                    radius;

                const y =
                    cy +
                    Math.sin(angle) *
                    radius;

                canvas.append(
                    svg(
                        "line",
                        {
                            x1: cx,
                            y1: cy,
                            x2: x,
                            y2: y,
                            class:
                                "niche-living-link"
                        }
                    )
                );

                const health =
                    String(
                        first(
                            surface,
                            [
                                "health",
                                "state",
                                "status"
                            ]
                        ) ||
                        "unknown"
                    ).toLowerCase();

                const changed =
                    Boolean(
                        first(
                            surface,
                            [
                                "changed",
                                "is_changed"
                            ]
                        )
                    );

                const node =
                    svg(
                        "circle",
                        {
                            cx: x,
                            cy: y,
                            r:
                                ring === 0
                                    ? 5
                                    : 4,
                            class:
                                "niche-living-node",
                            "data-health":
                                health,
                            "data-changed":
                                String(changed)
                        }
                    );

                canvas.append(node);
            }
        );

        canvas.append(
            svg(
                "circle",
                {
                    cx,
                    cy,
                    r: 8,
                    class:
                        "niche-living-center"
                }
            )
        );

        const label =
            svg(
                "text",
                {
                    x: cx,
                    y: cy + 25,
                    "text-anchor":
                        "middle",
                    class:
                        "niche-living-label"
                }
            );

        label.textContent =
            `${count} REPRESENTED SURFACES`;

        canvas.append(label);

        host.append(canvas);
    };

    const enhanceConstellation = () => {
        const edgeLayer =
            document.getElementById(
                "graph-edges"
            );

        if (!edgeLayer) {
            return;
        }

        let defs =
            edgeLayer.querySelector(
                "#niche-graph-defs"
            );

        if (!defs) {
            defs =
                svg(
                    "defs",
                    {
                        id:
                            "niche-graph-defs"
                    }
                );

            const marker =
                svg(
                    "marker",
                    {
                        id:
                            "niche-causal-arrow",
                        viewBox:
                            "0 0 10 10",
                        refX: 8,
                        refY: 5,
                        markerWidth: 5,
                        markerHeight: 5,
                        orient:
                            "auto-start-reverse"
                    }
                );

            marker.append(
                svg(
                    "path",
                    {
                        d:
                            "M 0 0 L 10 5 L 0 10 z",
                        class:
                            "niche-graph-vector-marker"
                    }
                )
            );

            defs.append(marker);
            edgeLayer.prepend(defs);
        }

        edgeLayer
            .querySelectorAll(
                "line, path"
            )
            .forEach(edge => {
                if (
                    edge.closest("defs")
                ) {
                    return;
                }

                edge.classList.add(
                    "niche-graph-vector"
                );

                edge.setAttribute(
                    "marker-end",
                    "url(#niche-causal-arrow)"
                );
            });
    };

    const renderAll = () => {
        runtime.selectedTaskId =
            currentTaskId();

        renderFrontier();
        renderBlockerRadar();
        renderTopology();
        renderLiving();
        enhanceConstellation();

        window.dispatchEvent(
            new CustomEvent(
                "niche:graphics-render",
                {
                    detail: {
                        schema: SCHEMA,
                        taskCount:
                            runtime.tasks.length,
                        selectedTaskId:
                            runtime.selectedTaskId,
                        livingSurfaceCount:
                            livingSurfaces(
                                runtime.living
                            ).length,
                        authorityEffect:
                            "none",
                        projectionOnly:
                            true
                    }
                }
            )
        );
    };

    const refresh = async () => {
        runtime.generation += 1;

        const generation =
            runtime.generation;

        runtime.controller?.abort();

        const controller =
            new AbortController();

        runtime.controller =
            controller;

        const [
            taskPayload,
            livingPayload
        ] = await Promise.all([
            fetchJson(
                "/api/tasks",
                controller
            ),
            fetchJson(
                "/api/living/fabric",
                controller
            )
        ]);

        if (
            generation !==
            runtime.generation
        ) {
            return false;
        }

        runtime.tasks =
            normalizeTasks(
                taskPayload
            );

        runtime.living =
            livingPayload;

        if (
            runtime.controller ===
            controller
        ) {
            runtime.controller = null;
        }

        renderAll();

        return true;
    };

    const scheduleRender = () => {
        if (runtime.refreshTimer) {
            return;
        }

        runtime.refreshTimer =
            window.setTimeout(
                () => {
                    runtime.refreshTimer =
                        null;

                    renderAll();
                },
                50
            );
    };

    const bindRuntime = () => {
        window.addEventListener(
            "niche:semantic-runtime-update",
            event => {
                if (
                    event.detail?.changed
                ) {
                    void refresh();
                }
            }
        );

        window.addEventListener(
            "niche:continuity-selection",
            event => {
                if (
                    event.detail?.taskId
                ) {
                    runtime.selectedTaskId =
                        event.detail.taskId;

                    scheduleRender();
                }
            }
        );

        document.addEventListener(
            "click",
            event => {
                const node =
                    event.target.closest(
                        "[data-task-id]"
                    );

                if (!node) {
                    return;
                }

                runtime.selectedTaskId =
                    node.dataset.taskId;

                scheduleRender();
            },
            true
        );
    };

    const observeConstellation = () => {
        const stage =
            document.getElementById(
                "graph-stage"
            );

        if (!stage) {
            return;
        }

        runtime.observer =
            new MutationObserver(
                () => {
                    enhanceConstellation();
                }
            );

        runtime.observer.observe(
            stage,
            {
                childList: true,
                subtree: true
            }
        );
    };

    const initialize = () => {
        if (runtime.initialized) {
            return;
        }

        runtime.initialized = true;

        bindRuntime();
        observeConstellation();

        document.documentElement
            .dataset.nicheGraphics =
            "ready";

        void refresh();

        window.dispatchEvent(
            new CustomEvent(
                "niche:graphics-ready",
                {
                    detail: {
                        schema: SCHEMA,
                        authorityEffect:
                            "none",
                        projectionOnly:
                            true
                    }
                }
            )
        );
    };

    window.NicheGraphics =
        Object.freeze({
            refresh,
            render: renderAll,

            state: () => ({
                schema: SCHEMA,
                taskCount:
                    runtime.tasks.length,
                selectedTaskId:
                    runtime.selectedTaskId,
                livingSurfaceCount:
                    livingSurfaces(
                        runtime.living
                    ).length,
                authorityEffect:
                    "none",
                projectionOnly:
                    true
            })
        });

    if (
        document.readyState ===
        "loading"
    ) {
        document.addEventListener(
            "DOMContentLoaded",
            initialize,
            { once: true }
        );
    } else {
        initialize();
    }
})();
