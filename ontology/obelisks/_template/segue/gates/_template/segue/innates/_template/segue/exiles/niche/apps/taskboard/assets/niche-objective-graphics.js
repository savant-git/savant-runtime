(() => {
    "use strict";

    const schema =
        "savant.niche.objective-graphics.v1";

    const svgNamespace =
        "http://www.w3.org/2000/svg";

    const runtime = {
        generation: 0,
        controller: null,
        tasks: [],
        initialized: false,
        observer: null,
        renderQueued: false
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

            if (
                typeof id === "string" &&
                id
            ) {
                return id;
            }
        }

        return null;
    };

    const titleOf = value => {
        const title =
            first(
                value,
                [
                    "title",
                    "name",
                    "label",
                    "summary"
                ]
            );

        return represented(title)
            ? String(title)
            : idOf(value) || "unknown";
    };

    const stateOf = task =>
        String(
            first(
                task,
                [
                    "state",
                    "status"
                ]
            ) || ""
        ).toLowerCase();

    const dependenciesOf = task =>
        array(
            first(
                task,
                [
                    "dependencies",
                    "dependency_ids"
                ]
            )
        )
            .map(idOf)
            .filter(Boolean);

    const blockersOf = task =>
        array(task?.blockers)
            .map(idOf)
            .filter(Boolean);

    const unsatisfiedOf = task =>
        array(
            task?.unsatisfied_dependencies
        )
            .map(idOf)
            .filter(Boolean);

    const classify = task => {
        const state =
            stateOf(task);

        if (
            blockersOf(task).length ||
            unsatisfiedOf(task).length ||
            state === "blocked"
        ) {
            return "blocked";
        }

        const ready =
            first(
                task,
                [
                    "ready",
                    "is_ready",
                    "readiness"
                ]
            );

        if (
            ready === true ||
            String(ready)
                .toLowerCase() === "ready"
        ) {
            return "ready";
        }

        if (
            [
                "done",
                "complete",
                "completed",
                "active",
                "running",
                "started",
                "in_progress",
                "in-progress"
            ].includes(state)
        ) {
            return "established";
        }

        return "future";
    };

    const currentTaskId = () => {
        try {
            const state =
                window.Niche?.state?.() ||
                {};

            return (
                state.selectedTaskId ||
                state.recommendedTaskId ||
                null
            );
        } catch {
            return null;
        }
    };

    const createSvg = (
        tag,
        attributes = {}
    ) => {
        const element =
            document.createElementNS(
                svgNamespace,
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

    const fetchTasks = async () => {
        runtime.generation += 1;

        const generation =
            runtime.generation;

        runtime.controller?.abort();

        const controller =
            new AbortController();

        runtime.controller =
            controller;

        try {
            const response =
                await fetch(
                    "/api/tasks",
                    {
                        cache: "no-store",
                        signal:
                            controller.signal,
                        headers: {
                            Accept:
                                "application/json"
                        }
                    }
                );

            if (!response.ok) {
                return false;
            }

            const payload =
                await response.json();

            if (
                generation !==
                runtime.generation
            ) {
                return false;
            }

            runtime.tasks =
                normalizeTasks(payload);

            render();

            return true;
        } catch (error) {
            if (
                error?.name !==
                "AbortError"
            ) {
                renderUnknown();
            }

            return false;
        } finally {
            if (
                runtime.controller ===
                controller
            ) {
                runtime.controller = null;
            }
        }
    };

    const objectiveOf = task =>
        first(
            task,
            [
                "objective",
                "objective_id",
                "objectiveId"
            ]
        );

    const trancheOf = task =>
        first(
            task,
            [
                "tranche",
                "tranche_id",
                "trancheId"
            ]
        );

    const actionOf = task =>
        first(
            task,
            [
                "action",
                "action_id",
                "actionId"
            ]
        );

    const primitive = (
        value,
        fallbackPrefix
    ) => {
        if (!represented(value)) {
            return null;
        }

        if (
            typeof value === "object"
        ) {
            return {
                id:
                    idOf(value) ||
                    titleOf(value),
                title:
                    titleOf(value)
            };
        }

        return {
            id:
                `${fallbackPrefix}:${String(value)}`,
            title:
                String(value)
        };
    };

    const project = () => {
        const objectives =
            new Map();

        const tranches =
            new Map();

        const tasks =
            new Map();

        const actions =
            new Map();

        const links = [];

        runtime.tasks.forEach(task => {
            const taskId =
                idOf(task);

            if (!taskId) {
                return;
            }

            tasks.set(
                taskId,
                {
                    id: taskId,
                    title:
                        titleOf(task),
                    state:
                        classify(task),
                    source:
                        task
                }
            );

            const objective =
                primitive(
                    objectiveOf(task),
                    "objective"
                );

            const tranche =
                primitive(
                    trancheOf(task),
                    "tranche"
                );

            const action =
                primitive(
                    actionOf(task),
                    "action"
                );

            if (objective) {
                objectives.set(
                    objective.id,
                    objective
                );
            }

            if (tranche) {
                tranches.set(
                    tranche.id,
                    tranche
                );
            }

            if (action) {
                actions.set(
                    action.id,
                    action
                );
            }

            if (
                objective &&
                tranche
            ) {
                links.push({
                    from:
                        objective.id,
                    to:
                        tranche.id,
                    kind:
                        "structural"
                });
            }

            if (tranche) {
                links.push({
                    from:
                        tranche.id,
                    to:
                        taskId,
                    kind:
                        classify(task)
                });
            } else if (objective) {
                links.push({
                    from:
                        objective.id,
                    to:
                        taskId,
                    kind:
                        classify(task)
                });
            }

            if (action) {
                links.push({
                    from:
                        taskId,
                    to:
                        action.id,
                    kind:
                        classify(task)
                });
            }
        });

        return {
            objectives:
                [...objectives.values()],
            tranches:
                [...tranches.values()],
            tasks:
                [...tasks.values()],
            actions:
                [...actions.values()],
            links
        };
    };

    const host = () => {
        const grid =
            document.getElementById(
                "objective-grid"
            );

        if (!grid) {
            return null;
        }

        let map =
            document.getElementById(
                "niche-objective-map"
            );

        if (!map) {
            map =
                document.createElement(
                    "div"
                );

            map.id =
                "niche-objective-map";

            map.className =
                "niche-objective-map";

            grid.before(map);
        }

        return map;
    };

    const renderUnknown = () => {
        const map = host();

        if (!map) {
            return;
        }

        map.innerHTML = `
            <div class="niche-objective-unknown">
                objective structural projection unavailable
            </div>
        `;
    };

    const trim = (
        value,
        length = 24
    ) => {
        const text =
            String(value || "");

        return text.length > length
            ? `${text.slice(
                0,
                length - 1
            )}…`
            : text;
    };

    const render = () => {
        const map = host();

        if (!map) {
            return;
        }

        const projection =
            project();

        const total =
            projection.objectives.length +
            projection.tranches.length +
            projection.tasks.length +
            projection.actions.length;

        if (!total) {
            renderUnknown();
            return;
        }

        map.textContent = "";

        const canvas =
            createSvg(
                "svg",
                {
                    class:
                        "niche-objective-svg",
                    viewBox:
                        "0 0 1000 360",
                    preserveAspectRatio:
                        "xMidYMid meet",
                    role: "img",
                    "aria-label":
                        "Objective structural projection"
                }
            );

        const levels = [
            {
                key: "objectives",
                label: "OBJECTIVE",
                x: 110,
                level: "objective"
            },
            {
                key: "tranches",
                label: "TRANCHE",
                x: 365,
                level: "tranche"
            },
            {
                key: "tasks",
                label: "TASK",
                x: 635,
                level: "task"
            },
            {
                key: "actions",
                label: "ACTION",
                x: 890,
                level: "action"
            }
        ];

        levels.forEach(level => {
            canvas.append(
                createSvg(
                    "line",
                    {
                        x1: level.x,
                        y1: 38,
                        x2: level.x,
                        y2: 338,
                        class:
                            "niche-objective-axis"
                    }
                )
            );

            const label =
                createSvg(
                    "text",
                    {
                        x: level.x,
                        y: 26,
                        "text-anchor":
                            "middle",
                        class:
                            "niche-objective-depth-label"
                    }
                );

            label.textContent =
                level.label;

            canvas.append(label);
        });

        const positions =
            new Map();

        levels.forEach(level => {
            const values =
                projection[level.key];

            const usableHeight = 270;

            values.forEach(
                (value, index) => {
                    const y =
                        values.length <= 1
                            ? 180
                            : (
                                55 +
                                (
                                    usableHeight *
                                    index
                                ) /
                                (
                                    values.length -
                                    1
                                )
                            );

                    positions.set(
                        value.id,
                        {
                            x: level.x,
                            y,
                            level:
                                level.level,
                            value
                        }
                    );
                }
            );
        });

        projection.links.forEach(link => {
            const from =
                positions.get(
                    link.from
                );

            const to =
                positions.get(
                    link.to
                );

            if (!from || !to) {
                return;
            }

            const middle =
                (
                    from.x +
                    to.x
                ) / 2;

            canvas.append(
                createSvg(
                    "path",
                    {
                        d:
                            `M ${from.x} ${from.y} ` +
                            `C ${middle} ${from.y}, ` +
                            `${middle} ${to.y}, ` +
                            `${to.x} ${to.y}`,
                        class:
                            "niche-objective-link",
                        "data-kind":
                            link.kind
                    }
                )
            );
        });

        const selected =
            currentTaskId();

        positions.forEach(
            position => {
                const {
                    x,
                    y,
                    level,
                    value
                } = position;

                const radius =
                    level === "objective"
                        ? 7
                        : level === "tranche"
                            ? 6
                            : level === "task"
                                ? 5
                                : 4;

                if (
                    level === "task" &&
                    value.id === selected
                ) {
                    canvas.append(
                        createSvg(
                            "circle",
                            {
                                cx: x,
                                cy: y,
                                r:
                                    radius + 7,
                                class:
                                    "niche-objective-current"
                            }
                        )
                    );
                }

                canvas.append(
                    createSvg(
                        "circle",
                        {
                            cx: x,
                            cy: y,
                            r: radius,
                            class:
                                "niche-objective-node",
                            "data-level":
                                level,
                            "data-state":
                                value.state ||
                                "projected"
                        }
                    )
                );

                const label =
                    createSvg(
                        "text",
                        {
                            x:
                                x + 12,
                            y:
                                y + 3,
                            class:
                                "niche-objective-label",
                            "data-level":
                                level
                        }
                    );

                label.textContent =
                    trim(value.title);

                canvas.append(label);
            }
        );

        map.append(canvas);

        window.dispatchEvent(
            new CustomEvent(
                "niche:objective-graphics-render",
                {
                    detail: {
                        schema,
                        objectiveCount:
                            projection
                                .objectives
                                .length,
                        trancheCount:
                            projection
                                .tranches
                                .length,
                        taskCount:
                            projection
                                .tasks
                                .length,
                        actionCount:
                            projection
                                .actions
                                .length,
                        authorityEffect:
                            "none",
                        projectionOnly:
                            true
                    }
                }
            )
        );
    };

    const queueRender = () => {
        if (runtime.renderQueued) {
            return;
        }

        runtime.renderQueued = true;

        requestAnimationFrame(
            () => {
                runtime.renderQueued =
                    false;

                render();
            }
        );
    };

    const bind = () => {
        window.addEventListener(
            "niche:continuity-selection",
            queueRender
        );

        window.addEventListener(
            "niche:semantic-runtime-update",
            event => {
                if (
                    event.detail?.changed
                ) {
                    void fetchTasks();
                }
            }
        );

        document.addEventListener(
            "click",
            event => {
                if (
                    event.target.closest(
                        "[data-task-id]"
                    )
                ) {
                    queueRender();
                }
            },
            true
        );
    };

    const initialize = () => {
        if (runtime.initialized) {
            return;
        }

        runtime.initialized = true;

        bind();

        document.documentElement
            .dataset
            .nicheObjectiveGraphics =
            "ready";

        void fetchTasks();

        window.dispatchEvent(
            new CustomEvent(
                "niche:objective-graphics-ready",
                {
                    detail: {
                        schema,
                        authorityEffect:
                            "none",
                        projectionOnly:
                            true
                    }
                }
            )
        );
    };

    window.NicheObjectiveGraphics =
        Object.freeze({
            refresh: fetchTasks,
            render,
            state: () => ({
                schema,
                taskCount:
                    runtime.tasks.length,
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
