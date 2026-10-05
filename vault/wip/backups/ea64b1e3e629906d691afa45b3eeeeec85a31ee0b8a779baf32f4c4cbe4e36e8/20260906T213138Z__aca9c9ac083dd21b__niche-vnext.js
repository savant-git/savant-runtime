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
        pendingGoTimer: null
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

    function applyCausalZoom(
        value,
        {
            persist = true
        } = {}
    ) {
        const next = clampZoom(value);
        state.causalZoom = next;

        for (const target of [
            $("#graph-nodes"),
            $("#graph-edges")
        ]) {
            if (!target) {
                continue;
            }

            target.style.transformOrigin = "0 0";
            target.style.transform = `scale(${next})`;
        }

        const label = $("#causal-zoom-label");
        if (label) {
            label.textContent =
                `${Math.round(next * 100)}%`;
        }

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

    function updateCausalModeState() {
        const projection = coreProjection();
        const task = selectedTask(projection);
        const stage = $("#graph-stage");

        if (!stage) {
            return;
        }

        stage.dataset.causalMode = state.causalMode;
        stage.dataset.selectedTaskId =
            task
                ? taskId(task)
                : "";

        const related = new Set();

        if (task) {
            const id = taskId(task);
            related.add(id);

            if (state.causalMode === "dependencies") {
                for (const dependency of taskDependencies(task)) {
                    related.add(dependency);
                }
            } else if (state.causalMode === "impact") {
                for (const dependent of dependentsOf(id, projection)) {
                    related.add(dependent);
                }
            } else if (state.causalMode === "objective") {
                const objective = taskObjective(task);

                for (const candidate of projectionTasks(projection)) {
                    if (taskObjective(candidate) === objective) {
                        related.add(taskId(candidate));
                    }
                }
            } else if (state.causalMode === "blockers") {
                related.add(id);

                for (const dependency of unresolvedDependencies(
                    task,
                    projection
                )) {
                    related.add(dependency);
                }
            }
        }

        for (const node of $$("[data-task-id]", stage)) {
            const id = asText(node.dataset.taskId);

            const shouldEmphasize =
                !task ||
                state.causalMode === "flow" ||
                state.causalMode === "authority" ||
                state.causalMode === "critical" ||
                related.has(id);

            node.dataset.semanticMatch =
                shouldEmphasize
                    ? "true"
                    : "false";
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
            emit(
                "view-sync",
                {
                    view
                }
            );
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
        syncFromCore();

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
