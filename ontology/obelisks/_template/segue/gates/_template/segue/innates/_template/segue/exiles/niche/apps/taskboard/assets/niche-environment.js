"use strict";

/*
 * savant / niche executable environment
 * authority_effect: none
 * projection_only: true
 */

(() => {
    "use strict";

    const schema = "savant.niche.environment.v1";
    const svgNS = "http://www.w3.org/2000/svg";

    const runtime = {
        initialized: false,
        generation: 0,
        controller: null,
        tasks: [],
        fabric: null,
        selectedTaskId: null,
        view: "execute",
        observer: null,
        resizeObserver: null,
        renderQueued: false
    };

    const array = value => Array.isArray(value) ? value : [];

    const represented = value =>
        value !== undefined &&
        value !== null &&
        value !== "";

    const first = (object, keys) => {
        for (const key of keys) {
            if (
                object &&
                Object.prototype.hasOwnProperty.call(object, key) &&
                represented(object[key])
            ) {
                return object[key];
            }
        }

        return null;
    };

    const identifier = value => {
        if (typeof value === "string" && value) {
            return value;
        }

        if (!value || typeof value !== "object") {
            return null;
        }

        const id = first(value, [
            "task_id",
            "taskId",
            "surface_id",
            "surfaceId",
            "id"
        ]);

        return represented(id) ? String(id) : null;
    };

    const title = value => {
        if (!value || typeof value !== "object") {
            return represented(value) ? String(value) : "unknown";
        }

        return String(
            first(value, [
                "title",
                "name",
                "label",
                "summary"
            ]) ||
            identifier(value) ||
            "unknown"
        );
    };

    const normalizeTasks = payload => {
        if (Array.isArray(payload)) {
            return payload;
        }

        for (const key of ["tasks", "items", "results"]) {
            if (Array.isArray(payload?.[key])) {
                return payload[key];
            }
        }

        return [];
    };

    const ids = value =>
        array(value)
            .map(identifier)
            .filter(Boolean);

    const dependencies = task =>
        ids(first(task, [
            "dependencies",
            "dependency_ids",
            "dependencyIds"
        ]));

    const unsatisfied = task =>
        ids(first(task, [
            "unsatisfied_dependencies",
            "unsatisfiedDependencies"
        ]));

    const blockers = task =>
        ids(first(task, [
            "blockers",
            "blocker_ids",
            "blockerIds"
        ]));

    const dependents = task =>
        ids(first(task, [
            "dependents",
            "dependent_ids",
            "dependentIds"
        ]));

    const state = task =>
        String(
            first(task, ["state", "status"]) || ""
        ).toLowerCase();

    const readiness = task =>
        first(task, [
            "ready",
            "is_ready",
            "readiness",
            "executable",
            "is_executable"
        ]);

    const classify = task => {
        const taskState = state(task);

        if (
            blockers(task).length ||
            unsatisfied(task).length ||
            taskState === "blocked"
        ) {
            return "blocked";
        }

        const ready = readiness(task);

        if (
            ready === true ||
            String(ready).toLowerCase() === "ready"
        ) {
            return "ready";
        }

        if (
            [
                "complete",
                "completed",
                "done",
                "closed"
            ].includes(taskState)
        ) {
            return "complete";
        }

        return "future";
    };

    const taskMap = () =>
        new Map(
            runtime.tasks
                .map(task => [identifier(task), task])
                .filter(([id]) => Boolean(id))
        );

    const nicheState = () => {
        try {
            return window.Niche?.state?.() || {};
        } catch {
            return {};
        }
    };

    const currentTaskId = () => {
        const current = nicheState();

        return (
            current.selectedTaskId ||
            runtime.selectedTaskId ||
            current.recommendedTaskId ||
            null
        );
    };

    const currentTask = () => {
        const id = currentTaskId();

        return id
            ? taskMap().get(id) || null
            : null;
    };

    const svg = (tag, attributes = {}) => {
        const node = document.createElementNS(svgNS, tag);

        for (const [key, value] of Object.entries(attributes)) {
            if (value !== undefined && value !== null) {
                node.setAttribute(key, String(value));
            }
        }

        return node;
    };

    const text = (x, y, value, className, anchor = "start") => {
        const node = svg("text", {
            x,
            y,
            class: className,
            "text-anchor": anchor
        });

        node.textContent = String(value);

        return node;
    };

    const trim = (value, length = 24) => {
        const string = String(value || "");

        return string.length > length
            ? `${string.slice(0, Math.max(1, length - 1))}…`
            : string;
    };

    const fetchJson = async (url, signal) => {
        const response = await fetch(url, {
            cache: "no-store",
            signal,
            headers: {
                Accept: "application/json"
            }
        });

        if (!response.ok) {
            throw new Error(`${url}: ${response.status}`);
        }

        return response.json();
    };

    const refresh = async () => {
        runtime.generation += 1;

        const generation = runtime.generation;

        runtime.controller?.abort();

        const controller = new AbortController();
        runtime.controller = controller;

        const [tasksResult, fabricResult] = await Promise.allSettled([
            fetchJson("/api/tasks?include_terminal=true", controller.signal),
            fetchJson("/api/living/fabric", controller.signal)
        ]);

        if (
            controller.signal.aborted ||
            generation !== runtime.generation
        ) {
            return;
        }

        if (tasksResult.status === "fulfilled") {
            runtime.tasks = normalizeTasks(tasksResult.value);
        }

        if (fabricResult.status === "fulfilled") {
            runtime.fabric = fabricResult.value;
        }

        queueRender();

        window.dispatchEvent(
            new CustomEvent("niche:environment-update", {
                detail: {
                    schema,
                    taskCount: runtime.tasks.length,
                    taskProjection:
                        tasksResult.status === "fulfilled"
                            ? "available"
                            : "degraded",
                    livingProjection:
                        fabricResult.status === "fulfilled"
                            ? "available"
                            : "degraded",
                    authorityEffect: "none",
                    projectionOnly: true
                }
            })
        );
    };

    const frontierPosition = (task, index, total) => {
        const kind = classify(task);

        const bands = {
            complete: [4, 29],
            ready: [36, 61],
            blocked: [69, 82],
            future: [84, 97]
        };

        const [start, end] = bands[kind] || bands.future;
        const span = Math.max(1, end - start);
        const seed = identifier(task) || String(index);

        let hash = 0;

        for (let i = 0; i < seed.length; i += 1) {
            hash = ((hash << 5) - hash + seed.charCodeAt(i)) | 0;
        }

        const x = start + Math.abs(hash % 1000) / 1000 * span;
        const y =
            18 +
            (
                ((index * 37) + Math.abs(hash % 53)) %
                Math.max(1, total * 5)
            ) /
            Math.max(1, total * 5) *
            64;

        return { x, y, kind };
    };

    const renderFrontier = () => {
        const host = document.getElementById("frontier-track");

        if (!host) {
            return;
        }

        let layer = host.querySelector(".niche-frontier-visual");

        if (!layer) {
            layer = document.createElement("div");
            layer.className = "niche-frontier-visual";
            host.append(layer);
        }

        layer.replaceChildren();

        const fragment = document.createDocumentFragment();
        const current = currentTaskId();

        runtime.tasks.forEach((task, index) => {
            const id = identifier(task);

            if (!id) {
                return;
            }

            const point = frontierPosition(
                task,
                index,
                runtime.tasks.length
            );

            const node = document.createElement("span");

            node.className = "niche-frontier-node";
            node.dataset.state = point.kind;
            node.dataset.current = String(id === current);
            node.style.left = `${point.x}%`;
            node.style.top = `${point.y}%`;
            node.title = `${id} · ${title(task)} · ${point.kind}`;

            fragment.append(node);
        });

        layer.append(fragment);
    };

    const instrumentHost = (parent, className) => {
        if (!parent) {
            return null;
        }

        let host = parent.querySelector(`:scope > .${className}`);

        if (!host) {
            host = document.createElement("div");
            host.className = `niche-instrument ${className}`;
            parent.prepend(host);
        }

        return host;
    };

    const renderTopology = () => {
        const metric = document.getElementById("topology-metrics");
        const panel = metric?.closest(".metric-panel");

        if (!panel) {
            return;
        }

        const host = instrumentHost(panel, "niche-topology");
        const task = currentTask();

        if (!host || !task) {
            if (host) {
                host.replaceChildren();
            }
            return;
        }

        const upstream = [
            ...new Set([
                ...dependencies(task),
                ...unsatisfied(task),
                ...blockers(task)
            ])
        ];

        const downstream = [...new Set(dependents(task))];

        const canvas = svg("svg", {
            viewBox: "0 0 360 170",
            role: "img",
            "aria-label": "Selected task execution topology"
        });

        [45, 85, 125].forEach(y => {
            canvas.append(svg("line", {
                x1: 0,
                y1: y,
                x2: 360,
                y2: y,
                class: "niche-grid-line"
            }));
        });

        const cx = 180;
        const cy = 85;

        const drawSide = (items, side) => {
            const count = Math.max(1, items.length);

            items.slice(0, 8).forEach((id, index) => {
                const y =
                    24 +
                    index * (122 / Math.max(1, count - 1));

                const x = side === "upstream" ? 56 : 304;

                canvas.append(svg("path", {
                    d:
                        side === "upstream"
                            ? `M ${x} ${y} C 105 ${y}, 118 ${cy}, ${cx} ${cy}`
                            : `M ${cx} ${cy} C 242 ${cy}, 255 ${y}, ${x} ${y}`,
                    class:
                        blockers(task).includes(id) ||
                        unsatisfied(task).includes(id)
                            ? "niche-trace blocked"
                            : "niche-trace"
                }));

                canvas.append(svg("rect", {
                    x: x - 4,
                    y: y - 4,
                    width: 8,
                    height: 8,
                    transform: `rotate(45 ${x} ${y})`,
                    class:
                        blockers(task).includes(id) ||
                        unsatisfied(task).includes(id)
                            ? "niche-nucleus blocked"
                            : "niche-nucleus"
                }));
            });
        };

        drawSide(upstream, "upstream");
        drawSide(downstream, "downstream");

        canvas.append(svg("circle", {
            cx,
            cy,
            r: 17,
            class: `niche-nucleus ${classify(task)}`
        }));

        canvas.append(svg("circle", {
            cx,
            cy,
            r: 28,
            class: "niche-reticle"
        }));

        canvas.append(
            text(cx, 145, trim(identifier(task), 22), "niche-depth-heading", "middle")
        );

        canvas.append(
            text(12, 15, "UPSTREAM", "niche-depth-heading")
        );

        canvas.append(
            text(348, 15, "DOWNSTREAM", "niche-depth-heading", "end")
        );

        host.replaceChildren(canvas);
    };

    const renderRadar = () => {
        const list = document.getElementById("blocker-list");
        const panel = list?.closest(".metric-panel");

        if (!panel) {
            return;
        }

        const host = instrumentHost(panel, "niche-radar");
        const task = currentTask();

        if (!host || !task) {
            if (host) {
                host.replaceChildren();
            }
            return;
        }

        const obstructionIds = [
            ...new Set([
                ...blockers(task),
                ...unsatisfied(task)
            ])
        ];

        const canvas = svg("svg", {
            viewBox: "0 0 300 190",
            role: "img",
            "aria-label": "Structural blocker radar"
        });

        const cx = 150;
        const cy = 96;

        [28, 55, 82].forEach(radius => {
            canvas.append(svg("circle", {
                cx,
                cy,
                r: radius,
                class: "niche-grid-line",
                fill: "none"
            }));
        });

        canvas.append(svg("line", {
            x1: 58,
            y1: cy,
            x2: 242,
            y2: cy,
            class: "niche-grid-line"
        }));

        canvas.append(svg("line", {
            x1: cx,
            y1: 5,
            x2: cx,
            y2: 187,
            class: "niche-grid-line"
        }));

        obstructionIds.slice(0, 12).forEach((id, index) => {
            const angle =
                -Math.PI / 2 +
                index * (Math.PI * 2 / Math.max(1, obstructionIds.length));

            const radius =
                35 +
                (index % 3) * 20;

            const x = cx + Math.cos(angle) * radius;
            const y = cy + Math.sin(angle) * radius;

            canvas.append(svg("line", {
                x1: cx,
                y1: cy,
                x2: x,
                y2: y,
                class: "niche-trace blocked"
            }));

            canvas.append(svg("rect", {
                x: x - 4,
                y: y - 4,
                width: 8,
                height: 8,
                transform: `rotate(45 ${x} ${y})`,
                class: "niche-nucleus blocked"
            }));
        });

        canvas.append(svg("circle", {
            cx,
            cy,
            r: 7,
            class: "niche-nucleus"
        }));

        canvas.append(
            text(
                10,
                16,
                obstructionIds.length
                    ? `${obstructionIds.length} REPRESENTED OBSTRUCTION${obstructionIds.length === 1 ? "" : "S"}`
                    : "NO REPRESENTED OBSTRUCTIONS",
                "niche-depth-heading"
            )
        );

        host.replaceChildren(canvas);
    };

    const objectiveValue = task =>
        first(task, [
            "objective",
            "objective_id",
            "objectiveId"
        ]);

    const trancheValue = task =>
        first(task, [
            "tranche",
            "tranche_id",
            "trancheId"
        ]);

    const actionValue = task =>
        first(task, [
            "action",
            "action_id",
            "actionId"
        ]);

    const primitive = (value, prefix) => {
        if (!represented(value)) {
            return null;
        }

        if (typeof value === "object") {
            return {
                id: identifier(value) || `${prefix}:${title(value)}`,
                title: title(value)
            };
        }

        return {
            id: `${prefix}:${String(value)}`,
            title: String(value)
        };
    };

    const objectiveProjection = () => {
        const objectives = new Map();
        const tranches = new Map();
        const tasks = new Map();
        const actions = new Map();
        const links = [];

        runtime.tasks.forEach(task => {
            const taskId = identifier(task);

            if (!taskId) {
                return;
            }

            tasks.set(taskId, {
                id: taskId,
                title: title(task),
                kind: classify(task)
            });

            const objective = primitive(objectiveValue(task), "objective");
            const tranche = primitive(trancheValue(task), "tranche");
            const action = primitive(actionValue(task), "action");

            if (objective) {
                objectives.set(objective.id, objective);
            }

            if (tranche) {
                tranches.set(tranche.id, tranche);
            }

            if (action) {
                actions.set(action.id, action);
            }

            if (objective && tranche) {
                links.push([objective.id, tranche.id, "normal"]);
            }

            if (tranche) {
                links.push([tranche.id, taskId, classify(task)]);
            } else if (objective) {
                links.push([objective.id, taskId, classify(task)]);
            }

            if (action) {
                links.push([taskId, action.id, classify(task)]);
            }
        });

        return {
            objectives: [...objectives.values()],
            tranches: [...tranches.values()],
            tasks: [...tasks.values()],
            actions: [...actions.values()],
            links
        };
    };

    const renderObjectives = () => {
        const grid = document.getElementById("objective-grid");

        if (!grid) {
            return;
        }

        let host = document.getElementById("niche-objective-field");

        if (!host) {
            host = document.createElement("div");
            host.id = "niche-objective-field";
            host.className = "niche-objective-field";
            grid.before(host);
        }

        const projection = objectiveProjection();

        if (!projection.tasks.length) {
            host.replaceChildren();
            return;
        }

        const canvas = svg("svg", {
            viewBox: "0 0 1100 520",
            role: "img",
            "aria-label": "Objective to task structural projection"
        });

        const levels = [
            ["objectives", "OBJECTIVE", 110, "objective"],
            ["tranches", "TRANCHE", 385, "tranche"],
            ["tasks", "TASK", 700, "task"],
            ["actions", "ACTION", 990, "action"]
        ];

        const positions = new Map();

        levels.forEach(([key, label, x, kind]) => {
            canvas.append(svg("line", {
                x1: x,
                y1: 48,
                x2: x,
                y2: 495,
                class: "niche-depth-axis"
            }));

            canvas.append(
                text(x, 28, label, "niche-depth-heading", "middle")
            );

            const values = projection[key];
            const count = values.length;

            values.forEach((value, index) => {
                const y =
                    count <= 1
                        ? 260
                        : 68 + index * (405 / Math.max(1, count - 1));

                positions.set(value.id, {
                    x,
                    y,
                    kind,
                    value
                });
            });
        });

        projection.links.forEach(([fromId, toId, kind]) => {
            const from = positions.get(fromId);
            const to = positions.get(toId);

            if (!from || !to) {
                return;
            }

            const middle = (from.x + to.x) / 2;

            canvas.append(svg("path", {
                d:
                    `M ${from.x} ${from.y} ` +
                    `C ${middle} ${from.y}, ${middle} ${to.y}, ${to.x} ${to.y}`,
                class:
                    kind === "blocked"
                        ? "niche-depth-link blocked"
                        : "niche-depth-link"
            }));
        });

        const current = currentTaskId();

        positions.forEach(({ x, y, kind, value }) => {
            const radius =
                kind === "objective"
                    ? 7
                    : kind === "tranche"
                        ? 6
                        : kind === "task"
                            ? 5
                            : 4;

            if (kind === "task" && value.id === current) {
                canvas.append(svg("circle", {
                    cx: x,
                    cy: y,
                    r: radius + 10,
                    class: "niche-reticle"
                }));
            }

            canvas.append(svg("circle", {
                cx: x,
                cy: y,
                r: radius,
                class:
                    `niche-depth-node ${kind}` +
                    (value.kind === "blocked" ? " blocked" : "")
            }));

            canvas.append(
                text(
                    x + 12,
                    y + 3,
                    trim(value.title, 28),
                    "niche-depth-label"
                )
            );
        });

        host.replaceChildren(canvas);
    };

    const livingSurfaces = () => {
        const payload = runtime.fabric;

        if (!payload || typeof payload !== "object") {
            return [];
        }

        const candidates = [
            payload.surfaces,
            payload.fabric?.surfaces,
            payload.current?.surfaces,
            payload.catalog?.surfaces,
            payload.items
        ];

        for (const candidate of candidates) {
            if (Array.isArray(candidate)) {
                return candidate;
            }

            if (candidate && typeof candidate === "object") {
                return Object.entries(candidate).map(([id, value]) => ({
                    id,
                    ...(value && typeof value === "object" ? value : { value })
                }));
            }
        }

        return [];
    };

    const renderLiving = () => {
        const summary = document.getElementById("living-summary");

        if (!summary) {
            return;
        }

        let host = document.getElementById("niche-living-observatory");

        if (!host) {
            host = document.createElement("div");
            host.id = "niche-living-observatory";
            host.className = "niche-living-observatory";
            summary.before(host);
        }

        const surfaces = livingSurfaces();

        if (!surfaces.length) {
            host.replaceChildren();
            return;
        }

        const canvas = svg("svg", {
            viewBox: "0 0 1000 520",
            role: "img",
            "aria-label": "Living Fabric topological projection"
        });

        const cx = 500;
        const cy = 260;

        [72, 140, 208].forEach(radius => {
            canvas.append(svg("circle", {
                cx,
                cy,
                r: radius,
                class: "niche-living-ring"
            }));
        });

        surfaces.slice(0, 72).forEach((surface, index) => {
            const ring = index % 3;
            const radius = [72, 140, 208][ring];
            const ringCount = Math.ceil(surfaces.length / 3);
            const angle =
                -Math.PI / 2 +
                (
                    Math.floor(index / 3) /
                    Math.max(1, ringCount)
                ) *
                Math.PI *
                2 +
                ring * .13;

            const x = cx + Math.cos(angle) * radius;
            const y = cy + Math.sin(angle) * radius;

            const changed =
                first(surface, [
                    "changed",
                    "is_changed",
                    "isChanged"
                ]) === true;

            canvas.append(svg("line", {
                x1: cx,
                y1: cy,
                x2: x,
                y2: y,
                class: "niche-living-link"
            }));

            canvas.append(svg("circle", {
                cx: x,
                cy: y,
                r: changed ? 5 : 3.2,
                class:
                    changed
                        ? "niche-living-node changed"
                        : "niche-living-node"
            }));
        });

        canvas.append(svg("circle", {
            cx,
            cy,
            r: 19,
            class: "niche-living-node changed"
        }));

        canvas.append(
            text(
                cx,
                cy + 3,
                String(surfaces.length),
                "niche-depth-label",
                "middle"
            )
        );

        canvas.append(
            text(
                20,
                26,
                "LIVING FABRIC / TOPOLOGICAL PROJECTION",
                "niche-depth-heading"
            )
        );

        host.replaceChildren(canvas);
    };

    const enhanceGraph = () => {
        const edgeRoot = document.getElementById("graph-edges");

        if (!edgeRoot) {
            return;
        }

        let defs = edgeRoot.querySelector("defs");

        if (!defs) {
            defs = svg("defs");
            edgeRoot.prepend(defs);
        }

        if (!defs.querySelector("#niche-arrow")) {
            const marker = svg("marker", {
                id: "niche-arrow",
                viewBox: "0 0 10 10",
                refX: 8,
                refY: 5,
                markerWidth: 5,
                markerHeight: 5,
                orient: "auto-start-reverse"
            });

            marker.append(svg("path", {
                d: "M 0 0 L 10 5 L 0 10 z",
                fill: "rgba(139,213,222,.55)"
            }));

            defs.append(marker);
        }

        edgeRoot
            .querySelectorAll("line, path")
            .forEach(edge => {
                if (edge.closest("defs")) {
                    return;
                }

                edge.setAttribute(
                    "marker-end",
                    "url(#niche-arrow)"
                );
            });
    };

    const installProjectionBadges = () => {
        document
            .querySelectorAll(".surface-heading")
            .forEach(heading => {
                if (
                    heading.querySelector(
                        ".niche-projection-badge"
                    )
                ) {
                    return;
                }

                const badge = document.createElement("span");
                badge.className = "niche-projection-badge";
                badge.textContent = "deterministic projection";

                heading.append(badge);
            });
    };

    const render = () => {
        renderFrontier();
        renderTopology();
        renderRadar();
        renderObjectives();
        renderLiving();
        enhanceGraph();
        installProjectionBadges();

        window.dispatchEvent(
            new CustomEvent("niche:environment-render", {
                detail: {
                    schema,
                    selectedTaskId: currentTaskId(),
                    taskCount: runtime.tasks.length,
                    livingSurfaceCount: livingSurfaces().length,
                    authorityEffect: "none",
                    projectionOnly: true
                }
            })
        );
    };

    const queueRender = () => {
        if (runtime.renderQueued) {
            return;
        }

        runtime.renderQueued = true;

        requestAnimationFrame(() => {
            runtime.renderQueued = false;
            render();
        });
    };

    const preserveSelection = event => {
        const target = event.target.closest("[data-task-id]");

        if (!target) {
            return;
        }

        const id = target.dataset.taskId;

        if (!id) {
            return;
        }

        runtime.selectedTaskId = id;

        try {
            localStorage.setItem(
                "savant.niche.interface.selected-task",
                id
            );
        } catch {
            /* interface persistence is optional */
        }

        queueRender();
    };

    const restoreInterfaceState = () => {
        try {
            runtime.selectedTaskId =
                localStorage.getItem(
                    "savant.niche.interface.selected-task"
                ) || null;

            const width = localStorage.getItem(
                "savant.niche.interface.inspector-width"
            );

            if (width) {
                document.documentElement.style.setProperty(
                    "--niche-inspector-width",
                    `${Math.max(320, Math.min(680, Number(width) || 420))}px`
                );
            }
        } catch {
            /* local interface state is non-authoritative */
        }
    };

    const installInspectorResize = () => {
        const inspector = document.getElementById("inspector");

        if (!inspector || matchMedia("(max-width: 860px)").matches) {
            return;
        }

        let active = false;

        const begin = event => {
            const rect = inspector.getBoundingClientRect();

            if (
                event.clientX >
                rect.left + 12
            ) {
                return;
            }

            active = true;
            inspector.setPointerCapture?.(event.pointerId);
            event.preventDefault();
        };

        const move = event => {
            if (!active) {
                return;
            }

            const width = Math.max(
                320,
                Math.min(
                    680,
                    window.innerWidth - event.clientX - 12
                )
            );

            document.documentElement.style.setProperty(
                "--niche-inspector-width",
                `${width}px`
            );
        };

        const end = () => {
            if (!active) {
                return;
            }

            active = false;

            const width = inspector.getBoundingClientRect().width;

            try {
                localStorage.setItem(
                    "savant.niche.interface.inspector-width",
                    String(Math.round(width))
                );
            } catch {
                /* optional interface preference */
            }
        };

        inspector.addEventListener("pointerdown", begin);
        window.addEventListener("pointermove", move, { passive: true });
        window.addEventListener("pointerup", end, { passive: true });
    };

    const bind = () => {
        document.addEventListener(
            "click",
            preserveSelection,
            true
        );

        window.addEventListener(
            "niche:continuity-selection",
            event => {
                if (event.detail?.taskId) {
                    runtime.selectedTaskId =
                        event.detail.taskId;
                }

                queueRender();
            }
        );

        window.addEventListener(
            "niche:semantic-runtime-update",
            event => {
                if (event.detail?.changed) {
                    void refresh();
                }
            }
        );

        document
            .querySelectorAll("[data-view]")
            .forEach(button => {
                button.addEventListener("click", () => {
                    runtime.view =
                        button.dataset.view || runtime.view;

                    queueRender();
                });
            });

        const graph = document.getElementById("graph-stage");

        if (graph) {
            runtime.observer = new MutationObserver(() => {
                enhanceGraph();
            });

            runtime.observer.observe(graph, {
                childList: true,
                subtree: true
            });
        }

        if ("ResizeObserver" in window) {
            runtime.resizeObserver =
                new ResizeObserver(queueRender);

            [
                document.getElementById("frontier-track"),
                document.getElementById("graph-stage")
            ]
                .filter(Boolean)
                .forEach(node =>
                    runtime.resizeObserver.observe(node)
                );
        }
    };

    const initialize = () => {
        if (runtime.initialized) {
            return;
        }

        runtime.initialized = true;

        restoreInterfaceState();
        bind();
        installInspectorResize();
        installProjectionBadges();

        document.documentElement.dataset
            .nicheEnvironment = "ready";

        void refresh();

        window.dispatchEvent(
            new CustomEvent("niche:environment-ready", {
                detail: {
                    schema,
                    authorityEffect: "none",
                    projectionOnly: true
                }
            })
        );
    };

    window.NicheEnvironment = Object.freeze({
        refresh,
        render: queueRender,
        state: () => ({
            schema,
            taskCount: runtime.tasks.length,
            selectedTaskId: currentTaskId(),
            livingSurfaceCount: livingSurfaces().length,
            authorityEffect: "none",
            projectionOnly: true
        })
    });

    if (document.readyState === "loading") {
        document.addEventListener(
            "DOMContentLoaded",
            initialize,
            { once: true }
        );
    } else {
        initialize();
    }
})();
