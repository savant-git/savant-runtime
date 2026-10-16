"use strict";

/*
 * savant / niche
 * living health waveform
 *
 * owner: exile:niche
 * authority_effect: none
 *
 * Visualizes observed projection availability only.
 */

(() => {
    "use strict";

    const MAX =
        48;

    const samples = [];

    const $ = (selector, root = document) =>
        root.querySelector(selector);

    function create() {
        if (
            $("#niche-health-wave")
        ) {
            return;
        }

        const living =
            $("#surface-living");

        if (!living) {
            return;
        }

        const shell =
            document.createElement(
                "section"
            );

        shell.id =
            "niche-health-wave";

        shell.className =
            "niche-health-wave";

        shell.innerHTML = `
            <header>
                <div>
                    <div class="eyebrow">LIVING PULSE</div>
                    <h2>Projection availability</h2>
                </div>
                <span id="niche-health-wave-label">unknown</span>
            </header>
            <div class="niche-health-wave-stage">
                <svg
                    id="niche-health-wave-svg"
                    viewBox="0 0 480 96"
                    preserveAspectRatio="none"
                    role="img"
                    aria-label="Recent projection availability"
                >
                    <polyline
                        id="niche-health-wave-line"
                        points=""
                        vector-effect="non-scaling-stroke"
                    ></polyline>
                </svg>
            </div>
        `;

        const heading =
            living.querySelector(
                ".surface-heading"
            );

        if (heading) {
            heading.insertAdjacentElement(
                "afterend",
                shell
            );
        } else {
            living.prepend(shell);
        }
    }

    function score(results) {
        const values =
            Object.values(
                results || {}
            );

        if (!values.length) {
            return null;
        }

        const healthy =
            values.filter(
                (result) =>
                    result?.ok
            ).length;

        return (
            healthy /
            values.length
        );
    }

    function render() {
        create();

        const line =
            $("#niche-health-wave-line");

        const label =
            $("#niche-health-wave-label");

        if (
            !line ||
            !label
        ) {
            return;
        }

        if (!samples.length) {
            line.setAttribute(
                "points",
                ""
            );

            label.textContent =
                "unknown";

            return;
        }

        const width =
            480;

        const height =
            96;

        const denominator =
            Math.max(
                1,
                samples.length - 1
            );

        const points =
            samples.map(
                (sample, index) => {
                    const x =
                        (
                            index /
                            denominator
                        ) *
                        width;

                    const y =
                        height -
                        (
                            sample.value *
                            height
                        );

                    return `${x.toFixed(2)},${y.toFixed(2)}`;
                }
            );

        line.setAttribute(
            "points",
            points.join(" ")
        );

        const latest =
            samples[
                samples.length - 1
            ];

        label.textContent =
            `${Math.round(
                latest.value *
                100
            )}% observed endpoints available`;
    }

    function ingest(detail) {
        const value =
            score(
                detail?.results
            );

        if (value === null) {
            return;
        }

        samples.push({
            value,
            at:
                new Date()
                    .toISOString()
        });

        if (
            samples.length >
            MAX
        ) {
            samples.splice(
                0,
                samples.length -
                MAX
            );
        }

        render();
    }

    function initialize() {
        create();

        window.addEventListener(
            "niche:api-status",
            (event) => {
                ingest(
                    event.detail
                );
            }
        );

        const current =
            window.NicheApiResilience
                ?.status?.();

        if (current) {
            ingest(current);
        }
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

    window.NicheHealthWave =
        Object.freeze({
            samples() {
                return samples.map(
                    (sample) => ({
                        ...sample
                    })
                );
            }
        });
})();
