(() => {
    "use strict";

    const SVG_NS =
        "http://www.w3.org/2000/svg";

    const state = {
        ready: false,
        observer: null,
        resizeObserver: null,
        scheduled: false,
        graphRevision: 0
    };

    const $ = (
        selector,
        root = document
    ) => root.querySelector(selector);

    const $$ = (
        selector,
        root = document
    ) => Array.from(
        root.querySelectorAll(selector)
    );

    function svg(
        name,
        attributes = {}
    ) {
        const element =
            document.createElementNS(
                SVG_NS,
                name
            );

        for (
            const [key, value]
            of Object.entries(attributes)
        ) {
            element.setAttribute(
                key,
                String(value)
            );
        }

        return element;
    }

    function icon(
        name,
        label = ""
    ) {
        const use =
            svg(
                "use",
                {
                    href:
                        `#sg-icon-${name}`
                }
            );

        const element =
            svg(
                "svg",
                {
                    class:
                        "sg-icon",
                    viewBox:
                        "0 0 24 24",
                    "aria-hidden":
                        label
                            ? "false"
                            : "true"
                }
            );

        if (label) {
            element.setAttribute(
                "role",
                "img"
            );

            element.setAttribute(
                "aria-label",
                label
            );
        }

        element.append(use);

        return element;
    }

    function installSprite() {
        if (
            $("#savant-graphics-sprite")
        ) {
            return;
        }

        const root =
            svg(
                "svg",
                {
                    id:
                        "savant-graphics-sprite",
                    width:
                        "0",
                    height:
                        "0",
                    "aria-hidden":
                        "true",
                    focusable:
                        "false",
                    style:
                        "position:absolute;width:0;height:0;overflow:hidden"
                }
            );

        const defs =
            svg("defs");

        const symbols = {
            reticle: [
                [
                    "circle",
                    {
                        cx: 12,
                        cy: 12,
                        r: 6
                    }
                ],
                [
                    "path",
                    {
                        d:
                            "M12 2v4M12 18v4M2 12h4M18 12h4"
                    }
                ]
            ],

            chevron: [
                [
                    "path",
                    {
                        d:
                            "M6 8l6 4 6-4M6 13l6 4 6-4"
                    }
                ]
            ],

            gate: [
                [
                    "path",
                    {
                        d:
                            "M5 20V5h14v15M9 20V9h6v11"
                    }
                ]
            ],

            authority: [
                [
                    "path",
                    {
                        d:
                            "M12 3l7 3v5c0 4.6-2.8 8-7 10-4.2-2-7-5.4-7-10V6l7-3z"
                    }
                ],
                [
                    "path",
                    {
                        d:
                            "M9 12l2 2 4-5"
                    }
                ]
            ],

            evidence: [
                [
                    "path",
                    {
                        d:
                            "M7 3h8l4 4v14H7z"
                    }
                ],
                [
                    "path",
                    {
                        d:
                            "M15 3v5h4M10 12h6M10 16h6"
                    }
                ]
            ],

            trace: [
                [
                    "path",
                    {
                        d:
                            "M3 16h4l2-8 3 11 3-6h6"
                    }
                ]
            ],

            objective: [
                [
                    "circle",
                    {
                        cx: 12,
                        cy: 12,
                        r: 8
                    }
                ],
                [
                    "circle",
                    {
                        cx: 12,
                        cy: 12,
                        r: 3
                    }
                ],
                [
                    "path",
                    {
                        d:
                            "M12 2v3M22 12h-3M12 22v-3M2 12h3"
                    }
                ]
            ]
        };

        for (
            const [name, shapes]
            of Object.entries(symbols)
        ) {
            const symbol =
                svg(
                    "symbol",
                    {
                        id:
                            `sg-icon-${name}`,
                        viewBox:
                            "0 0 24 24"
                    }
                );

            for (
                const [shapeName, attrs]
                of shapes
            ) {
                symbol.append(
                    svg(
                        shapeName,
                        attrs
                    )
                );
            }

            defs.append(symbol);
        }

        root.append(defs);

        document.body.prepend(root);
    }

    function ensureHud() {
        const stage =
            $("#graph-stage");

        if (!stage) {
            return;
        }

        if (
            !$(".sg-hud-corners", stage)
        ) {
            const corners =
                document.createElement(
                    "div"
                );

            corners.className =
                "sg-hud-corners";

            corners.setAttribute(
                "aria-hidden",
                "true"
            );

            stage.append(corners);
        }

        if (
            !$(".sg-depth-scale", stage)
        ) {
            const scale =
                document.createElement(
                    "div"
                );

            scale.className =
                "sg-depth-scale";

            scale.setAttribute(
                "aria-hidden",
                "true"
            );

            stage.append(scale);
        }
    }

    function installGraphDefs() {
        const edges =
            $("#graph-edges");

        if (!edges) {
            return;
        }

        let defs =
            $(
                "defs[data-savant-graphics]",
                edges
            );

        if (defs) {
            return;
        }

        defs =
            svg(
                "defs",
                {
                    "data-savant-graphics":
                        "true"
                }
            );

        const soft =
            svg(
                "filter",
                {
                    id:
                        "savant-edge-soft",
                    x:
                        "-25%",
                    y:
                        "-25%",
                    width:
                        "150%",
                    height:
                        "150%",
                    "color-interpolation-filters":
                        "sRGB"
                }
            );

        soft.append(
            svg(
                "feGaussianBlur",
                {
                    stdDeviation:
                        ".18"
                }
            )
        );

        const ready =
            svg(
                "filter",
                {
                    id:
                        "savant-edge-ready",
                    x:
                        "-35%",
                    y:
                        "-35%",
                    width:
                        "170%",
                    height:
                        "170%",
                    "color-interpolation-filters":
                        "sRGB"
                }
            );

        ready.append(
            svg(
                "feGaussianBlur",
                {
                    in:
                        "SourceGraphic",
                    stdDeviation:
                        ".22",
                    result:
                        "blur"
                }
            )
        );

        const merge =
            svg("feMerge");

        merge.append(
            svg(
                "feMergeNode",
                {
                    in:
                        "blur"
                }
            )
        );

        merge.append(
            svg(
                "feMergeNode",
                {
                    in:
                        "SourceGraphic"
                }
            )
        );

        ready.append(merge);

        const arrow =
            svg(
                "marker",
                {
                    id:
                        "savant-edge-arrow",
                    markerWidth:
                        "8",
                    markerHeight:
                        "8",
                    refX:
                        "6.8",
                    refY:
                        "4",
                    orient:
                        "auto",
                    markerUnits:
                        "strokeWidth",
                    viewBox:
                        "0 0 8 8"
                }
            );

        arrow.append(
            svg(
                "path",
                {
                    d:
                        "M0 0L8 4L0 8L2.2 4Z",
                    fill:
                        "context-stroke",
                    opacity:
                        ".76"
                }
            )
        );

        const readyArrow =
            svg(
                "marker",
                {
                    id:
                        "savant-edge-arrow-ready",
                    markerWidth:
                        "8",
                    markerHeight:
                        "8",
                    refX:
                        "6.8",
                    refY:
                        "4",
                    orient:
                        "auto",
                    markerUnits:
                        "strokeWidth",
                    viewBox:
                        "0 0 8 8"
                }
            );

        readyArrow.append(
            svg(
                "path",
                {
                    d:
                        "M0 0L8 4L0 8L2.2 4Z",
                    fill:
                        "#9ff2ca",
                    opacity:
                        ".95"
                }
            )
        );

        defs.append(
            soft,
            ready,
            arrow,
            readyArrow
        );

        edges.prepend(defs);
    }

    function decorateEdges() {
        installGraphDefs();

        for (
            const edge
            of $$(
                "#graph-edges .graph-edge"
            )
        ) {
            edge.setAttribute(
                "marker-end",
                edge.classList.contains(
                    "ready"
                )
                    ? "url(#savant-edge-arrow-ready)"
                    : "url(#savant-edge-arrow)"
            );

            edge.setAttribute(
                "vector-effect",
                "non-scaling-stroke"
            );
        }
    }

    function depthBand(
        leftPercent
    ) {
        if (
            !Number.isFinite(
                leftPercent
            )
        ) {
            return "mid";
        }

        if (
            leftPercent < 31
        ) {
            return "far";
        }

        if (
            leftPercent > 69
        ) {
            return "near";
        }

        return "mid";
    }

    function decorateNodes() {
        const nodes =
            $$(
                "#graph-nodes .graph-node"
            );

        nodes.forEach(
            (
                node,
                index
            ) => {
                const left =
                    Number.parseFloat(
                        node.style.left
                    );

                node.dataset.savantDepth =
                    depthBand(left);

                node.dataset.savantOrdinal =
                    String(index + 1)
                        .padStart(
                            3,
                            "0"
                        );

                if (
                    !node.hasAttribute(
                        "data-savant-graphics"
                    )
                ) {
                    node.setAttribute(
                        "data-savant-graphics",
                        "nucleus"
                    );
                }
            }
        );
    }

    function semanticZoom() {
        const stage =
            $("#graph-stage");

        const nodes =
            $("#graph-nodes");

        if (
            !stage ||
            !nodes
        ) {
            return;
        }

        const transform =
            nodes.style.transform ||
            getComputedStyle(nodes)
                .transform;

        let zoom = 1;

        const scaleMatch =
            transform.match(
                /scale\(([-\d.]+)\)/
            );

        const matrixMatch =
            transform.match(
                /^matrix\(([-\d.]+)/
            );

        if (scaleMatch) {
            zoom =
                Number.parseFloat(
                    scaleMatch[1]
                );
        } else if (
            matrixMatch
        ) {
            zoom =
                Number.parseFloat(
                    matrixMatch[1]
                );
        }

        if (
            !Number.isFinite(zoom)
        ) {
            zoom = 1;
        }

        stage.dataset.semanticZoom =
            zoom < .78
                ? "low"
                : zoom < 1.16
                    ? "medium"
                    : "high";
    }

    function decorateSurfaceGrammar() {
        const mappings = [
            [
                "#surface-objectives",
                "objective"
            ],
            [
                "#surface-timeline",
                "trace"
            ],
            [
                "#surface-evidence",
                "evidence"
            ],
            [
                "#surface-living",
                "reticle"
            ],
            [
                "#surface-history",
                "authority"
            ]
        ];

        for (
            const [
                selector,
                iconName
            ]
            of mappings
        ) {
            const surface =
                $(selector);

            const heading =
                surface
                    ?.querySelector(
                        ".surface-heading .eyebrow"
                    );

            if (
                !heading ||
                heading.querySelector(
                    ".sg-icon"
                )
            ) {
                continue;
            }

            heading.prepend(
                icon(iconName)
            );
        }
    }

    function decorateControls() {
        const mapping = [
            [
                "[data-causal-mode='topology']",
                "reticle"
            ],
            [
                "[data-causal-mode='flow']",
                "trace"
            ],
            [
                "[data-causal-mode='dependencies']",
                "chevron"
            ],
            [
                "[data-causal-mode='objective']",
                "objective"
            ],
            [
                "[data-causal-mode='authority']",
                "authority"
            ],
            [
                "[data-execute-action='evidence']",
                "evidence"
            ]
        ];

        for (
            const [
                selector,
                iconName
            ]
            of mapping
        ) {
            const button =
                $(selector);

            if (
                !button ||
                button.querySelector(
                    ".sg-icon"
                )
            ) {
                continue;
            }

            button.prepend(
                icon(iconName)
            );
        }
    }

    function scheduleDecorate() {
        if (
            state.scheduled
        ) {
            return;
        }

        state.scheduled = true;

        requestAnimationFrame(
            () => {
                state.scheduled = false;

                state.graphRevision += 1;

                ensureHud();
                decorateEdges();
                decorateNodes();
                semanticZoom();
                decorateSurfaceGrammar();
                decorateControls();
            }
        );
    }

    function observeGraph() {
        const stage =
            $("#graph-stage");

        const edges =
            $("#graph-edges");

        const nodes =
            $("#graph-nodes");

        if (
            !stage ||
            !edges ||
            !nodes
        ) {
            return;
        }

        state.observer
            ?.disconnect();

        state.resizeObserver
            ?.disconnect();

        state.observer =
            new MutationObserver(
                records => {
                    const externalChange =
                        records.some(
                            record => {
                                if (
                                    record.type ===
                                    "attributes"
                                ) {
                                    return (
                                        record.target ===
                                        nodes
                                    );
                                }

                                const additions =
                                    Array.from(
                                        record.addedNodes
                                    );

                                const removals =
                                    Array.from(
                                        record.removedNodes
                                    );

                                const relevantAddition =
                                    additions.some(
                                        added => {
                                            return !(
                                                added.nodeType ===
                                                    Node.ELEMENT_NODE &&
                                                added.matches?.(
                                                    "defs[data-savant-graphics], .sg-hud-corners, .sg-depth-scale"
                                                )
                                            );
                                        }
                                    );

                                return (
                                    relevantAddition ||
                                    removals.length > 0
                                );
                            }
                        );

                    if (
                        externalChange
                    ) {
                        scheduleDecorate();
                    }
                }
            );

        state.observer.observe(
            edges,
            {
                childList: true,
                subtree: false
            }
        );

        state.observer.observe(
            nodes,
            {
                childList: true,
                subtree: false,
                attributes: true,
                attributeFilter: [
                    "style"
                ]
            }
        );

        state.resizeObserver =
            new ResizeObserver(
                () => {
                    semanticZoom();
                }
            );

        state.resizeObserver
            .observe(stage);

        state.resizeObserver
            .observe(nodes);
    }

    function markReady() {
        document
            .documentElement
            .dataset
            .savantGraphics =
            "ready";

        state.ready = true;

        document.dispatchEvent(
            new CustomEvent(
                "niche:graphics-ready",
                {
                    detail: {
                        owner:
                            "niche:graphics",
                        authority_effect:
                            "none",
                        projection_only:
                            true,
                        renderer:
                            "svg-css-native",
                        graph_revision:
                            state.graphRevision
                    }
                }
            )
        );
    }

    function start() {
        if (
            state.ready
        ) {
            return;
        }

        installSprite();
        ensureHud();
        decorateSurfaceGrammar();
        decorateControls();
        decorateEdges();
        decorateNodes();
        semanticZoom();
        observeGraph();
        markReady();
    }

    if (
        document.readyState ===
        "loading"
    ) {
        document.addEventListener(
            "DOMContentLoaded",
            start,
            {
                once: true
            }
        );
    } else {
        start();
    }

    window.NicheGraphics =
        Object.freeze({
            state() {
                return {
                    ready:
                        state.ready,
                    graphRevision:
                        state.graphRevision,
                    authorityEffect:
                        "none",
                    projectionOnly:
                        true
                };
            },

            refresh:
                scheduleDecorate
        });
})();
