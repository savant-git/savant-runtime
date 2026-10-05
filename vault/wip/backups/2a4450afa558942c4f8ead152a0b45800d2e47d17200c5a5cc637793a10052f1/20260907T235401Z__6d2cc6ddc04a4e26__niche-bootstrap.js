"use strict";

/*
 * savant / niche / bootstrap
 *
 * owner: exile:niche
 * semantic_role: frontend capability coordinator
 * authority_effect: none
 * projection_only: true
 *
 * savant substantive projection programming
 *
 * principles:
 * - declarative capabilities
 * - one semantic owner
 * - deterministic projection
 * - explicit optionality
 * - idempotent realization
 * - failure isolation
 * - no authoritative mutation
 * - no duplicate boot ownership
 */

(() => {
    "use strict";

    const ROOT =
        document.documentElement;

    const EVENT_PREFIX =
        "niche:";

    const STATUS = Object.freeze({
        DORMANT:
            "dormant",

        REQUESTED:
            "requested",

        AVAILABLE:
            "available",

        DEGRADED:
            "degraded",

        UNAVAILABLE:
            "unavailable"
    });

    const KIND = Object.freeze({
        STYLESHEET:
            "stylesheet",

        SCRIPT:
            "script"
    });

    /*
     * This registry is intentionally declarative.
     *
     * It describes optional frontend projections.
     * It does not own their behavior.
     *
     * command.html may already load any of these
     * explicitly. In that case bootstrap observes
     * and accepts that existing realization rather
     * than creating a duplicate.
     */
    const CAPABILITIES =
        Object.freeze([
            Object.freeze({
                id:
                    "graphics-style",

                owner:
                    "niche:graphics",

                kind:
                    KIND.STYLESHEET,

                href:
                    "/assets/niche-graphics.css",

                optional:
                    true
            }),

            Object.freeze({
                id:
                    "themes-style",

                owner:
                    "niche:themes",

                kind:
                    KIND.STYLESHEET,

                href:
                    "/assets/niche-themes.css",

                optional:
                    true
            }),

            Object.freeze({
                id:
                    "navigation-style",

                owner:
                    "niche:navigation",

                kind:
                    KIND.STYLESHEET,

                href:
                    "/assets/niche-navigation.css",

                optional:
                    true
            }),

            Object.freeze({
                id:
                    "graphics-controller",

                owner:
                    "niche:graphics",

                kind:
                    KIND.SCRIPT,

                href:
                    "/assets/niche-graphics.js",

                optional:
                    true
            }),

            Object.freeze({
                id:
                    "themes-controller",

                owner:
                    "niche:themes",

                kind:
                    KIND.SCRIPT,

                href:
                    "/assets/niche-themes.js",

                optional:
                    true
            }),

            Object.freeze({
                id:
                    "navigation-controller",

                owner:
                    "niche:navigation",

                kind:
                    KIND.SCRIPT,

                href:
                    "/assets/niche-navigation.js",

                optional:
                    true
            })
        ]);

    const runtime =
        new Map(
            CAPABILITIES.map(
                capability => [
                    capability.id,

                    {
                        definition:
                            capability,

                        status:
                            STATUS.DORMANT,

                        element:
                            null,

                        requestedAt:
                            null,

                        settledAt:
                            null,

                        error:
                            null
                    }
                ]
            )
        );

    const state = {
        initialized:
            false,

        initializedAt:
            null,

        realizationStarted:
            false,

        realizationSettled:
            false,

        frontendReadyDispatched:
            false
    };

    function timestamp() {
        return new Date()
            .toISOString();
    }

    function emit(
        name,
        detail = {}
    ) {
        window.dispatchEvent(
            new CustomEvent(
                `${EVENT_PREFIX}${name}`,
                {
                    detail: Object.freeze({
                        authority_effect:
                            "none",

                        projection_only:
                            true,

                        ...detail
                    })
                }
            )
        );
    }

    function selectorFor(
        capability
    ) {
        const escaped =
            CSS.escape(
                capability.href
            );

        if (
            capability.kind ===
            KIND.STYLESHEET
        ) {
            return (
                `link[rel="stylesheet"]` +
                `[href="${escaped}"]`
            );
        }

        return (
            `script[src="${escaped}"]`
        );
    }

    function findExisting(
        capability
    ) {
        /*
         * Attribute values here are fixed internal
         * constants. Avoiding broad URL matching keeps
         * capability identity deterministic.
         */
        if (
            capability.kind ===
            KIND.STYLESHEET
        ) {
            return Array.from(
                document.querySelectorAll(
                    'link[rel="stylesheet"]'
                )
            ).find(
                element =>
                    element.getAttribute(
                        "href"
                    ) ===
                    capability.href
            ) || null;
        }

        return Array.from(
            document.querySelectorAll(
                "script[src]"
            )
        ).find(
            element =>
                element.getAttribute(
                    "src"
                ) ===
                    capability.href
            ) || null;
    }

    function statusRecord(
        id
    ) {
        const record =
            runtime.get(id);

        if (!record) {
            throw new Error(
                `unknown frontend capability: ${id}`
            );
        }

        return record;
    }

    function mark(
        id,
        status,
        {
            element = null,
            error = null
        } = {}
    ) {
        const record =
            statusRecord(id);

        record.status =
            status;

        if (element) {
            record.element =
                element;
        }

        if (
            status ===
            STATUS.REQUESTED
        ) {
            record.requestedAt =
                timestamp();
        }

        if (
            status ===
                STATUS.AVAILABLE ||
            status ===
                STATUS.DEGRADED ||
            status ===
                STATUS.UNAVAILABLE
        ) {
            record.settledAt =
                timestamp();
        }

        record.error =
            error
                ? String(
                    error.message ||
                    error
                )
                : null;

        emit(
            "capability-state",
            {
                capability:
                    id,

                owner:
                    record
                        .definition
                        .owner,

                status:
                    record.status,

                optional:
                    record
                        .definition
                        .optional,

                href:
                    record
                        .definition
                        .href,

                error:
                    record.error
            }
        );
    }

    function buildElement(
        capability
    ) {
        if (
            capability.kind ===
            KIND.STYLESHEET
        ) {
            const element =
                document.createElement(
                    "link"
                );

            element.rel =
                "stylesheet";

            element.href =
                capability.href;

            element.dataset
                .savantCapability =
                capability.id;

            return element;
        }

        const element =
            document.createElement(
                "script"
            );

        element.src =
            capability.href;

        element.defer =
            true;

        element.async =
            false;

        element.dataset
            .savantCapability =
            capability.id;

        return element;
    }

    function observeSettlement(
        capability,
        element,
        preexisting
    ) {
        return new Promise(
            resolve => {
                const record =
                    statusRecord(
                        capability.id
                    );

                if (
                    preexisting
                ) {
                    /*
                     * Existing parser-loaded assets are
                     * considered realized by this
                     * coordinator. Their own modules remain
                     * responsible for semantic readiness.
                     */
                    mark(
                        capability.id,
                        STATUS.AVAILABLE,
                        {
                            element
                        }
                    );

                    resolve(
                        record.status
                    );

                    return;
                }

                let settled =
                    false;

                const settle =
                    (
                        status,
                        error = null
                    ) => {
                        if (
                            settled
                        ) {
                            return;
                        }

                        settled =
                            true;

                        mark(
                            capability.id,
                            status,
                            {
                                element,
                                error
                            }
                        );

                        resolve(
                            status
                        );
                    };

                element.addEventListener(
                    "load",
                    () => {
                        settle(
                            STATUS.AVAILABLE
                        );
                    },
                    {
                        once: true
                    }
                );

                element.addEventListener(
                    "error",
                    () => {
                        settle(
                            capability.optional
                                ? STATUS.DEGRADED
                                : STATUS.UNAVAILABLE,

                            new Error(
                                `failed to load ${capability.href}`
                            )
                        );
                    },
                    {
                        once: true
                    }
                );
            }
        );
    }

    async function realize(
        capability
    ) {
        const record =
            statusRecord(
                capability.id
            );

        if (
            record.status !==
            STATUS.DORMANT
        ) {
            return record.status;
        }

        const existing =
            findExisting(
                capability
            );

        mark(
            capability.id,
            STATUS.REQUESTED,
            {
                element:
                    existing
            }
        );

        if (existing) {
            return observeSettlement(
                capability,
                existing,
                true
            );
        }

        const element =
            buildElement(
                capability
            );

        record.element =
            element;

        const settlement =
            observeSettlement(
                capability,
                element,
                false
            );

        document.head.append(
            element
        );

        return settlement;
    }

    async function realizeCapabilities() {
        if (
            state.realizationStarted
        ) {
            return;
        }

        state.realizationStarted =
            true;

        ROOT.dataset
            .nicheCapabilities =
            "realizing";

        /*
         * Styles are realized before controllers.
         * Controllers are realized in registry order.
         *
         * This creates deterministic optional capability
         * ordering without turning those capabilities
         * into core boot requirements.
         */
        const styles =
            CAPABILITIES.filter(
                capability =>
                    capability.kind ===
                    KIND.STYLESHEET
            );

        const scripts =
            CAPABILITIES.filter(
                capability =>
                    capability.kind ===
                    KIND.SCRIPT
            );

        await Promise.all(
            styles.map(
                realize
            )
        );

        for (
            const capability
            of scripts
        ) {
            await realize(
                capability
            );
        }

        state.realizationSettled =
            true;

        ROOT.dataset
            .nicheCapabilities =
            summarizeCapabilityHealth();

        emit(
            "capabilities-settled",
            {
                status:
                    summarizeCapabilityHealth(),

                capabilities:
                    snapshotCapabilities()
            }
        );
    }

    function summarizeCapabilityHealth() {
        const records =
            Array.from(
                runtime.values()
            );

        if (
            records.some(
                record =>
                    record.status ===
                    STATUS.UNAVAILABLE &&
                    !record
                        .definition
                        .optional
            )
        ) {
            return "unavailable";
        }

        if (
            records.some(
                record =>
                    record.status ===
                        STATUS.DEGRADED ||
                    record.status ===
                        STATUS.UNAVAILABLE
            )
        ) {
            return "degraded";
        }

        if (
            records.every(
                record =>
                    record.status ===
                    STATUS.AVAILABLE
            )
        ) {
            return "available";
        }

        return "realizing";
    }

    function snapshotCapabilities() {
        return Array.from(
            runtime.entries(),
            (
                [
                    id,
                    record
                ]
            ) =>
                Object.freeze({
                    id,

                    owner:
                        record
                            .definition
                            .owner,

                    kind:
                        record
                            .definition
                            .kind,

                    href:
                        record
                            .definition
                            .href,

                    optional:
                        record
                            .definition
                            .optional,

                    status:
                        record.status,

                    requestedAt:
                        record
                            .requestedAt,

                    settledAt:
                        record
                            .settledAt,

                    error:
                        record.error
                })
        );
    }

    function dispatchFrontendReady() {
        if (
            state.frontendReadyDispatched
        ) {
            return;
        }

        state.frontendReadyDispatched =
            true;

        ROOT.dataset
            .nicheFrontend =
            "ready";

        emit(
            "frontend-ready",
            {
                initialized_at:
                    state.initializedAt,

                owner:
                    "exile:niche"
            }
        );
    }

    function initialize() {
        if (
            state.initialized
        ) {
            return;
        }

        state.initialized =
            true;

        state.initializedAt =
            timestamp();

        ROOT.dataset
            .nicheBootstrap =
            "ready";

        /*
         * Core frontend readiness is independent of
         * optional presentation capabilities.
         *
         * Execute must not wait on graphics, themes or
         * Navigation to become available.
         */
        dispatchFrontendReady();

        void realizeCapabilities()
            .catch(
                error => {
                    ROOT.dataset
                        .nicheCapabilities =
                        "degraded";

                    emit(
                        "capabilities-settled",
                        {
                            status:
                                "degraded",

                            error:
                                String(
                                    error.message ||
                                    error
                                ),

                            capabilities:
                                snapshotCapabilities()
                        }
                    );
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
                once: true
            }
        );
    } else {
        initialize();
    }

    window.NicheBootstrap =
        Object.freeze({
            state() {
                return Object.freeze({
                    initialized:
                        state.initialized,

                    initializedAt:
                        state.initializedAt,

                    realizationStarted:
                        state.realizationStarted,

                    realizationSettled:
                        state.realizationSettled,

                    capabilityHealth:
                        summarizeCapabilityHealth(),

                    authorityEffect:
                        "none",

                    projectionOnly:
                        true
                });
            },

            capabilities() {
                return snapshotCapabilities();
            }
        });
})();
