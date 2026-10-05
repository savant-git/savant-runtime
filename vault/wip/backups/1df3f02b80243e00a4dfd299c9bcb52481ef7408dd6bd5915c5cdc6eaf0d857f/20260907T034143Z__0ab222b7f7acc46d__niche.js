"use strict";

/*
 * savant / niche
 * executable task environment
 *
 * projection/interface owner: exile:niche
 * authority_effect: none
 *
 * Niche reads authoritative/projection state exposed by the existing API.
 * State mutation occurs only through explicit API transitions initiated
 * by the operator.
 */

(() => {
    const API = Object.freeze({
        health: "/api/health",
        dashboard: "/api/dashboard",
        state: "/api/state",
        tasks: "/api/tasks?include_terminal=true",
        history: "/api/history",
        living: "/api/living",
        fabric: "/api/living/fabric"
    });



    const RESOURCE_STATE = Object.freeze({
        unknown: "unknown",
        loading: "loading",
        available: "available",
        degraded: "degraded",
        unavailable: "unavailable"
    });

    const LIFECYCLE = Object.freeze({
        dormant: "dormant",
        booting: "booting",
        coreReady: "core_ready",
        dataLoading: "data_loading",
        available: "available",
        degraded: "degraded",
        unavailable: "unavailable"
    });

    const LANES = Object.freeze([
        "ready",
        "active",
        "blocked",
        "waiting",
        "review",
        "complete"
    ]);

    const state = {
        health: null,
        dashboard: null,
        taskState: null,
        tasks: [],
        history: [],
        living: null,
        fabric: null,

        taskById: new Map(),
        dependents: new Map(),

        selectedTaskId: null,
        recommendedTaskId: null,
        activeView: "execute",

        paletteIndex: 0,
        paletteItems: [],

        transitionTaskId: null,

        graph: {
            scale: 1,
            x: 0,
            y: 0
        },

        refreshController: null,
        refreshTimer: null,
        refreshPromise: null,
        refreshing: false,
        requestGeneration: 0,
        initialized: false,
        lifecycle: LIFECYCLE.dormant,
        resources: {
            health: RESOURCE_STATE.unknown,
            dashboard: RESOURCE_STATE.unknown,
            state: RESOURCE_STATE.unknown,
            tasks: RESOURCE_STATE.unknown,
            history: RESOURCE_STATE.unknown,
            living: RESOURCE_STATE.unknown,
            fabric: RESOURCE_STATE.unknown
        },
        resourceErrors: new Map(),
        lastRefreshAt: null,
        lastDigest: "",
        lastChangedIds: new Set()
    };

    const $ = (selector, root = document) =>
        root.querySelector(selector);

    const $$ = (selector, root = document) =>
        Array.from(root.querySelectorAll(selector));

    function text(value, fallback = "unknown") {
        if (
            value === null ||
            value === undefined ||
            value === ""
        ) {
            return fallback;
        }

        return String(value);
    }

    function array(value) {
        return Array.isArray(value) ? value : [];
    }

    function object(value) {
        return value && typeof value === "object"
            ? value
            : {};
    }

    function first(...values) {
        for (const value of values) {
            if (
                value !== undefined &&
                value !== null &&
                value !== ""
            ) {
                return value;
            }
        }

        return null;
    }

    function number(value, fallback = 0) {
        const parsed = Number(value);

        return Number.isFinite(parsed)
            ? parsed
            : fallback;
    }

    function bool(value) {
        return value === true;
    }

    function lower(value) {
        return text(value, "").toLowerCase();
    }

    function clamp(value, min, max) {
        return Math.min(max, Math.max(min, value));
    }

    function taskId(task) {
        return text(
            first(
                task.id,
                task.task_id,
                task.identity,
                task.key
            ),
            ""
        );
    }

    function taskTitle(task) {
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

    function taskState(task) {
        const raw = lower(
            first(
                task.state,
                task.status,
                task.lifecycle_state
            )
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

    function taskReady(task) {
        const value = first(
            task.ready,
            task.is_ready,
            task.readiness
        );

        if (typeof value === "boolean") {
            return value;
        }

        const normalized = lower(value);

        return (
            normalized === "ready" ||
            normalized === "true" ||
            normalized === "yes"
        );
    }

    function taskPriority(task) {
        return text(
            first(
                task.priority,
                task.authoritative_priority,
                task.rank
            ),
            "unknown"
        );
    }

    function taskObjective(task) {
        return text(
            first(
                task.objective,
                task.objective_id,
                task.root_objective,
                task.ancestry?.objective
            ),
            "unknown objective"
        );
    }

    function taskParent(task) {
        return first(
            task.parent,
            task.parent_id,
            task.parent_task_id,
            task.ancestry?.parent
        );
    }

    function taskDependencies(task) {
        const candidate = first(
            task.dependencies,
            task.depends_on,
            task.prerequisites,
            task.requires
        );

        if (Array.isArray(candidate)) {
            return candidate.map((item) => {
                if (typeof item === "string") {
                    return item;
                }

                return text(
                    first(
                        item.id,
                        item.task_id,
                        item.key
                    ),
                    ""
                );
            }).filter(Boolean);
        }

        return [];
    }

    function taskBlockers(task) {
        const candidate = first(
            task.blockers,
            task.blocked_by
        );

        if (Array.isArray(candidate)) {
            return candidate;
        }

        if (candidate) {
            return [candidate];
        }

        return [];
    }

    function taskEvidence(task) {
        return first(
            task.evidence,
            task.receipts,
            task.completion_evidence,
            task.verification
        );
    }

    function taskCompletion(task) {
        return first(
            task.completion_condition,
            task.completion,
            task.done_when,
            task.acceptance
        );
    }

    function priorityWeight(priority) {
        const normalized = lower(priority);

        if (
            normalized === "critical" ||
            normalized === "p0"
        ) {
            return 1000;
        }

        if (
            normalized === "high" ||
            normalized === "p1"
        ) {
            return 750;
        }

        if (
            normalized === "medium" ||
            normalized === "normal" ||
            normalized === "p2"
        ) {
            return 500;
        }

        if (
            normalized === "low" ||
            normalized === "p3"
        ) {
            return 250;
        }

        const numeric = Number(priority);

        if (Number.isFinite(numeric)) {
            return 600 - numeric;
        }

        return 0;
    }

    function dependencyIds(task) {
        return taskDependencies(task);
    }

    function unresolvedDependencies(task) {
        return dependencyIds(task).filter((id) => {
            const dependency = state.taskById.get(id);

            if (!dependency) {
                return true;
            }

            return taskState(dependency) !== "complete";
        });
    }

    function dependentIds(id) {
        return array(state.dependents.get(id));
    }

    function downstreamCount(id, visited = new Set()) {
        if (!id || visited.has(id)) {
            return 0;
        }

        visited.add(id);

        let total = 0;

        for (const dependent of dependentIds(id)) {
            total += 1;
            total += downstreamCount(dependent, visited);
        }

        return total;
    }

    function recommendationScore(task) {
        if (taskState(task) === "complete") {
            return -Infinity;
        }

        let score = priorityWeight(taskPriority(task));

        if (taskReady(task)) {
            score += 500;
        }

        if (taskState(task) === "active") {
            score += 650;
        }

        if (taskState(task) === "blocked") {
            score -= 5000;
        }

        const unresolved = unresolvedDependencies(task);

        score -= unresolved.length * 1000;
        score += downstreamCount(taskId(task)) * 8;

        return score;
    }

    function recommendationReason(task) {
        if (!task) {
            return "No legitimate executable task is currently exposed.";
        }

        const reasons = [];

        if (taskState(task) === "active") {
            reasons.push("already active");
        }

        if (taskReady(task)) {
            reasons.push("reported ready");
        }

        const priority = taskPriority(task);

        if (priority !== "unknown") {
            reasons.push(`priority ${priority}`);
        }

        const unresolved = unresolvedDependencies(task);

        if (!unresolved.length) {
            reasons.push("no unresolved dependency visible");
        }

        const unlocks = downstreamCount(taskId(task));

        if (unlocks > 0) {
            reasons.push(`${unlocks} downstream task${unlocks === 1 ? "" : "s"}`);
        }

        if (!reasons.length) {
            return "Recommendation is based only on available task state. Missing factors remain unknown.";
        }

        return `${reasons.join("; ")}.`;
    }

    function rebuildIndexes() {
        state.taskById = new Map();
        state.dependents = new Map();

        for (const task of state.tasks) {
            const id = taskId(task);

            if (id) {
                state.taskById.set(id, task);
            }
        }

        for (const task of state.tasks) {
            const id = taskId(task);

            for (const dependency of dependencyIds(task)) {
                if (!state.dependents.has(dependency)) {
                    state.dependents.set(dependency, []);
                }

                state.dependents.get(dependency).push(id);
            }
        }
    }

    function chooseRecommendation() {
        const explicitId =
            explicitRecommendationId();

        if (
            explicitId &&
            state.taskById.has(explicitId)
        ) {
            state.recommendedTaskId =
                explicitId;
            return;
        }

        const candidates = state.tasks
            .filter((task) => {
                if (taskState(task) === "complete") {
                    return false;
                }

                if (taskState(task) === "blocked") {
                    return false;
                }

                if (unresolvedDependencies(task).length) {
                    return false;
                }

                return (
                    taskReady(task) ||
                    taskState(task) === "active"
                );
            })
            .sort((a, b) => {
                const scoreDifference =
                    recommendationScore(b) -
                    recommendationScore(a);

                if (scoreDifference !== 0) {
                    return scoreDifference;
                }

                return taskId(a).localeCompare(taskId(b));
            });

        state.recommendedTaskId =
            candidates.length
                ? taskId(candidates[0])
                : null;
    }

    async function fetchJson(url, signal) {
        const response = await fetch(url, {
            method: "GET",
            headers: {
                Accept: "application/json"
            },
            cache: "no-store",
            signal
        });

        if (!response.ok) {
            throw new Error(
                `${url}: HTTP ${response.status}`
            );
        }

        return response.json();
    }

    function extractTasks(payload) {
        if (Array.isArray(payload)) {
            return payload;
        }

        const source = object(payload);

        const candidates = [
            source.tasks,
            source.items,
            source.data,
            source.results,
            source.state?.tasks,
            source.dashboard?.tasks
        ];

        for (const candidate of candidates) {
            if (Array.isArray(candidate)) {
                return candidate;
            }
        }

        return [];
    }

    function extractHistory(payload) {
        if (Array.isArray(payload)) {
            return payload;
        }

        const source = object(payload);

        for (const candidate of [
            source.history,
            source.events,
            source.transitions,
            source.items,
            source.data
        ]) {
            if (Array.isArray(candidate)) {
                return candidate;
            }
        }

        return [];
    }

    function digestTasks(tasks) {
        return tasks.map((task) => [
            taskId(task),
            taskState(task),
            taskPriority(task),
            taskReady(task),
            dependencyIds(task).join(",")
        ].join(":")).join("|");
    }

    async function refresh({ quiet = false } = {}) {
        if (state.refreshing && state.refreshPromise) {
            return state.refreshPromise;
        }

        state.refreshing = true;
        state.requestGeneration += 1;

        const generation =
            state.requestGeneration;

        state.refreshController?.abort();

        const controller =
            new AbortController();

        state.refreshController =
            controller;

        beginResourceLoad();
        setLifecycle(
            state.tasks.length
                ? LIFECYCLE.coreReady
                : LIFECYCLE.dataLoading
        );

        renderStatus();

        state.refreshPromise = (async () => {
            try {
                const results = await Promise.allSettled([
                    fetchJson(API.health, controller.signal),
                    fetchJson(API.dashboard, controller.signal),
                    fetchJson(API.state, controller.signal),
                    fetchJson(API.tasks, controller.signal),
                    fetchJson(API.history, controller.signal),
                    fetchJson(API.living, controller.signal),
                    fetchJson(API.fabric, controller.signal)
                ]);

                if (
                    generation !==
                    state.requestGeneration
                ) {
                    return;
                }

                const [
                    health,
                    dashboard,
                    taskStatePayload,
                    tasks,
                    history,
                    living,
                    fabric
                ] = results;

                const prior = {
                    health: Boolean(state.health),
                    dashboard: Boolean(state.dashboard),
                    state: Boolean(state.taskState),
                    tasks: state.tasks.length > 0,
                    history: state.history.length > 0,
                    living: Boolean(state.living),
                    fabric: Boolean(state.fabric)
                };

                const resourceResults = {
                    health,
                    dashboard,
                    state: taskStatePayload,
                    tasks,
                    history,
                    living,
                    fabric
                };

                for (
                    const [resource, result]
                    of Object.entries(resourceResults)
                ) {
                    setResourceState(
                        resource,
                        resultResourceState(
                            result,
                            prior[resource]
                        ),
                        result.status === "rejected"
                            ? result.reason
                            : null
                    );
                }

                if (health.status === "fulfilled") {
                    state.health = health.value;
                }

                if (dashboard.status === "fulfilled") {
                    state.dashboard = dashboard.value;
                }

                if (taskStatePayload.status === "fulfilled") {
                    state.taskState = taskStatePayload.value;
                }

                if (tasks.status === "fulfilled") {
                    const nextTasks =
                        extractTasks(tasks.value);

                    const nextDigest =
                        digestTasks(nextTasks);

                    if (
                        state.lastDigest &&
                        state.lastDigest !== nextDigest
                    ) {
                        const previous = new Map(
                            state.tasks.map((task) => [
                                taskId(task),
                                `${taskState(task)}:${taskReady(task)}`
                            ])
                        );

                        state.lastChangedIds =
                            new Set(
                                nextTasks
                                    .filter((task) => {
                                        const id =
                                            taskId(task);

                                        return (
                                            previous.get(id) !==
                                            `${taskState(task)}:${taskReady(task)}`
                                        );
                                    })
                                    .map(taskId)
                            );
                    } else {
                        state.lastChangedIds =
                            new Set();
                    }

                    state.tasks =
                        nextTasks;

                    state.lastDigest =
                        nextDigest;
                }

                if (history.status === "fulfilled") {
                    state.history =
                        extractHistory(history.value);
                }

                if (living.status === "fulfilled") {
                    state.living =
                        living.value;
                }

                if (fabric.status === "fulfilled") {
                    state.fabric =
                        fabric.value;
                }

                rebuildIndexes();
                chooseRecommendation();

                state.lastRefreshAt =
                    new Date().toISOString();

                const tasksUsable =
                    state.resources.tasks ===
                        RESOURCE_STATE.available ||
                    (
                        state.resources.tasks ===
                            RESOURCE_STATE.degraded &&
                        state.tasks.length > 0
                    );

                const coreUsable =
                    tasksUsable &&
                    (
                        state.resources.health ===
                            RESOURCE_STATE.available ||
                        state.resources.health ===
                            RESOURCE_STATE.degraded ||
                        state.resources.health ===
                            RESOURCE_STATE.unavailable
                    );

                const anyDegraded =
                    Object.values(state.resources)
                        .some(
                            (value) =>
                                value ===
                                    RESOURCE_STATE.degraded ||
                                value ===
                                    RESOURCE_STATE.unavailable
                        );

                setLifecycle(
                    !coreUsable
                        ? LIFECYCLE.unavailable
                        : anyDegraded
                            ? LIFECYCLE.degraded
                            : LIFECYCLE.available
                );

                render();

                window.dispatchEvent(
                    new CustomEvent(
                        "niche:projection",
                        {
                            detail: {
                                generation,
                                lifecycle:
                                    state.lifecycle,
                                resources: {
                                    ...state.resources
                                },
                                task_count:
                                    state.tasks.length,
                                recommended_task_id:
                                    state.recommendedTaskId,
                                authority_effect:
                                    "none",
                                projection_only:
                                    true
                            }
                        }
                    )
                );

                if (!quiet) {
                    toast(
                        anyDegraded
                            ? "Niche refreshed with degraded secondary projections."
                            : "Niche projections refreshed."
                    );
                }
            } catch (error) {
                if (
                    error?.name !==
                    "AbortError"
                ) {
                    setLifecycle(
                        state.tasks.length
                            ? LIFECYCLE.degraded
                            : LIFECYCLE.unavailable
                    );

                    if (!quiet) {
                        toast(
                            error.message,
                            "error"
                        );
                    }
                }
            } finally {
                if (
                    generation ===
                    state.requestGeneration
                ) {
                    state.refreshing =
                        false;

                    state.refreshPromise =
                        null;

                    renderStatus();
                }
            }
        })();

        return state.refreshPromise;
    }

    function setStatus(
        indicatorSelector,
        textSelector,
        healthy,
        label
    ) {
        const indicator = $(indicatorSelector);
        const labelElement = $(textSelector);

        if (indicator) {
            indicator.classList.toggle("good", healthy);
            indicator.classList.toggle("bad", !healthy);
        }

        if (labelElement) {
            labelElement.textContent = label;
        }
    }

    function resourceLabel(resource, availableLabel = "available") {
        const value =
            state.resources[resource] ||
            RESOURCE_STATE.unknown;

        if (
            resource === "tasks" &&
            state.tasks.length &&
            (
                value === RESOURCE_STATE.available ||
                value === RESOURCE_STATE.degraded
            )
        ) {
            return `${state.tasks.length} ${value}`;
        }

        if (value === RESOURCE_STATE.available) {
            return availableLabel;
        }

        return value;
    }

    function resourceHealthy(resource) {
        return (
            state.resources[resource] ===
                RESOURCE_STATE.available ||
            state.resources[resource] ===
                RESOURCE_STATE.degraded
        );
    }

    function renderStatus() {
        setStatus(
            "#api-status",
            "#api-status-text",
            state.lifecycle ===
                LIFECYCLE.available ||
                state.lifecycle ===
                    LIFECYCLE.degraded,
            state.lifecycle
        );

        setStatus(
            "#task-status",
            "#task-status-text",
            resourceHealthy("tasks") &&
                state.tasks.length > 0,
            resourceLabel("tasks")
        );

        const fabric = object(state.fabric);

        const surfaceCount =
            number(
                first(
                    fabric.surface_count,
                    fabric.fabric?.surface_count,
                    fabricSurfaces().length
                ),
                0
            );

        const fabricLabel =
            state.resources.fabric ===
                RESOURCE_STATE.available
                ? `${surfaceCount} available`
                : state.resources.fabric ===
                    RESOURCE_STATE.degraded &&
                    surfaceCount
                    ? `${surfaceCount} degraded`
                    : resourceLabel("fabric");

        setStatus(
            "#fabric-status",
            "#fabric-status-text",
            resourceHealthy("fabric"),
            fabricLabel
        );

        setStatus(
            "#authority-status",
            "#authority-status-text",
            true,
            "projection only"
        );

        const projection =
            $("#projection-status");

        if (projection) {
            if (
                state.resources.tasks ===
                RESOURCE_STATE.loading
            ) {
                projection.textContent =
                    "loading task projection";
            } else if (
                state.resources.tasks ===
                    RESOURCE_STATE.unavailable &&
                !state.tasks.length
            ) {
                projection.textContent =
                    "task projection unavailable";
            } else if (
                state.lastChangedIds.size
            ) {
                projection.textContent =
                    `${state.lastChangedIds.size} task state change${state.lastChangedIds.size === 1 ? "" : "s"} observed`;
            } else {
                projection.textContent =
                    "projection stable";
            }
        }
    }

    function renderExecute() {
        const task =
            state.taskById.get(state.recommendedTaskId);

        const heading = $("#execute-heading");
        const purpose = $("#execute-purpose");
        const priority = $("#execute-priority");
        const ancestry = $("#execute-ancestry");
        const startLabel = $("#start-next-label");
        const startDetail = $("#start-next-detail");

        if (!task) {
            heading.textContent =
                "No executable action exposed";

            purpose.textContent =
                "Niche will not fabricate a next action when available task state does not establish one.";

            priority.textContent =
                "PRIORITY UNKNOWN";

            ancestry.replaceChildren();

            startLabel.textContent =
                "NO READY TASK";

            startDetail.textContent =
                "Inspect Flow or Blocker Radar";

            renderOracle(null);
            renderFrontier();
            return;
        }

        heading.textContent = taskTitle(task);

        purpose.textContent = text(
            first(
                task.purpose,
                task.description,
                task.objective_text,
                task.action
            ),
            "Purpose not exposed by current task projection."
        );

        priority.textContent =
            `PRIORITY ${taskPriority(task).toUpperCase()}`;

        ancestry.replaceChildren();

        const chain = [
            taskObjective(task),
            taskParent(task),
            taskId(task)
        ].filter(Boolean);

        for (const value of chain) {
            const span = document.createElement("span");
            span.textContent = value;
            ancestry.append(span);
        }

        const active =
            taskState(task) === "active";

        startLabel.textContent =
            active ? "CONTINUE" : "START NEXT";

        startDetail.textContent =
            active
                ? "Return to current active task"
                : recommendationReason(task);

        renderOracle(task);
        renderFrontier();
    }

    function oracleFactor(label, value, display) {
        const row = document.createElement("div");
        row.className = "factor-row";

        const name = document.createElement("label");
        name.textContent = label;

        const track = document.createElement("span");
        track.className = "factor-track";

        const fill = document.createElement("i");
        fill.style.width =
            `${clamp(value, 0, 100)}%`;

        track.append(fill);

        const result = document.createElement("b");
        result.textContent = display;

        row.append(name, track, result);

        return row;
    }

    function renderOracle(task) {
        const container = $("#oracle-factors");
        const explanation = $("#oracle-explanation");

        container.replaceChildren();

        if (!task) {
            container.append(
                oracleFactor("priority", 0, "unknown"),
                oracleFactor("readiness", 0, "none"),
                oracleFactor("blockers", 0, "unknown"),
                oracleFactor("unlock effect", 0, "unknown")
            );

            explanation.textContent =
                "No task currently satisfies the executable criteria exposed to Niche.";

            return;
        }

        const unresolved =
            unresolvedDependencies(task);

        const unlocks =
            downstreamCount(taskId(task));

        const priority =
            priorityWeight(taskPriority(task));

        container.append(
            oracleFactor(
                "priority",
                clamp(priority / 10, 0, 100),
                taskPriority(task)
            ),
            oracleFactor(
                "readiness",
                taskReady(task) ? 100 : 50,
                taskReady(task)
                    ? "ready"
                    : taskState(task)
            ),
            oracleFactor(
                "prerequisites",
                unresolved.length ? 10 : 100,
                unresolved.length
                    ? `${unresolved.length} unresolved`
                    : "resolved"
            ),
            oracleFactor(
                "unlock effect",
                clamp(unlocks * 12, 0, 100),
                unlocks
                    ? `${unlocks} downstream`
                    : "none exposed"
            )
        );

        explanation.textContent =
            recommendationReason(task);
    }

    function renderFrontier() {
        const track = $("#frontier-track");
        track.replaceChildren();

        const tasks = state.tasks.slice(0, 80);

        if (!tasks.length) {
            return;
        }

        tasks.forEach((task, index) => {
            const dot = document.createElement("span");

            dot.className =
                `frontier-dot ${taskState(task)}`;

            dot.style.left =
                `${(index / Math.max(1, tasks.length - 1)) * 100}%`;

            dot.title = taskTitle(task);

            track.append(dot);
        });
    }

    function laneFor(task) {
        const current = taskState(task);

        return LANES.includes(current)
            ? current
            : "waiting";
    }

    function taskCard(task) {
        const card = document.createElement("article");
        const id = taskId(task);

        card.className = "task-card";
        card.dataset.state = laneFor(task);
        card.dataset.taskId = id;
        card.tabIndex = 0;

        if (state.lastChangedIds.has(id)) {
            card.dataset.changed = "true";
        }

        const title = document.createElement("h3");
        title.textContent = taskTitle(task);

        const identity = document.createElement("div");
        identity.className = "task-id";
        identity.textContent = id;

        const meta = document.createElement("div");
        meta.className = "task-meta";

        const priority = document.createElement("span");
        priority.textContent = taskPriority(task);

        const dependency = document.createElement("span");
        const unresolved =
            unresolvedDependencies(task).length;

        dependency.textContent =
            unresolved
                ? `${unresolved} unresolved`
                : taskReady(task)
                    ? "ready"
                    : laneFor(task);

        meta.append(priority, dependency);

        card.append(title, identity, meta);

        card.addEventListener("click", () => {
            openInspector(id);
        });

        card.addEventListener("keydown", (event) => {
            if (
                event.key === "Enter" ||
                event.key === " "
            ) {
                event.preventDefault();
                openInspector(id);
            }
        });

        return card;
    }

    function renderFlow() {
        const board = $("#flow-board");
        board.replaceChildren();

        for (const lane of LANES) {
            const section = document.createElement("section");
            section.className = "lane";
            section.dataset.lane = lane;

            const tasks = state.tasks.filter(
                (task) => laneFor(task) === lane
            );

            const head = document.createElement("header");
            head.className = "lane-head";

            const name = document.createElement("span");
            name.textContent = lane;

            const count = document.createElement("span");
            count.textContent = String(tasks.length);

            head.append(name, count);

            const body = document.createElement("div");
            body.className = "lane-body";

            if (!tasks.length) {
                const empty = document.createElement("div");
                empty.className = "empty";
                empty.textContent = "No projected tasks";
                body.append(empty);
            } else {
                for (const task of tasks) {
                    body.append(taskCard(task));
                }
            }

            section.append(head, body);
            board.append(section);
        }

        const summary = $("#flow-summary");

        summary.textContent =
            `${state.tasks.length} task projections · no drag mutation`;
    }

    function graphDepth(task, memo = new Map()) {
        const id = taskId(task);

        if (memo.has(id)) {
            return memo.get(id);
        }

        const dependencies =
            dependencyIds(task);

        if (!dependencies.length) {
            memo.set(id, 0);
            return 0;
        }

        let depth = 0;

        for (const dependencyId of dependencies) {
            const dependency =
                state.taskById.get(dependencyId);

            if (dependency) {
                depth = Math.max(
                    depth,
                    graphDepth(dependency, memo) + 1
                );
            }
        }

        memo.set(id, depth);

        return depth;
    }

    function renderConstellation() {
        const stage = $("#graph-stage");
        const edges = $("#graph-edges");
        const nodes = $("#graph-nodes");

        edges.replaceChildren();
        nodes.replaceChildren();

        const tasks = state.tasks.slice(0, 120);

        if (!tasks.length) {
            nodes.innerHTML =
                '<div class="empty">No task graph available.</div>';
            return;
        }

        const memo = new Map();
        const groups = new Map();

        for (const task of tasks) {
            const depth = graphDepth(task, memo);

            if (!groups.has(depth)) {
                groups.set(depth, []);
            }

            groups.get(depth).push(task);
        }

        const maxDepth = Math.max(
            1,
            ...groups.keys()
        );

        const positions = new Map();

        for (const [depth, group] of groups) {
            group.forEach((task, index) => {
                const x =
                    8 +
                    (depth / maxDepth) * 84;

                const y =
                    8 +
                    ((index + 1) /
                        (group.length + 1)) *
                        84;

                positions.set(taskId(task), {
                    x,
                    y
                });
            });
        }

        const namespace =
            "http://www.w3.org/2000/svg";

        for (const task of tasks) {
            const target =
                positions.get(taskId(task));

            if (!target) {
                continue;
            }

            for (const dependencyId of dependencyIds(task)) {
                const source =
                    positions.get(dependencyId);

                if (!source) {
                    continue;
                }

                const path =
                    document.createElementNS(
                        namespace,
                        "path"
                    );

                const sx = source.x;
                const sy = source.y;
                const tx = target.x;
                const ty = target.y;
                const mid = (sx + tx) / 2;

                path.setAttribute(
                    "d",
                    `M ${sx} ${sy} C ${mid} ${sy}, ${mid} ${ty}, ${tx} ${ty}`
                );

                path.setAttribute(
                    "class",
                    taskReady(task)
                        ? "graph-edge ready"
                        : "graph-edge"
                );

                path.setAttribute(
                    "vector-effect",
                    "non-scaling-stroke"
                );

                edges.append(path);
            }
        }

        edges.setAttribute(
            "viewBox",
            "0 0 100 100"
        );

        for (const task of tasks) {
            const position =
                positions.get(taskId(task));

            const node = document.createElement("button");

            node.type = "button";
            node.className =
                `graph-node ${laneFor(task)}`;

            node.style.left = `${position.x}%`;
            node.style.top = `${position.y}%`;

            const title =
                document.createElement("strong");

            title.textContent =
                taskTitle(task);

            const meta =
                document.createElement("small");

            meta.textContent =
                `${taskPriority(task)} · ${laneFor(task)}`;

            node.append(title, meta);

            node.addEventListener("click", () => {
                openInspector(taskId(task));
            });

            nodes.append(node);
        }

        $("#constellation-summary").textContent =
            `${tasks.length} visible nodes · dependency edges`;
    }

    function renderObjectives() {
        const grid = $("#objective-grid");
        grid.replaceChildren();

        const objectives = new Map();

        for (const task of state.tasks) {
            const id = taskObjective(task);

            if (!objectives.has(id)) {
                objectives.set(id, []);
            }

            objectives.get(id).push(task);
        }

        for (const [id, tasks] of objectives) {
            const card = document.createElement("article");
            card.className = "objective";

            const eyebrow = document.createElement("div");
            eyebrow.className = "eyebrow";
            eyebrow.textContent = "OBJECTIVE";

            const heading = document.createElement("h2");
            heading.textContent = id;

            const complete = tasks.filter(
                (task) => taskState(task) === "complete"
            ).length;

            const ready = tasks.filter(taskReady).length;

            const blocked = tasks.filter(
                (task) => taskState(task) === "blocked"
            ).length;

            const stats = document.createElement("div");
            stats.className = "objective-stats";

            for (const value of [
                `${complete}/${tasks.length} complete`,
                `${ready} ready`,
                `${blocked} blocked`
            ]) {
                const span = document.createElement("span");
                span.textContent = value;
                stats.append(span);
            }

            const progress = document.createElement("div");
            progress.className = "progress-line";

            const fill = document.createElement("i");
            fill.style.width =
                `${tasks.length ? (complete / tasks.length) * 100 : 0}%`;

            progress.append(fill);

            card.append(
                eyebrow,
                heading,
                stats,
                progress
            );

            grid.append(card);
        }

        $("#objective-summary").textContent =
            `${objectives.size} objective projection${objectives.size === 1 ? "" : "s"}`;
    }

    function eventTimestamp(event) {
        return text(
            first(
                event.timestamp,
                event.time,
                event.created_at,
                event.updated_at,
                event.at
            ),
            "time unknown"
        );
    }

    function eventTitle(event) {
        return text(
            first(
                event.title,
                event.action,
                event.transition,
                event.event,
                event.type
            ),
            "task event"
        );
    }

    function eventDetail(event) {
        return text(
            first(
                event.reason,
                event.detail,
                event.description,
                event.task_id,
                event.id
            ),
            "No additional detail exposed."
        );
    }

    function renderTimeline() {
        const timeline = $("#timeline");
        timeline.replaceChildren();

        const events = state.history.slice(-100).reverse();

        if (!events.length) {
            timeline.innerHTML =
                '<div class="empty">No immutable history exposed.</div>';
            return;
        }

        for (const event of events) {
            const item = document.createElement("article");
            item.className = "timeline-event";

            const time = document.createElement("time");
            time.textContent = eventTimestamp(event);

            const heading = document.createElement("h3");
            heading.textContent = eventTitle(event);

            const detail = document.createElement("p");
            detail.textContent = eventDetail(event);

            item.append(time, heading, detail);
            timeline.append(item);
        }
    }

    function evidenceStatus(task) {
        const evidence = taskEvidence(task);
        const completion = taskCompletion(task);

        if (taskState(task) === "complete" && evidence) {
            return "established";
        }

        if (completion && !evidence) {
            return "required / unresolved";
        }

        if (evidence) {
            return "available";
        }

        return "unknown";
    }

    function renderEvidence() {
        const grid = $("#evidence-grid");
        grid.replaceChildren();

        const relevant = state.tasks.filter((task) =>
            taskEvidence(task) ||
            taskCompletion(task) ||
            taskState(task) === "review"
        );

        if (!relevant.length) {
            grid.innerHTML =
                '<div class="empty">No evidence requirements exposed.</div>';
        }

        for (const task of relevant) {
            const card = document.createElement("article");
            card.className = "evidence-card";

            const eyebrow = document.createElement("div");
            eyebrow.className = "eyebrow";
            eyebrow.textContent =
                evidenceStatus(task).toUpperCase();

            const heading = document.createElement("h3");
            heading.textContent = taskTitle(task);

            const detail = document.createElement("p");
            detail.textContent = text(
                taskCompletion(task),
                "Completion condition unknown."
            );

            card.append(
                eyebrow,
                heading,
                detail
            );

            card.tabIndex = 0;

            card.addEventListener("click", () => {
                openInspector(taskId(task));
            });

            grid.append(card);
        }

        $("#evidence-summary").textContent =
            `${relevant.length} evidence-relevant task${relevant.length === 1 ? "" : "s"}`;
    }

    function fabricPayload() {
        const fabric = object(state.fabric);

        return object(
            first(
                fabric.fabric,
                fabric
            )
        );
    }

    function fabricSurfaces() {
        const fabric = fabricPayload();

        const surfaces =
            first(
                fabric.surfaces,
                state.living?.fabric?.surfaces,
                state.living?.surfaces
            );

        if (Array.isArray(surfaces)) {
            return surfaces;
        }

        if (
            surfaces &&
            typeof surfaces === "object"
        ) {
            return Object.entries(surfaces).map(
                ([name, value]) => ({
                    name,
                    ...object(value)
                })
            );
        }

        return [];
    }

    function renderLiving() {
        const summary = $("#living-summary");
        const grid = $("#living-grid");
        const identity = $("#fabric-identity");

        summary.replaceChildren();
        grid.replaceChildren();

        const fabric = fabricPayload();
        const surfaces = fabricSurfaces();

        const summaryValues = [
            [
                "surfaces",
                first(
                    fabric.surface_count,
                    surfaces.length
                )
            ],
            [
                "sequence",
                first(
                    fabric.sequence,
                    "unknown"
                )
            ],
            [
                "changed",
                first(
                    fabric.change_count,
                    array(fabric.changed_surfaces).length
                )
            ],
            [
                "authority",
                bool(fabric.projection_only)
                    ? "projected"
                    : "unknown"
            ]
        ];

        for (const [label, value] of summaryValues) {
            const metric = document.createElement("div");
            metric.className = "metric";

            const strong = document.createElement("strong");
            strong.textContent = text(value);

            const span = document.createElement("span");
            span.textContent = label;

            metric.append(strong, span);
            summary.append(metric);
        }

        identity.textContent =
            `${text(
                first(
                    fabric.schema,
                    state.fabric?.schema
                ),
                "living fabric"
            )} · authority_effect ${text(
                first(
                    fabric.authority_effect,
                    state.fabric?.authority_effect
                ),
                "none"
            )}`;

        if (!surfaces.length) {
            grid.innerHTML =
                '<div class="empty">Living fabric surface detail unavailable.</div>';
            return;
        }

        const changed =
            new Set(array(
                first(
                    fabric.changed_surfaces,
                    []
                )
            ));

        for (const surface of surfaces) {
            const name = text(
                first(
                    surface.name,
                    surface.id,
                    surface.surface
                )
            );

            const card = document.createElement("article");
            card.className = "living-surface";

            if (
                changed.has(name) ||
                bool(surface.changed)
            ) {
                card.classList.add("changed");
            }

            const eyebrow = document.createElement("div");
            eyebrow.className = "eyebrow";
            eyebrow.textContent = text(
                first(
                    surface.class,
                    surface.surface_class,
                    surface.mode
                ),
                "LIVING SURFACE"
            ).toUpperCase();

            const heading = document.createElement("h3");
            heading.textContent = name;

            const meta = document.createElement("div");
            meta.className = "living-meta";

            for (const value of [
                first(surface.owner, "owner unknown"),
                first(surface.mode, "mode unknown"),
                first(
                    surface.healthy,
                    surface.health,
                    "health unknown"
                ),
                bool(surface.authoritative)
                    ? "authoritative"
                    : "projected"
            ]) {
                const span = document.createElement("span");
                span.textContent = text(value);
                meta.append(span);
            }

            card.append(
                eyebrow,
                heading,
                meta
            );

            card.tabIndex = 0;

            card.addEventListener("click", () => {
                openInformation(
                    name,
                    surface
                );
            });

            grid.append(card);
        }
    }

    function renderHistory() {
        const list = $("#history-list");
        list.replaceChildren();

        const events = state.history.slice().reverse();

        if (!events.length) {
            list.innerHTML =
                '<div class="empty">No historical events exposed.</div>';
            return;
        }

        for (const event of events.slice(0, 250)) {
            const item = document.createElement("article");
            item.className = "history-event";

            const time = document.createElement("time");
            time.textContent = eventTimestamp(event);

            const heading = document.createElement("h3");
            heading.textContent = eventTitle(event);

            const detail = document.createElement("p");
            detail.textContent = eventDetail(event);

            item.append(time, heading, detail);
            list.append(item);
        }
    }

    function renderPeripheral() {
        const topology = $("#topology-metrics");
        topology.replaceChildren();

        const metrics = {
            ready: state.tasks.filter(taskReady).length,
            active: state.tasks.filter(
                (task) => taskState(task) === "active"
            ).length,
            blocked: state.tasks.filter(
                (task) => taskState(task) === "blocked"
            ).length,
            complete: state.tasks.filter(
                (task) => taskState(task) === "complete"
            ).length
        };

        for (const [label, value] of Object.entries(metrics)) {
            const metric = document.createElement("div");
            metric.className = "metric";

            const strong = document.createElement("strong");
            strong.textContent = String(value);

            const span = document.createElement("span");
            span.textContent = label;

            metric.append(strong, span);
            topology.append(metric);
        }

        const blockers = $("#blocker-list");
        blockers.replaceChildren();

        const rankedBlockers = state.tasks
            .filter(
                (task) => taskState(task) === "blocked"
            )
            .sort(
                (a, b) =>
                    downstreamCount(taskId(b)) -
                    downstreamCount(taskId(a))
            )
            .slice(0, 6);

        if (!rankedBlockers.length) {
            blockers.innerHTML =
                '<div class="empty">No blocked task projected.</div>';
        }

        for (const task of rankedBlockers) {
            const item = document.createElement("div");
            item.className = "compact-item";
            item.tabIndex = 0;

            const title = document.createElement("span");
            title.textContent = taskTitle(task);

            const impact = document.createElement("span");
            impact.textContent =
                `${downstreamCount(taskId(task))} downstream`;

            item.append(title, impact);

            item.addEventListener("click", () => {
                openInspector(taskId(task));
            });

            blockers.append(item);
        }

        const recent = $("#recent-list");
        recent.replaceChildren();

        const events =
            state.history.slice(-6).reverse();

        if (!events.length) {
            recent.innerHTML =
                '<div class="empty">No recent transition history.</div>';
        }

        for (const event of events) {
            const item = document.createElement("div");
            item.className = "compact-item";

            const title = document.createElement("span");
            title.textContent = eventTitle(event);

            const time = document.createElement("span");
            time.textContent = eventTimestamp(event);

            item.append(title, time);
            recent.append(item);
        }
    }

    function render() {
        renderStatus();
        renderExecute();
        renderPeripheral();
        renderFlow();
        renderConstellation();
        renderObjectives();
        renderTimeline();
        renderEvidence();
        renderLiving();
        renderHistory();

        if (state.selectedTaskId) {
            renderInspector(
                state.taskById.get(
                    state.selectedTaskId
                )
            );
        }
    }

    function inspectorSection(
        title,
        content
    ) {
        const section = document.createElement("section");
        section.className = "inspector-section";

        const heading = document.createElement("h3");
        heading.textContent = title.toUpperCase();

        const paragraph = document.createElement("p");

        if (
            typeof content === "object" &&
            content !== null
        ) {
            paragraph.textContent =
                JSON.stringify(content, null, 2);
        } else {
            paragraph.textContent =
                text(content);
        }

        section.append(heading, paragraph);

        return section;
    }

    function renderInspector(task) {
        const body = $("#inspector-body");
        const title = $("#inspector-title");

        body.replaceChildren();

        if (!task) {
            title.textContent =
                "Task unavailable";

            body.append(
                inspectorSection(
                    "Identity",
                    "Task projection no longer available."
                )
            );

            return;
        }

        const id = taskId(task);

        title.textContent =
            taskTitle(task);

        const identity = document.createElement("section");
        identity.className = "inspector-section";

        const heading = document.createElement("h3");
        heading.textContent = "IDENTITY";

        const dl = document.createElement("dl");
        dl.className = "kv";

        const values = [
            ["id", id],
            ["state", taskState(task)],
            ["priority", taskPriority(task)],
            ["ready", taskReady(task)],
            ["objective", taskObjective(task)],
            ["parent", taskParent(task) || "unknown"]
        ];

        for (const [key, value] of values) {
            const dt = document.createElement("dt");
            dt.textContent = key;

            const dd = document.createElement("dd");
            dd.textContent = text(value);

            dl.append(dt, dd);
        }

        identity.append(heading, dl);

        body.append(
            identity,
            inspectorSection(
                "Purpose",
                first(
                    task.purpose,
                    task.description,
                    task.action
                )
            ),
            inspectorSection(
                "Authority",
                first(
                    task.authority,
                    task.authority_effect,
                    "unknown"
                )
            ),
            inspectorSection(
                "edifice",
                {
                    objective: taskObjective(task),
                    parent: taskParent(task),
                    ancestry: first(
                        task.ancestry,
                        "unknown"
                    )
                }
            ),
            inspectorSection(
                "Dependencies",
                dependencyIds(task)
            ),
            inspectorSection(
                "Dependents",
                dependentIds(id)
            ),
            inspectorSection(
                "Completion",
                taskCompletion(task)
            ),
            inspectorSection(
                "Evidence",
                taskEvidence(task)
            ),
            inspectorSection(
                "Impact",
                {
                    immediate_dependents:
                        dependentIds(id),
                    downstream_count:
                        downstreamCount(id)
                }
            ),
            inspectorSection(
                "Context",
                first(
                    task.context,
                    task.metadata,
                    "unknown"
                )
            )
        );
    }

    function openInspector(id) {
        const inspector = $("#inspector");

        state.selectedTaskId = id;

        window.dispatchEvent(
            new CustomEvent(
                "niche:task-selected",
                {
                    detail: {
                        taskId: id,
                        task_id: id,
                        authority_effect:
                            "none",
                        projection_only:
                            true
                    }
                }
            )
        );

        renderInspector(
            state.taskById.get(id)
        );

        inspector.classList.add("open");
        inspector.setAttribute(
            "aria-hidden",
            "false"
        );

        $("#close-inspector")?.focus();
    }

    function closeInspector() {
        const inspector = $("#inspector");

        inspector.classList.remove("open");
        inspector.setAttribute(
            "aria-hidden",
            "true"
        );
    }

    function openInformation(title, content) {
        const shell = $("#information-shell");
        const heading = $("#information-title");
        const body = $("#information-body");

        heading.textContent = title;
        body.replaceChildren();

        const pre = document.createElement("p");
        pre.textContent =
            typeof content === "object"
                ? JSON.stringify(content, null, 2)
                : text(content);

        body.append(pre);

        shell.hidden = false;

        $("#information-close")?.focus();
    }

    function closeInformation() {
        $("#information-shell").hidden = true;
    }

    function setView(view) {
        const target =
            $(`[data-surface="${view}"]`);

        if (!target) {
            return;
        }

        const previousView =
            state.activeView;

        state.activeView = view;

        document.documentElement.dataset.nicheView =
            view;

        $$(".surface").forEach((surface) => {
            surface.classList.toggle(
                "active",
                surface === target
            );
        });

        $$(".nav [data-view]").forEach((button) => {
            const active =
                button.dataset.view === view;

            button.classList.toggle(
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
        });

        target.scrollIntoView({
            block: "start"
        });

        window.dispatchEvent(
            new CustomEvent(
                "niche:view",
                {
                    detail: {
                        view,
                        previous_view:
                            previousView,
                        authority_effect:
                            "none",
                        projection_only:
                            true
                    }
                }
            )
        );
    }

    function commandItems(query = "") {
        const normalized =
            query.trim().toLowerCase();

        const commands = [
            {
                label: "Go to next task",
                detail: "Execution Focus",
                run: startRecommended
            },
            {
                label: "Show ready tasks",
                detail: "Flow",
                run: () => setView("flow")
            },
            {
                label: "Show blockers",
                detail: "Execution",
                run: () => {
                    setView("execute");
                    $("#blocker-list")?.scrollIntoView({
                        behavior: "smooth",
                        block: "center"
                    });
                }
            },
            {
                label: "Show constellation",
                detail: "Dependency topology",
                run: () => setView("constellation")
            },
            {
                label: "Show objectives",
                detail: "edifice",
                run: () => setView("objectives")
            },
            {
                label: "Show timeline",
                detail: "Temporal projection",
                run: () => setView("timeline")
            },
            {
                label: "Show evidence needed",
                detail: "Evidence Gate",
                run: () => setView("evidence")
            },
            {
                label: "Open living fabric",
                detail: "Living Observatory",
                run: () => setView("living")
            },
            {
                label: "Show history",
                detail: "Execution replay",
                run: () => setView("history")
            },
            {
                label: "Refresh projections",
                detail: "Read current API state",
                run: () => refresh()
            }
        ];

        const taskItems = state.tasks.map((task) => ({
            label: taskTitle(task),
            detail:
                `${taskId(task)} · ${taskState(task)} · ${taskPriority(task)}`,
            run: () => openInspector(taskId(task))
        }));

        const all = [
            ...commands,
            ...taskItems
        ];

        if (!normalized) {
            return all.slice(0, 30);
        }

        const tokens =
            normalized.split(/\s+/).filter(Boolean);

        return all.filter((item) => {
            const haystack =
                `${item.label} ${item.detail}`.toLowerCase();

            return tokens.every(
                (token) => haystack.includes(token)
            );
        }).slice(0, 50);
    }

    function renderPalette() {
        const results = $("#palette-results");
        const input = $("#palette-input");

        state.paletteItems =
            commandItems(input.value);

        state.paletteIndex =
            clamp(
                state.paletteIndex,
                0,
                Math.max(
                    0,
                    state.paletteItems.length - 1
                )
            );

        results.replaceChildren();

        if (!state.paletteItems.length) {
            const empty = document.createElement("div");
            empty.className = "empty";
            empty.textContent =
                "No matching command or task.";
            results.append(empty);
            return;
        }

        state.paletteItems.forEach(
            (item, index) => {
                const button =
                    document.createElement("button");

                button.type = "button";
                button.className =
                    "palette-result";

                button.setAttribute(
                    "role",
                    "option"
                );

                button.setAttribute(
                    "aria-selected",
                    index === state.paletteIndex
                        ? "true"
                        : "false"
                );

                if (
                    index === state.paletteIndex
                ) {
                    button.classList.add(
                        "selected"
                    );
                }

                const label =
                    document.createElement("span");

                label.textContent =
                    item.label;

                const detail =
                    document.createElement("small");

                detail.textContent =
                    item.detail;

                button.append(label, detail);

                button.addEventListener(
                    "click",
                    () => {
                        closePalette();
                        item.run();
                    }
                );

                results.append(button);
            }
        );
    }

    function openPalette() {
        const shell = $("#palette-shell");

        shell.hidden = false;

        state.paletteIndex = 0;

        const input = $("#palette-input");
        input.value = "";

        renderPalette();

        requestAnimationFrame(() => {
            input.focus();
        });
    }

    function closePalette() {
        $("#palette-shell").hidden = true;
    }

    function executePaletteSelection() {
        const item =
            state.paletteItems[
                state.paletteIndex
            ];

        if (!item) {
            return;
        }

        closePalette();
        item.run();
    }

    function showExecutionDetail(kind) {
        const task =
            state.taskById.get(
                state.recommendedTaskId
            );

        if (!task) {
            openInformation(
                kind,
                "No executable task is currently exposed."
            );
            return;
        }

        if (kind === "why") {
            openInformation(
                "Why this task now?",
                recommendationReason(task)
            );
            return;
        }

        if (kind === "dependencies") {
            openInformation(
                "Dependencies",
                {
                    dependencies:
                        dependencyIds(task),
                    unresolved:
                        unresolvedDependencies(task),
                    dependents:
                        dependentIds(taskId(task))
                }
            );
            return;
        }

        if (kind === "impact") {
            openInformation(
                "Consequence preview",
                {
                    immediate_dependents:
                        dependentIds(taskId(task)),
                    downstream_count:
                        downstreamCount(taskId(task)),
                    projection_only: true,
                    certainty:
                        "Only consequences derivable from current visible task relationships are shown."
                }
            );
            return;
        }

        if (kind === "evidence") {
            openInformation(
                "Evidence Gate",
                {
                    completion_condition:
                        taskCompletion(task),
                    evidence:
                        taskEvidence(task),
                    status:
                        evidenceStatus(task)
                }
            );
        }
    }

    function startRecommended() {
        const task =
            state.taskById.get(
                state.recommendedTaskId
            );

        if (!task) {
            toast(
                "No executable task is currently exposed.",
                "error"
            );
            return;
        }

        state.transitionTaskId =
            taskId(task);

        const shell =
            $("#transition-shell");

        $("#transition-title").textContent =
            taskTitle(task);

        $("#transition-description").textContent =
            `${taskId(task)} · ${taskState(task)} · ${taskPriority(task)}`;

        $("#transition-action").value =
            taskState(task) === "active"
                ? "start"
                : "start";

        $("#transition-reason").value = "";
        $("#transition-evidence").value = "";

        renderConsequencePreview();

        shell.hidden = false;

        $("#transition-action")?.focus();
    }

    function closeTransition() {
        $("#transition-shell").hidden = true;
        state.transitionTaskId = null;
    }

    function renderConsequencePreview() {
        const task =
            state.taskById.get(
                state.transitionTaskId
            );

        const preview =
            $("#consequence-preview");

        if (!task) {
            preview.textContent =
                "No deterministic consequence projection available.";
            return;
        }

        const action =
            $("#transition-action").value;

        const dependents =
            dependentIds(taskId(task));

        if (action === "complete") {
            preview.textContent =
                dependents.length
                    ? `Projection: ${dependents.length} immediate dependent task${dependents.length === 1 ? "" : "s"} may be affected. Readiness will be re-read from the authoritative task API after confirmation.`
                    : "Projection: no immediate dependent task is visible. Niche will re-read authoritative state after confirmation.";
            return;
        }

        if (action === "block") {
            preview.textContent =
                `Projection: this task has ${downstreamCount(taskId(task))} visible downstream task relationship${downstreamCount(taskId(task)) === 1 ? "" : "s"}. Niche does not infer their authoritative state before the transition is accepted.`;
            return;
        }

        preview.textContent =
            "Projection: Niche will not predict an authoritative state mutation beyond relationships established by current task data.";
    }

    async function submitTransition(event) {
        event.preventDefault();

        const task =
            state.taskById.get(
                state.transitionTaskId
            );

        if (!task) {
            toast(
                "Transition task is unavailable.",
                "error"
            );
            return;
        }

        const action =
            $("#transition-action").value;

        const reason =
            $("#transition-reason").value.trim();

        const evidence =
            $("#transition-evidence").value.trim();

        const id =
            encodeURIComponent(taskId(task));

        const payload = {
            action,
            reason: reason || null,
            evidence: evidence || null
        };

        const button =
            $("#transition-confirm");

        button.disabled = true;

        try {
            const response = await fetch(
                `/api/tasks/${id}/transition`,
                {
                    method: "POST",
                    headers: {
                        "Content-Type":
                            "application/json",
                        Accept:
                            "application/json"
                    },
                    body: JSON.stringify(payload)
                }
            );

            if (!response.ok) {
                let detail = "";

                try {
                    const body =
                        await response.json();

                    detail = text(
                        first(
                            body.error,
                            body.message,
                            body.detail
                        ),
                        ""
                    );
                } catch {
                    detail = "";
                }

                throw new Error(
                    detail ||
                    `Transition rejected: HTTP ${response.status}`
                );
            }

            closeTransition();

            toast(
                "Transition accepted. Refreshing authoritative projection."
            );

            await refresh({
                quiet: true
            });
        } catch (error) {
            toast(
                error.message,
                "error"
            );
        } finally {
            button.disabled = false;
        }
    }

    function toast(message, kind = "") {
        const container = $("#toasts");

        if (!container) {
            return;
        }

        const element =
            document.createElement("div");

        element.className =
            `toast ${kind}`.trim();

        element.textContent =
            text(message);

        container.append(element);

        window.setTimeout(() => {
            element.remove();
        }, 4200);
    }

    function bindNavigation() {
        $$(".nav [data-view]").forEach(
            (button) => {
                button.addEventListener(
                    "click",
                    () => {
                        setView(
                            button.dataset.view
                        );
                    }
                );
            }
        );
    }

    function bindExecution() {
        $("#start-next")?.addEventListener(
            "click",
            startRecommended
        );

        $$("[data-execute-action]").forEach(
            (button) => {
                button.addEventListener(
                    "click",
                    () => {
                        showExecutionDetail(
                            button.dataset.executeAction
                        );
                    }
                );
            }
        );
    }

    function bindInspector() {
        $("#close-inspector")?.addEventListener(
            "click",
            closeInspector
        );
    }

    function bindPalette() {
        $("#open-palette")?.addEventListener(
            "click",
            openPalette
        );

        $("#palette-input")?.addEventListener(
            "input",
            () => {
                state.paletteIndex = 0;
                renderPalette();
            }
        );

        $("#palette-input")?.addEventListener(
            "keydown",
            (event) => {
                if (event.key === "ArrowDown") {
                    event.preventDefault();

                    state.paletteIndex =
                        clamp(
                            state.paletteIndex + 1,
                            0,
                            Math.max(
                                0,
                                state.paletteItems.length - 1
                            )
                        );

                    renderPalette();
                    return;
                }

                if (event.key === "ArrowUp") {
                    event.preventDefault();

                    state.paletteIndex =
                        clamp(
                            state.paletteIndex - 1,
                            0,
                            Math.max(
                                0,
                                state.paletteItems.length - 1
                            )
                        );

                    renderPalette();
                    return;
                }

                if (event.key === "Enter") {
                    event.preventDefault();
                    executePaletteSelection();
                }
            }
        );

        $("#palette-shell")?.addEventListener(
            "pointerdown",
            (event) => {
                if (
                    event.target ===
                    $("#palette-shell")
                ) {
                    closePalette();
                }
            }
        );
    }

    function bindDialogs() {
        $("#transition-cancel")?.addEventListener(
            "click",
            closeTransition
        );

        $("#transition-form")?.addEventListener(
            "submit",
            submitTransition
        );

        $("#transition-action")?.addEventListener(
            "change",
            renderConsequencePreview
        );

        $("#information-close")?.addEventListener(
            "click",
            closeInformation
        );

        $("#transition-shell")?.addEventListener(
            "pointerdown",
            (event) => {
                if (
                    event.target ===
                    $("#transition-shell")
                ) {
                    closeTransition();
                }
            }
        );

        $("#information-shell")?.addEventListener(
            "pointerdown",
            (event) => {
                if (
                    event.target ===
                    $("#information-shell")
                ) {
                    closeInformation();
                }
            }
        );
    }

    function bindKeyboard() {
        document.addEventListener(
            "keydown",
            (event) => {
                const modifier =
                    event.ctrlKey ||
                    event.metaKey;

                if (
                    modifier &&
                    event.key.toLowerCase() === "k"
                ) {
                    event.preventDefault();

                    if (
                        $("#palette-shell").hidden
                    ) {
                        openPalette();
                    } else {
                        closePalette();
                    }

                    return;
                }

                if (
                    event.key === "Escape"
                ) {
                    if (
                        !$("#transition-shell").hidden
                    ) {
                        closeTransition();
                        return;
                    }

                    if (
                        !$("#information-shell").hidden
                    ) {
                        closeInformation();
                        return;
                    }

                    if (
                        !$("#palette-shell").hidden
                    ) {
                        closePalette();
                        return;
                    }

                    if (
                        $("#inspector").classList.contains(
                            "open"
                        )
                    ) {
                        closeInspector();
                    }
                }
            }
        );
    }

    function bindRefresh() {
        $("#refresh")?.addEventListener(
            "click",
            () => refresh()
        );

        document.addEventListener(
            "visibilitychange",
            () => {
                if (!document.hidden) {
                    refresh({
                        quiet: true
                    });
                }
            }
        );

        window.addEventListener(
            "online",
            () => refresh({
                quiet: true
            })
        );
    }

    function startRealtimeProjection() {
        if (state.refreshTimer) {
            clearInterval(
                state.refreshTimer
            );
        }

        state.refreshTimer =
            window.setInterval(
                () => {
                    if (
                        !document.hidden &&
                        navigator.onLine
                    ) {
                        refresh({
                            quiet: true
                        });
                    }
                },
                15000
            );
    }

    function projectionSnapshot() {
        return Object.freeze({
            source: Object.freeze({
                health: state.health,
                dashboard: state.dashboard,
                state: state.taskState,
                tasks: Object.freeze(state.tasks.slice()),
                history: Object.freeze(state.history.slice()),
                living: state.living,
                fabric: state.fabric
            }),
            normalized: Object.freeze({
                taskById: new Map(state.taskById),
                dependents: new Map(
                    Array.from(
                        state.dependents.entries(),
                        ([key, values]) => [
                            key,
                            Object.freeze(array(values).slice())
                        ]
                    )
                ),
                selectedTaskId: state.selectedTaskId,
                recommendedTaskId: state.recommendedTaskId,
                activeView: state.activeView
            }),
            resources: Object.freeze({
                ...state.resources
            }),
            lifecycle: state.lifecycle,
            lastRefreshAt: state.lastRefreshAt,
            requestGeneration: state.requestGeneration,
            authorityEffect: "none",
            projectionOnly: true
        });
    }

    function initialize() {
        if (state.initialized) {
            return;
        }

        state.initialized = true;

        setLifecycle(
            LIFECYCLE.booting
        );

        bindNavigation();
        bindExecution();
        bindInspector();
        bindPalette();
        bindDialogs();
        bindKeyboard();
        bindRefresh();

        setView("execute");

        setLifecycle(
            LIFECYCLE.coreReady
        );

        refresh({
            quiet: true
        });

        startRealtimeProjection();

        window.dispatchEvent(
            new CustomEvent(
                "niche:frontend-ready",
                {
                    detail: {
                        lifecycle:
                            state.lifecycle,
                        authority_effect:
                            "none",
                        projection_only:
                            true
                    }
                }
            )
        );
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

    window.Niche = Object.freeze({
        refresh: () => refresh(),
        view: setView,
        task: openInspector,
        execute: startRecommended,
        projection: projectionSnapshot,
        state: () => ({
            lifecycle:
                state.lifecycle,
            resources: {
                ...state.resources
            },
            activeView:
                state.activeView,
            selectedTaskId:
                state.selectedTaskId,
            recommendedTaskId:
                state.recommendedTaskId,
            taskCount:
                state.tasks.length,
            historyCount:
                state.history.length,
            livingSurfaceCount:
                fabricSurfaces().length,
            lastRefreshAt:
                state.lastRefreshAt,
            authorityEffect:
                "none",
            projectionOnly:
                true
        })
    });

})();
