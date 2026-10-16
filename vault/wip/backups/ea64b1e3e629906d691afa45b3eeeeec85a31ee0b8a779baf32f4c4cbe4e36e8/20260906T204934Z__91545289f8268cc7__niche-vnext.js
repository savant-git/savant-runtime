"use strict";

/*
 * savant / niche vnext
 * progressive intelligence and interface convergence coordinator
 *
 * owner: exile:niche
 * semantic_role: non-authoritative interface coordinator
 * authority_effect: none
 * projection_only: true
 *
 * authoritative task state remains owned by the established niche
 * backend. this module coordinates interface projection, comprehension,
 * navigation continuity, causal explanation, and non-authoritative
 * local preferences.
 */

(() => {
    "use strict";

    const API = Object.freeze({
        tasks: "/api/tasks?include_terminal=true",
        history: "/api/history",
        health: "/api/health",
        living: "/api/living",
        fabric: "/api/living/fabric"
    });

    const STORAGE = Object.freeze({
        theme: "savant.niche.ui.theme",
        causalMode: "savant.niche.ui.causal-mode",
        causalZoom: "savant.niche.ui.causal-zoom",
        disclosure: "savant.niche.ui.disclosure",
        density: "savant.niche.ui.density",
        selectedTaskId: "savant.niche.ui.selected-task",
        objectiveFilter: "savant.niche.ui.objective-filter",
        objectiveSearch: "savant.niche.ui.objective-search",
        commandHistory: "savant.niche.ui.command-history",
        inspectorPinned: "savant.niche.ui.inspector-pinned"
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

    const DISCLOSURE = Object.freeze([
        "glance",
        "work",
        "deep"
    ]);

    const DENSITIES = Object.freeze([
        "comfortable",
        "compact",
        "dense"
    ]);

    const CAUSAL_MODES = Object.freeze({
        flow: {
            label: "FLOW",
            question:
                "What work is moving, waiting, blocked, or complete?",
            description:
                "Execution state projected into one causal workspace."
        },

        dependencies: {
            label: "DEPENDENCIES",
            question:
                "What does the selected work require?",
            description:
                "Represented prerequisites and immediate dependency structure."
        },

        impact: {
            label: "IMPACT",
            question:
                "What represented work may be affected downstream?",
            description:
                "Represented dependents and downstream reach."
        },

        objective: {
            label: "OBJECTIVE",
            question:
                "How does this work contribute to its represented outcome?",
            description:
                "Objective membership and represented structural context."
        },

        critical: {
            label: "CRITICAL PATH",
            question:
                "What path is reported or derived as execution-critical?",
            description:
                "Critical-path information only where the current model exposes it."
        },

        blockers: {
            label: "BLOCKERS",
            question:
                "What represented conditions prevent progress?",
            description:
                "Blocked tasks and unresolved dependency structure."
        },

        authority: {
            label: "AUTHORITY",
            question:
                "Which values are authoritative and which are projections?",
            description:
                "Authority boundaries, projection status, and represented ownership."
        }
    });

    const STATUS_LANGUAGE = Object.freeze({
        ready: {
            plain:
                "Can be worked on now",
            canonical:
                "ready"
        },

        active: {
            plain:
                "Work is currently underway",
            canonical:
                "active"
        },

        blocked: {
            plain:
                "Something represented must happen first",
            canonical:
                "blocked"
        },

        waiting: {
            plain:
                "Waiting for a represented condition or decision",
            canonical:
                "waiting"
        },

        review: {
            plain:
                "Needs review or verification",
            canonical:
                "review"
        },

        complete: {
            plain:
                "Recorded as complete",
            canonical:
                "complete"
        },

        unknown: {
            plain:
                "The current source does not establish this state",
            canonical:
                "unknown"
        }
    });

    const HELP = Object.freeze({
        authority: {
            title:
                "Authority",
            plain:
                "The source that is allowed to determine real task state.",
            deep:
                "Interface geometry, visual emphasis, local preferences, derived rankings, and projections do not become task authority."
        },

        projection: {
            title:
                "Projection",
            plain:
                "A calculated or visual representation of source data.",
            deep:
                "A projection may help explain or navigate work, but it does not independently change authoritative task state."
        },

        dependencies: {
            title:
                "Dependencies",
            plain:
                "What this task needs before it can progress.",
            deep:
                "Only represented dependency relationships are shown. Missing relationships are not inferred."
        },

        dependents: {
            title:
                "Dependents",
            plain:
                "What represented work relies on this task.",
            deep:
                "Dependent counts are derived from represented dependency links and are not guaranteed execution consequences."
        },

        evidence: {
            title:
                "Evidence",
            plain:
                "Proof or verification associated with completion.",
            deep:
                "Evidence is called missing only when a requirement is actually represented. Absence of a represented requirement remains unknown or not represented."
        },

        unknown: {
            title:
                "Unknown",
            plain:
                "The current source does not establish a value.",
            deep:
                "Unknown is not zero, false, empty, healthy, complete, or not applicable."
        },

        causal: {
            title:
                "Causal Field",
            plain:
                "Explains why represented work depends on, blocks, or affects other work.",
            deep:
                "Causal Field answers why. Navigation answers where. Geometry remains projection-only."
        },

        navigation: {
            title:
                "Navigation",
            plain:
                "Shows where represented work sits in task space.",
            deep:
                "Routes are represented relationship routes, not execution orders."
        }
    });

    const state = {
        ready:
            false,

        theme:
            "nexus",

        causalMode:
            "flow",

        causalZoom:
            1,

        disclosure:
            "work",

        density:
            "comfortable",

        selectedTaskId:
            null,

        objectiveFilter:
            "all",

        objectiveSearch:
            "",

        inspectorPinned:
            false,

        commandHistory:
            [],

        tasks:
            [],

        taskById:
            new Map(),

        dependentsById:
            new Map(),

        history:
            [],

        health:
            null,

        living:
            null,

        fabric:
            null,

        requestGeneration:
            0,

        requestController:
            null,

        loading:
            false,

        lastProjectionDigest:
            "",

        enhancementObserver:
            null,

        enhancementQueued:
            false,

        activeCommandIndex:
            0,

        commandItems:
            [],

        helpReturnFocus:
            null
    };

    const $ = (
        selector,
        root = document
    ) =>
        root.querySelector(
            selector
        );

    const $$ = (
        selector,
        root = document
    ) =>
        Array.from(
            root.querySelectorAll(
                selector
            )
        );

    function asText(
        value,
        fallback = ""
    ) {
        if (
            value === null ||
            value === undefined ||
            value === ""
        ) {
            return fallback;
        }

        return (
            String(value).trim() ||
            fallback
        );
    }

    function lower(
        value
    ) {
        return asText(
            value
        ).toLocaleLowerCase();
    }

    function firstRepresented(
        ...values
    ) {
        for (
            const value
            of values
        ) {
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

    function escapeHtml(
        value
    ) {
        return asText(
            value
        )
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
                "\"",
                "&quot;"
            )
            .replaceAll(
                "'",
                "&#039;"
            );
    }

    function safeRead(
        key
    ) {
        try {
            return window
                .localStorage
                .getItem(
                    key
                );
        } catch {
            return null;
        }
    }

    function safeWrite(
        key,
        value
    ) {
        try {
            window
                .localStorage
                .setItem(
                    key,
                    value
                );
        } catch {
            return;
        }
    }

    function safeJsonRead(
        key,
        fallback
    ) {
        const raw =
            safeRead(
                key
            );

        if (!raw) {
            return fallback;
        }

        try {
            return JSON.parse(
                raw
            );
        } catch {
            return fallback;
        }
    }

    function emit(
        type,
        detail = {}
    ) {
        window.dispatchEvent(
            new CustomEvent(
                `niche:vnext:${type}`,
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

    function currentNicheState() {
        try {
            if (
                window.Niche &&
                typeof window.Niche.state ===
                    "function"
            ) {
                return window
                    .Niche
                    .state();
            }
        } catch {
            return null;
        }

        return null;
    }

    function taskId(
        task
    ) {
        return asText(
            firstRepresented(
                task?.id,
                task?.task_id,
                task?.identity,
                task?.key
            )
        );
    }

    function taskTitle(
        task
    ) {
        return asText(
            firstRepresented(
                task?.title,
                task?.name,
                task?.action,
                task?.summary,
                taskId(task)
            ),
            "untitled task"
        );
    }

    function taskReady(
        task
    ) {
        const value =
            firstRepresented(
                task?.ready,
                task?.is_ready,
                task?.readiness
            );

        if (
            typeof value ===
            "boolean"
        ) {
            return value;
        }

        const normalized =
            lower(
                value
            );

        return (
            normalized === "ready" ||
            normalized === "true" ||
            normalized === "yes"
        );
    }

    function taskState(
        task
    ) {
        const raw =
            lower(
                firstRepresented(
                    task?.state,
                    task?.status,
                    task?.lifecycle_state
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
            raw.includes(
                "review"
            ) ||
            raw.includes(
                "evidence"
            ) ||
            raw.includes(
                "verify"
            )
        ) {
            return "review";
        }

        if (
            raw.includes(
                "wait"
            ) ||
            raw.includes(
                "defer"
            ) ||
            raw.includes(
                "pending"
            )
        ) {
            return "waiting";
        }

        if (
            taskReady(
                task
            )
        ) {
            return "ready";
        }

        return (
            raw ||
            "unknown"
        );
    }

    function taskPriority(
        task
    ) {
        return asText(
            firstRepresented(
                task?.priority,
                task?.authoritative_priority,
                task?.rank
            ),
            "unknown"
        );
    }

    function taskObjective(
        task
    ) {
        return asText(
            firstRepresented(
                task?.objective,
                task?.objective_id,
                task?.root_objective,
                task?.ancestry?.objective
            ),
            "unknown objective"
        );
    }

    function taskParent(
        task
    ) {
        return asText(
            firstRepresented(
                task?.parent,
                task?.parent_id,
                task?.parent_task_id,
                task?.ancestry?.parent
            )
        );
    }

    function taskDependencies(
        task
    ) {
        const candidate =
            firstRepresented(
                task?.dependencies,
                task?.depends_on,
                task?.prerequisites,
                task?.requires
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
                (
                    item
                ) => {
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
                            item?.key
                        )
                    );
                }
            )
            .filter(
                Boolean
            );
    }

    function taskBlockers(
        task
    ) {
        const candidate =
            firstRepresented(
                task?.blockers,
                task?.blocked_by
            );

        if (
            Array.isArray(
                candidate
            )
        ) {
            return candidate;
        }

        return candidate
            ? [candidate]
            : [];
    }

    function taskEvidence(
        task
    ) {
        return firstRepresented(
            task?.evidence,
            task?.receipts,
            task?.completion_evidence,
            task?.verification
        );
    }

    function taskCompletion(
        task
    ) {
        return firstRepresented(
            task?.completion_condition,
            task?.completion,
            task?.done_when,
            task?.acceptance
        );
    }

    function taskAuthority(
        task
    ) {
        return firstRepresented(
            task?.authority,
            task?.authority_owner,
            task?.task_authority_owner,
            task?.authority_effect
        );
    }

    function normalizeTask(
        task
    ) {
        const id =
            taskId(
                task
            );

        if (!id) {
            return null;
        }

        return Object.freeze({
            id,

            title:
                taskTitle(
                    task
                ),

            state:
                taskState(
                    task
                ),

            ready:
                taskReady(
                    task
                ),

            priority:
                taskPriority(
                    task
                ),

            objective:
                taskObjective(
                    task
                ),

            parent:
                taskParent(
                    task
                ),

            dependencies:
                Object.freeze(
                    taskDependencies(
                        task
                    )
                ),

            blockers:
                Object.freeze(
                    taskBlockers(
                        task
                    )
                ),

            evidence:
                taskEvidence(
                    task
                ),

            completion:
                taskCompletion(
                    task
                ),

            authority:
                taskAuthority(
                    task
                ),

            purpose:
                firstRepresented(
                    task?.purpose,
                    task?.description,
                    task?.action
                ),

            raw:
                task
        });
    }

    function normalizeTaskPayload(
        payload
    ) {
        const source =
            Array.isArray(
                payload
            )
                ? payload
                : Array.isArray(
                    payload?.tasks
                )
                    ? payload.tasks
                    : Array.isArray(
                        payload?.items
                    )
                        ? payload.items
                        : [];

        return source
            .map(
                normalizeTask
            )
            .filter(
                Boolean
            )
            .sort(
                (
                    a,
                    b
                ) =>
                    a.objective
                        .localeCompare(
                            b.objective
                        ) ||
                    a.title
                        .localeCompare(
                            b.title
                        ) ||
                    a.id
                        .localeCompare(
                            b.id
                        )
            );
    }

    function rebuildIndexes() {
        state.taskById =
            new Map();

        state.dependentsById =
            new Map();

        for (
            const task
            of state.tasks
        ) {
            state.taskById
                .set(
                    task.id,
                    task
                );

            state.dependentsById
                .set(
                    task.id,
                    []
                );
        }

        for (
            const task
            of state.tasks
        ) {
            for (
                const dependency
                of task.dependencies
            ) {
                if (
                    state
                        .dependentsById
                        .has(
                            dependency
                        )
                ) {
                    state
                        .dependentsById
                        .get(
                            dependency
                        )
                        .push(
                            task.id
                        );
                }
            }
        }

        for (
            const values
            of state
                .dependentsById
                .values()
        ) {
            values.sort(
                (
                    a,
                    b
                ) =>
                    a.localeCompare(
                        b
                    )
            );
        }
    }

    function unresolvedDependencies(
        task
    ) {
        if (!task) {
            return [];
        }

        return task
            .dependencies
            .filter(
                (
                    id
                ) => {
                    const dependency =
                        state
                            .taskById
                            .get(
                                id
                            );

                    return (
                        !dependency ||
                        dependency.state !==
                            "complete"
                    );
                }
            );
    }

    function downstreamIds(
        id
    ) {
        const result = [];
        const visited =
            new Set();

        const queue = [
            ...(
                state
                    .dependentsById
                    .get(
                        id
                    ) ||
                []
            )
        ];

        while (
            queue.length
        ) {
            const current =
                queue.shift();

            if (
                !current ||
                visited.has(
                    current
                )
            ) {
                continue;
            }

            visited.add(
                current
            );

            result.push(
                current
            );

            for (
                const next
                of (
                    state
                        .dependentsById
                        .get(
                            current
                        ) ||
                    []
                )
            ) {
                if (
                    !visited.has(
                        next
                    )
                ) {
                    queue.push(
                        next
                    );
                }
            }
        }

        return result;
    }

    function statusLanguage(
        value
    ) {
        return (
            STATUS_LANGUAGE[
                value
            ] ||
            STATUS_LANGUAGE
                .unknown
        );
    }

    function selectedTask() {
        const candidate =
            state.selectedTaskId ||
            currentNicheState()
                ?.selectedTaskId ||
            null;

        if (!candidate) {
            return null;
        }

        return (
            state
                .taskById
                .get(
                    String(
                        candidate
                    )
                ) ||
            null
        );
    }

    function recommendedTask() {
        const id =
            currentNicheState()
                ?.recommendedTaskId;

        if (!id) {
            return null;
        }

        return (
            state
                .taskById
                .get(
                    String(
                        id
                    )
                ) ||
            null
        );
    }

    function projectionDigest() {
        return state.tasks
            .map(
                (
                    task
                ) =>
                    [
                        task.id,
                        task.state,
                        task.ready,
                        task.priority,
                        task.objective
                    ].join(
                        ":"
                    )
            )
            .join(
                "|"
            );
    }

    async function fetchJson(
        url,
        signal
    ) {
        const response =
            await fetch(
                url,
                {
                    method:
                        "GET",

                    headers: {
                        Accept:
                            "application/json"
                    },

                    cache:
                        "no-store",

                    signal
                }
            );

        if (
            !response.ok
        ) {
            throw new Error(
                `${url} http ${response.status}`
            );
        }

        return response.json();
    }

    async function refreshSemanticProjection(
        {
            quiet = true
        } = {}
    ) {
        state.requestGeneration +=
            1;

        const generation =
            state.requestGeneration;

        state.requestController
            ?.abort();

        const controller =
            new AbortController();

        state.requestController =
            controller;

        state.loading =
            true;

        document
            .documentElement
            .dataset
            .nicheVnextProjection =
            "loading";

        try {
            const results =
                await Promise.allSettled([
                    fetchJson(
                        API.tasks,
                        controller.signal
                    ),

                    fetchJson(
                        API.history,
                        controller.signal
                    ),

                    fetchJson(
                        API.health,
                        controller.signal
                    ),

                    fetchJson(
                        API.living,
                        controller.signal
                    ),

                    fetchJson(
                        API.fabric,
                        controller.signal
                    )
                ]);

            if (
                generation !==
                state.requestGeneration
            ) {
                return;
            }

            const [
                tasksResult,
                historyResult,
                healthResult,
                livingResult,
                fabricResult
            ] = results;

            if (
                tasksResult.status ===
                "fulfilled"
            ) {
                state.tasks =
                    normalizeTaskPayload(
                        tasksResult.value
                    );

                rebuildIndexes();
            }

            if (
                historyResult.status ===
                "fulfilled"
            ) {
                const payload =
                    historyResult.value;

                state.history =
                    Array.isArray(
                        payload
                    )
                        ? payload
                        : Array.isArray(
                            payload?.events
                        )
                            ? payload.events
                            : Array.isArray(
                                payload?.history
                            )
                                ? payload.history
                                : [];
            }

            state.health =
                healthResult.status ===
                "fulfilled"
                    ? healthResult.value
                    : null;

            state.living =
                livingResult.status ===
                "fulfilled"
                    ? livingResult.value
                    : null;

            state.fabric =
                fabricResult.status ===
                "fulfilled"
                    ? fabricResult.value
                    : null;

            const digest =
                projectionDigest();

            const changed =
                digest !==
                state.lastProjectionDigest;

            state.lastProjectionDigest =
                digest;

            document
                .documentElement
                .dataset
                .nicheVnextProjection =
                tasksResult.status ===
                    "fulfilled"
                    ? "available"
                    : "degraded";

            if (changed) {
                queueEnhancementPass();
            } else {
                enhanceGlobalStatus();
                enhanceExecute();
            }

            emit(
                "projection",
                {
                    task_count:
                        state.tasks
                            .length,

                    history_count:
                        state.history
                            .length,

                    status:
                        document
                            .documentElement
                            .dataset
                            .nicheVnextProjection
                }
            );
        } catch (
            error
        ) {
            if (
                error?.name !==
                "AbortError"
            ) {
                document
                    .documentElement
                    .dataset
                    .nicheVnextProjection =
                    "degraded";

                if (!quiet) {
                    announce(
                        "Secondary interface projection is degraded. Execute remains available if the core task engine is healthy."
                    );
                }
            }
        } finally {
            if (
                generation ===
                state.requestGeneration
            ) {
                state.loading =
                    false;
            }
        }
    }

    function validTheme(
        value
    ) {
        return THEMES.includes(
            value
        )
            ? value
            : "nexus";
    }

    function validDisclosure(
        value
    ) {
        return DISCLOSURE.includes(
            value
        )
            ? value
            : "work";
    }

    function validDensity(
        value
    ) {
        return DENSITIES.includes(
            value
        )
            ? value
            : "comfortable";
    }

    function validCausalMode(
        value
    ) {
        return Object.prototype
            .hasOwnProperty
            .call(
                CAUSAL_MODES,
                value
            )
            ? value
            : "flow";
    }

    function applyTheme(
        value,
        {
            persist = true
        } = {}
    ) {
        const next =
            validTheme(
                value
            );

        state.theme =
            next;

        document
            .documentElement
            .dataset
            .nicheTheme =
            next;

        const control =
            $("#niche-theme");

        if (
            control &&
            control.value !==
                next
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

        emit(
            "theme",
            {
                theme:
                    next
            }
        );
    }

    function applyDisclosure(
        value,
        {
            persist = true
        } = {}
    ) {
        const next =
            validDisclosure(
                value
            );

        state.disclosure =
            next;

        document
            .documentElement
            .dataset
            .nicheDisclosure =
            next;

        const control =
            $("#niche-disclosure");

        if (
            control &&
            control.value !==
                next
        ) {
            control.value =
                next;
        }

        if (persist) {
            safeWrite(
                STORAGE.disclosure,
                next
            );
        }

        enhanceInspector();

        emit(
            "disclosure",
            {
                disclosure:
                    next
            }
        );
    }

    function applyDensity(
        value,
        {
            persist = true
        } = {}
    ) {
        const next =
            validDensity(
                value
            );

        state.density =
            next;

        document
            .documentElement
            .dataset
            .nicheDensity =
            next;

        const control =
            $("#niche-density");

        if (
            control &&
            control.value !==
                next
        ) {
            control.value =
                next;
        }

        if (persist) {
            safeWrite(
                STORAGE.density,
                next
            );
        }

        emit(
            "density",
            {
                density:
                    next
            }
        );
    }

    function applyCausalMode(
        value,
        {
            persist = true
        } = {}
    ) {
        const next =
            validCausalMode(
                value
            );

        state.causalMode =
            next;

        const workspace =
            $(".causal-workspace");

        const graph =
            $("#graph-stage");

        const flow =
            $("#causal-flow");

        if (workspace) {
            workspace
                .dataset
                .causalActive =
                next;
        }

        if (graph) {
            graph.hidden =
                next ===
                "flow";
        }

        if (flow) {
            flow.hidden =
                next !==
                "flow";
        }

        for (
            const button
            of $$(
                "[data-causal-mode]"
            )
        ) {
            const active =
                button
                    .dataset
                    .causalMode ===
                next;

            button
                .classList
                .toggle(
                    "active",
                    active
                );

            button
                .setAttribute(
                    "aria-pressed",
                    active
                        ? "true"
                        : "false"
                );

            if (
                button
                    .dataset
                    .causalMode ===
                "topology"
            ) {
                button.hidden =
                    true;
            }
        }

        const metadata =
            CAUSAL_MODES[
                next
            ];

        const label =
            $(
                "#causal-mode-label"
            );

        const description =
            $(
                "#causal-mode-description"
            );

        if (label) {
            label.textContent =
                metadata.label;
        }

        if (description) {
            description.textContent =
                `${metadata.question} ${metadata.description}`;
        }

        if (persist) {
            safeWrite(
                STORAGE.causalMode,
                next
            );
        }

        renderCausalProjection();
        applyCausalSemantics();

        emit(
            "causal-mode",
            {
                mode:
                    next
            }
        );
    }

    function causalDepth(
        task,
        memo = new Map(),
        visiting = new Set()
    ) {
        if (!task) {
            return 0;
        }

        if (
            memo.has(
                task.id
            )
        ) {
            return memo.get(
                task.id
            );
        }

        if (
            visiting.has(
                task.id
            )
        ) {
            return 0;
        }

        visiting.add(
            task.id
        );

        let depth = 0;

        for (
            const dependencyId
            of task.dependencies
        ) {
            const dependency =
                state
                    .taskById
                    .get(
                        dependencyId
                    );

            if (dependency) {
                depth =
                    Math.max(
                        depth,
                        causalDepth(
                            dependency,
                            memo,
                            visiting
                        ) +
                            1
                    );
            }
        }

        visiting.delete(
            task.id
        );

        memo.set(
            task.id,
            depth
        );

        return depth;
    }

    function causalSubset() {
        const mode =
            state.causalMode;

        const selected =
            selectedTask();

        let tasks =
            state.tasks
                .slice();

        if (
            mode ===
            "dependencies"
        ) {
            if (!selected) {
                return [];
            }

            const ids =
                new Set([
                    selected.id,
                    ...selected.dependencies
                ]);

            tasks =
                tasks.filter(
                    (
                        task
                    ) =>
                        ids.has(
                            task.id
                        )
                );
        } else if (
            mode ===
            "impact"
        ) {
            if (!selected) {
                return [];
            }

            const ids =
                new Set([
                    selected.id,
                    ...downstreamIds(
                        selected.id
                    )
                ]);

            tasks =
                tasks.filter(
                    (
                        task
                    ) =>
                        ids.has(
                            task.id
                        )
                );
        } else if (
            mode ===
            "objective"
        ) {
            if (!selected) {
                return [];
            }

            tasks =
                tasks.filter(
                    (
                        task
                    ) =>
                        task.objective ===
                        selected.objective
                );
        } else if (
            mode ===
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
                        task
                    );

                if (
                    task.state ===
                        "blocked" ||
                    unresolved.length
                ) {
                    ids.add(
                        task.id
                    );

                    for (
                        const id
                        of unresolved
                    ) {
                        ids.add(
                            id
                        );
                    }
                }
            }

            tasks =
                tasks.filter(
                    (
                        task
                    ) =>
                        ids.has(
                            task.id
                        )
                );
        } else if (
            mode ===
            "critical"
        ) {
            tasks =
                tasks.filter(
                    (
                        task
                    ) => {
                        const raw =
                            task.raw ||
                            {};

                        return (
                            raw.critical_path ===
                                true ||
                            raw.on_critical_path ===
                                true ||
                            raw.critical ===
                                true ||
                            lower(
                                raw.path_class
                            ) ===
                                "critical"
                        );
                    }
                );
        }

        return tasks.slice(
            0,
            180
        );
    }

    function causalNodeClass(
        task
    ) {
        const stateValue =
            STATUS_LANGUAGE[
                task.state
            ]
                ? task.state
                : "unknown";

        return (
            `graph-node ${stateValue}`
        );
    }

    function renderCausalUnavailable(
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

        nodes.style.width =
            "100%";

        nodes.style.height =
            "100%";

        const panel =
            document.createElement(
                "div"
            );

        panel.className =
            "causal-projection-empty";

        panel.innerHTML =
            `<strong>${escapeHtml(message)}</strong><span>No relationship is invented to fill this view.</span>`;

        nodes.append(
            panel
        );
    }

    function renderCausalProjection() {
        if (
            state.causalMode ===
            "flow"
        ) {
            return;
        }

        const nodes =
            $("#graph-nodes");

        const edges =
            $("#graph-edges");

        const summary =
            $(
                "#constellation-summary"
            );

        if (
            !nodes ||
            !edges ||
            !state.tasks.length
        ) {
            return;
        }

        const selected =
            selectedTask();

        const subset =
            causalSubset();

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
            renderCausalUnavailable(
                "Select a represented task to answer this causal question."
            );

            if (summary) {
                summary.textContent =
                    "Selection required · projection only";
            }

            return;
        }

        if (
            state.causalMode ===
                "critical" &&
            !subset.length
        ) {
            renderCausalUnavailable(
                "No explicit critical-path membership is represented in the current task payload."
            );

            if (summary) {
                summary.textContent =
                    "Critical-path membership not represented";
            }

            return;
        }

        const included =
            new Set(
                subset.map(
                    (
                        task
                    ) =>
                        task.id
                )
            );

        const memo =
            new Map();

        const groups =
            new Map();

        for (
            const task
            of subset
        ) {
            const depth =
                causalDepth(
                    task,
                    memo
                );

            if (
                !groups.has(
                    depth
                )
            ) {
                groups.set(
                    depth,
                    []
                );
            }

            groups
                .get(
                    depth
                )
                .push(
                    task
                );
        }

        for (
            const group
            of groups.values()
        ) {
            group.sort(
                (
                    a,
                    b
                ) =>
                    a.objective
                        .localeCompare(
                            b.objective
                        ) ||
                    a.title
                        .localeCompare(
                            b.title
                        ) ||
                    a.id
                        .localeCompare(
                            b.id
                        )
            );
        }

        const depthKeys =
            Array.from(
                groups.keys()
            ).sort(
                (
                    a,
                    b
                ) =>
                    a - b
            );

        const columnWidth =
            270;

        const rowHeight =
            92;

        const nodeWidth =
            220;

        const nodeHeight =
            64;

        const padX =
            64;

        const padY =
            64;

        const positions =
            new Map();

        let maxRows =
            1;

        depthKeys.forEach(
            (
                depth,
                columnIndex
            ) => {
                const group =
                    groups.get(
                        depth
                    ) ||
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
                            task.id,
                            {
                                x:
                                    padX +
                                    columnIndex *
                                        columnWidth,

                                y:
                                    padY +
                                    rowIndex *
                                        rowHeight,

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

        const worldWidth =
            Math.max(
                760,
                padX * 2 +
                    Math.max(
                        1,
                        depthKeys.length
                    ) *
                        columnWidth
            );

        const worldHeight =
            Math.max(
                480,
                padY * 2 +
                    maxRows *
                        rowHeight
            );

        nodes.replaceChildren();
        edges.replaceChildren();

        nodes.style.width =
            `${worldWidth}px`;

        nodes.style.height =
            `${worldHeight}px`;

        edges.setAttribute(
            "viewBox",
            `0 0 ${worldWidth} ${worldHeight}`
        );

        edges.setAttribute(
            "width",
            String(
                worldWidth
            )
        );

        edges.setAttribute(
            "height",
            String(
                worldHeight
            )
        );

        edges.style.width =
            `${worldWidth}px`;

        edges.style.height =
            `${worldHeight}px`;

        const namespace =
            "http://www.w3.org/2000/svg";

        let edgeCount =
            0;

        for (
            const task
            of subset
        ) {
            const target =
                positions.get(
                    task.id
                );

            if (!target) {
                continue;
            }

            for (
                const dependencyId
                of task.dependencies
            ) {
                if (
                    !included.has(
                        dependencyId
                    )
                ) {
                    continue;
                }

                const source =
                    positions.get(
                        dependencyId
                    );

                if (!source) {
                    continue;
                }

                const path =
                    document.createElementNS(
                        namespace,
                        "path"
                    );

                const sx =
                    source.x +
                    source.width;

                const sy =
                    source.y +
                    source.height /
                        2;

                const tx =
                    target.x;

                const ty =
                    target.y +
                    target.height /
                        2;

                const mid =
                    sx +
                    Math.max(
                        48,
                        (
                            tx -
                            sx
                        ) /
                            2
                    );

                path.setAttribute(
                    "d",
                    `M ${sx} ${sy} C ${mid} ${sy}, ${mid} ${ty}, ${tx} ${ty}`
                );

                path.setAttribute(
                    "class",
                    (
                        `graph-edge ${
                            task.ready
                                ? "ready"
                                : ""
                        }`
                    ).trim()
                );

                path.setAttribute(
                    "vector-effect",
                    "non-scaling-stroke"
                );

                path.dataset
                    .sourceTaskId =
                    dependencyId;

                path.dataset
                    .targetTaskId =
                    task.id;

                edges.append(
                    path
                );

                edgeCount +=
                    1;
            }
        }

        for (
            const task
            of subset
        ) {
            const position =
                positions.get(
                    task.id
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
                causalNodeClass(
                    task
                );

            node.dataset
                .taskId =
                task.id;

            node.dataset
                .objective =
                task.objective;

            node.dataset
                .state =
                task.state;

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
                `${task.title}. ${statusLanguage(task.state).plain}. Objective ${task.objective}.`
            );

            node.innerHTML =
                `<strong>${escapeHtml(task.title)}</strong><small>${escapeHtml(task.priority)} · ${escapeHtml(task.state)}</small>`;

            if (
                task.id ===
                selected?.id
            ) {
                node.dataset
                    .selected =
                    "true";
            }

            node.addEventListener(
                "click",
                () => {
                    selectTask(
                        task.id,
                        {
                            openInspector:
                                true,
                            source:
                                "causal"
                        }
                    );
                }
            );

            nodes.append(
                node
            );
        }

        if (summary) {
            summary.textContent =
                `${subset.length} represented task${subset.length === 1 ? "" : "s"} · ${edgeCount} represented dependency edge${edgeCount === 1 ? "" : "s"} · deterministic projection`;
        }
    }

    function applyCausalSemantics() {
        const mode =
            state.causalMode;

        const selected =
            selectedTask();

        const graph =
            $("#graph-stage");

        if (!graph) {
            return;
        }

        graph.dataset
            .semanticMode =
            mode;

        graph.dataset
            .selectedTask =
            selected?.id ||
            "";

        const nodes =
            $$(
                ".graph-node",
                graph
            );

        const cards =
            $$(
                ".task-card",
                $(
                    "#causal-flow"
                ) ||
                document
            );

        const related =
            new Set();

        if (selected) {
            related.add(
                selected.id
            );

            if (
                mode ===
                    "dependencies" ||
                mode ===
                    "blockers"
            ) {
                for (
                    const id
                    of unresolvedDependencies(
                        selected
                    )
                ) {
                    related.add(
                        id
                    );
                }

                for (
                    const id
                    of selected.dependencies
                ) {
                    related.add(
                        id
                    );
                }
            } else if (
                mode ===
                "impact"
            ) {
                for (
                    const id
                    of downstreamIds(
                        selected.id
                    )
                ) {
                    related.add(
                        id
                    );
                }
            } else if (
                mode ===
                "objective"
            ) {
                for (
                    const task
                    of state.tasks
                ) {
                    if (
                        task.objective ===
                        selected.objective
                    ) {
                        related.add(
                            task.id
                        );
                    }
                }
            }
        }

        for (
            const element
            of [
                ...nodes,
                ...cards
            ]
        ) {
            const id =
                element.dataset
                    .taskId ||
                element.getAttribute(
                    "data-task-id"
                ) ||
                "";

            element.dataset
                .semanticMatch =
                (
                    !selected ||
                    mode ===
                        "authority" ||
                    mode ===
                        "critical" ||
                    mode ===
                        "flow" ||
                    !id ||
                    related.has(
                        id
                    )
                )
                    ? "true"
                    : "false";
        }
    }

    function clampZoom(
        value
    ) {
        return clamp(
            Number(
                value
            ) ||
                1,
            0.55,
            1.8
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
                value
            );

        state.causalZoom =
            next;

        const nodes =
            $("#graph-nodes");

        const edges =
            $("#graph-edges");

        for (
            const target
            of [
                nodes,
                edges
            ]
        ) {
            if (!target) {
                continue;
            }

            target.style
                .transformOrigin =
                "0 0";

            target.style
                .transform =
                `scale(${next})`;
        }

        const label =
            $(
                "#causal-zoom-label"
            );

        if (label) {
            label.textContent =
                `${Math.round(
                    next *
                        100
                )}%`;
        }

        if (persist) {
            safeWrite(
                STORAGE.causalZoom,
                String(
                    next
                )
            );
        }
    }

    function ensureInterfaceControls() {
        const actions =
            $(".top-actions") ||
            $(".topbar-actions") ||
            $("header .actions");

        if (
            !actions ||
            $("#niche-disclosure")
        ) {
            return;
        }

        const cluster =
            document.createElement(
                "div"
            );

        cluster.className =
            "niche-understanding-controls";

        cluster.innerHTML = `
            <label class="niche-control-label">
                <span>DETAIL</span>

                <select
                    id="niche-disclosure"
                    aria-label="Interface detail level"
                >
                    <option value="glance">
                        Glance
                    </option>

                    <option value="work">
                        Work
                    </option>

                    <option value="deep">
                        Deep
                    </option>
                </select>
            </label>

            <label class="niche-control-label">
                <span>DENSITY</span>

                <select
                    id="niche-density"
                    aria-label="Interface density"
                >
                    <option value="comfortable">
                        Comfortable
                    </option>

                    <option value="compact">
                        Compact
                    </option>

                    <option value="dense">
                        Dense
                    </option>
                </select>
            </label>

            <button
                id="niche-help"
                class="niche-help-button"
                type="button"
                aria-haspopup="dialog"
                aria-label="Explain the interface"
            >
                ?
            </button>
        `;

        actions.prepend(
            cluster
        );

        $("#niche-disclosure")
            ?.addEventListener(
                "change",
                (
                    event
                ) => {
                    applyDisclosure(
                        event.currentTarget
                            .value
                    );
                }
            );

        $("#niche-density")
            ?.addEventListener(
                "change",
                (
                    event
                ) => {
                    applyDensity(
                        event.currentTarget
                            .value
                    );
                }
            );

        $("#niche-help")
            ?.addEventListener(
                "click",
                (
                    event
                ) => {
                    openHelp(
                        "projection",
                        event.currentTarget
                    );
                }
            );

        applyDisclosure(
            state.disclosure,
            {
                persist:
                    false
            }
        );

        applyDensity(
            state.density,
            {
                persist:
                    false
            }
        );
    }

    function ensureHelpShell() {
        if (
            $(
                "#niche-help-shell"
            )
        ) {
            return;
        }

        const shell =
            document.createElement(
                "div"
            );

        shell.id =
            "niche-help-shell";

        shell.className =
            "niche-help-shell";

        shell.hidden =
            true;

        shell.setAttribute(
            "role",
            "dialog"
        );

        shell.setAttribute(
            "aria-modal",
            "true"
        );

        shell.setAttribute(
            "aria-labelledby",
            "niche-help-title"
        );

        shell.innerHTML = `
            <div class="niche-help-dialog">
                <div class="eyebrow">
                    CONTEXTUAL ORIENTATION
                </div>

                <h2 id="niche-help-title">
                    Context
                </h2>

                <p id="niche-help-plain">
                </p>

                <details id="niche-help-deep">
                    <summary>
                        Technical meaning
                    </summary>

                    <p id="niche-help-deep-copy">
                    </p>
                </details>

                <div class="niche-help-actions">
                    <button
                        type="button"
                        id="niche-help-close"
                        class="confirm"
                    >
                        Close
                    </button>
                </div>
            </div>
        `;

        document.body.append(
            shell
        );

        $("#niche-help-close", shell)
            ?.addEventListener(
                "click",
                closeHelp
            );

        shell.addEventListener(
            "click",
            (
                event
            ) => {
                if (
                    event.target ===
                    shell
                ) {
                    closeHelp();
                }
            }
        );
    }

    function openHelp(
        key,
        returnFocus =
            document.activeElement
    ) {
        ensureHelpShell();

        const content =
            HELP[
                key
            ] ||
            HELP.projection;

        state.helpReturnFocus =
            returnFocus instanceof
                HTMLElement
                ? returnFocus
                : null;

        $("#niche-help-title")
            .textContent =
            content.title;

        $("#niche-help-plain")
            .textContent =
            content.plain;

        $("#niche-help-deep-copy")
            .textContent =
            content.deep;

        const shell =
            $("#niche-help-shell");

        shell.hidden =
            false;

        $("#niche-help-close")
            ?.focus();
    }

    function closeHelp() {
        const shell =
            $("#niche-help-shell");

        if (
            !shell ||
            shell.hidden
        ) {
            return;
        }

        shell.hidden =
            true;

        state
            .helpReturnFocus
            ?.focus();

        state.helpReturnFocus =
            null;
    }

    function ensureLiveRegion() {
        if (
            $(
                "#niche-vnext-live"
            )
        ) {
            return;
        }

        const live =
            document.createElement(
                "div"
            );

        live.id =
            "niche-vnext-live";

        live.className =
            "sr-only";

        live.setAttribute(
            "aria-live",
            "polite"
        );

        live.setAttribute(
            "aria-atomic",
            "true"
        );

        document.body.append(
            live
        );
    }

    function announce(
        message
    ) {
        ensureLiveRegion();

        const live =
            $("#niche-vnext-live");

        live.textContent =
            "";

        window.setTimeout(
            () => {
                live.textContent =
                    message;
            },
            20
        );
    }

    function enhanceGlobalStatus() {
        const statusrail =
            $("#statusrail");

        if (
            !statusrail ||
            $(
                "#vnext-status-explainer",
                statusrail
            )
        ) {
            return;
        }

        const explainer =
            document.createElement(
                "button"
            );

        explainer.id =
            "vnext-status-explainer";

        explainer.className =
            "vnext-status-explainer";

        explainer.type =
            "button";

        explainer.textContent =
            "WHAT DO THESE STATES MEAN?";

        explainer.addEventListener(
            "click",
            (
                event
            ) => {
                openHelp(
                    "projection",
                    event.currentTarget
                );
            }
        );

        statusrail.append(
            explainer
        );
    }

    function ensureExecuteOrientation() {
        const surface =
            $("#surface-execute");

        const executionCore =
            $(
                ".execution-core",
                surface ||
                document
            );

        if (
            !surface ||
            !executionCore ||
            $("#execute-orientation")
        ) {
            return;
        }

        const orientation =
            document.createElement(
                "section"
            );

        orientation.id =
            "execute-orientation";

        orientation.className =
            "execute-orientation";

        orientation.setAttribute(
            "aria-label",
            "Current work orientation"
        );

        orientation.innerHTML = `
            <div class="orientation-primary">
                <span class="orientation-kicker">
                    RIGHT NOW
                </span>

                <strong id="orientation-action">
                    Finding the next represented action…
                </strong>

                <span id="orientation-plain-state">
                    Current source is loading.
                </span>
            </div>

            <div
                class="orientation-facts"
                role="list"
            >
                <button
                    type="button"
                    role="listitem"
                    data-orientation="why"
                >
                    <span>
                        WHY THIS
                    </span>

                    <strong id="orientation-why">
                        Unknown
                    </strong>
                </button>

                <button
                    type="button"
                    role="listitem"
                    data-orientation="needs"
                >
                    <span>
                        NEEDS
                    </span>

                    <strong id="orientation-needs">
                        Unknown
                    </strong>
                </button>

                <button
                    type="button"
                    role="listitem"
                    data-orientation="affects"
                >
                    <span>
                        AFFECTS
                    </span>

                    <strong id="orientation-affects">
                        Unknown
                    </strong>
                </button>

                <button
                    type="button"
                    role="listitem"
                    data-orientation="proof"
                >
                    <span>
                        PROOF
                    </span>

                    <strong id="orientation-proof">
                        Unknown
                    </strong>
                </button>
            </div>

            <div class="orientation-authority">
                <span>
                    INTERFACE STATUS
                </span>

                <strong>
                    projection only
                </strong>

                <button
                    type="button"
                    data-help="projection"
                >
                    what does that mean?
                </button>
            </div>
        `;

        executionCore
            .insertAdjacentElement(
                "afterbegin",
                orientation
            );

        $(
            '[data-help="projection"]',
            orientation
        )?.addEventListener(
            "click",
            (
                event
            ) => {
                openHelp(
                    "projection",
                    event.currentTarget
                );
            }
        );

        for (
            const button
            of $$(
                "[data-orientation]",
                orientation
            )
        ) {
            button.addEventListener(
                "click",
                () => {
                    const key =
                        button
                            .dataset
                            .orientation;

                    if (
                        key ===
                        "needs"
                    ) {
                        openHelp(
                            "dependencies",
                            button
                        );

                        return;
                    }

                    if (
                        key ===
                        "proof"
                    ) {
                        openHelp(
                            "evidence",
                            button
                        );

                        return;
                    }

                    if (
                        key ===
                        "affects"
                    ) {
                        openHelp(
                            "dependents",
                            button
                        );

                        return;
                    }

                    focusInspectorForRecommended();
                }
            );
        }
    }

    function evidenceSummary(
        task
    ) {
        if (!task) {
            return "Unknown";
        }

        const requirementRepresented =
            task.completion !==
                undefined &&
            task.completion !==
                null &&
            task.completion !==
                "";

        const evidenceRepresented =
            task.evidence !==
                undefined &&
            task.evidence !==
                null &&
            task.evidence !==
                "";

        if (
            evidenceRepresented
        ) {
            return "Available";
        }

        if (
            requirementRepresented
        ) {
            return "Required / unresolved";
        }

        return "Requirement unknown";
    }

    function enhanceExecute() {
        ensureExecuteOrientation();

        const task =
            recommendedTask();

        const action =
            $("#orientation-action");

        const plainState =
            $("#orientation-plain-state");

        const why =
            $("#orientation-why");

        const needs =
            $("#orientation-needs");

        const affects =
            $("#orientation-affects");

        const proof =
            $("#orientation-proof");

        if (
            !action ||
            !plainState ||
            !why ||
            !needs ||
            !affects ||
            !proof
        ) {
            return;
        }

        if (!task) {
            action.textContent =
                "No executable recommendation is currently represented.";

            plainState.textContent =
                "The core task engine may still be loading, degraded, or exposing no eligible task.";

            why.textContent =
                "Unknown";

            needs.textContent =
                "Unknown";

            affects.textContent =
                "Unknown";

            proof.textContent =
                "Unknown";

            return;
        }

        const unresolved =
            unresolvedDependencies(
                task
            );

        const downstream =
            downstreamIds(
                task.id
            );

        const language =
            statusLanguage(
                task.state
            );

        action.textContent =
            task.title;

        plainState.textContent =
            `${language.plain}. Canonical state: ${language.canonical}.`;

        why.textContent =
            task.priority !==
                "unknown"
                ? `${task.state} · ${task.priority}`
                : task.state;

        needs.textContent =
            unresolved.length
                ? `${unresolved.length} unresolved`
                : task.dependencies.length
                    ? "Represented prerequisites complete"
                    : "No represented prerequisite";

        affects.textContent =
            downstream.length
                ? `${downstream.length} downstream`
                : "No represented downstream task";

        proof.textContent =
            evidenceSummary(
                task
            );
    }

    function focusInspectorForRecommended() {
        const task =
            recommendedTask();

        if (!task) {
            return;
        }

        selectTask(
            task.id,
            {
                openInspector:
                    true,
                source:
                    "execute-orientation"
            }
        );
    }

    function selectTask(
        id,
        {
            openInspector =
                false,

            source =
                "vnext"
        } = {}
    ) {
        const normalized =
            asText(
                id
            );

        if (!normalized) {
            return;
        }

        state.selectedTaskId =
            normalized;

        safeWrite(
            STORAGE.selectedTaskId,
            normalized
        );

        if (
            openInspector &&
            window.Niche &&
            typeof window.Niche.task ===
                "function"
        ) {
            try {
                window.Niche
                    .task(
                        normalized
                    );
            } catch {
                return;
            }
        }

        enhanceInspector();
        enhanceCausalCompanion();
        renderCausalProjection();
        applyCausalSemantics();
        updateDeepLink();

        emit(
            "selection",
            {
                task_id:
                    normalized,

                source
            }
        );
    }

    function enhanceInspector() {
        const inspector =
            $("#inspector");

        const body =
            $("#inspector-body");

        if (
            !inspector ||
            !body
        ) {
            return;
        }

        const nicheState =
            currentNicheState();

        const selected =
            asText(
                nicheState
                    ?.selectedTaskId ||
                state
                    .selectedTaskId
            );

        if (selected) {
            state.selectedTaskId =
                selected;

            safeWrite(
                STORAGE.selectedTaskId,
                selected
            );
        }

        if (
            !$(
                "#inspector-vnext-toolbar",
                inspector
            )
        ) {
            const toolbar =
                document.createElement(
                    "div"
                );

            toolbar.id =
                "inspector-vnext-toolbar";

            toolbar.className =
                "inspector-vnext-toolbar";

            toolbar.innerHTML = `
                <button
                    type="button"
                    id="inspector-pin"
                    aria-pressed="false"
                >
                    PIN
                </button>

                <button
                    type="button"
                    data-inspector-detail="glance"
                >
                    GLANCE
                </button>

                <button
                    type="button"
                    data-inspector-detail="work"
                >
                    WORK
                </button>

                <button
                    type="button"
                    data-inspector-detail="deep"
                >
                    DEEP
                </button>
            `;

            const head =
                $(
                    ".inspector-head",
                    inspector
                ) ||
                inspector
                    .firstElementChild;

            head
                ?.insertAdjacentElement(
                    "afterend",
                    toolbar
                );

            $("#inspector-pin", toolbar)
                ?.addEventListener(
                    "click",
                    (
                        event
                    ) => {
                        state.inspectorPinned =
                            !state.inspectorPinned;

                        safeWrite(
                            STORAGE.inspectorPinned,
                            state.inspectorPinned
                                ? "true"
                                : "false"
                        );

                        inspector.dataset
                            .pinned =
                            state.inspectorPinned
                                ? "true"
                                : "false";

                        event.currentTarget
                            .setAttribute(
                                "aria-pressed",
                                state.inspectorPinned
                                    ? "true"
                                    : "false"
                            );
                    }
                );

            for (
                const button
                of $$(
                    "[data-inspector-detail]",
                    toolbar
                )
            ) {
                button.addEventListener(
                    "click",
                    () => {
                        applyDisclosure(
                            button
                                .dataset
                                .inspectorDetail
                        );
                    }
                );
            }
        }

        inspector.dataset
            .pinned =
            state.inspectorPinned
                ? "true"
                : "false";

        $("#inspector-pin", inspector)
            ?.setAttribute(
                "aria-pressed",
                state.inspectorPinned
                    ? "true"
                    : "false"
            );

        const sections =
            $$(
                ".inspector-section",
                body
            );

        const glance =
            new Set([
                "IDENTITY",
                "PURPOSE",
                "DEPENDENCIES",
                "COMPLETION",
                "EVIDENCE"
            ]);

        const work =
            new Set([
                ...glance,
                "DEPENDENTS",
                "IMPACT",
                "edifice",
                "AUTHORITY"
            ]);

        for (
            const section
            of sections
        ) {
            const label =
                asText(
                    $(
                        "h3",
                        section
                    )
                        ?.textContent
                )
                    .toUpperCase();

            section.dataset
                .inspectorSection =
                label
                    .toLocaleLowerCase()
                    .replaceAll(
                        " ",
                        "-"
                    );

            if (
                state.disclosure ===
                "glance"
            ) {
                section.hidden =
                    !glance.has(
                        label
                    );
            } else if (
                state.disclosure ===
                "work"
            ) {
                section.hidden =
                    !work.has(
                        label
                    );
            } else {
                section.hidden =
                    false;
            }
        }
    }

    function enhanceCausalCompanion() {
        const target =
            $(
                "#causal-companion-body"
            );

        if (!target) {
            return;
        }

        const task =
            selectedTask();

        if (!task) {
            target.innerHTML = `
                <div class="causal-empty-explanation">
                    <strong>
                        Select a represented task.
                    </strong>

                    <span>
                        This panel will explain why it is connected,
                        what it needs, and what may rely on it.
                    </span>
                </div>
            `;

            return;
        }

        const unresolved =
            unresolvedDependencies(
                task
            );

        const directDependents =
            state
                .dependentsById
                .get(
                    task.id
                ) ||
            [];

        const downstream =
            downstreamIds(
                task.id
            );

        const authority =
            task.authority ===
                undefined ||
            task.authority ===
                null ||
            task.authority ===
                ""
                ? "unknown"
                : asText(
                    task.authority
                );

        target.innerHTML = `
            <dl class="causal-companion-grid">
                <dt>
                    selected
                </dt>

                <dd>
                    ${escapeHtml(task.title)}
                </dd>

                <dt>
                    state
                </dt>

                <dd>
                    ${escapeHtml(statusLanguage(task.state).plain)}
                    <small>
                        ${escapeHtml(task.state)}
                    </small>
                </dd>

                <dt>
                    objective
                </dt>

                <dd>
                    ${escapeHtml(task.objective)}
                </dd>

                <dt>
                    needs
                </dt>

                <dd>
                    ${
                        unresolved.length
                            ? `${unresolved.length} unresolved represented prerequisite${unresolved.length === 1 ? "" : "s"}`
                            : "No unresolved represented prerequisite"
                    }
                </dd>

                <dt>
                    direct dependents
                </dt>

                <dd>
                    ${directDependents.length}
                </dd>

                <dt>
                    downstream reach
                </dt>

                <dd>
                    ${downstream.length}
                </dd>

                <dt>
                    authority
                </dt>

                <dd>
                    ${escapeHtml(authority)}
                </dd>

                <dt>
                    geometry
                </dt>

                <dd>
                    projection only
                </dd>
            </dl>
        `;
    }

    function ensureObjectiveNavigator() {
        const surface =
            $("#surface-objectives");

        const grid =
            $("#objective-grid");

        if (
            !surface ||
            !grid ||
            $("#objective-navigator")
        ) {
            return;
        }

        const navigator =
            document.createElement(
                "aside"
            );

        navigator.id =
            "objective-navigator";

        navigator.className =
            "objective-navigator";

        navigator.setAttribute(
            "aria-label",
            "Objective navigator"
        );

        navigator.innerHTML = `
            <div class="objective-navigator-head">
                <span class="eyebrow">
                    OBJECTIVE NAVIGATOR
                </span>

                <strong id="objective-navigator-count">
                    0 represented objectives
                </strong>
            </div>

            <div
                id="objective-navigator-list"
                class="objective-navigator-list"
            >
            </div>
        `;

        grid.insertAdjacentElement(
            "beforebegin",
            navigator
        );
    }

    function objectiveGroups() {
        const groups =
            new Map();

        for (
            const task
            of state.tasks
        ) {
            if (
                !groups.has(
                    task.objective
                )
            ) {
                groups.set(
                    task.objective,
                    []
                );
            }

            groups
                .get(
                    task.objective
                )
                .push(
                    task
                );
        }

        return Array
            .from(
                groups.entries()
            )
            .sort(
                (
                    [a],
                    [b]
                ) =>
                    a.localeCompare(
                        b
                    )
            );
    }

    function objectiveMatchesFilter(
        tasks,
        filter
    ) {
        if (
            filter ===
            "all"
        ) {
            return true;
        }

        if (
            filter ===
            "active"
        ) {
            return tasks.some(
                (
                    task
                ) =>
                    task.state ===
                    "active"
            );
        }

        if (
            filter ===
            "ready"
        ) {
            return tasks.some(
                (
                    task
                ) =>
                    task.ready ||
                    task.state ===
                        "ready"
            );
        }

        if (
            filter ===
            "blocked"
        ) {
            return tasks.some(
                (
                    task
                ) =>
                    task.state ===
                    "blocked"
            );
        }

        if (
            filter ===
            "complete"
        ) {
            return (
                tasks.length >
                    0 &&
                tasks.every(
                    (
                        task
                    ) =>
                        task.state ===
                        "complete"
                )
            );
        }

        return true;
    }

    function enhanceObjectives() {
        ensureObjectiveNavigator();

        const list =
            $(
                "#objective-navigator-list"
            );

        const count =
            $(
                "#objective-navigator-count"
            );

        const grid =
            $("#objective-grid");

        if (
            !list ||
            !count ||
            !grid
        ) {
            return;
        }

        const groups =
            objectiveGroups();

        count.textContent =
            `${groups.length} represented objective${groups.length === 1 ? "" : "s"}`;

        const query =
            lower(
                state.objectiveSearch
            );

        const fragment =
            document.createDocumentFragment();

        for (
            const [
                objective,
                tasks
            ]
            of groups
        ) {
            if (
                query &&
                !lower(
                    objective
                ).includes(
                    query
                ) &&
                !tasks.some(
                    (
                        task
                    ) =>
                        lower(
                            task.title
                        )
                            .includes(
                                query
                            )
                )
            ) {
                continue;
            }

            if (
                !objectiveMatchesFilter(
                    tasks,
                    state.objectiveFilter
                )
            ) {
                continue;
            }

            const complete =
                tasks.filter(
                    (
                        task
                    ) =>
                        task.state ===
                        "complete"
                ).length;

            const ready =
                tasks.filter(
                    (
                        task
                    ) =>
                        task.ready ||
                        task.state ===
                            "ready"
                ).length;

            const blocked =
                tasks.filter(
                    (
                        task
                    ) =>
                        task.state ===
                        "blocked"
                ).length;

            const progress =
                tasks.length
                    ? (
                        complete /
                        tasks.length
                    ) *
                        100
                    : 0;

            const button =
                document.createElement(
                    "button"
                );

            button.type =
                "button";

            button.className =
                "objective-navigator-item";

            button.innerHTML = `
                <strong>
                    ${escapeHtml(objective)}
                </strong>

                <span>
                    ${complete}/${tasks.length} complete ·
                    ${ready} ready ·
                    ${blocked} blocked
                </span>

                <i
                    aria-hidden="true"
                    style="--objective-progress:${progress}%"
                >
                </i>
            `;

            button.addEventListener(
                "click",
                () => {
                    focusObjective(
                        objective
                    );
                }
            );

            fragment.append(
                button
            );
        }

        list.replaceChildren(
            fragment
        );

        for (
            const card
            of Array.from(
                grid.children
            )
        ) {
            card.classList.add(
                "objective-progressive-card"
            );

            if (
                !card.hasAttribute(
                    "tabindex"
                )
            ) {
                card.tabIndex =
                    0;
            }

            const heading =
                $(
                    "h2",
                    card
                );

            if (heading) {
                card.dataset
                    .objectiveId =
                    asText(
                        heading.textContent
                    );
            }
        }
    }

    function focusObjective(
        objective
    ) {
        const grid =
            $("#objective-grid");

        if (!grid) {
            return;
        }

        let found =
            null;

        for (
            const card
            of Array.from(
                grid.children
            )
        ) {
            const match =
                card
                    .dataset
                    .objectiveId ===
                objective;

            card.hidden =
                !match;

            if (match) {
                found =
                    card;
            }
        }

        grid.dataset
            .objectiveFocus =
            objective;

        if (found) {
            found.scrollIntoView({
                block:
                    "start",
                behavior:
                    prefersReducedMotion()
                        ? "auto"
                        : "smooth"
            });

            found.focus({
                preventScroll:
                    true
            });
        }

        announce(
            `Focused objective ${objective}.`
        );
    }

    function clearObjectiveFocus() {
        const grid =
            $("#objective-grid");

        if (!grid) {
            return;
        }

        delete grid
            .dataset
            .objectiveFocus;

        for (
            const card
            of Array.from(
                grid.children
            )
        ) {
            card.hidden =
                false;
        }

        enhanceObjectives();
    }

    function bindObjectiveControls() {
        const search =
            $("#objective-search");

        if (
            search &&
            !search
                .dataset
                .vnextBound
        ) {
            search.dataset
                .vnextBound =
                "true";

            search.value =
                state.objectiveSearch;

            search.addEventListener(
                "input",
                () => {
                    state.objectiveSearch =
                        search.value
                            .trim();

                    safeWrite(
                        STORAGE.objectiveSearch,
                        state.objectiveSearch
                    );

                    enhanceObjectives();
                }
            );
        }

        for (
            const button
            of $$(
                "[data-objective-filter]"
            )
        ) {
            if (
                button.dataset
                    .vnextBound
            ) {
                continue;
            }

            button.dataset
                .vnextBound =
                "true";

            button.addEventListener(
                "click",
                () => {
                    state.objectiveFilter =
                        button
                            .dataset
                            .objectiveFilter ||
                        "all";

                    safeWrite(
                        STORAGE.objectiveFilter,
                        state.objectiveFilter
                    );

                    for (
                        const candidate
                        of $$(
                            "[data-objective-filter]"
                        )
                    ) {
                        candidate
                            .classList
                            .toggle(
                                "active",
                                candidate ===
                                    button
                            );
                    }

                    enhanceObjectives();
                }
            );
        }

        const surface =
            $("#surface-objectives");

        if (
            surface &&
            !$(
                "#objective-focus-clear",
                surface
            )
        ) {
            const button =
                document.createElement(
                    "button"
                );

            button.id =
                "objective-focus-clear";

            button.className =
                "objective-focus-clear";

            button.type =
                "button";

            button.textContent =
                "SHOW ALL OBJECTIVES";

            button.addEventListener(
                "click",
                clearObjectiveFocus
            );

            $(
                ".surface-head",
                surface
            )
                ?.append(
                    button
                );
        }
    }

    function ensureTimelineTools() {
        const timeline =
            $("#timeline");

        if (
            !timeline ||
            $("#timeline-vnext-tools")
        ) {
            return;
        }

        const tools =
            document.createElement(
                "div"
            );

        tools.id =
            "timeline-vnext-tools";

        tools.className =
            "vnext-filterbar";

        tools.innerHTML = `
            <input
                id="timeline-vnext-search"
                type="search"
                autocomplete="off"
                placeholder="Search recorded history…"
                aria-label="Search timeline"
            >

            <select
                id="timeline-vnext-range"
                aria-label="Timeline range"
            >
                <option value="recent">
                    Recent
                </option>

                <option value="all">
                    All loaded history
                </option>
            </select>

            <button
                type="button"
                data-help="unknown"
            >
                UNKNOWN IS NOT EMPTY
            </button>
        `;

        timeline
            .insertAdjacentElement(
                "beforebegin",
                tools
            );

        $("#timeline-vnext-search")
            ?.addEventListener(
                "input",
                filterTimelineDom
            );

        $("#timeline-vnext-range")
            ?.addEventListener(
                "change",
                filterTimelineDom
            );

        $(
            '[data-help="unknown"]',
            tools
        )
            ?.addEventListener(
                "click",
                (
                    event
                ) => {
                    openHelp(
                        "unknown",
                        event.currentTarget
                    );
                }
            );
    }

    function filterTimelineDom() {
        const query =
            lower(
                $(
                    "#timeline-vnext-search"
                )
                    ?.value
            );

        const range =
            $(
                "#timeline-vnext-range"
            )
                ?.value ||
            "recent";

        const items =
            $(
                "#timeline"
            )
                ? $$(
                    "#timeline > *"
                )
                : [];

        items.forEach(
            (
                item,
                index
            ) => {
                const matchesQuery =
                    !query ||
                    lower(
                        item.textContent
                    )
                        .includes(
                            query
                        );

                const matchesRange =
                    range ===
                        "all" ||
                    index <
                        100;

                item.hidden =
                    !(
                        matchesQuery &&
                        matchesRange
                    );
            }
        );
    }

    function ensureEvidenceTools() {
        const grid =
            $("#evidence-grid");

        if (
            !grid ||
            $("#evidence-vnext-tools")
        ) {
            return;
        }

        const tools =
            document.createElement(
                "div"
            );

        tools.id =
            "evidence-vnext-tools";

        tools.className =
            "vnext-filterbar";

        tools.innerHTML = `
            <input
                id="evidence-vnext-search"
                type="search"
                autocomplete="off"
                placeholder="Search evidence context…"
                aria-label="Search evidence"
            >

            <select
                id="evidence-vnext-state"
                aria-label="Evidence state"
            >
                <option value="all">
                    All represented states
                </option>

                <option value="available">
                    Available
                </option>

                <option value="required">
                    Required / unresolved
                </option>

                <option value="unknown">
                    Requirement unknown
                </option>
            </select>

            <button
                type="button"
                data-help="evidence"
            >
                WHAT COUNTS AS MISSING?
            </button>
        `;

        grid.insertAdjacentElement(
            "beforebegin",
            tools
        );

        $("#evidence-vnext-search")
            ?.addEventListener(
                "input",
                filterEvidenceDom
            );

        $("#evidence-vnext-state")
            ?.addEventListener(
                "change",
                filterEvidenceDom
            );

        $(
            '[data-help="evidence"]',
            tools
        )
            ?.addEventListener(
                "click",
                (
                    event
                ) => {
                    openHelp(
                        "evidence",
                        event.currentTarget
                    );
                }
            );
    }

    function classifyEvidenceElement(
        element
    ) {
        const value =
            lower(
                element.textContent
            );

        if (
            value.includes(
                "available"
            ) ||
            value.includes(
                "established"
            )
        ) {
            return "available";
        }

        if (
            value.includes(
                "required"
            ) ||
            value.includes(
                "unresolved"
            )
        ) {
            return "required";
        }

        return "unknown";
    }

    function filterEvidenceDom() {
        const query =
            lower(
                $(
                    "#evidence-vnext-search"
                )
                    ?.value
            );

        const filter =
            $(
                "#evidence-vnext-state"
            )
                ?.value ||
            "all";

        for (
            const item
            of $$(
                "#evidence-grid > *"
            )
        ) {
            const matchesQuery =
                !query ||
                lower(
                    item.textContent
                )
                    .includes(
                        query
                    );

            const evidenceState =
                classifyEvidenceElement(
                    item
                );

            const matchesState =
                filter ===
                    "all" ||
                evidenceState ===
                    filter;

            item.hidden =
                !(
                    matchesQuery &&
                    matchesState
                );
        }
    }

    function ensureHistoryTools() {
        const list =
            $("#history-list");

        if (
            !list ||
            $("#history-vnext-tools")
        ) {
            return;
        }

        const tools =
            document.createElement(
                "div"
            );

        tools.id =
            "history-vnext-tools";

        tools.className =
            "vnext-filterbar";

        tools.innerHTML = `
            <input
                id="history-vnext-search"
                type="search"
                autocomplete="off"
                placeholder="Search immutable history…"
                aria-label="Search history"
            >

            <select
                id="history-vnext-limit"
                aria-label="History density"
            >
                <option value="50">
                    50 records
                </option>

                <option value="100">
                    100 records
                </option>

                <option value="250">
                    250 records
                </option>
            </select>

            <span class="vnext-readonly-mark">
                READ ONLY
            </span>
        `;

        list.insertAdjacentElement(
            "beforebegin",
            tools
        );

        $("#history-vnext-search")
            ?.addEventListener(
                "input",
                filterHistoryDom
            );

        $("#history-vnext-limit")
            ?.addEventListener(
                "change",
                filterHistoryDom
            );
    }

    function filterHistoryDom() {
        const query =
            lower(
                $(
                    "#history-vnext-search"
                )
                    ?.value
            );

        const limit =
            Number(
                $(
                    "#history-vnext-limit"
                )
                    ?.value ||
                50
            );

        $$(
            "#history-list > *"
        )
            .forEach(
                (
                    item,
                    index
                ) => {
                    const matches =
                        !query ||
                        lower(
                            item.textContent
                        )
                            .includes(
                                query
                            );

                    item.hidden =
                        !(
                            matches &&
                            index <
                                limit
                        );
                }
            );
    }

    function ensureLivingExplanation() {
        const surface =
            $("#surface-living");

        if (
            !surface ||
            $("#living-vnext-explanation")
        ) {
            return;
        }

        const panel =
            document.createElement(
                "div"
            );

        panel.id =
            "living-vnext-explanation";

        panel.className =
            "living-vnext-explanation";

        panel.innerHTML = `
            <strong>
                Living is an operational observatory.
            </strong>

            <span>
                It reports represented surface health and freshness.
                It does not override task state or invent task-to-surface relationships.
            </span>
        `;

        $("#living-summary", surface)
            ?.insertAdjacentElement(
                "beforebegin",
                panel
            );
    }

    function parseQuery(
        query
    ) {
        const terms =
            asText(
                query
            )
                .split(
                    /\s+/
                )
                .filter(
                    Boolean
                );

        const filters =
            {};

        const textTerms =
            [];

        for (
            const term
            of terms
        ) {
            const match =
                term.match(
                    /^([a-z]+):(.*)$/i
                );

            if (!match) {
                textTerms.push(
                    term
                );

                continue;
            }

            const key =
                lower(
                    match[1]
                );

            const value =
                lower(
                    match[2]
                );

            if (
                [
                    "state",
                    "priority",
                    "objective"
                ].includes(
                    key
                ) &&
                value
            ) {
                filters[
                    key
                ] =
                    value;
            } else {
                textTerms.push(
                    term
                );
            }
        }

        return {
            text:
                lower(
                    textTerms.join(
                        " "
                    )
                ),

            filters
        };
    }

    function taskMatchesParsedQuery(
        task,
        parsed
    ) {
        if (
            parsed.filters
                .state &&
            lower(
                task.state
            ) !==
                parsed.filters
                    .state
        ) {
            return false;
        }

        if (
            parsed.filters
                .priority &&
            lower(
                task.priority
            ) !==
                parsed.filters
                    .priority
        ) {
            return false;
        }

        if (
            parsed.filters
                .objective &&
            !lower(
                task.objective
            )
                .includes(
                    parsed
                        .filters
                        .objective
                )
        ) {
            return false;
        }

        if (!parsed.text) {
            return true;
        }

        return [
            task.id,
            task.title,
            task.objective,
            task.priority,
            task.state
        ]
            .some(
                (
                    value
                ) =>
                    lower(
                        value
                    )
                        .includes(
                            parsed.text
                        )
            );
    }

    function goToView(
        view
    ) {
        if (
            view ===
                "navigation" &&
            window
                .NicheNavigation &&
            typeof window
                .NicheNavigation
                .open ===
                "function"
        ) {
            window
                .NicheNavigation
                .open();

            safeViewInUrl(
                view
            );

            return;
        }

        if (
            window.Niche &&
            typeof window.Niche.view ===
                "function"
        ) {
            window.Niche
                .view(
                    view
                );
        } else {
            $(
                `.nav [data-view="${view}"]`
            )
                ?.click();
        }

        safeViewInUrl(
            view
        );
    }

    function commandCandidates(
        query
    ) {
        const parsed =
            parseQuery(
                query
            );

        const views = [
            {
                kind:
                    "view",
                label:
                    "Execute",
                detail:
                    "What should I do next?",
                run:
                    () =>
                        goToView(
                            "execute"
                        )
            },

            {
                kind:
                    "view",
                label:
                    "Navigation",
                detail:
                    "Where is represented work?",
                run:
                    () =>
                        goToView(
                            "navigation"
                        )
            },

            {
                kind:
                    "view",
                label:
                    "Causal Field",
                detail:
                    "Why is represented work connected?",
                run:
                    () =>
                        goToView(
                            "causal"
                        )
            },

            {
                kind:
                    "view",
                label:
                    "Objectives",
                detail:
                    "What outcomes are represented?",
                run:
                    () =>
                        goToView(
                            "objectives"
                        )
            },

            {
                kind:
                    "view",
                label:
                    "Timeline",
                detail:
                    "What happened when?",
                run:
                    () =>
                        goToView(
                            "timeline"
                        )
            },

            {
                kind:
                    "view",
                label:
                    "Evidence",
                detail:
                    "What proof is represented?",
                run:
                    () =>
                        goToView(
                            "evidence"
                        )
            },

            {
                kind:
                    "view",
                label:
                    "Living",
                detail:
                    "What operational surfaces are represented?",
                run:
                    () =>
                        goToView(
                            "living"
                        )
            },

            {
                kind:
                    "view",
                label:
                    "History",
                detail:
                    "What immutable changes are recorded?",
                run:
                    () =>
                        goToView(
                            "history"
                        )
            },

            {
                kind:
                    "help",
                label:
                    "Explain authority and projection",
                detail:
                    "Contextual orientation",
                run:
                    () =>
                        openHelp(
                            "projection",
                            $("#palette-input")
                        )
            }
        ];

        const textQuery =
            parsed.text;

        const filteredViews =
            views.filter(
                (
                    item
                ) =>
                    !textQuery ||
                    lower(
                        `${item.label} ${item.detail}`
                    )
                        .includes(
                            textQuery
                        )
            );

        const taskItems =
            state.tasks
                .filter(
                    (
                        task
                    ) =>
                        taskMatchesParsedQuery(
                            task,
                            parsed
                        )
                )
                .slice(
                    0,
                    40
                )
                .map(
                    (
                        task
                    ) => ({
                        kind:
                            "task",

                        label:
                            task.title,

                        detail:
                            `${task.state} · ${task.priority} · ${task.objective}`,

                        run:
                            () => {
                                selectTask(
                                    task.id,
                                    {
                                        openInspector:
                                            true,
                                        source:
                                            "command"
                                    }
                                );
                            }
                    })
                );

        return [
            ...filteredViews,
            ...taskItems
        ]
            .slice(
                0,
                50
            );
    }

    function ensureCommandEnvironment() {
        const shell =
            $("#palette-shell");

        const input =
            $("#palette-input");

        const results =
            $("#palette-results");

        if (
            !shell ||
            !input ||
            !results ||
            shell.dataset
                .vnextCommand ===
                "true"
        ) {
            return;
        }

        shell.dataset
            .vnextCommand =
            "true";

        input.placeholder =
            "Go anywhere or find represented work…";

        input.setAttribute(
            "aria-describedby",
            "palette-vnext-hint"
        );

        const hint =
            document.createElement(
                "p"
            );

        hint.id =
            "palette-vnext-hint";

        hint.className =
            "palette-vnext-hint";

        hint.textContent =
            "Try a task title, objective, view, state:ready, state:blocked, priority:critical, or ? for help.";

        input.insertAdjacentElement(
            "afterend",
            hint
        );

        input.addEventListener(
            "input",
            (
                event
            ) => {
                event
                    .stopImmediatePropagation();

                renderCommandEnvironment();
            },
            true
        );

        input.addEventListener(
            "keydown",
            (
                event
            ) => {
                handleCommandKeyboard(
                    event
                );
            },
            true
        );

        $("#open-palette")
            ?.addEventListener(
                "click",
                () => {
                    window.setTimeout(
                        renderCommandEnvironment,
                        0
                    );
                },
                true
            );
    }

    function renderCommandEnvironment() {
        const input =
            $("#palette-input");

        const results =
            $("#palette-results");

        if (
            !input ||
            !results
        ) {
            return;
        }

        state.commandItems =
            commandCandidates(
                input.value
            );

        state.activeCommandIndex =
            clamp(
                state.activeCommandIndex,
                0,
                Math.max(
                    0,
                    state.commandItems
                        .length -
                        1
                )
            );

        const fragment =
            document.createDocumentFragment();

        state.commandItems
            .forEach(
                (
                    item,
                    index
                ) => {
                    const button =
                        document.createElement(
                            "button"
                        );

                    button.type =
                        "button";

                    button.className =
                        "palette-result vnext-command-result";

                    button.dataset
                        .commandIndex =
                        String(
                            index
                        );

                    button.setAttribute(
                        "role",
                        "option"
                    );

                    button.setAttribute(
                        "aria-selected",
                        index ===
                            state.activeCommandIndex
                            ? "true"
                            : "false"
                    );

                    button.innerHTML = `
                        <strong>
                            ${escapeHtml(item.label)}
                        </strong>

                        <small>
                            ${escapeHtml(item.detail)}
                        </small>

                        <span>
                            ${escapeHtml(item.kind)}
                        </span>
                    `;

                    button.addEventListener(
                        "click",
                        () => {
                            executeCommand(
                                index,
                                input.value
                            );
                        }
                    );

                    fragment.append(
                        button
                    );
                }
            );

        results.replaceChildren(
            fragment
        );
    }

    function handleCommandKeyboard(
        event
    ) {
        if (
            !state.commandItems
                .length
        ) {
            return;
        }

        if (
            event.key ===
            "ArrowDown"
        ) {
            event.preventDefault();
            event.stopImmediatePropagation();

            state.activeCommandIndex =
                (
                    state.activeCommandIndex +
                    1
                ) %
                state.commandItems.length;

            renderCommandEnvironment();
            focusActiveCommandResult();

            return;
        }

        if (
            event.key ===
            "ArrowUp"
        ) {
            event.preventDefault();
            event.stopImmediatePropagation();

            state.activeCommandIndex =
                (
                    state.activeCommandIndex -
                    1 +
                    state.commandItems.length
                ) %
                state.commandItems.length;

            renderCommandEnvironment();
            focusActiveCommandResult();

            return;
        }

        if (
            event.key ===
            "Enter"
        ) {
            event.preventDefault();
            event.stopImmediatePropagation();

            executeCommand(
                state.activeCommandIndex,
                $("#palette-input")
                    ?.value ||
                    ""
            );
        }
    }

    function focusActiveCommandResult() {
        $(
            `[data-command-index="${state.activeCommandIndex}"]`,
            $("#palette-results") ||
            document
        )
            ?.scrollIntoView({
                block:
                    "nearest"
            });
    }

    function executeCommand(
        index,
        query
    ) {
        const item =
            state.commandItems[
                index
            ];

        if (!item) {
            return;
        }

        if (query) {
            state.commandHistory = [
                query,
                ...state
                    .commandHistory
                    .filter(
                        (
                            value
                        ) =>
                            value !==
                            query
                    )
            ]
                .slice(
                    0,
                    20
                );

            safeWrite(
                STORAGE.commandHistory,
                JSON.stringify(
                    state.commandHistory
                )
            );
        }

        item.run();

        const shell =
            $("#palette-shell");

        if (shell) {
            shell.hidden =
                true;
        }
    }

    function currentView() {
        return (
            currentNicheState()
                ?.activeView ||
            $(".nav [data-view].active")
                ?.dataset
                .view ||
            "execute"
        );
    }

    function safeViewInUrl(
        view
    ) {
        try {
            const url =
                new URL(
                    window.location.href
                );

            url.searchParams
                .set(
                    "view",
                    view
                );

            if (
                state.selectedTaskId
            ) {
                url.searchParams
                    .set(
                        "task",
                        state.selectedTaskId
                    );
            } else {
                url.searchParams
                    .delete(
                        "task"
                    );
            }

            history.replaceState(
                history.state,
                "",
                url
            );
        } catch {
            return;
        }
    }

    function updateDeepLink() {
        safeViewInUrl(
            currentView()
        );
    }

    function restoreDeepLink() {
        try {
            const url =
                new URL(
                    window.location.href
                );

            const view =
                url.searchParams
                    .get(
                        "view"
                    );

            const task =
                url.searchParams
                    .get(
                        "task"
                    );

            if (task) {
                state.selectedTaskId =
                    task;
            }

            if (
                view &&
                [
                    "execute",
                    "navigation",
                    "causal",
                    "objectives",
                    "timeline",
                    "evidence",
                    "living",
                    "history"
                ].includes(
                    view
                )
            ) {
                window.setTimeout(
                    () => {
                        goToView(
                            view
                        );
                    },
                    0
                );
            }
        } catch {
            return;
        }
    }

    function bindNavigationContinuity() {
        document.addEventListener(
            "click",
            (
                event
            ) => {
                const viewButton =
                    event.target
                        .closest
                        ?.(
                            ".nav [data-view]"
                        );

                if (viewButton) {
                    safeViewInUrl(
                        viewButton
                            .dataset
                            .view
                    );
                }

                const taskElement =
                    event.target
                        .closest
                        ?.(
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
                            source:
                                "dom"
                        }
                    );
                }
            },
            true
        );

        window.addEventListener(
            "niche:task-selected",
            (
                event
            ) => {
                const detail =
                    event.detail ||
                    {};

                const id =
                    firstRepresented(
                        detail.taskId,
                        detail.task_id,
                        detail.id
                    );

                if (id) {
                    selectTask(
                        id,
                        {
                            source:
                                "core-event"
                        }
                    );
                }
            }
        );

        window.addEventListener(
            "niche:navigation:selection",
            (
                event
            ) => {
                const id =
                    event.detail
                        ?.task_id;

                if (id) {
                    selectTask(
                        id,
                        {
                            source:
                                "navigation"
                        }
                    );
                }
            }
        );
    }

    function bindTheme() {
        const control =
            $("#niche-theme");

        if (
            !control ||
            control.dataset
                .vnextBound
        ) {
            return;
        }

        control.dataset
            .vnextBound =
            "true";

        control.addEventListener(
            "change",
            () => {
                applyTheme(
                    control.value
                );
            }
        );
    }

    function bindCausalControls() {
        for (
            const button
            of $$(
                "[data-causal-mode]"
            )
        ) {
            if (
                button.dataset
                    .vnextBound
            ) {
                continue;
            }

            button.dataset
                .vnextBound =
                "true";

            button.addEventListener(
                "click",
                () => {
                    applyCausalMode(
                        button
                            .dataset
                            .causalMode
                    );
                }
            );
        }

        for (
            const button
            of $$(
                "[data-causal-viewport]"
            )
        ) {
            if (
                button.dataset
                    .vnextBound
            ) {
                continue;
            }

            button.dataset
                .vnextBound =
                "true";

            button.addEventListener(
                "click",
                () => {
                    const action =
                        button
                            .dataset
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

                    applyCausalZoom(
                        1
                    );
                }
            );
        }
    }

    function editableTarget(
        target
    ) {
        return (
            target instanceof
                Element &&
            Boolean(
                target.closest(
                    "input, textarea, select, [contenteditable='true']"
                )
            )
        );
    }

    function prefersReducedMotion() {
        return (
            window
                .matchMedia
                ?.(
                    "(prefers-reduced-motion: reduce)"
                )
                ?.matches ===
            true
        );
    }

    function bindKeyboard() {
        let awaitingGo =
            false;

        let goTimer =
            null;

        const destinations =
            Object.freeze({
                e:
                    "execute",
                n:
                    "navigation",
                c:
                    "causal",
                o:
                    "objectives",
                t:
                    "timeline",
                v:
                    "evidence",
                l:
                    "living",
                h:
                    "history"
            });

        document.addEventListener(
            "keydown",
            (
                event
            ) => {
                if (
                    event.key ===
                    "Escape"
                ) {
                    const help =
                        $("#niche-help-shell");

                    if (
                        help &&
                        !help.hidden
                    ) {
                        event.preventDefault();

                        closeHelp();

                        return;
                    }
                }

                if (
                    editableTarget(
                        event.target
                    )
                ) {
                    return;
                }

                if (
                    event.key ===
                        "?" &&
                    !event.ctrlKey &&
                    !event.metaKey &&
                    !event.altKey
                ) {
                    event.preventDefault();

                    openHelp(
                        "projection",
                        event.target instanceof
                            HTMLElement
                            ? event.target
                            : null
                    );

                    return;
                }

                if (
                    event.key ===
                        "/" &&
                    !event.ctrlKey &&
                    !event.metaKey &&
                    !event.altKey
                ) {
                    event.preventDefault();

                    $("#open-palette")
                        ?.click();

                    window.setTimeout(
                        () => {
                            $("#palette-input")
                                ?.focus();
                        },
                        0
                    );

                    return;
                }

                if (
                    lower(
                        event.key
                    ) ===
                        "g" &&
                    !event.ctrlKey &&
                    !event.metaKey &&
                    !event.altKey
                ) {
                    awaitingGo =
                        true;

                    window.clearTimeout(
                        goTimer
                    );

                    goTimer =
                        window.setTimeout(
                            () => {
                                awaitingGo =
                                    false;
                            },
                            900
                        );

                    return;
                }

                if (
                    awaitingGo &&
                    destinations[
                        lower(
                            event.key
                        )
                    ]
                ) {
                    event.preventDefault();

                    awaitingGo =
                        false;

                    window.clearTimeout(
                        goTimer
                    );

                    goToView(
                        destinations[
                            lower(
                                event.key
                            )
                        ]
                    );

                    return;
                }

                awaitingGo =
                    false;

                if (
                    lower(
                        event.key
                    ) ===
                        "f" &&
                    !event.ctrlKey &&
                    !event.metaKey &&
                    !event.altKey
                ) {
                    event.preventDefault();

                    goToView(
                        "execute"
                    );

                    $("#start-next")
                        ?.focus();

                    return;
                }

                if (
                    event.key ===
                        " " &&
                    state.selectedTaskId &&
                    !event.ctrlKey &&
                    !event.metaKey &&
                    !event.altKey
                ) {
                    event.preventDefault();

                    selectTask(
                        state.selectedTaskId,
                        {
                            openInspector:
                                true,
                            source:
                                "keyboard"
                        }
                    );
                }
            }
        );
    }

    function enhanceTransitionDialog() {
        const shell =
            $("#transition-shell");

        const preview =
            $("#consequence-preview");

        if (
            !shell ||
            !preview
        ) {
            return;
        }

        shell.dataset
            .vnextConsequence =
            "true";

        if (
            $(
                "#vnext-consequence-legend",
                shell
            )
        ) {
            return;
        }

        const legend =
            document.createElement(
                "div"
            );

        legend.id =
            "vnext-consequence-legend";

        legend.className =
            "vnext-consequence-legend";

        legend.innerHTML = `
            <strong>
                BEFORE YOU CHANGE TASK STATE
            </strong>

            <span>
                Direct effects shown here must come from represented state.
                Downstream eligibility is confirmed only after authoritative recomputation.
            </span>
        `;

        preview.insertAdjacentElement(
            "beforebegin",
            legend
        );
    }

    function ensureSurfaceQuestions() {
        const definitions = [
            [
                "#surface-causal",
                "WHY ARE THESE TASKS RELATED?",
                "Causal Field explains represented dependency, blocker, impact, objective, and authority relationships.",
                "causal"
            ],

            [
                "#surface-objectives",
                "WHAT OUTCOME DOES THE WORK SERVE?",
                "Objectives organize represented work around larger outcomes without fabricating missing edifice.",
                null
            ],

            [
                "#surface-timeline",
                "WHAT HAPPENED WHEN?",
                "Timeline is a projection over recorded events. History remains immutable.",
                null
            ],

            [
                "#surface-evidence",
                "WHAT PROOF EXISTS OR IS REQUIRED?",
                "A requirement can be unresolved only when that requirement is represented.",
                "evidence"
            ],

            [
                "#surface-living",
                "WHAT IS THE SYSTEM REPORTING NOW?",
                "Living reports represented operational surfaces and must not override task authority.",
                null
            ],

            [
                "#surface-history",
                "WHAT CHANGED IN THE IMMUTABLE RECORD?",
                "History is read-only evidence of recorded change.",
                null
            ]
        ];

        for (
            const [
                selector,
                question,
                answer,
                helpKey
            ]
            of definitions
        ) {
            const surface =
                $(
                    selector
                );

            if (
                !surface ||
                $(
                    ".surface-question",
                    surface
                )
            ) {
                continue;
            }

            const head =
                $(
                    ".surface-head",
                    surface
                ) ||
                surface
                    .firstElementChild;

            if (!head) {
                continue;
            }

            const panel =
                document.createElement(
                    "div"
                );

            panel.className =
                "surface-question";

            panel.innerHTML = `
                <span>
                    ${escapeHtml(question)}
                </span>

                <strong>
                    ${escapeHtml(answer)}
                </strong>
            `;

            if (helpKey) {
                const button =
                    document.createElement(
                        "button"
                    );

                button.type =
                    "button";

                button.textContent =
                    "explain";

                button.addEventListener(
                    "click",
                    (
                        event
                    ) => {
                        openHelp(
                            helpKey,
                            event.currentTarget
                        );
                    }
                );

                panel.append(
                    button
                );
            }

            head.insertAdjacentElement(
                "afterend",
                panel
            );
        }
    }

    function queueEnhancementPass() {
        if (
            state.enhancementQueued
        ) {
            return;
        }

        state.enhancementQueued =
            true;

        requestAnimationFrame(
            () => {
                state.enhancementQueued =
                    false;

                enhancementPass();
            }
        );
    }

    function enhancementPass() {
        ensureInterfaceControls();
        ensureHelpShell();
        ensureLiveRegion();
        enhanceGlobalStatus();
        ensureSurfaceQuestions();
        enhanceExecute();
        enhanceInspector();
        bindObjectiveControls();
        enhanceObjectives();
        ensureTimelineTools();
        ensureEvidenceTools();
        ensureHistoryTools();
        ensureLivingExplanation();
        ensureCommandEnvironment();
        enhanceTransitionDialog();
        enhanceCausalCompanion();
        renderCausalProjection();
        applyCausalSemantics();
        filterTimelineDom();
        filterEvidenceDom();
        filterHistoryDom();
    }

    function installEnhancementObserver() {
        if (
            state.enhancementObserver ||
            !(
                "MutationObserver" in
                window
            )
        ) {
            return;
        }

        const root =
            $("#main") ||
            document.body;

        state.enhancementObserver =
            new MutationObserver(
                (
                    records
                ) => {
                    if (
                        !records.some(
                            (
                                record
                            ) =>
                                record
                                    .addedNodes
                                    .length ||
                                record
                                    .removedNodes
                                    .length
                        )
                    ) {
                        return;
                    }

                    queueEnhancementPass();
                }
            );

        state.enhancementObserver
            .observe(
                root,
                {
                    childList:
                        true,
                    subtree:
                        true
                }
            );
    }

    function restoreState() {
        state.theme =
            validTheme(
                safeRead(
                    STORAGE.theme
                ) ||
                "nexus"
            );

        state.causalMode =
            validCausalMode(
                safeRead(
                    STORAGE.causalMode
                ) ||
                "flow"
            );

        state.causalZoom =
            clampZoom(
                safeRead(
                    STORAGE.causalZoom
                ) ||
                1
            );

        state.disclosure =
            validDisclosure(
                safeRead(
                    STORAGE.disclosure
                ) ||
                "work"
            );

        state.density =
            validDensity(
                safeRead(
                    STORAGE.density
                ) ||
                "comfortable"
            );

        state.selectedTaskId =
            asText(
                safeRead(
                    STORAGE.selectedTaskId
                )
            ) ||
            null;

        state.objectiveFilter =
            asText(
                safeRead(
                    STORAGE.objectiveFilter
                ),
                "all"
            );

        state.objectiveSearch =
            asText(
                safeRead(
                    STORAGE.objectiveSearch
                )
            );

        state.commandHistory =
            safeJsonRead(
                STORAGE.commandHistory,
                []
            );

        state.inspectorPinned =
            safeRead(
                STORAGE.inspectorPinned
            ) ===
            "true";

        applyTheme(
            state.theme,
            {
                persist:
                    false
            }
        );

        applyDisclosure(
            state.disclosure,
            {
                persist:
                    false
            }
        );

        applyDensity(
            state.density,
            {
                persist:
                    false
            }
        );

        applyCausalMode(
            state.causalMode,
            {
                persist:
                    false
            }
        );

        applyCausalZoom(
            state.causalZoom,
            {
                persist:
                    false
            }
        );
    }

    function bindRefreshCoordination() {
        $("#refresh")
            ?.addEventListener(
                "click",
                () => {
                    window.setTimeout(
                        () => {
                            void refreshSemanticProjection({
                                quiet:
                                    true
                            });
                        },
                        30
                    );
                }
            );

        window.addEventListener(
            "online",
            () => {
                void refreshSemanticProjection({
                    quiet:
                        true
                });
            }
        );

        document.addEventListener(
            "visibilitychange",
            () => {
                if (
                    !document.hidden
                ) {
                    void refreshSemanticProjection({
                        quiet:
                            true
                    });
                }
            }
        );
    }

    function bindCoreReadySignals() {
        window.addEventListener(
            "niche:frontend-ready",
            queueEnhancementPass
        );

        window.addEventListener(
            "niche:available",
            queueEnhancementPass
        );

        window.addEventListener(
            "niche:task-selected",
            queueEnhancementPass
        );
    }

    function initialize() {
        if (
            state.ready
        ) {
            return;
        }

        state.ready =
            true;

        restoreState();
        bindTheme();
        bindCausalControls();
        bindObjectiveControls();
        bindNavigationContinuity();
        bindKeyboard();
        bindRefreshCoordination();
        bindCoreReadySignals();
        installEnhancementObserver();
        restoreDeepLink();
        enhancementPass();

        void refreshSemanticProjection({
            quiet:
                true
        });

        document
            .documentElement
            .dataset
            .nicheVnext =
            "ready";

        emit(
            "ready",
            {
                visual_system:
                    state.theme,

                causal_mode:
                    state.causalMode,

                disclosure:
                    state.disclosure,

                density:
                    state.density
            }
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
                once:
                    true
            }
        );
    } else {
        initialize();
    }

    window.NicheVnext =
        Object.freeze({
            state() {
                return Object.freeze({
                    ready:
                        state.ready,

                    theme:
                        state.theme,

                    causalMode:
                        state.causalMode,

                    causalZoom:
                        state.causalZoom,

                    disclosure:
                        state.disclosure,

                    density:
                        state.density,

                    selectedTaskId:
                        state.selectedTaskId,

                    representedTaskCount:
                        state.tasks.length,

                    projectionStatus:
                        document
                            .documentElement
                            .dataset
                            .nicheVnextProjection ||
                        "unknown",

                    authorityEffect:
                        "none",

                    projectionOnly:
                        true
                });
            },

            theme:
                applyTheme,

            causalMode:
                applyCausalMode,

            causalZoom:
                applyCausalZoom,

            disclosure:
                applyDisclosure,

            density:
                applyDensity,

            task(
                id
            ) {
                selectTask(
                    id,
                    {
                        openInspector:
                            true,
                        source:
                            "public"
                    }
                );
            },

            view:
                goToView,

            refresh() {
                return refreshSemanticProjection({
                    quiet:
                        false
                });
            },

            help:
                openHelp
        });
})();
