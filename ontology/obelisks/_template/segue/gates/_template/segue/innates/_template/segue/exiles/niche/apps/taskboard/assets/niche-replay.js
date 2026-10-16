"use strict";

/*
 * savant / niche
 * temporal ghost / immutable-history projection
 *
 * owner: exile:niche
 * authority_effect: none
 *
 * This module renders historical observations only. Replay cannot
 * transition tasks or become a replacement task store.
 */

(() => {
    "use strict";

    const state = {
        events: [],
        cursor: -1,
        active: false
    };

    const $ = (selector, root = document) =>
        root.querySelector(selector);

    function safe(value) {
        return value === undefined ||
            value === null
            ? ""
            : String(value);
    }

    function create() {
        if ($("#niche-replay")) {
            return;
        }

        const shell =
            document.createElement("section");

        shell.id = "niche-replay";
        shell.className = "niche-replay";
        shell.hidden = true;

        shell.innerHTML = `
            <header class="niche-replay-head">
                <div>
                    <div class="eyebrow">TEMPORAL GHOST</div>
                    <h2>Historical replay</h2>
                </div>
                <button type="button" id="niche-replay-close" class="icon-button" aria-label="Close historical replay">×</button>
            </header>
            <div id="niche-replay-event" class="niche-replay-event"></div>
            <div class="niche-replay-controls">
                <button type="button" id="niche-replay-first">FIRST</button>
                <button type="button" id="niche-replay-prev">PREVIOUS</button>
                <span id="niche-replay-position">0 / 0</span>
                <button type="button" id="niche-replay-next">NEXT</button>
                <button type="button" id="niche-replay-last">LATEST</button>
            </div>
        `;

        const history =
            $("#surface-history");

        if (history) {
            history.prepend(shell);
        }

        $("#niche-replay-close")
            ?.addEventListener(
                "click",
                close
            );

        $("#niche-replay-first")
            ?.addEventListener(
                "click",
                () => move(0)
            );

        $("#niche-replay-prev")
            ?.addEventListener(
                "click",
                () => move(
                    state.cursor - 1
                )
            );

        $("#niche-replay-next")
            ?.addEventListener(
                "click",
                () => move(
                    state.cursor + 1
                )
            );

        $("#niche-replay-last")
            ?.addEventListener(
                "click",
                () => move(
                    state.events.length - 1
                )
            );
    }

    function normalizeHistory(body) {
        if (Array.isArray(body)) {
            return body;
        }

        for (const key of [
            "history",
            "events",
            "items",
            "results"
        ]) {
            if (Array.isArray(body?.[key])) {
                return body[key];
            }
        }

        return [];
    }

    function eventTime(event) {
        return (
            event?.timestamp ||
            event?.created_at ||
            event?.time ||
            event?.at ||
            "unknown"
        );
    }

    function eventTask(event) {
        return (
            event?.task_id ||
            event?.task?.id ||
            event?.subject_id ||
            event?.identity ||
            "unknown"
        );
    }

    function eventAction(event) {
        return (
            event?.action ||
            event?.event ||
            event?.type ||
            event?.transition ||
            "historical event"
        );
    }

    function render() {
        const event =
            state.events[state.cursor];

        const output =
            $("#niche-replay-event");

        const position =
            $("#niche-replay-position");

        if (position) {
            position.textContent =
                state.events.length
                    ? `${state.cursor + 1} / ${state.events.length}`
                    : "0 / 0";
        }

        if (!output) {
            return;
        }

        output.replaceChildren();

        if (!event) {
            const empty =
                document.createElement("p");

            empty.textContent =
                "No immutable history event is available for replay.";

            output.append(empty);
            return;
        }

        const title =
            document.createElement("h3");

        title.textContent =
            eventAction(event);

        const meta =
            document.createElement("dl");

        for (const [label, value] of [
            ["task", eventTask(event)],
            ["time", eventTime(event)],
            [
                "authority effect",
                event?.authority_effect ??
                    "unknown"
            ]
        ]) {
            const dt =
                document.createElement("dt");

            const dd =
                document.createElement("dd");

            dt.textContent = label;
            dd.textContent = safe(value);

            meta.append(dt, dd);
        }

        const raw =
            document.createElement("pre");

        raw.textContent =
            JSON.stringify(
                event,
                null,
                2
            );

        output.append(
            title,
            meta,
            raw
        );

        window.dispatchEvent(
            new CustomEvent(
                "niche:temporal-ghost",
                {
                    detail: {
                        cursor:
                            state.cursor,
                        event,
                        authority_effect:
                            "none"
                    }
                }
            )
        );
    }

    function move(cursor) {
        if (!state.events.length) {
            state.cursor = -1;
            render();
            return;
        }

        state.cursor =
            Math.max(
                0,
                Math.min(
                    cursor,
                    state.events.length - 1
                )
            );

        render();
    }

    function open() {
        create();

        const shell =
            $("#niche-replay");

        if (!shell) {
            return;
        }

        shell.hidden = false;
        state.active = true;

        if (
            state.cursor < 0 &&
            state.events.length
        ) {
            state.cursor =
                state.events.length - 1;
        }

        render();
    }

    function close() {
        const shell =
            $("#niche-replay");

        if (shell) {
            shell.hidden = true;
        }

        state.active = false;
    }

    function ingest(apiState) {
        const history =
            apiState?.results
                ?.history;

        if (!history?.ok) {
            state.events = [];
            state.cursor = -1;

            if (state.active) {
                render();
            }

            return;
        }

        state.events =
            normalizeHistory(
                history.body
            );

        if (
            state.events.length &&
            (
                state.cursor < 0 ||
                state.cursor >=
                    state.events.length
            )
        ) {
            state.cursor =
                state.events.length - 1;
        }

        if (state.active) {
            render();
        }
    }

    function install() {
        create();

        window.addEventListener(
            "niche:api-status",
            (event) => {
                ingest(
                    event.detail
                );
            }
        );

        document.addEventListener(
            "keydown",
            (event) => {
                if (
                    event.target instanceof
                        HTMLInputElement ||
                    event.target instanceof
                        HTMLTextAreaElement ||
                    event.target instanceof
                        HTMLSelectElement ||
                    event.target?.isContentEditable
                ) {
                    return;
                }

                if (
                    event.key.toLowerCase() ===
                    "t" &&
                    event.altKey
                ) {
                    event.preventDefault();

                    window.NicheContinuity
                        ?.view?.(
                            "history"
                        );

                    open();
                }

                if (
                    event.key ===
                        "Escape" &&
                    state.active
                ) {
                    close();
                }
            }
        );

        $("#surface-history")
            ?.addEventListener(
                "dblclick",
                (event) => {
                    if (
                        event.target.closest(
                            "#niche-replay"
                        )
                    ) {
                        return;
                    }

                    open();
                }
            );
    }

    if (document.readyState === "loading") {
        document.addEventListener(
            "DOMContentLoaded",
            install,
            { once: true }
        );
    } else {
        install();
    }

    window.NicheReplay =
        Object.freeze({
            open,
            close,
            move,

            state() {
                return {
                    active:
                        state.active,
                    cursor:
                        state.cursor,
                    count:
                        state.events.length
                };
            }
        });
})();
