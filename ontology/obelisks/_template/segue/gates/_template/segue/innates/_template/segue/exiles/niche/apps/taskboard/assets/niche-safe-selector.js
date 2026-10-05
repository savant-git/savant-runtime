"use strict";

/*
 * savant / niche
 * safe selector primitive
 *
 * owner: exile:niche
 * authority_effect: none
 */

(() => {
    "use strict";

    function escape(value) {
        const text =
            String(
                value ?? ""
            );

        if (
            window.CSS &&
            typeof window.CSS.escape ===
                "function"
        ) {
            return window.CSS.escape(
                text
            );
        }

        return text.replace(
            /(^-?\d)|[^a-zA-Z0-9_-]/g,
            (match, leadingDigit) => {
                if (leadingDigit) {
                    return `\\3${leadingDigit} `;
                }

                const code =
                    match.codePointAt(0)
                        .toString(16);

                return `\\${code} `;
            }
        );
    }

    function attribute(
        name,
        value
    ) {
        return (
            `[${escape(name)}="${escape(value)}"]`
        );
    }

    function task(taskId) {
        return attribute(
            "data-task-id",
            taskId
        );
    }

    window.NicheSafeSelector =
        Object.freeze({
            escape,
            attribute,
            task
        });
})();
