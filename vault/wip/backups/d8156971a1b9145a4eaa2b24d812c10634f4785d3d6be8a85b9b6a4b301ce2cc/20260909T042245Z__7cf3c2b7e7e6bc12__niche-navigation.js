"use strict";

/**
 * savant / niche / atlas
 * generational code reconstruction: modular spatial computational cartography
 *
 * build: atlas-v2026.generation-reconstruction
 * authority_effect: none
 * projection_only: true
 */

(() => {
    const BUILD = "atlas-v2026.generation-reconstruction";
    const SVG_NS = "http://www.w3.org/2000/svg";
    const VIEW = "navigation";
    const STORE_KEY = "savant.niche.atlas.v2026.reconstructed";

    // -------------------------------------------------------------------------
    // I. ATOMS & UTILITY PRIMITIVES
    // -------------------------------------------------------------------------
    const txt = (v, f = "") => (v == null ? f : (String(v).trim() || f));
    const low = v => txt(v).toLowerCase();
    const arr = v => (Array.isArray(v) ? v : []);
    const clamp = (v, min, max) => Math.min(max, Math.max(min, v));

    const fnv1a = (str) => {
        let h = 2166136261;
        for (const c of txt(str)) {
            h ^= c.charCodeAt(0);
            h = Math.imul(h, 16777619);
        }
        return h >>> 0;
    };

    const $ = (sel, root = document) => root.querySelector(sel);
    const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));

    // -------------------------------------------------------------------------
    // II. CONSTANTS & MOOD REGISTRY
    // -------------------------------------------------------------------------
    const Z_LEVELS = Object.freeze({
        min: 0.12,
        max: 4.8,
        world: 0.52,
        district: 1.05,
        locality: 1.95,
        step: 1.25
    });

    const GEOMETRY_METRICS = Object.freeze({
        pad: 48,
        gap: 32,
        head: 74,
        inner: 24,
        taskW: 200,
        taskH: 52,
        minW: 460,
        minH: 300
    });

    const CHROMATIC_PALETTE = Object.freeze([
        { h: 194, s: 94, l: 56 },
        { h: 218, s: 92, l: 62 },
        { h: 268, s: 86, l: 68 },
        { h: 322, s: 84, l: 64 },
        { h: 12,  s: 90, l: 60 },
        { h: 38,  s: 96, l: 58 },
        { h: 148, s: 84, l: 52 },
        { h: 168, s: 88, l: 50 },
        { h: 284, s: 80, l: 66 }
    ]);

    // -------------------------------------------------------------------------
    // III. INSTANCE: AUDIO SYNTHESIZER BEHAVIOR
    // -------------------------------------------------------------------------
    class SpatialAcoustics {
        constructor() {
            this.ctx = null;
        }

        init() {
            if (!this.ctx && typeof AudioContext !== "undefined") {
                this.ctx = new (window.AudioContext || window.webkitAudioContext)();
            }
            if (this.ctx && this.ctx.state === "suspended") {
                this.ctx.resume();
            }
        }

        pulse(freqStart, freqEnd, duration, gainMax) {
            if (window.matchMedia?.("(prefers-reduced-motion: reduce)").matches) return;
            try {
                this.init();
                if (!this.ctx) return;
                const osc = this.ctx.createOscillator();
                const gain = this.ctx.createGain();
                osc.connect(gain);
                gain.connect(this.ctx.destination);
                const now = this.ctx.currentTime;
                osc.frequency.setValueAtTime(freqStart, now);
                osc.frequency.exponentialRampToValueAtTime(freqEnd, now + duration);
                gain.gain.setValueAtTime(gainMax, now);
                gain.gain.linearRampToValueAtTime(0, now + duration);
                osc.start(now);
                osc.stop(now + duration);
            } catch {}
        }

        tick() { this.pulse(820, 380, 0.025, 0.012); }
        warp() { this.pulse(200, 680, 0.08, 0.028); }
    }

    const acoustics = new SpatialAcoustics();

    // -------------------------------------------------------------------------
    // IV. AUTHORITATIVE PROJECTION CONSUMPTION SEGUE
    // -------------------------------------------------------------------------
    const taskId = t => txt(t?.id ?? t?.task_id ?? t?.identity ?? t?.key);
    const taskTitle = t => txt(t?.title ?? t?.name ?? t?.action ?? t?.summary ?? taskId(t), "untitled task");
    const taskObjective = t => txt(t?.objective ?? t?.objective_id ?? t?.root_objective ?? t?.ancestry?.objective, "general");
    const taskPriority = t => txt(t?.priority ?? t?.authoritative_priority ?? t?.rank, "normal");
    const taskDeps = t => arr(t?.dependencies ?? t?.depends_on ?? t?.prerequisites ?? t?.requires)
        .map(x => (typeof x === "string" ? x.trim() : txt(x?.id ?? x?.task_id ?? x?.key))).filter(Boolean);

    function taskState(t) {
        const s = low(t?.state ?? t?.status ?? t?.lifecycle_state);
        if (s.includes("complete") || s === "done" || s === "closed") return "complete";
        if (s.includes("block") || s === "failed") return "blocked";
        if (s.includes("active") || s.includes("progress") || s === "started") return "active";
        if (s.includes("review") || s.includes("verify") || s.includes("evidence")) return "review";
        if (s.includes("wait") || s.includes("pending") || s.includes("defer")) return "waiting";
        if (t?.ready === true || t?.is_ready === true || low(t?.readiness) === "ready") return "ready";
        return s || "unknown";
    }

    class SemanticGraphSegue {
        static transform(projection) {
            const rawTasks = arr(projection?.source?.tasks)
                .filter(t => taskId(t))
                .sort((a, b) => taskId(a).localeCompare(taskId(b)));

            const taskById = new Map();
            const dependents = new Map();

            for (const t of rawTasks) {
                const id = taskId(t);
                taskById.set(id, t);
                dependents.set(id, []);
            }

            for (const t of rawTasks) {
                const id = taskId(t);
                for (const d of taskDeps(t)) {
                    dependents.get(d)?.push(id);
                }
            }

            const groups = new Map();
            for (const t of rawTasks) {
                const obj = taskObjective(t);
                if (!groups.has(obj)) {
                    groups.set(obj, { id: `obj:${obj}`, label: obj, tasks: [] });
                }
                groups.get(obj).tasks.push(t);
            }

            const territories = Array.from(groups.values()).map(g => {
                const stats = { total: g.tasks.length, complete: 0, ready: 0, active: 0, blocked: 0, waiting: 0 };
                for (const t of g.tasks) {
                    const s = taskState(t);
                    if (s in stats) stats[s]++;
                }
                return {
                    ...g,
                    statistics: stats,
                    ratio: stats.total ? stats.complete / stats.total : 0
                };
            }).sort((a, b) => b.tasks.length - a.tasks.length || a.label.localeCompare(b.label));

            const taskToTerritory = new Map();
            for (const terr of territories) {
                for (const t of terr.tasks) {
                    taskToTerritory.set(taskId(t), terr.id);
                }
            }

            const edgeMap = new Map();
            for (const t of rawTasks) {
                const target = taskId(t);
                const targetTerr = taskToTerritory.get(target);
                for (const source of taskDeps(t)) {
                    const sourceTerr = taskToTerritory.get(source);
                    if (!sourceTerr || !targetTerr || sourceTerr === targetTerr) continue;
                    const key = `${sourceTerr}→${targetTerr}`;
                    if (!edgeMap.has(key)) {
                        edgeMap.set(key, { id: key, source: sourceTerr, target: targetTerr, count: 0 });
                    }
                    edgeMap.get(key).count++;
                }
            }

            return {
                tasks: rawTasks,
                taskById,
                dependents,
                territories,
                taskToTerritory,
                edges: Array.from(edgeMap.values()),
                recommendedTaskId: txt(projection?.normalized?.recommendedTaskId),
                selectedTaskId: txt(projection?.normalized?.selectedTaskId)
            };
        }
    }

    // -------------------------------------------------------------------------
    // V. COMPUTATIONAL GEOMETRY ENGINE (DECOUPLED FROM RENDERER)
    // -------------------------------------------------------------------------
    class SpatialGeometryEngine {
        static layout(graph) {
            const placed = new Map();
            let cx = GEOMETRY_METRICS.pad;
            let cy = GEOMETRY_METRICS.pad;
            let rowH = 0;
            const targetRowWidth = Math.max(1600, Math.ceil(Math.sqrt(graph.territories.length) * 580));

            for (const t of graph.territories) {
                const cols = Math.max(2, Math.min(5, Math.ceil(Math.sqrt(t.tasks.length))));
                const rows = Math.ceil(t.tasks.length / cols);
                const w = Math.max(GEOMETRY_METRICS.minW, cols * (GEOMETRY_METRICS.taskW + 16) + GEOMETRY_METRICS.inner * 2);
                const h = Math.max(GEOMETRY_METRICS.minH, GEOMETRY_METRICS.head + rows * (GEOMETRY_METRICS.taskH + 14) + GEOMETRY_METRICS.inner * 2);

                if (cx + w > targetRowWidth && cx > GEOMETRY_METRICS.pad) {
                    cx = GEOMETRY_METRICS.pad;
                    cy += rowH + GEOMETRY_METRICS.gap;
                    rowH = 0;
                }

                placed.set(t.id, { id: t.id, x: cx, y: cy, w, h });
                cx += w + GEOMETRY_METRICS.gap;
                rowH = Math.max(rowH, h);
            }

            let worldW = 1;
            let worldH = 1;
            for (const p of placed.values()) {
                worldW = Math.max(worldW, p.x + p.w + GEOMETRY_METRICS.pad);
                worldH = Math.max(worldH, p.y + p.h + GEOMETRY_METRICS.pad);
            }

            const tasksGeom = new Map();
            for (const t of graph.territories) {
                const tp = placed.get(t.id);
                if (!tp) continue;
                const left = tp.x + GEOMETRY_METRICS.inner;
                const top = tp.y + GEOMETRY_METRICS.head + 10;
                const cols = Math.max(1, Math.floor((tp.w - GEOMETRY_METRICS.inner * 2) / (GEOMETRY_METRICS.taskW + 16)));

                t.tasks.forEach((task, idx) => {
                    const c = idx % cols;
                    const r = Math.floor(idx / cols);
                    tasksGeom.set(taskId(task), {
                        x: left + c * (GEOMETRY_METRICS.taskW + 16),
                        y: top + r * (GEOMETRY_METRICS.taskH + 14),
                        w: GEOMETRY_METRICS.taskW,
                        h: GEOMETRY_METRICS.taskH,
                        territoryId: t.id
                    });
                });
            }

            const conduits = [];
            for (const edge of graph.edges) {
                const sp = placed.get(edge.source);
                const tp = placed.get(edge.target);
                if (!sp || !tp) continue;
                const sx = sp.x + sp.w;
                const sy = sp.y + sp.h / 2;
                const tx = tp.x;
                const ty = tp.y + tp.h / 2;
                const mx = (sx + tx) / 2;
                conduits.push({
                    id: edge.id,
                    path: `M ${sx} ${sy} H ${mx} V ${ty} H ${tx}`,
                    count: edge.count
                });
            }

            return {
                worldW,
                worldH,
                territories: placed,
                tasks: tasksGeom,
                conduits
            };
        }
    }

    // -------------------------------------------------------------------------
    // VI. MODUS-MASKED SVG RENDERER (SINGLE SUBSTANCE, VARIABLE MASKS)
    // -------------------------------------------------------------------------
    class RetainedSvgRenderer {
        constructor(elements) {
            this.dom = elements;
        }

        render(graph, geometry, activeLens = "domains") {
            const { dom } = this;
            dom.ground.setAttribute("width", String(geometry.worldW));
            dom.ground.setAttribute("height", String(geometry.worldH));

            // Concourse interstitial infrastructure
            const meshFrag = document.createDocumentFragment();
            for (const tp of geometry.territories.values()) {
                const pad = document.createElementNS(SVG_NS, "rect");
                pad.setAttribute("x", String(tp.x - 14));
                pad.setAttribute("y", String(tp.y - 14));
                pad.setAttribute("width", String(tp.w + 28));
                pad.setAttribute("height", String(tp.h + 28));
                pad.setAttribute("class", "atlas-concourse-plate");
                meshFrag.append(pad);
            }
            dom.concourseMesh.replaceChildren(meshFrag);

            // Orthogonal conduits
            const conduitFrag = document.createDocumentFragment();
            for (const c of geometry.conduits) {
                const p = document.createElementNS(SVG_NS, "path");
                p.setAttribute("d", c.path);
                p.setAttribute("class", "atlas-bus-conduit");
                p.setAttribute("marker-end", "url(#atlas-arrow)");
                conduitFrag.append(p);
            }
            dom.conduits.replaceChildren(conduitFrag);

            // Territories (Modus Mask: Lens variations)
            const terrFrag = document.createDocumentFragment();
            graph.territories.forEach((t, i) => {
                const tp = geometry.territories.get(t.id);
                if (!tp) return;
                const color = CHROMATIC_PALETTE[i % CHROMATIC_PALETTE.length];
                const g = document.createElementNS(SVG_NS, "g");
                g.setAttribute("class", "atlas-territory-group");
                g.style.setProperty("--tc", `hsl(${color.h} ${color.s}% ${color.l}%)`);

                const hull = document.createElementNS(SVG_NS, "rect");
                hull.setAttribute("x", String(tp.x));
                hull.setAttribute("y", String(tp.y));
                hull.setAttribute("width", String(tp.w));
                hull.setAttribute("height", String(tp.h));
                hull.setAttribute("class", "atlas-territory-hull");

                const title = document.createElementNS(SVG_NS, "text");
                title.setAttribute("x", String(tp.x + 20));
                title.setAttribute("y", String(tp.y + 36));
                title.setAttribute("class", "atlas-territory-title");
                title.textContent = t.label.toUpperCase();

                const meta = document.createElementNS(SVG_NS, "text");
                meta.setAttribute("x", String(tp.x + 20));
                meta.setAttribute("y", String(tp.y + 56));
                meta.setAttribute("class", "atlas-territory-telemetry");

                if (activeLens === "heatmap") {
                    meta.textContent = `HEAT SCORE: ${(t.statistics.blocked * 3 + t.statistics.active).toFixed(1)}`;
                } else {
                    meta.textContent = `UNITS:${t.statistics.total} | READY:${t.statistics.ready} | BLK:${t.statistics.blocked}`;
                }

                g.append(hull, title, meta);
                terrFrag.append(g);
            });
            dom.territories.replaceChildren(terrFrag);

            // Unit Nodes
            const taskFrag = document.createDocumentFragment();
            for (const t of graph.tasks) {
                const id = taskId(t);
                const g = geometry.tasks.get(id);
                if (!g) continue;

                const node = document.createElementNS(SVG_NS, "g");
                const stateClass = taskState(t);
                const isRec = id === graph.recommendedTaskId;

                node.setAttribute("class", `atlas-unit-node state-${stateClass} ${isRec ? "frontier" : ""}`);
                node.setAttribute("transform", `translate(${g.x} ${g.y})`);
                node.dataset.taskId = id;

                const body = document.createElementNS(SVG_NS, "rect");
                body.setAttribute("width", String(g.w));
                body.setAttribute("height", String(g.h));
                body.setAttribute("class", "atlas-unit-body");

                const text = document.createElementNS(SVG_NS, "text");
                text.setAttribute("x", "14");
                text.setAttribute("y", "24");
                text.setAttribute("class", "atlas-unit-title");
                text.textContent = taskTitle(t).slice(0, 24);

                const sub = document.createElementNS(SVG_NS, "text");
                sub.setAttribute("x", "14");
                sub.setAttribute("y", "40");
                sub.setAttribute("class", "atlas-unit-sub");
                sub.textContent = `${stateClass.toUpperCase()} // ${taskPriority(t)}`;

                node.append(body, text, sub);
                taskFrag.append(node);
            }
            dom.tasks.replaceChildren(taskFrag);

            // Minimap
            dom.minimap.setAttribute("viewBox", `0 0 ${geometry.worldW} ${geometry.worldH}`);
            const mmFrag = document.createDocumentFragment();
            for (const tp of geometry.territories.values()) {
                const r = document.createElementNS(SVG_NS, "rect");
                r.setAttribute("x", String(tp.x));
                r.setAttribute("y", String(tp.y));
                r.setAttribute("width", String(tp.w));
                r.setAttribute("height", String(tp.h));
                r.setAttribute("class", "atlas-mm-cell");
                mmFrag.append(r);
            }
            dom.minimap.replaceChildren(mmFrag);
        }
    }

    // -------------------------------------------------------------------------
    // VII. APPLICATION CONTROLLER & KINEMATIC VIEWPORT SEGUE
    // -------------------------------------------------------------------------
    class AtlasApplication {
        constructor() {
            this.state = {
                active: false,
                installed: false,
                graph: null,
                geometry: null,
                viewport: { x: 0, y: 0, scale: 1 },
                pointer: { active: new Map(), sx: 0, sy: 0, ox: 0, oy: 0 },
                lens: "domains"
            };
            this.dom = Object.create(null);
            this.renderer = null;
        }

        ensureDom() {
            let s = $("#surface-navigation");
            if (!s) {
                const p = $(".surfaces") || $("main") || document.body;
                s = document.createElement("section");
                s.id = "surface-navigation";
                s.className = "surface niche-navigation-surface atlas-surface";
                s.dataset.surface = VIEW;
                s.hidden = true;
                p.append(s);
            }
            s.innerHTML = `
              <div class="atlas-shell">
                <header class="atlas-header">
                  <div class="atlas-brand">
                    <span class="atlas-badge">SAVANT-ATLAS</span>
                    <h1>FACILITY COMPILATION</h1>
                    <div class="atlas-telemetry-hud">
                      <span id="atlas-hud-datum">X:0 Y:0</span>
                      <span id="atlas-hud-scale">1.00X</span>
                      <span class="atlas-hud-pill">${BUILD}</span>
                    </div>
                  </div>
                  <div class="atlas-commandbar">
                    <div class="atlas-search-box">
                      <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/></svg>
                      <input id="atlas-search" type="search" placeholder="Search workspace (/)..." autocomplete="off">
                    </div>
                    <div class="atlas-btn-group">
                      <button id="atlas-btn-fit" class="atlas-cmd-btn" type="button">FIT</button>
                      <button id="atlas-btn-frontier" class="atlas-cmd-btn frontier" type="button">FRONTIER</button>
                      <button id="atlas-btn-drawer" class="atlas-cmd-btn" type="button">INSPECT</button>
                    </div>
                  </div>
                </header>
                <div class="atlas-main">
                  <div id="atlas-viewport" class="atlas-viewport" tabindex="0">
                    <svg id="atlas-svg" class="atlas-svg">
                      <defs>
                        <pattern id="atlas-grid" width="48" height="48" patternUnits="userSpaceOnUse">
                          <path d="M 48 0 L 0 0 0 48" fill="none" stroke="rgba(85,216,255,0.06)" stroke-width="1"/>
                        </pattern>
                        <marker id="atlas-arrow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto">
                          <path d="M 0 1 L 10 5 L 0 9 z" fill="var(--a-accent)"/>
                        </marker>
                      </defs>
                      <g id="atlas-world">
                        <rect id="atlas-ground" class="atlas-ground" fill="url(#atlas-grid)"/>
                        <g id="atlas-concourse-mesh"></g>
                        <g id="atlas-conduits"></g>
                        <g id="atlas-territories"></g>
                        <g id="atlas-tasks"></g>
                      </g>
                    </svg>
                    <div class="atlas-spatial-radar">
                      <svg id="atlas-minimap" class="atlas-minimap"></svg>
                    </div>
                  </div>
                  <aside id="atlas-drawer" class="atlas-drawer" aria-hidden="true">
                    <div class="atlas-drawer-header">
                      <h2>FACILITY TELEMETRY</h2>
                      <button id="atlas-drawer-close" type="button">×</button>
                    </div>
                    <div id="atlas-drawer-content" class="atlas-drawer-content">
                      <p class="atlas-placeholder-text">Select any task node or computational territory.</p>
                    </div>
                  </aside>
                </div>
                <footer class="atlas-footer">
                  <div class="atlas-footer-l">
                    <span class="atlas-stat-dot"></span>
                    <span id="atlas-engine-status">RECONSTRUCTED // PROJECTION ONLY</span>
                  </div>
                  <div class="atlas-footer-r">
                    <span>TIERS: RECONSTRUCTED</span>
                    <span>BUILD: ${BUILD}</span>
                  </div>
                </footer>
              </div>
            `;

            const list = ["viewport", "svg", "world", "ground", "concourse-mesh", "conduits", "territories", "tasks", "minimap", "drawer", "drawer-content", "drawer-close", "search", "btn-fit", "btn-frontier", "btn-drawer", "hud-datum", "hud-scale"];
            for (const id of list) {
                this.dom[id.replace(/-([a-z])/g, (_, c) => c.toUpperCase())] = $(`#atlas-${id}`);
            }
            this.renderer = new RetainedSvgRenderer(this.dom);
        }

        setTransform(x, y, scale, anim = false) {
            this.state.viewport.x = x;
            this.state.viewport.y = y;
            this.state.viewport.scale = clamp(scale, Z_LEVELS.min, Z_LEVELS.max);
            this.dom.world.style.transition = anim ? "transform 0.26s cubic-bezier(0.16, 1, 0.3, 1)" : "none";
            this.dom.world.setAttribute("transform", `translate(${x} ${y}) scale(${this.state.viewport.scale})`);
            this.dom.hudDatum.textContent = `X:${Math.round(-x)} Y:${Math.round(-y)}`;
            this.dom.hudScale.textContent = `${this.state.viewport.scale.toFixed(2)}X`;

            if (this.state.geometry) {
                const r = this.dom.viewport.getBoundingClientRect();
                const mmW = 180, mmH = 110;
                const sX = mmW / this.state.geometry.worldW;
                const sY = mmH / this.state.geometry.worldH;
                let indicator = $("#atlas-mm-lens");
                if (!indicator) {
                    indicator = document.createElementNS(SVG_NS, "rect");
                    indicator.id = "atlas-mm-lens";
                    indicator.setAttribute("class", "atlas-mm-lens");
                    this.dom.minimap.append(indicator);
                }
                indicator.setAttribute("x", `${(-x * sX) / this.state.viewport.scale}`);
                indicator.setAttribute("y", `${(-y * sY) / this.state.viewport.scale}`);
                indicator.setAttribute("width", `${(r.width * sX) / this.state.viewport.scale}`);
                indicator.setAttribute("height", `${(r.height * sY) / this.state.viewport.scale}`);
            }
        }

        fitWorld(anim = true) {
            if (!this.state.geometry) return;
            const r = this.dom.viewport.getBoundingClientRect();
            if (!r.width || !r.height) return;
            const sc = clamp(Math.min(r.width / this.state.geometry.worldW, r.height / this.state.geometry.worldH) * 0.92, Z_LEVELS.min, 1.25);
            const tx = (r.width - this.state.geometry.worldW * sc) / 2;
            const ty = (r.height - this.state.geometry.worldH * sc) / 2;
            this.setTransform(tx, ty, sc, anim);
            acoustics.warp();
        }

        focusTask(id) {
            if (!this.state.geometry) return;
            const g = this.state.geometry.tasks.get(id);
            if (!g) return;
            const r = this.dom.viewport.getBoundingClientRect();
            const sc = Math.max(this.state.viewport.scale, 1.35);
            const tx = r.width / 2 - (g.x + g.w / 2) * sc;
            const ty = r.height / 2 - (g.y + g.h / 2) * sc;
            this.setTransform(tx, ty, sc, true);
            acoustics.tick();
        }

        inspectTask(id) {
            if (!this.state.graph) return;
            const t = this.state.graph.taskById.get(id);
            if (!t) return;
            this.dom.drawer.classList.add("active");
            this.dom.drawer.setAttribute("aria-hidden", "false");
            acoustics.tick();

            this.dom.drawerContent.innerHTML = `
              <div class="atlas-drawer-unit">
                <span class="atlas-badge">TASK SPECIFICATION</span>
                <h3 style="font-size:1.1rem;margin:0.5rem 0;color:var(--a-text);">${taskTitle(t)}</h3>
                <dl class="atlas-spec-table">
                  <dt>IDENTIFIER</dt><dd>${id}</dd>
                  <dt>OBJECTIVE</dt><dd>${taskObjective(t)}</dd>
                  <dt>STATE</dt><dd class="state-txt ${taskState(t)}">${taskState(t).toUpperCase()}</dd>
                  <dt>PRIORITY</dt><dd>${taskPriority(t).toUpperCase()}</dd>
                  <dt>PREREQUISITES</dt><dd>${taskDeps(t).length ? taskDeps(t).join(", ") : "NONE REPORTED"}</dd>
                  <dt>AUTHORITY EFFECT</dt><dd>NONE (PROJECTION BRIDGE)</dd>
                </dl>
                <button id="atlas-drawer-teleport" class="atlas-teleport-btn">WARP VIEWPORT</button>
              </div>
            `;
            $("#atlas-drawer-teleport", this.dom.drawerContent)?.addEventListener("click", () => this.focusTask(id));
        }

        bindEvents() {
            this.dom.btnFit.addEventListener("click", () => this.fitWorld(true));
            this.dom.btnFrontier.addEventListener("click", () => {
                const rec = this.state.graph?.recommendedTaskId;
                if (rec) {
                    this.focusTask(rec);
                    this.inspectTask(rec);
                }
            });
            this.dom.btnDrawer.addEventListener("click", () => {
                this.dom.drawer.classList.toggle("active");
            });
            this.dom.drawerClose.addEventListener("click", () => {
                this.dom.drawer.classList.remove("active");
            });

            this.dom.viewport.addEventListener("click", e => {
                const node = e.target.closest("[data-task-id]");
                if (node) this.inspectTask(node.dataset.taskId);
            });

            this.dom.viewport.addEventListener("wheel", e => {
                e.preventDefault();
                const r = this.dom.viewport.getBoundingClientRect();
                const delta = Math.exp(-e.deltaY * 0.0018);
                const cx = e.clientX - r.left;
                const cy = e.clientY - r.top;
                const nx = cx - (cx - this.state.viewport.x) * delta;
                const ny = cy - (cy - this.state.viewport.y) * delta;
                this.setTransform(nx, ny, this.state.viewport.scale * delta, false);
            }, { passive: false });

            this.dom.viewport.addEventListener("pointerdown", e => {
                if (e.target.closest("button, input")) return;
                this.state.pointer.active.set(e.pointerId, { x: e.clientX, y: e.clientY });
                this.state.pointer.sx = e.clientX;
                this.state.pointer.sy = e.clientY;
                this.state.pointer.ox = this.state.viewport.x;
                this.state.pointer.oy = this.state.viewport.y;
                this.dom.viewport.setPointerCapture?.(e.pointerId);
            });

            window.addEventListener("pointermove", e => {
                if (!this.state.pointer.active.has(e.pointerId)) return;
                const dx = e.clientX - this.state.pointer.sx;
                const dy = e.clientY - this.state.pointer.sy;
                this.setTransform(this.state.pointer.ox + dx, this.state.pointer.oy + dy, this.state.viewport.scale, false);
            });

            const release = e => {
                this.state.pointer.active.delete(e.pointerId);
            };
            window.addEventListener("pointerup", release);
            window.addEventListener("pointercancel", release);

            this.dom.search.addEventListener("keydown", e => {
                if (e.key === "Enter" && this.state.graph) {
                    const q = low(this.dom.search.value);
                    const hit = this.state.graph.tasks.find(t => low(taskId(t)).includes(q) || low(taskTitle(t)).includes(q));
                    if (hit) {
                        this.focusTask(taskId(hit));
                        this.inspectTask(taskId(hit));
                    }
                }
            });

            window.addEventListener("keydown", e => {
                if (e.key === "/" && document.activeElement !== this.dom.search) {
                    e.preventDefault();
                    this.dom.search.focus();
                }
                if (e.key === "0") {
                    e.preventDefault();
                    this.fitWorld(true);
                }
            });
        }

        sync() {
            const rawProj = window.Niche?.projection?.();
            if (!rawProj) return;
            this.state.graph = SemanticGraphSegue.transform(rawProj);
            this.state.geometry = SpatialGeometryEngine.layout(this.state.graph);
            this.renderer.render(this.state.graph, this.state.geometry, this.state.lens);

            if (!this.state.installed) {
                this.state.installed = true;
                requestAnimationFrame(() => this.fitWorld(false));
            }
        }

        open() {
            this.ensureDom();
            const surf = $("#surface-navigation");
            surf.hidden = false;
            surf.classList.add("active");
            for (const s of $$(".surface")) {
                if (s !== surf) {
                    s.classList.remove("active");
                    s.hidden = true;
                }
            }
            this.state.active = true;
            this.sync();
            this.fitWorld(false);
        }

        install() {
            this.ensureDom();
            this.bindEvents();
            this.sync();
            window.addEventListener("niche:projection", () => this.sync());
            document.addEventListener("click", e => {
                const btn = e.target.closest('.nav [data-view="navigation"]');
                if (btn) {
                    e.preventDefault();
                    this.open();
                }
            }, true);
        }
    }

    const app = new AtlasApplication();

    // -------------------------------------------------------------------------
    // VIII. PUBLIC INTEGRATION CONTRACT
    // -------------------------------------------------------------------------
    const API = Object.freeze({
        open: () => app.open(),
        fit: () => app.fitWorld(true),
        select: id => {
            app.focusTask(id);
            app.inspectTask(id);
        },
        state: () => Object.freeze({
            build: BUILD,
            ready: Boolean(app.state.graph),
            tasks: app.state.graph ? app.state.graph.tasks.length : 0,
            authorityEffect: "none",
            projectionOnly: true
        })
    });

    window.NicheAtlas = API;
    window.NicheNavigation = API;

    document.readyState === "loading"
        ? document.addEventListener("DOMContentLoaded", () => app.install(), { once: true })
        : app.install();
})();
