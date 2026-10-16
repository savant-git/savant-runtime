"use strict";

/*
 * savant / niche
 * execution focus and consequence projection
 *
 * owner: exile:niche
 * authority_effect: none
 *
 * This layer exposes task execution context already present in Niche's
 * rendered projection. It does not manufacture authority or task facts.
 */

(() => {
    "use strict";

    const state = {
        taskId: null,
        panel: null,
        lastTrigger: null
    };

    const $ = (selector, root = document) =>
        root.querySelector(selector);

    const $$ = (selector, root = document) =>
        Array.from(root.querySelectorAll(selector));

    function safe(value, fallback = "") {
        return value === undefined ||
            value === null
            ? fallback
            : String(value);
    }

    function escape(value) {
        if (window.CSS?.escape) {
            return CSS.escape(
                safe(value)
            );
        }

        return safe(value).replace(
            /["\\]/g,
            "\\$&"
        );
    }

    function selectedTaskId() {
        return (
            window.NicheContinuity
                ?.state?.()
                ?.taskId ||
            $(
                "[data-task-id][data-niche-selected='true']"
            )?.dataset.taskId ||
            $(
                "[data-task-id][aria-current='true']"
            )?.dataset.taskId ||
            null
        );
    }

    function taskElement(taskId) {
        if (!taskId) {
            return null;
        }

        return $(
            `[data-task-id="${escape(taskId)}"]`
        );
    }

    function listFromDataset(
        element,
        key
    ) {
        const raw =
            element?.dataset?.[key];

        if (!raw) {
            return [];
        }

        return raw
            .split(",")
            .map(
                (value) =>
                    value.trim()
            )
            .filter(Boolean);
    }

    function titleOf(element) {
        return (
            $("h3", element)
                ?.textContent
                ?.trim() ||
            element?.dataset?.title ||
            element?.dataset?.taskId ||
            "Unknown task"
        );
    }

    function stateOf(element) {
        return (
            element?.dataset?.state ||
            "unknown"
        );
    }

    function textNode(
        tag,
        className,
        text
    ) {
        const node =
            document.createElement(tag);

        if (className) {
            node.className =
                className;
        }

        node.textContent =
            safe(text);

        return node;
    }

    function createPanel() {
        if (
            $("#niche-focus-panel")
        ) {
            return $(
                "#niche-focus-panel"
            );
        }

        const panel =
            document.createElement(
                "aside"
            );

        panel.id =
            "niche-focus-panel";

        panel.className =
            "niche-focus-panel";

        panel.hidden = true;

        panel.setAttribute(
            "aria-hidden",
            "true"
        );

        panel.setAttribute(
            "aria-labelledby",
            "niche-focus-title"
        );

        const header =
            document.createElement(
                "header"
            );

        header.className =
            "niche-focus-head";

        const heading =
            document.createElement(
                "div"
            );

        heading.append(
            textNode(
                "div",
                "eyebrow",
                "EXECUTION FOCUS"
            ),
            textNode(
                "h2",
                "",
                "Task context"
            )
        );

        heading.lastChild.id =
            "niche-focus-title";

        const close =
            document.createElement(
                "button"
            );

        close.type = "button";
        close.className =
            "icon-button";

        close.textContent = "×";

        close.setAttribute(
            "aria-label",
            "Close execution focus"
        );

        close.addEventListener(
            "click",
            closePanel
        );

        header.append(
            heading,
            close
        );

        const body =
            document.createElement(
                "div"
            );

        body.id =
            "niche-focus-body";

        body.className =
            "niche-focus-body";

        panel.append(
            header,
            body
        );

        document.body.append(
            panel
        );

        state.panel = panel;

        return panel;
    }

    function row(label, value) {
        const wrapper =
            document.createElement(
                "div"
            );

        wrapper.className =
            "niche-focus-row";

        wrapper.append(
            textNode(
                "span",
                "",
                label
            ),
            textNode(
                "strong",
                "",
                value
            )
        );

        return wrapper;
    }

    function taskLink(taskId) {
        const button =
            document.createElement(
                "button"
            );

        button.type = "button";
        button.className =
            "niche-focus-task";

        const source =
            taskElement(taskId);

        button.append(
            textNode(
                "span",
                "",
                titleOf(source)
            ),
            textNode(
                "small",
                "",
                taskId
            )
        );

        button.addEventListener(
            "click",
            () => {
                window.NicheContinuity
                    ?.select?.(
                        taskId
                    );

                source?.click();

                render(
                    taskId
                );
            }
        );

        return button;
    }

    function section(
        title,
        values,
        emptyText
    ) {
        const wrapper =
            document.createElement(
                "section"
            );

        wrapper.className =
            "niche-focus-section";

        wrapper.append(
            textNode(
                "h3",
                "",
                title
            )
        );

        if (!values.length) {
            wrapper.append(
                textNode(
                    "p",
                    "niche-focus-empty",
                    emptyText
                )
            );

            return wrapper;
        }

        const list =
            document.createElement(
                "div"
            );

        list.className =
            "niche-focus-task-list";

        values.forEach(
            (value) => {
                list.append(
                    taskLink(value)
                );
            }
        );

        wrapper.append(list);

        return wrapper;
    }

    function render(taskId) {
        const source =
            taskElement(taskId);

        if (!source) {
            return;
        }

        state.taskId = taskId;

        const panel =
            createPanel();

        const body =
            $("#niche-focus-body");

        const dependencies =
            listFromDataset(
                source,
                "dependencies"
            );

        const dependents =
            listFromDataset(
                source,
                "dependents"
            );

        const blockers =
            listFromDataset(
                source,
                "blockers"
            );

        const receipts =
            listFromDataset(
                source,
                "receipts"
            );

        body.replaceChildren();

        const identity =
            document.createElement(
                "section"
            );

        identity.className =
            "niche-focus-identity";

        identity.append(
            textNode(
                "div",
                "eyebrow",
                "IDENTITY"
            ),
            textNode(
                "h2",
                "",
                titleOf(source)
            ),
            textNode(
                "code",
                "",
                taskId
            )
        );

        const metrics =
            document.createElement(
                "div"
            );

        metrics.className =
            "niche-focus-metrics";

        metrics.append(
            row(
                "STATE",
                stateOf(source)
            ),
            row(
                "DEPENDENCIES",
                dependencies.length
            ),
            row(
                "BLOCKERS",
                blockers.length
            ),
            row(
                "UNLOCKS",
                dependents.length
            )
        );

        body.append(
            identity,
            metrics,
            section(
                "Dependencies",
                dependencies,
                "No dependency identifiers are exposed by this rendered projection."
            ),
            section(
                "Blockers",
                blockers,
                "No blocker identifiers are exposed by this rendered projection."
            ),
            section(
                "Unlock horizon",
                dependents,
                "No dependent identifiers are exposed by this rendered projection."
            )
        );

        const evidence =
            document.createElement(
                "section"
            );

        evidence.className =
            "niche-focus-section";

        evidence.append(
            textNode(
                "h3",
                "",
                "Evidence"
            )
        );

        if (receipts.length) {
            const list =
                document.createElement(
                    "div"
                );

            list.className =
                "niche-focus-receipts";

            receipts.forEach(
                (receipt) => {
                    list.append(
                        textNode(
                            "code",
                            "",
                            receipt
                        )
                    );
                }
            );

            evidence.append(list);
        } else {
            evidence.append(
                textNode(
                    "p",
                    "niche-focus-empty",
                    "No receipt identifiers are exposed by this rendered projection."
                )
            );
        }

        body.append(evidence);

        const actions =
            document.createElement(
                "div"
            );

        actions.className =
            "niche-focus-actions";

        const inspect =
            document.createElement(
                "button"
            );

        inspect.type = "button";
        inspect.textContent =
            "OPEN CONTEXT";

        inspect.addEventListener(
            "click",
            () => {
                source.click();
            }
        );

        const graph =
            document.createElement(
                "button"
            );

        graph.type = "button";
        graph.textContent =
            "SHOW CAUSAL FIELD";

        graph.addEventListener(
            "click",
            () => {
                window.NicheContinuity
                    ?.view?.(
                        "constellation"
                    );
            }
        );

        const flow =
            document.createElement(
                "button"
            );

        flow.type = "button";
        flow.textContent =
            "SHOW FLOW";

        flow.addEventListener(
            "click",
            () => {
                window.NicheContinuity
                    ?.view?.(
                        "flow"
                    );
            }
        );

        actions.append(
            inspect,
            graph,
            flow
        );

        body.append(actions);

        openPanel();
    }

    function openPanel() {
        const panel =
            createPanel();

        panel.hidden = false;

        panel.setAttribute(
            "aria-hidden",
            "false"
        );

        document.body.classList.add(
            "niche-focus-open"
        );
    }

    function closePanel() {
        const panel =
            createPanel();

        panel.hidden = true;

        panel.setAttribute(
            "aria-hidden",
            "true"
        );

        document.body.classList.remove(
            "niche-focus-open"
        );

        state.lastTrigger?.focus?.();
    }

    function showSelected(trigger) {
        const taskId =
            selectedTaskId();

        if (!taskId) {
            return;
        }

        state.lastTrigger =
            trigger ||
            document.activeElement;

        render(taskId);
    }

    function installExecuteControls() {
        document.addEventListener(
            "click",
            (event) => {
                const action =
                    event.target.closest(
                        "[data-execute-action]"
                    );

                if (!action) {
                    return;
                }

                const type =
                    action.dataset
                        .executeAction;

                if (
                    ![
                        "dependencies",
                        "impact",
                        "evidence"
                    ].includes(type)
                ) {
                    return;
                }

                const next =
                    window.Niche
                        ?.nextTask?.();

                const taskId =
                    next?.id ||
                    next?.task_id ||
                    selectedTaskId();

                if (!taskId) {
                    return;
                }

                window.NicheContinuity
                    ?.select?.(
                        taskId
                    );

                state.lastTrigger =
                    action;

                render(taskId);
            },
            true
        );
    }

    function installTaskShortcut() {
        document.addEventListener(
            "keydown",
            (event) => {
                const target =
                    event.target;

                if (
                    target instanceof
                        HTMLInputElement ||
                    target instanceof
                        HTMLTextAreaElement ||
                    target instanceof
                        HTMLSelectElement ||
                    target?.isContentEditable
                ) {
                    return;
                }

                if (
                    event.key.toLowerCase() ===
                    "i"
                ) {
                    event.preventDefault();

                    if (
                        $("#niche-focus-panel")
                            ?.hidden === false
                    ) {
                        closePanel();
                    } else {
                        showSelected(
                            document.activeElement
                        );
                    }
                }

                if (
                    event.key === "Escape" &&
                    $("#niche-focus-panel")
                        ?.hidden === false
                ) {
                    closePanel();
                }
            }
        );
    }

    function installSelectedTaskGesture() {
        document.addEventListener(
            "contextmenu",
            (event) => {
                const task =
                    event.target.closest(
                        "[data-task-id]"
                    );

                if (!task?.dataset.taskId) {
                    return;
                }

                event.preventDefault();

                window.NicheContinuity
                    ?.select?.(
                        task.dataset.taskId
                    );

                state.lastTrigger =
                    task;

                render(
                    task.dataset.taskId
                );
            }
        );
    }

    function initialize() {
        createPanel();
        installExecuteControls();
        installTaskShortcut();
        installSelectedTaskGesture();
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

    window.NicheFocus =
        Object.freeze({
            open(taskId) {
                const resolved =
                    taskId ||
                    selectedTaskId();

                if (resolved) {
                    render(
                        safe(resolved)
                    );
                }
            },

            close:
                closePanel,

            selected:
                selectedTaskId
        });
})();
