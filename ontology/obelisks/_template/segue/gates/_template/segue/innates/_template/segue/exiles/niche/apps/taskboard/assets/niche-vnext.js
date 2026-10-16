"use strict";

/*
 * savant / niche vnext
 * interface projection coordinator
 *
 * owner: exile:niche
 * semantic_role: non-authoritative interface coordination
 * authority_effect: none
 * projection_only: true
 *
 * Core task substance, recommendation, refresh, selection, and active-view
 * ownership are delegated to window.Niche. This module owns only local
 * presentation state and deterministic secondary projections.
 */

(() => {
    "use strict";

    const STORAGE = Object.freeze({
        theme: "savant.niche.ui.theme",
        causalMode: "savant.niche.ui.causal-mode",
        causalZoom: "savant.niche.ui.causal-zoom",
        objectiveFilter: "savant.niche.ui.objective-filter",
        objectiveSearch: "savant.niche.ui.objective-search"
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
        flow: Object.freeze({
            label: "FLOW",
            description:
                "What represented work is moving, ready, waiting, blocked, or complete?"
        }),
        dependencies: Object.freeze({
            label: "DEPENDENCIES",
            description:
                "What represented prerequisites does the selected task require?"
        }),
        impact: Object.freeze({
            label: "IMPACT",
            description:
                "What represented work depends on the selected task?"
        }),
        objective: Object.freeze({
            label: "OBJECTIVE",
            description:
                "How does the selected task sit inside its represented objective?"
        }),
        critical: Object.freeze({
            label: "CRITICAL PATH",
            description:
                "What explicit or accepted-derived critical-path information is represented?"
        }),
        blockers: Object.freeze({
            label: "BLOCKERS",
            description:
                "What represented blockers and unresolved prerequisites prevent progress?"
        }),
        authority: Object.freeze({
            label: "AUTHORITY",
            description:
                "Which displayed values are authoritative, derived, projected, or unknown?"
        })
    });

    const RESOURCE_LABELS = Object.freeze({
        health: "NICHE",
        tasks: "TASKS",
        living: "LIVING",
        fabric: "LIVING FABRIC",
        history: "HISTORY"
    });

    const VALID_RESOURCE_STATES = new Set([
        "available",
        "degraded",
        "unavailable",
        "unknown",
        "loading"
    ]);

    const state = {
        installed: false,
        theme: "nexus",
        causalMode: "flow",
        causalZoom: 1,
        objectiveFilter: "all",
        objectiveSearch: "",
        lastProjectionGeneration: -1,
        lastSelectedTaskId: null,
        lastActiveView: null,
        renderQueued: false,
        pendingGo: false,
        pendingGoTimer: null,

        causal: {
            active: false,
            firstFit: false,
            x: 0,
            y: 0,
            width: 1,
            height: 1,
            worldWidth: 1,
            worldHeight: 1,
            layoutKey: "",
            nodes: new Map(),
            edges: [],
            pointerId: null,
            pointerStartX: 0,
            pointerStartY: 0,
            pointerOriginX: 0,
            pointerOriginY: 0,
            resizeObserver: null,
            transformQueued: false
        }
    };

    const $ = (selector, root = document) =>
        root.querySelector(selector);

    const $$ = (selector, root = document) =>
        Array.from(root.querySelectorAll(selector));

    function asText(value, fallback = "") {
        if (value === null || value === undefined) {
            return fallback;
        }

        const normalized = String(value).trim();
        return normalized || fallback;
    }

    function lower(value) {
        return asText(value).toLocaleLowerCase();
    }

    function safeRead(key) {
        try {
            return window.localStorage.getItem(key);
        } catch {
            return null;
        }
    }

    function safeWrite(key, value) {
        try {
            window.localStorage.setItem(key, value);
        } catch {
            return;
        }
    }

    function emit(type, detail = {}) {
        window.dispatchEvent(
            new CustomEvent(
                `niche:vnext:${type}`,
                {
                    detail: {
                        ...detail,
                        authority_effect: "none",
                        projection_only: true
                    }
                }
            )
        );
    }

    function coreAvailable() {
        return Boolean(
            window.Niche &&
            typeof window.Niche.state === "function"
        );
    }

    function coreState() {
        if (!coreAvailable()) {
            return null;
        }

        try {
            return window.Niche.state();
        } catch {
            return null;
        }
    }

    function coreProjection() {
        if (
            !coreAvailable() ||
            typeof window.Niche.projection !== "function"
        ) {
            return null;
        }

        try {
            return window.Niche.projection();
        } catch {
            return null;
        }
    }

    function projectionTasks(projection = coreProjection()) {
        const tasks = projection?.source?.tasks;
        return Array.isArray(tasks)
            ? tasks
            : [];
    }

    function projectionTaskMap(projection = coreProjection()) {
        const candidate = projection?.normalized?.taskById;

        if (candidate instanceof Map) {
            return candidate;
        }

        return new Map(
            projectionTasks(projection)
                .map((task) => [
                    asText(task?.id ?? task?.task_id),
                    task
                ])
                .filter(([id]) => Boolean(id))
        );
    }

    function selectedTaskId(projection = coreProjection()) {
        return (
            asText(
                projection?.normalized?.selectedTaskId ??
                coreState()?.selectedTaskId
            ) ||
            null
        );
    }

    function recommendedTaskId(projection = coreProjection()) {
        return (
            asText(
                projection?.normalized?.recommendedTaskId ??
                coreState()?.recommendedTaskId
            ) ||
            null
        );
    }

    function activeView(projection = coreProjection()) {
        return (
            asText(
                projection?.normalized?.activeView ??
                coreState()?.activeView
            ) ||
            "execute"
        );
    }

    function validTheme(value) {
        return THEMES.includes(value)
            ? value
            : "nexus";
    }

    function validCausalMode(value) {
        return Object.prototype.hasOwnProperty.call(
            CAUSAL_MODES,
            value
        )
            ? value
            : "flow";
    }

    function clampZoom(value) {
        return Math.min(
            1.8,
            Math.max(
                0.55,
                Number(value) || 1
            )
        );
    }

    function applyTheme(
        value,
        {
            persist = true
        } = {}
    ) {
        const next = validTheme(value);

        state.theme = next;
        document.documentElement.dataset.nicheTheme = next;

        const control = $("#niche-theme");
        if (control && control.value !== next) {
            control.value = next;
        }

        if (persist) {
            safeWrite(
                STORAGE.theme,
                next
            );
        }

        emit(
            "theme",
            {
                theme: next
            }
        );
    }

    function applyCausalMode(
        value,
        {
            persist = true
        } = {}
    ) {
        const next = validCausalMode(value);
        state.causalMode = next;

        const workspace = $(".causal-workspace");
        const graph = $("#graph-stage");
        const flow = $("#causal-flow");

        if (workspace) {
            workspace.dataset.causalActive = next;
        }

        const flowActive = next === "flow";

        if (graph) {
            graph.hidden = flowActive;
        }

        if (flow) {
            flow.hidden = !flowActive;
        }

        for (const button of $$("[data-causal-mode]")) {
            const mode = button.dataset.causalMode;
            const recognized = Object.prototype.hasOwnProperty.call(
                CAUSAL_MODES,
                mode
            );

            if (!recognized) {
                button.hidden = true;
                continue;
            }

            const current = mode === next;

            button.classList.toggle(
                "active",
                current
            );

            button.setAttribute(
                "aria-pressed",
                current
                    ? "true"
                    : "false"
            );
        }

        const metadata = CAUSAL_MODES[next];

        const label = $("#causal-mode-label");
        if (label) {
            label.textContent = metadata.label;
        }

        const description = $("#causal-mode-description");
        if (description) {
            description.textContent = metadata.description;
        }

        if (persist) {
            safeWrite(
                STORAGE.causalMode,
                next
            );
        }

        renderCausalCompanion();
        updateCausalModeState();

        emit(
            "causal-mode",
            {
                mode: next
            }
        );
    }

    function applyCausalTransform() {
        const transform =
            `translate(${state.causal.x}px, ${state.causal.y}px) ` +
            `scale(${state.causalZoom})`;

        for (const target of [
            $("#graph-nodes"),
            $("#graph-edges")
        ]) {
            if (!target) {
                continue;
            }

            target.style.transformOrigin = "0 0";
            target.style.transform = transform;
        }

        const label = $("#causal-zoom-label");
        if (label) {
            label.textContent =
                `${Math.round(state.causalZoom * 100)}%`;
        }
    }

    function queueCausalTransform() {
        if (state.causal.transformQueued) {
            return;
        }

        state.causal.transformQueued = true;

        requestAnimationFrame(
            () => {
                state.causal.transformQueued = false;
                applyCausalTransform();
            }
        );
    }

    function applyCausalZoom(
        value,
        {
            persist = true,
            clientX = null,
            clientY = null
        } = {}
    ) {
        const previous = state.causalZoom;
        const next = clampZoom(value);

        if (
            Number.isFinite(clientX) &&
            Number.isFinite(clientY)
        ) {
            const stage =
                $("#graph-stage");

            const rectangle =
                stage?.getBoundingClientRect();

            if (rectangle) {
                const localX =
                    clientX -
                    rectangle.left;

                const localY =
                    clientY -
                    rectangle.top;

                const worldX =
                    (
                        localX -
                        state.causal.x
                    ) /
                    previous;

                const worldY =
                    (
                        localY -
                        state.causal.y
                    ) /
                    previous;

                state.causal.x =
                    localX -
                    worldX *
                    next;

                state.causal.y =
                    localY -
                    worldY *
                    next;
            }
        }

        state.causalZoom = next;

        queueCausalTransform();

        if (persist) {
            safeWrite(
                STORAGE.causalZoom,
                String(next)
            );
        }

        emit(
            "causal-zoom",
            {
                zoom: next
            }
        );
    }

    function normalizeResourceState(value) {
        const normalized = lower(value);

        if (VALID_RESOURCE_STATES.has(normalized)) {
            return normalized;
        }

        return "unknown";
    }

    function renderStatusRail() {
        const rail = $("#statusrail");
        if (!rail) {
            return;
        }

        const projection = coreProjection();
        const resources = projection?.resources ?? {};
        const taskCount = projectionTasks(projection).length;

        const values = [
            [
                "health",
                normalizeResourceState(resources.health)
            ],
            [
                "tasks",
                normalizeResourceState(resources.tasks)
            ],
            [
                "living",
                normalizeResourceState(resources.living)
            ],
            [
                "fabric",
                normalizeResourceState(resources.fabric)
            ],
            [
                "history",
                normalizeResourceState(resources.history)
            ]
        ];

        const fragment = document.createDocumentFragment();

        for (const [key, resourceState] of values) {
            const item = document.createElement("span");

            item.className = "vnext-resource-status";
            item.dataset.resource = key;
            item.dataset.state = resourceState;

            const count =
                key === "tasks" &&
                taskCount > 0
                    ? ` ${taskCount}`
                    : "";

            item.textContent =
                `${RESOURCE_LABELS[key]}${count} ${resourceState}`;

            fragment.append(item);
        }

        rail.replaceChildren(fragment);
        rail.dataset.vnextStatus = "true";
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

    function taskState(task) {
        const raw = lower(
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

    function taskObjective(task) {
        return asText(
            task?.objective ??
            task?.objective_id ??
            task?.root_objective ??
            task?.ancestry?.objective,
            "unknown objective"
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
                if (typeof entry === "string") {
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

    function dependentsOf(id, projection = coreProjection()) {
        const map = projection?.normalized?.dependents;

        if (map instanceof Map) {
            const values = map.get(id);
            return Array.isArray(values)
                ? values
                : [];
        }

        const result = [];

        for (const task of projectionTasks(projection)) {
            if (taskDependencies(task).includes(id)) {
                result.push(taskId(task));
            }
        }

        return result.filter(Boolean);
    }

    function selectedTask(projection = coreProjection()) {
        const id = selectedTaskId(projection);
        if (!id) {
            return null;
        }

        return projectionTaskMap(projection).get(id) ?? null;
    }

    function recommendedTask(projection = coreProjection()) {
        const id = recommendedTaskId(projection);
        if (!id) {
            return null;
        }

        return projectionTaskMap(projection).get(id) ?? null;
    }

    function unresolvedDependencies(
        task,
        projection = coreProjection()
    ) {
        if (!task) {
            return [];
        }

        const map = projectionTaskMap(projection);

        return taskDependencies(task)
            .filter((id) => {
                const dependency = map.get(id);

                return (
                    !dependency ||
                    taskState(dependency) !== "complete"
                );
            });
    }

    function evidenceSummary(task) {
        if (!task) {
            return "unknown";
        }

        const requirement =
            task?.completion_condition ??
            task?.completion ??
            task?.done_when ??
            task?.acceptance;

        const evidence =
            task?.evidence ??
            task?.receipts ??
            task?.completion_evidence ??
            task?.verification;

        if (
            evidence !== undefined &&
            evidence !== null &&
            evidence !== ""
        ) {
            return "available";
        }

        if (
            requirement !== undefined &&
            requirement !== null &&
            requirement !== ""
        ) {
            return "required / unresolved";
        }

        return "requirement unknown";
    }

    function setText(selector, value) {
        const target = $(selector);
        if (target) {
            target.textContent = value;
        }
    }

    function renderExecuteConsistency() {
        const projection = coreProjection();
        const recommendation = recommendedTask(projection);

        const action = $("#orientation-action");
        const stateLabel = $("#orientation-plain-state");
        const why = $("#orientation-why");
        const needs = $("#orientation-needs");
        const affects = $("#orientation-affects");
        const proof = $("#orientation-proof");

        if (!action) {
            return;
        }

        if (!recommendation) {
            action.textContent =
                "No executable recommendation is currently represented.";

            if (stateLabel) {
                stateLabel.textContent =
                    "The current core projection exposes no recommended task.";
            }

            if (why) {
                why.textContent = "unknown";
            }

            if (needs) {
                needs.textContent = "unknown";
            }

            if (affects) {
                affects.textContent = "unknown";
            }

            if (proof) {
                proof.textContent = "unknown";
            }

            return;
        }

        const id = taskId(recommendation);
        const unresolved =
            unresolvedDependencies(
                recommendation,
                projection
            );

        const dependents =
            dependentsOf(
                id,
                projection
            );

        action.textContent =
            taskTitle(recommendation);

        if (stateLabel) {
            stateLabel.textContent =
                `${taskState(recommendation)} · ${taskObjective(recommendation)}`;
        }

        if (why) {
            why.textContent =
                `${taskPriority(recommendation)} · ${taskState(recommendation)}`;
        }

        if (needs) {
            needs.textContent =
                unresolved.length
                    ? `${unresolved.length} unresolved`
                    : taskDependencies(recommendation).length
                        ? "represented prerequisites resolved"
                        : "no represented prerequisite";
        }

        if (affects) {
            affects.textContent =
                dependents.length
                    ? `${dependents.length} direct dependents`
                    : "no represented direct dependent";
        }

        if (proof) {
            proof.textContent =
                evidenceSummary(recommendation);
        }
    }

    function renderSelectionLabel() {
        const projection = coreProjection();
        const task = selectedTask(projection);
        const label =
            $("#causal-selection-label") ??
            $("#selected-task-label");

        if (!label) {
            return;
        }

        label.textContent =
            task
                ? taskTitle(task)
                : "No task selected";
    }

    function renderCausalCompanion() {
        const target = $("#causal-companion-body");

        if (!target) {
            return;
        }

        const projection = coreProjection();
        const task = selectedTask(projection);

        if (!task) {
            target.replaceChildren();

            const strong = document.createElement("strong");
            strong.textContent = "Select a represented task.";

            const copy = document.createElement("p");
            copy.textContent =
                "This panel explains represented prerequisites, dependents, objective context, and projection boundaries.";

            target.append(
                strong,
                copy
            );

            return;
        }

        const id = taskId(task);
        const unresolved =
            unresolvedDependencies(
                task,
                projection
            );

        const dependents =
            dependentsOf(
                id,
                projection
            );

        const dl = document.createElement("dl");

        const rows = [
            [
                "selected",
                taskTitle(task)
            ],
            [
                "state",
                taskState(task)
            ],
            [
                "objective",
                taskObjective(task)
            ],
            [
                "unresolved prerequisites",
                String(unresolved.length)
            ],
            [
                "direct dependents",
                String(dependents.length)
            ],
            [
                "priority",
                taskPriority(task)
            ],
            [
                "geometry",
                "projection only"
            ]
        ];

        for (const [term, value] of rows) {
            const dt = document.createElement("dt");
            const dd = document.createElement("dd");

            dt.textContent = term;
            dd.textContent = value;

            dl.append(
                dt,
                dd
            );
        }

        target.replaceChildren(dl);
    }

    function taskAuthorityClass(task) {
        const value =
            lower(
                task?.authority_effect ??
                task?.authority ??
                task?.authority_owner ??
                task?.task_authority_owner
            );

        if (
            value.includes("authoritative") ||
            value.includes("authority")
        ) {
            return "authoritative";
        }

        if (
            value.includes("derived")
        ) {
            return "derived";
        }

        if (
            value.includes("projection") ||
            value === "none"
        ) {
            return "projected";
        }

        return "unknown";
    }

    function taskIsExplicitCritical(task) {
        return (
            task?.critical_path === true ||
            task?.on_critical_path === true ||
            task?.critical === true ||
            lower(task?.path_class) ===
                "critical"
        );
    }

    function downstreamClosure(
        sourceId,
        projection
    ) {
        const visited =
            new Set();

        const queue =
            (
                dependentsOf(
                    sourceId,
                    projection
                ) ||
                []
            ).map((id) => ({
                id,
                depth: 1
            }));

        while (queue.length) {
            const current =
                queue.shift();

            if (
                !current?.id ||
                visited.has(
                    current.id
                )
            ) {
                continue;
            }

            visited.add(
                current.id
            );

            for (
                const next
                of dependentsOf(
                    current.id,
                    projection
                )
            ) {
                if (
                    !visited.has(next)
                ) {
                    queue.push({
                        id: next,
                        depth:
                            current.depth +
                            1
                    });
                }
            }
        }

        return visited;
    }

    function causalSubset(
        projection
    ) {
        const tasks =
            projectionTasks(
                projection
            );

        const taskMap =
            projectionTaskMap(
                projection
            );

        const selected =
            selectedTask(
                projection
            );

        if (
            state.causalMode ===
            "flow"
        ) {
            return [];
        }

        if (
            state.causalMode ===
            "dependencies"
        ) {
            if (!selected) {
                return [];
            }

            const selectedId =
                taskId(selected);

            const ids =
                new Set([
                    selectedId,
                    ...taskDependencies(
                        selected
                    ),
                    ...dependentsOf(
                        selectedId,
                        projection
                    )
                ]);

            return tasks.filter(
                (task) =>
                    ids.has(
                        taskId(task)
                    )
            );
        }

        if (
            state.causalMode ===
            "impact"
        ) {
            if (!selected) {
                return [];
            }

            const selectedId =
                taskId(selected);

            const ids =
                downstreamClosure(
                    selectedId,
                    projection
                );

            ids.add(
                selectedId
            );

            return tasks.filter(
                (task) =>
                    ids.has(
                        taskId(task)
                    )
            );
        }

        if (
            state.causalMode ===
            "objective"
        ) {
            if (!selected) {
                return [];
            }

            const objective =
                taskObjective(
                    selected
                );

            return tasks.filter(
                (task) =>
                    taskObjective(
                        task
                    ) === objective
            );
        }

        if (
            state.causalMode ===
            "critical"
        ) {
            return tasks.filter(
                taskIsExplicitCritical
            );
        }

        if (
            state.causalMode ===
            "blockers"
        ) {
            const ids =
                new Set();

            for (
                const task
                of tasks
            ) {
                const unresolved =
                    unresolvedDependencies(
                        task,
                        projection
                    );

                if (
                    taskState(task) ===
                        "blocked" ||
                    unresolved.length
                ) {
                    ids.add(
                        taskId(task)
                    );

                    for (
                        const dependency
                        of unresolved
                    ) {
                        if (
                            taskMap.has(
                                dependency
                            )
                        ) {
                            ids.add(
                                dependency
                            );
                        }
                    }
                }
            }

            return tasks.filter(
                (task) =>
                    ids.has(
                        taskId(task)
                    )
            );
        }

        return tasks;
    }

    function causalEdges(
        subset
    ) {
        const included =
            new Set(
                subset.map(
                    taskId
                )
            );

        const edges = [];

        for (
            const task
            of subset
        ) {
            const target =
                taskId(task);

            for (
                const source
                of taskDependencies(
                    task
                )
            ) {
                if (
                    included.has(source)
                ) {
                    edges.push({
                        source,
                        target,
                        type:
                            "dependency"
                    });
                }
            }
        }

        edges.sort(
            (a, b) =>
                a.source.localeCompare(
                    b.source
                ) ||
                a.target.localeCompare(
                    b.target
                )
        );

        return edges;
    }

    function causalDepths(
        subset,
        edges
    ) {
        const ids =
            subset
                .map(taskId)
                .sort(
                    (a, b) =>
                        a.localeCompare(b)
                );

        const incoming =
            new Map(
                ids.map((id) => [
                    id,
                    []
                ])
            );

        for (
            const edge
            of edges
        ) {
            incoming
                .get(edge.target)
                ?.push(edge.source);
        }

        const memo =
            new Map();

        const visiting =
            new Set();

        function depth(id) {
            if (
                memo.has(id)
            ) {
                return memo.get(
                    id
                );
            }

            if (
                visiting.has(id)
            ) {
                return 0;
            }

            visiting.add(id);

            let value = 0;

            const sources =
                (
                    incoming.get(id) ||
                    []
                )
                    .slice()
                    .sort(
                        (a, b) =>
                            a.localeCompare(b)
                    );

            for (
                const source
                of sources
            ) {
                value =
                    Math.max(
                        value,
                        depth(source) +
                            1
                    );
            }

            visiting.delete(id);
            memo.set(
                id,
                value
            );

            return value;
        }

        for (
            const id
            of ids
        ) {
            depth(id);
        }

        return memo;
    }

    function dependencyFocusLayout(
        subset,
        projection
    ) {
        const selected =
            selectedTask(
                projection
            );

        if (!selected) {
            return null;
        }

        const selectedId =
            taskId(selected);

        const taskMap =
            projectionTaskMap(
                projection
            );

        const prerequisites =
            taskDependencies(
                selected
            )
                .filter((id) =>
                    taskMap.has(id)
                )
                .sort(
                    (a, b) =>
                        a.localeCompare(b)
                );

        const dependents =
            dependentsOf(
                selectedId,
                projection
            )
                .filter((id) =>
                    taskMap.has(id)
                )
                .sort(
                    (a, b) =>
                        a.localeCompare(b)
                );

        const columns = [
            prerequisites,
            [selectedId],
            dependents
        ];

        const nodeWidth =
            230;

        const nodeHeight =
            68;

        const columnGap =
            125;

        const rowGap =
            28;

        const padding =
            70;

        const positions =
            new Map();

        let maxRows = 1;

        columns.forEach(
            (
                ids,
                column
            ) => {
                maxRows =
                    Math.max(
                        maxRows,
                        ids.length
                    );

                ids.forEach(
                    (
                        id,
                        row
                    ) => {
                        positions.set(
                            id,
                            {
                                x:
                                    padding +
                                    column *
                                        (
                                            nodeWidth +
                                            columnGap
                                        ),
                                y:
                                    padding +
                                    row *
                                        (
                                            nodeHeight +
                                            rowGap
                                        ),
                                width:
                                    nodeWidth,
                                height:
                                    nodeHeight
                            }
                        );
                    }
                );
            }
        );

        return {
            positions,
            width:
                padding *
                    2 +
                columns.length *
                    nodeWidth +
                (
                    columns.length -
                    1
                ) *
                    columnGap,
            height:
                padding *
                    2 +
                maxRows *
                    nodeHeight +
                Math.max(
                    0,
                    maxRows -
                        1
                ) *
                    rowGap
        };
    }

    function deterministicLayeredLayout(
        subset,
        edges
    ) {
        const depthMap =
            causalDepths(
                subset,
                edges
            );

        const groups =
            new Map();

        for (
            const task
            of subset
        ) {
            const id =
                taskId(task);

            const depth =
                depthMap.get(id) ??
                0;

            if (
                !groups.has(depth)
            ) {
                groups.set(
                    depth,
                    []
                );
            }

            groups
                .get(depth)
                .push(task);
        }

        for (
            const group
            of groups.values()
        ) {
            group.sort(
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
        }

        const depths =
            Array.from(
                groups.keys()
            ).sort(
                (a, b) =>
                    a - b
            );

        const nodeWidth =
            228;

        const nodeHeight =
            68;

        const columnGap =
            118;

        const rowGap =
            26;

        const padding =
            72;

        const positions =
            new Map();

        let maxRows = 1;

        depths.forEach(
            (
                depth,
                columnIndex
            ) => {
                const group =
                    groups.get(depth) ||
                    [];

                maxRows =
                    Math.max(
                        maxRows,
                        group.length
                    );

                group.forEach(
                    (
                        task,
                        rowIndex
                    ) => {
                        positions.set(
                            taskId(task),
                            {
                                x:
                                    padding +
                                    columnIndex *
                                        (
                                            nodeWidth +
                                            columnGap
                                        ),
                                y:
                                    padding +
                                    rowIndex *
                                        (
                                            nodeHeight +
                                            rowGap
                                        ),
                                width:
                                    nodeWidth,
                                height:
                                    nodeHeight
                            }
                        );
                    }
                );
            }
        );

        return {
            positions,
            width:
                padding *
                    2 +
                Math.max(
                    1,
                    depths.length
                ) *
                    nodeWidth +
                Math.max(
                    0,
                    depths.length -
                        1
                ) *
                    columnGap,
            height:
                padding *
                    2 +
                maxRows *
                    nodeHeight +
                Math.max(
                    0,
                    maxRows -
                        1
                ) *
                    rowGap
        };
    }

    function causalLayout(
        subset,
        edges,
        projection
    ) {
        if (
            state.causalMode ===
            "dependencies"
        ) {
            return (
                dependencyFocusLayout(
                    subset,
                    projection
                ) ||
                deterministicLayeredLayout(
                    subset,
                    edges
                )
            );
        }

        return deterministicLayeredLayout(
            subset,
            edges
        );
    }

    function causalPath(
        source,
        target
    ) {
        const sx =
            source.x +
            source.width;

        const sy =
            source.y +
            source.height / 2;

        const tx =
            target.x;

        const ty =
            target.y +
            target.height / 2;

        const bend =
            sx +
            Math.max(
                44,
                (
                    tx - sx
                ) /
                    2
            );

        return (
            `M ${sx} ${sy} ` +
            `C ${bend} ${sy}, ` +
            `${bend} ${ty}, ` +
            `${tx} ${ty}`
        );
    }

    function causalEmptyMessage(
        projection,
        subset
    ) {
        const selected =
            selectedTask(
                projection
            );

        if (
            [
                "dependencies",
                "impact",
                "objective"
            ].includes(
                state.causalMode
            ) &&
            !selected
        ) {
            return (
                "NO TASK SELECTED\n" +
                "Select a represented task to answer this causal question."
            );
        }

        if (
            state.causalMode ===
                "critical" &&
            subset.length ===
                0
        ) {
            return (
                "NO EXPLICIT CRITICAL PATH REPRESENTED\n" +
                "The current task projection does not expose critical-path membership."
            );
        }

        if (
            state.causalMode ===
                "blockers" &&
            subset.length ===
                0
        ) {
            return (
                "NO REPRESENTED BLOCKERS\n" +
                "No loaded task currently exposes a blocked state or unresolved represented prerequisite."
            );
        }

        return (
            "NO REPRESENTED CAUSAL DATA\n" +
            "This mode has no represented task relationships to display."
        );
    }

    function renderCausalEmpty(
        message
    ) {
        const nodes =
            $("#graph-nodes");

        const edges =
            $("#graph-edges");

        if (
            !nodes ||
            !edges
        ) {
            return;
        }

        edges.replaceChildren();
        nodes.replaceChildren();

        const panel =
            document.createElement(
                "div"
            );

        panel.className =
            "causal-projection-empty";

        const [
            title,
            ...rest
        ] =
            message.split(
                "\n"
            );

        const strong =
            document.createElement(
                "strong"
            );

        strong.textContent =
            title;

        const copy =
            document.createElement(
                "span"
            );

        copy.textContent =
            rest.join(" ");

        panel.append(
            strong,
            copy
        );

        nodes.style.width =
            "100%";

        nodes.style.height =
            "100%";

        nodes.append(
            panel
        );

        state.causal.nodes =
            new Map();

        state.causal.edges =
            [];
    }

    function renderCausalField() {
        if (
            state.causalMode ===
            "flow"
        ) {
            return;
        }

        const stage =
            $("#graph-stage");

        const nodes =
            $("#graph-nodes");

        const edgesSvg =
            $("#graph-edges");

        if (
            !stage ||
            !nodes ||
            !edgesSvg
        ) {
            return;
        }

        const projection =
            coreProjection();

        if (!projection) {
            renderCausalEmpty(
                "CAUSAL FIELD DEGRADED\nCore task projection is unavailable."
            );

            return;
        }

        const subset =
            causalSubset(
                projection
            );

        if (
            subset.length ===
            0
        ) {
            renderCausalEmpty(
                causalEmptyMessage(
                    projection,
                    subset
                )
            );

            setText(
                "#constellation-summary",
                "no represented causal projection"
            );

            return;
        }

        const edges =
            causalEdges(
                subset
            );

        const layout =
            causalLayout(
                subset,
                edges,
                projection
            );

        state.causal.worldWidth =
            Math.max(
                1,
                layout.width
            );

        state.causal.worldHeight =
            Math.max(
                1,
                layout.height
            );

        state.causal.nodes =
            layout.positions;

        state.causal.edges =
            edges;

        nodes.style.width =
            `${state.causal.worldWidth}px`;

        nodes.style.height =
            `${state.causal.worldHeight}px`;

        edgesSvg.setAttribute(
            "width",
            String(
                state.causal.worldWidth
            )
        );

        edgesSvg.setAttribute(
            "height",
            String(
                state.causal.worldHeight
            )
        );

        edgesSvg.setAttribute(
            "viewBox",
            `0 0 ${state.causal.worldWidth} ${state.causal.worldHeight}`
        );

        edgesSvg.style.width =
            `${state.causal.worldWidth}px`;

        edgesSvg.style.height =
            `${state.causal.worldHeight}px`;

        const edgeFragment =
            document.createDocumentFragment();

        for (
            const edge
            of edges
        ) {
            const source =
                layout.positions.get(
                    edge.source
                );

            const target =
                layout.positions.get(
                    edge.target
                );

            if (
                !source ||
                !target
            ) {
                continue;
            }

            const path =
                document.createElementNS(
                    "http://www.w3.org/2000/svg",
                    "path"
                );

            path.setAttribute(
                "d",
                causalPath(
                    source,
                    target
                )
            );

            path.setAttribute(
                "class",
                "graph-edge"
            );

            path.setAttribute(
                "vector-effect",
                "non-scaling-stroke"
            );

            path.dataset.sourceTaskId =
                edge.source;

            path.dataset.targetTaskId =
                edge.target;

            edgeFragment.append(
                path
            );
        }

        const nodeFragment =
            document.createDocumentFragment();

        const selectedId =
            selectedTaskId(
                projection
            );

        for (
            const task
            of subset
        ) {
            const id =
                taskId(task);

            const position =
                layout.positions.get(
                    id
                );

            if (!position) {
                continue;
            }

            const node =
                document.createElement(
                    "button"
                );

            node.type =
                "button";

            node.className =
                `graph-node ${taskState(task)}`;

            node.dataset.taskId =
                id;

            node.dataset.state =
                taskState(task);

            node.dataset.objective =
                taskObjective(task);

            node.dataset.authority =
                taskAuthorityClass(
                    task
                );

            if (
                id ===
                selectedId
            ) {
                node.dataset.selected =
                    "true";
            }

            node.style.left =
                `${position.x}px`;

            node.style.top =
                `${position.y}px`;

            node.style.width =
                `${position.width}px`;

            node.style.height =
                `${position.height}px`;

            node.setAttribute(
                "aria-label",
                `${taskTitle(task)}. State ${taskState(task)}. Objective ${taskObjective(task)}.`
            );

            const title =
                document.createElement(
                    "strong"
                );

            title.textContent =
                taskTitle(task);

            const meta =
                document.createElement(
                    "small"
                );

            meta.textContent =
                state.causalMode ===
                "authority"
                    ? `${taskAuthorityClass(task)} · ${taskPriority(task)}`
                    : `${taskState(task)} · ${taskPriority(task)}`;

            node.append(
                title,
                meta
            );

            nodeFragment.append(
                node
            );
        }

        edgesSvg.replaceChildren(
            edgeFragment
        );

        nodes.replaceChildren(
            nodeFragment
        );

        setText(
            "#constellation-summary",
            `${subset.length} represented tasks · ${edges.length} represented dependency edges · deterministic projection`
        );

        applyCausalTransform();
    }

    function measureCausalStage() {
        const stage =
            $("#graph-stage");

        const rectangle =
            stage?.getBoundingClientRect();

        if (
            !rectangle ||
            rectangle.width <
                160 ||
            rectangle.height <
                180
        ) {
            return false;
        }

        state.causal.width =
            rectangle.width;

        state.causal.height =
            rectangle.height;

        return true;
    }

    function fitCausalField() {
        if (
            !measureCausalStage() ||
            state.causal.worldWidth <=
                1 ||
            state.causal.worldHeight <=
                1
        ) {
            return;
        }

        const padding =
            state.causal.width <
            560
                ? 24
                : 48;

        const scale =
            clampZoom(
                Math.min(
                    (
                        state.causal.width -
                        padding *
                            2
                    ) /
                        state.causal.worldWidth,
                    (
                        state.causal.height -
                        padding *
                            2
                    ) /
                        state.causal.worldHeight
                )
            );

        state.causalZoom =
            scale;

        state.causal.x =
            (
                state.causal.width -
                state.causal.worldWidth *
                    scale
            ) /
            2;

        state.causal.y =
            (
                state.causal.height -
                state.causal.worldHeight *
                    scale
            ) /
            2;

        safeWrite(
            STORAGE.causalZoom,
            String(scale)
        );

        queueCausalTransform();
    }

    function focusCausalTask(
        id
    ) {
        const position =
            state.causal.nodes.get(
                id
            );

        if (
            !position ||
            !measureCausalStage()
        ) {
            return;
        }

        const scale =
            clampZoom(
                Math.max(
                    state.causalZoom,
                    1.05
                )
            );

        state.causalZoom =
            scale;

        state.causal.x =
            state.causal.width /
                2 -
            (
                position.x +
                position.width /
                    2
            ) *
                scale;

        state.causal.y =
            state.causal.height /
                2 -
            (
                position.y +
                position.height /
                    2
            ) *
                scale;

        queueCausalTransform();
    }

    function bindCausalStageInteraction() {
        const stage =
            $("#graph-stage");

        if (
            !stage ||
            stage.dataset.causalInteractionBound ===
                "true"
        ) {
            return;
        }

        stage.dataset.causalInteractionBound =
            "true";

        stage.addEventListener(
            "click",
            (event) => {
                const node =
                    event.target.closest?.(
                        "[data-task-id]"
                    );

                const id =
                    asText(
                        node?.dataset
                            ?.taskId
                    );

                if (
                    !id ||
                    !window.Niche ||
                    typeof window.Niche.task !==
                        "function"
                ) {
                    return;
                }

                window.Niche.task(
                    id
                );

                focusCausalTask(
                    id
                );
            }
        );

        stage.addEventListener(
            "wheel",
            (event) => {
                event.preventDefault();

                applyCausalZoom(
                    state.causalZoom *
                    Math.exp(
                        -event.deltaY *
                        0.0012
                    ),
                    {
                        clientX:
                            event.clientX,
                        clientY:
                            event.clientY
                    }
                );
            },
            {
                passive:
                    false
            }
        );

        stage.addEventListener(
            "pointerdown",
            (event) => {
                if (
                    event.button !==
                        0 &&
                    event.pointerType ===
                        "mouse"
                ) {
                    return;
                }

                state.causal.pointerId =
                    event.pointerId;

                state.causal.pointerStartX =
                    event.clientX;

                state.causal.pointerStartY =
                    event.clientY;

                state.causal.pointerOriginX =
                    state.causal.x;

                state.causal.pointerOriginY =
                    state.causal.y;

                stage.setPointerCapture?.(
                    event.pointerId
                );
            }
        );

        stage.addEventListener(
            "pointermove",
            (event) => {
                if (
                    state.causal.pointerId !==
                    event.pointerId
                ) {
                    return;
                }

                state.causal.x =
                    state.causal.pointerOriginX +
                    (
                        event.clientX -
                        state.causal.pointerStartX
                    );

                state.causal.y =
                    state.causal.pointerOriginY +
                    (
                        event.clientY -
                        state.causal.pointerStartY
                    );

                queueCausalTransform();
            }
        );

        const release =
            (event) => {
                if (
                    state.causal.pointerId ===
                    event.pointerId
                ) {
                    state.causal.pointerId =
                        null;
                }
            };

        stage.addEventListener(
            "pointerup",
            release
        );

        stage.addEventListener(
            "pointercancel",
            release
        );

        stage.addEventListener(
            "keydown",
            (event) => {
                if (
                    event.key ===
                    "0"
                ) {
                    event.preventDefault();
                    fitCausalField();
                }
            }
        );
    }

    function installCausalResizeObserver() {
        const stage =
            $("#graph-stage");

        if (
            !stage ||
            state.causal.resizeObserver
        ) {
            return;
        }

        if (
            "ResizeObserver" in
            window
        ) {
            state.causal.resizeObserver =
                new ResizeObserver(
                    () => {
                        if (
                            state.causal.active &&
                            measureCausalStage()
                        ) {
                            if (
                                !state.causal.firstFit
                            ) {
                                state.causal.firstFit =
                                    true;

                                fitCausalField();
                            } else {
                                queueCausalTransform();
                            }
                        }
                    }
                );

            state.causal.resizeObserver.observe(
                stage
            );
        }
    }

    function activateCausalField() {
        state.causal.active =
            true;

        bindCausalStageInteraction();
        installCausalResizeObserver();

        requestAnimationFrame(
            () => {
                if (
                    !measureCausalStage()
                ) {
                    return;
                }

                renderCausalField();

                if (
                    !state.causal.firstFit
                ) {
                    state.causal.firstFit =
                        true;

                    fitCausalField();
                } else {
                    queueCausalTransform();
                }
            }
        );
    }

    function deactivateCausalField() {
        state.causal.active =
            false;
    }

    function updateCausalModeState() {
        const projection =
            coreProjection();

        const task =
            selectedTask(
                projection
            );

        const stage =
            $("#graph-stage");

        if (!stage) {
            return;
        }

        stage.dataset.causalMode =
            state.causalMode;

        stage.dataset.selectedTaskId =
            task
                ? taskId(task)
                : "";

        renderCausalField();

        if (
            state.causal.active &&
            measureCausalStage()
        ) {
            fitCausalField();
        }
    }

    function objectiveCards() {
        return $$("#objective-grid > *");
    }

    function applyObjectiveFilters() {
        const query = lower(state.objectiveSearch);

        for (const card of objectiveCards()) {
            const text = lower(card.textContent);

            const queryMatch =
                !query ||
                text.includes(query);

            const filter =
                state.objectiveFilter;

            const filterMatch =
                filter === "all" ||
                card.dataset.state === filter ||
                card.dataset.objectiveState === filter ||
                text.includes(filter);

            card.hidden =
                !(queryMatch && filterMatch);
        }
    }

    function bindObjectiveControls() {
        const search = $("#objective-search");

        if (search && search.dataset.vnextBound !== "true") {
            search.dataset.vnextBound = "true";
            search.value = state.objectiveSearch;

            search.addEventListener(
                "input",
                () => {
                    state.objectiveSearch =
                        search.value.trim();

                    safeWrite(
                        STORAGE.objectiveSearch,
                        state.objectiveSearch
                    );

                    applyObjectiveFilters();
                }
            );
        }

        for (const button of $$("[data-objective-filter]")) {
            if (button.dataset.vnextBound === "true") {
                continue;
            }

            button.dataset.vnextBound = "true";

            button.addEventListener(
                "click",
                () => {
                    state.objectiveFilter =
                        asText(
                            button.dataset.objectiveFilter,
                            "all"
                        );

                    safeWrite(
                        STORAGE.objectiveFilter,
                        state.objectiveFilter
                    );

                    for (const candidate of $$("[data-objective-filter]")) {
                        candidate.classList.toggle(
                            "active",
                            candidate === button
                        );
                    }

                    applyObjectiveFilters();

                    emit(
                        "objective-filter",
                        {
                            filter: state.objectiveFilter
                        }
                    );
                }
            );
        }
    }

    function goToView(view) {
        if (
            view === "navigation" &&
            window.NicheNavigation &&
            typeof window.NicheNavigation.open === "function"
        ) {
            window.NicheNavigation.open();
            return;
        }

        if (
            window.Niche &&
            typeof window.Niche.view === "function"
        ) {
            window.Niche.view(view);
            return;
        }

        $(`.nav [data-view="${view}"]`)?.click();
    }

    function bindViewShortcuts() {
        const destinations = Object.freeze({
            e: "execute",
            n: "navigation",
            c: "causal",
            o: "objectives",
            t: "timeline",
            v: "evidence",
            l: "living",
            h: "history"
        });

        document.addEventListener(
            "keydown",
            (event) => {
                if (
                    event.ctrlKey ||
                    event.metaKey ||
                    event.altKey ||
                    event.target instanceof HTMLInputElement ||
                    event.target instanceof HTMLTextAreaElement ||
                    event.target instanceof HTMLSelectElement ||
                    event.target?.isContentEditable
                ) {
                    return;
                }

                const key = lower(event.key);

                if (key === "g") {
                    state.pendingGo = true;

                    window.clearTimeout(
                        state.pendingGoTimer
                    );

                    state.pendingGoTimer =
                        window.setTimeout(
                            () => {
                                state.pendingGo = false;
                            },
                            900
                        );

                    return;
                }

                if (
                    state.pendingGo &&
                    destinations[key]
                ) {
                    event.preventDefault();

                    state.pendingGo = false;

                    window.clearTimeout(
                        state.pendingGoTimer
                    );

                    goToView(
                        destinations[key]
                    );

                    return;
                }

                state.pendingGo = false;
            }
        );
    }

    function bindControls() {
        const theme = $("#niche-theme");

        if (theme && theme.dataset.vnextBound !== "true") {
            theme.dataset.vnextBound = "true";

            theme.addEventListener(
                "change",
                () => {
                    applyTheme(theme.value);
                }
            );
        }

        for (const button of $$("[data-causal-mode]")) {
            if (button.dataset.vnextBound === "true") {
                continue;
            }

            button.dataset.vnextBound = "true";

            button.addEventListener(
                "click",
                () => {
                    applyCausalMode(
                        button.dataset.causalMode
                    );
                }
            );
        }

        for (const button of $$("[data-causal-viewport]")) {
            if (button.dataset.vnextBound === "true") {
                continue;
            }

            button.dataset.vnextBound = "true";

            button.addEventListener(
                "click",
                () => {
                    const action =
                        button.dataset.causalViewport;

                    if (action === "zoom-in") {
                        applyCausalZoom(
                            state.causalZoom + 0.1
                        );
                    } else if (action === "zoom-out") {
                        applyCausalZoom(
                            state.causalZoom - 0.1
                        );
                    } else {
                        applyCausalZoom(1);
                    }
                }
            );
        }

        bindObjectiveControls();
    }

    function syncFromCore() {
        const projection = coreProjection();

        if (!projection) {
            renderStatusRail();
            return;
        }

        const generation =
            Number(
                projection.requestGeneration
            );

        if (
            Number.isFinite(generation) &&
            generation < state.lastProjectionGeneration
        ) {
            return;
        }

        if (Number.isFinite(generation)) {
            state.lastProjectionGeneration =
                generation;
        }

        const selected =
            selectedTaskId(projection);

        const view =
            activeView(projection);

        const selectionChanged =
            selected !== state.lastSelectedTaskId;

        const viewChanged =
            view !== state.lastActiveView;

        state.lastSelectedTaskId = selected;
        state.lastActiveView = view;

        renderStatusRail();
        renderExecuteConsistency();
        renderSelectionLabel();
        renderCausalCompanion();
        updateCausalModeState();
        applyObjectiveFilters();

        if (selectionChanged) {
            emit(
                "selection-sync",
                {
                    task_id: selected
                }
            );
        }

        if (viewChanged) {
            if (view === "causal") {
                activateCausalField();
            } else {
                deactivateCausalField();
            }

            emit(
                "view-sync",
                {
                    view
                }
            );
        } else if (
            view === "causal" &&
            state.causal.active
        ) {
            renderCausalField();
        }
    }

    function queueCoreSync() {
        if (state.renderQueued) {
            return;
        }

        state.renderQueued = true;

        requestAnimationFrame(
            () => {
                state.renderQueued = false;
                syncFromCore();
            }
        );
    }

    function bindCoreEvents() {
        const events = [
            "niche:lifecycle",
            "niche:projection",
            "niche:view",
            "niche:task-selected"
        ];

        for (const eventName of events) {
            window.addEventListener(
                eventName,
                queueCoreSync
            );
        }

        window.addEventListener(
            "niche:navigation:selection",
            (event) => {
                const id = asText(
                    event.detail?.task_id
                );

                if (
                    id &&
                    window.Niche &&
                    typeof window.Niche.task === "function"
                ) {
                    window.Niche.task(id);
                }
            }
        );
    }

    function restoreState() {
        applyTheme(
            safeRead(STORAGE.theme) ||
                "nexus",
            {
                persist: false
            }
        );

        applyCausalMode(
            safeRead(STORAGE.causalMode) ||
                "flow",
            {
                persist: false
            }
        );

        applyCausalZoom(
            safeRead(STORAGE.causalZoom) ||
                1,
            {
                persist: false
            }
        );

        state.objectiveFilter =
            asText(
                safeRead(STORAGE.objectiveFilter),
                "all"
            );

        state.objectiveSearch =
            asText(
                safeRead(STORAGE.objectiveSearch)
            );
    }

    function initialize() {
        if (state.installed) {
            return;
        }

        state.installed = true;

        restoreState();
        bindControls();
        bindViewShortcuts();
        bindCoreEvents();
        bindCausalStageInteraction();
        installCausalResizeObserver();
        syncFromCore();

        if (activeView() === "causal") {
            activateCausalField();
        }

        document.documentElement.dataset.nicheVnext =
            "ready";

        emit(
            "ready",
            {
                theme: state.theme,
                causal_mode: state.causalMode
            }
        );
    }

    if (document.readyState === "loading") {
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

    window.NicheVnext = Object.freeze({
        state() {
            return Object.freeze({
                installed: state.installed,
                theme: state.theme,
                causalMode: state.causalMode,
                causalZoom: state.causalZoom,
                selectedTaskId:
                    selectedTaskId(),
                recommendedTaskId:
                    recommendedTaskId(),
                activeView:
                    activeView(),
                projectionGeneration:
                    state.lastProjectionGeneration,
                causalViewport:
                    Object.freeze({
                        x: state.causal.x,
                        y: state.causal.y,
                        scale: state.causalZoom,
                        worldWidth:
                            state.causal.worldWidth,
                        worldHeight:
                            state.causal.worldHeight,
                        active:
                            state.causal.active
                    }),
                authorityEffect: "none",
                projectionOnly: true
            });
        },

        theme: applyTheme,
        causalMode: applyCausalMode,
        causalZoom: applyCausalZoom,

        view(view) {
            goToView(
                asText(view)
            );
        },

        task(id) {
            const normalized = asText(id);

            if (
                normalized &&
                window.Niche &&
                typeof window.Niche.task === "function"
            ) {
                window.Niche.task(normalized);
            }
        },

        refresh() {
            if (
                window.Niche &&
                typeof window.Niche.refresh === "function"
            ) {
                return window.Niche.refresh();
            }

            return Promise.resolve();
        },

        sync: syncFromCore
    });
})();
