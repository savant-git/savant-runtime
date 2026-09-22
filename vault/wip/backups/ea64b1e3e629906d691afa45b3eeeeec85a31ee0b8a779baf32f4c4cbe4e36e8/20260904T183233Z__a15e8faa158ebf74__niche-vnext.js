"use strict";

/*
 * savant / niche vnext
 * consolidated frontend convergence layer
 *
 * owner: exile:niche
 * authority_effect: none
 * projection_only: true
 *
 * This layer does not own task authority or task transitions.
 * It reorganizes existing rendered Niche projections and interface state.
 */

(() => {
    "use strict";

    const schema = "savant.niche.vnext.v1";

    const themes = [
        ["nexus", "#62e7ff"],
        ["phosphor", "#78ff91"],
        ["volt", "#8e78ff"],
        ["ember", "#ffad57"],
        ["ultraviolet", "#dd74ff"],
        ["monolith", "#e8f0f3"],
        ["afterimage", "#55ecff"]
    ];

    const runtime = {
        initialized: false,
        theme: "nexus",
        selectedTaskId: null,
        objective: null,
        causalMode: "topology",
        observer: null,
        renderQueued: false,
        graphSignature: "",
        objectiveSignature: ""
    };

    const $ = (selector, root = document) =>
        root.querySelector(selector);

    const $$ = (selector, root = document) =>
        Array.from(root.querySelectorAll(selector));

    function text(value, fallback = "UNKNOWN") {
        if (
            value === undefined ||
            value === null ||
            value === ""
        ) {
            return fallback;
        }

        return String(value);
    }

    function first(...values) {
        return values.find(
            (value) =>
                value !== undefined &&
                value !== null &&
                value !== ""
        );
    }

    function array(value) {
        return Array.isArray(value)
            ? value
            : [];
    }

    function nicheState() {
        try {
            return window.Niche?.state?.() || {};
        } catch {
            return {};
        }
    }

    function tasks() {
        const candidates = [
            window.Niche?.tasks,
            nicheState().tasks,
            window.NicheState?.tasks
        ];

        for (const candidate of candidates) {
            if (Array.isArray(candidate)) {
                return candidate;
            }
        }

        return [];
    }

    async function fetchTasks() {
        try {
            const response =
                await fetch(
                    "/api/tasks?include_terminal=true",
                    {
                        headers: {
                            Accept: "application/json"
                        },
                        cache: "no-store"
                    }
                );

            if (!response.ok) {
                return [];
            }

            const payload = await response.json();

            if (Array.isArray(payload)) {
                return payload;
            }

            for (const key of [
                "tasks",
                "items",
                "results"
            ]) {
                if (Array.isArray(payload?.[key])) {
                    return payload[key];
                }
            }
        } catch {
            return [];
        }

        return [];
    }

    function taskId(task) {
        return text(
            first(
                task?.task_id,
                task?.id,
                task?.taskId
            ),
            ""
        );
    }

    function taskTitle(task) {
        return text(
            first(
                task?.title,
                task?.name,
                task?.summary
            ),
            taskId(task) || "UNTITLED TASK"
        );
    }

    function taskState(task) {
        return text(
            first(
                task?.state,
                task?.status
            ),
            "unknown"
        ).toLowerCase();
    }

    function taskPriority(task) {
        return text(
            first(
                task?.priority,
                task?.priority_label
            ),
            "priority unknown"
        );
    }

    function taskObjective(task) {
        const value =
            first(
                task?.objective,
                task?.objective_id,
                task?.objectiveId,
                task?.parent_objective
            );

        if (
            value &&
            typeof value === "object"
        ) {
            return text(
                first(
                    value.id,
                    value.title,
                    value.name
                ),
                "OBJECTIVE UNKNOWN"
            );
        }

        return text(
            value,
            "OBJECTIVE UNKNOWN"
        );
    }

    function dependencies(task) {
        return array(
            first(
                task?.dependencies,
                task?.dependency_ids,
                task?.direct_dependencies
            )
        ).map((item) =>
            typeof item === "object"
                ? text(
                    first(
                        item.task_id,
                        item.id,
                        item.title
                    ),
                    ""
                )
                : text(item, "")
        ).filter(Boolean);
    }

    function dependents(task) {
        return array(
            first(
                task?.dependents,
                task?.dependent_ids,
                task?.reverse_dependencies,
                task?.direct_dependents
            )
        ).map((item) =>
            typeof item === "object"
                ? text(
                    first(
                        item.task_id,
                        item.id,
                        item.title
                    ),
                    ""
                )
                : text(item, "")
        ).filter(Boolean);
    }

    function blockers(task) {
        return array(
            first(
                task?.blockers,
                task?.blocking_tasks,
                task?.unsatisfied_dependencies
            )
        ).map((item) =>
            typeof item === "object"
                ? text(
                    first(
                        item.task_id,
                        item.id,
                        item.title,
                        item.reason
                    ),
                    ""
                )
                : text(item, "")
        ).filter(Boolean);
    }

    function evidenceCount(task) {
        const candidates = [
            task?.evidence,
            task?.receipts,
            task?.evidence_receipts
        ];

        let represented = false;
        let count = 0;

        for (const candidate of candidates) {
            if (Array.isArray(candidate)) {
                represented = true;
                count += candidate.length;
            }
        }

        return represented
            ? String(count)
            : "UNKNOWN";
    }

    function isComplete(task) {
        return [
            "complete",
            "completed",
            "done"
        ].includes(taskState(task));
    }

    function isBlocked(task) {
        return (
            taskState(task) === "blocked" ||
            blockers(task).length > 0
        );
    }

    function isReady(task) {
        const represented =
            first(
                task?.ready,
                task?.is_ready,
                task?.readiness
            );

        if (represented === true) {
            return true;
        }

        if (
            typeof represented === "string" &&
            represented.toLowerCase() === "ready"
        ) {
            return true;
        }

        return false;
    }

    function findTask(id, source) {
        return source.find(
            (task) => taskId(task) === id
        ) || null;
    }

    function selectTask(id) {
        if (!id) {
            return;
        }

        runtime.selectedTaskId = id;

        try {
            localStorage.setItem(
                "savant.niche.vnext.selected-task",
                id
            );
        } catch {
            /* interface persistence is optional */
        }

        $$(".graph-node").forEach((node) => {
            node.dataset.vnextSelected =
                node.dataset.taskId === id
                    ? "true"
                    : "false";
        });

        window.dispatchEvent(
            new CustomEvent(
                "niche:continuity-selection",
                {
                    detail: {
                        taskId: id,
                        source: "niche-vnext",
                        authority_effect: "none"
                    }
                }
            )
        );

        renderCompanion();
    }

    function loadInterfaceState() {
        try {
            const savedTheme =
                localStorage.getItem(
                    "savant.niche.vnext.theme"
                );

            if (
                themes.some(
                    ([name]) => name === savedTheme
                )
            ) {
                runtime.theme = savedTheme;
            }

            runtime.selectedTaskId =
                localStorage.getItem(
                    "savant.niche.vnext.selected-task"
                ) || null;

            runtime.objective =
                localStorage.getItem(
                    "savant.niche.vnext.objective"
                ) || null;

            runtime.causalMode =
                localStorage.getItem(
                    "savant.niche.vnext.causal-mode"
                ) || "topology";
        } catch {
            /* local UI persistence is non-authoritative */
        }
    }

    function setTheme(theme) {
        if (
            !themes.some(
                ([name]) => name === theme
            )
        ) {
            theme = "nexus";
        }

        runtime.theme = theme;

        document.documentElement.dataset.nicheTheme =
            theme;

        try {
            localStorage.setItem(
                "savant.niche.vnext.theme",
                theme
            );
        } catch {
            /* optional interface state */
        }

        $$(".niche-theme-switcher button")
            .forEach((button) => {
                button.setAttribute(
                    "aria-pressed",
                    button.dataset.theme === theme
                        ? "true"
                        : "false"
                );
            });
    }

    function installThemeDock() {
        if ($(".niche-vnext-theme-dock")) {
            return;
        }

        const dock =
            document.createElement("div");

        dock.className =
            "niche-vnext-theme-d
