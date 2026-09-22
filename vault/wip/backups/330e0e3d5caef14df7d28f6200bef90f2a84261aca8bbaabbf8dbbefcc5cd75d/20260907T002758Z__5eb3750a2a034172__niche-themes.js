(() => {
    "use strict";

    const STORAGE_KEY =
        "savant.niche.ui.theme.v2";

    const LEGACY_STORAGE_KEY =
        "savant.niche.ui.theme";

    const SELECTOR_ID =
        "niche-theme";

    const THEMES =
        Object.freeze([
            [
                "nexus-industrial",
                "Nexus Industrial"
            ],
            [
                "monolith-editorial",
                "Monolith Editorial"
            ],
            [
                "phosphor-lab",
                "Phosphor Lab"
            ],
            [
                "ultraviolet-architecture",
                "Ultraviolet Architecture"
            ],
            [
                "ember-analog",
                "Ember Analog"
            ],
            [
                "afterimage-spectral",
                "Afterimage Spectral"
            ],
            [
                "white-room",
                "White Room System"
            ],
            [
                "signal-brutalist",
                "Signal Brutalist"
            ],
            [
                "liquid-systems",
                "Liquid Systems"
            ],
            [
                "void-cartography",
                "Void Cartography"
            ]
        ]);

    const VALID =
        new Set(
            THEMES.map(
                ([value]) => value
            )
        );

    const DEFAULT_THEME =
        THEMES[0][0];

    function readStorage(
        key
    ) {
        try {
            return localStorage
                .getItem(key);
        } catch {
            return null;
        }
    }

    function writeStorage(
        key,
        value
    ) {
        try {
            localStorage
                .setItem(
                    key,
                    value
                );
        } catch {
            return;
        }
    }

    function normalize(
        value
    ) {
        if (
            VALID.has(value)
        ) {
            return value;
        }

        const legacyMap = {
            nexus:
                "nexus-industrial",

            monolith:
                "monolith-editorial",

            phosphor:
                "phosphor-lab",

            ultraviolet:
                "ultraviolet-architecture",

            ember:
                "ember-analog",

            afterimage:
                "afterimage-spectral",

            volt:
                "ultraviolet-architecture"
        };

        return (
            legacyMap[value] ||
            DEFAULT_THEME
        );
    }

    function updateMetaColor() {
        const meta =
            document.querySelector(
                'meta[name="theme-color"]'
            );

        if (!meta) {
            return;
        }

        const value =
            getComputedStyle(
                document.documentElement
            )
                .getPropertyValue(
                    "--theme-browser-color"
                )
                .trim();

        if (value) {
            meta.setAttribute(
                "content",
                value
            );
        }
    }

    function updateSelector(
        theme
    ) {
        const select =
            document.getElementById(
                SELECTOR_ID
            );

        if (
            select &&
            select.value !== theme
        ) {
            select.value =
                theme;
        }
    }

    function applyTheme(
        rawTheme,
        {
            persist = true,
            announce = true
        } = {}
    ) {
        const theme =
            normalize(rawTheme);

        const root =
            document.documentElement;

        root.dataset.nicheTheme =
            theme;

        root.dataset.nicheThemeOwner =
            "niche-themes";

        updateSelector(theme);

        if (persist) {
            writeStorage(
                STORAGE_KEY,
                theme
            );

            writeStorage(
                LEGACY_STORAGE_KEY,
                theme
            );
        }

        requestAnimationFrame(
            updateMetaColor
        );

        if (announce) {
            window.dispatchEvent(
                new CustomEvent(
                    "niche:theme-change",
                    {
                        detail: {
                            theme,
                            authority_effect:
                                "none",
                            projection_only:
                                true,
                            owner:
                                "niche-themes"
                        }
                    }
                )
            );
        }

        return theme;
    }

    function populateSelector() {
        const select =
            document.getElementById(
                SELECTOR_ID
            );

        if (!select) {
            return null;
        }

        const fragment =
            document
                .createDocumentFragment();

        for (
            const [value, label]
            of THEMES
        ) {
            const option =
                document.createElement(
                    "option"
                );

            option.value =
                value;

            option.textContent =
                label;

            fragment.append(
                option
            );
        }

        select.replaceChildren(
            fragment
        );

        select.setAttribute(
            "aria-label",
            "Savant visual system"
        );

        select.dataset.themeOwner =
            "niche-themes";

        /*
         * Capture plus stopImmediatePropagation
         * makes this selector's theme mutation
         * presentation-owned. Legacy listeners
         * cannot subsequently rewrite the theme.
         */
        select.addEventListener(
            "change",
            event => {
                event
                    .stopImmediatePropagation();

                applyTheme(
                    event
                        .currentTarget
                        .value
                );
            },
            {
                capture: true
            }
        );

        return select;
    }

    function boot() {
        const select =
            populateSelector();

        const stored =
            readStorage(
                STORAGE_KEY
            );

        const legacyStored =
            readStorage(
                LEGACY_STORAGE_KEY
            );

        const current =
            document
                .documentElement
                .dataset
                .nicheTheme;

        const initial =
            stored ||
            legacyStored ||
            current ||
            DEFAULT_THEME;

        const theme =
            applyTheme(
                initial,
                {
                    persist: true,
                    announce: false
                }
            );

        if (select) {
            select.value =
                theme;
        }

        document
            .documentElement
            .dataset
            .nicheThemes =
            "ready";

        window.dispatchEvent(
            new CustomEvent(
                "niche:themes-ready",
                {
                    detail: {
                        theme,
                        count:
                            THEMES.length,
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
        document.readyState ===
        "loading"
    ) {
        document.addEventListener(
            "DOMContentLoaded",
            boot,
            {
                once: true
            }
        );
    } else {
        boot();
    }

    window.NicheThemes =
        Object.freeze({
            themes() {
                return THEMES.map(
                    (
                        [
                            value,
                            label
                        ]
                    ) => ({
                        value,
                        label
                    })
                );
            },

            current() {
                return normalize(
                    document
                        .documentElement
                        .dataset
                        .nicheTheme
                );
            },

            apply(theme) {
                return applyTheme(
                    theme
                );
            }
        });
})();
