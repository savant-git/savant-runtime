"use strict";

/*
 * savant / niche
 * command environment extensions
 *
 * owner: exile:niche
 * authority_effect: none
 */

(() => {
    "use strict";

    const commands = Object.freeze([
        {
            id: "diagnostics",
            label: "Open runtime evidence",
            keywords: "diagnostics api failures evidence",
            run() {
                window.NicheDiagnostics
                    ?.show?.();
            }
        },
        {
            id: "replay",
            label: "Open temporal ghost",
            keywords: "history replay temporal ghost",
            run() {
                window.NicheContinuity
                    ?.view?.(
                        "history"
                    );

                window.NicheReplay
                    ?.open?.();
            }
        },
        {
            id: "execute",
            label: "Return to executable frontier",
            keywords: "execute start next frontier",
            run() {
                window.NicheContinuity
                    ?.view?.(
                        "execute"
                    );
            }
        },
        {
            id: "living",
            label: "Open living observatory",
            keywords: "living fabric observatory health",
            run() {
                window.NicheContinuity
                    ?.view?.(
                        "living"
                    );
            }
        },
        {
            id: "constellation",
            label: "Open causal field",
            keywords: "constellation dependencies causal graph",
            run() {
                window.NicheContinuity
                    ?.view?.(
                        "constellation"
                    );
            }
        }
    ]);

    function editable(target) {
        return (
            target instanceof
                HTMLInputElement ||
            target instanceof
                HTMLTextAreaElement ||
            target instanceof
                HTMLSelectElement ||
            target?.isContentEditable
        );
    }

    function run(id) {
        const command =
            commands.find(
                (candidate) =>
                    candidate.id === id
            );

        command?.run?.();
    }

    function initialize() {
        document.addEventListener(
            "keydown",
            (event) => {
                if (editable(event.target)) {
                    return;
                }

                if (
                    event.altKey &&
                    event.key === "1"
                ) {
                    event.preventDefault();
                    run("execute");
                }

                if (
                    event.altKey &&
                    event.key === "2"
                ) {
                    event.preventDefault();
                    run("constellation");
                }

                if (
                    event.altKey &&
                    event.key === "7"
                ) {
                    event.preventDefault();
                    run("living");
                }

                if (
                    event.altKey &&
                    event.key === "8"
                ) {
                    event.preventDefault();
                    run("replay");
                }
            }
        );

        window.dispatchEvent(
            new CustomEvent(
                "niche:commands-extended",
                {
                    detail: {
                        commands:
                            commands.map(
                                ({
                                    id,
                                    label,
                                    keywords
                                }) => ({
                                    id,
                                    label,
                                    keywords
                                })
                            ),
                        authority_effect:
                            "none"
                    }
                }
            )
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
                once: true
            }
        );
    } else {
        initialize();
    }

    window.NicheCommandExtensions =
        Object.freeze({
            commands,
            run
        });
})();
