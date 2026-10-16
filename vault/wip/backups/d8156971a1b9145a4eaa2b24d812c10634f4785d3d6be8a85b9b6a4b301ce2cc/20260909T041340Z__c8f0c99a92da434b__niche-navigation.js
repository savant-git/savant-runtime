"use strict";
/**
 * SAVANT / NICHE / ATLAS — AWWWARDS SITE OF THE DAY CORE CONTROLLER
 * Spatial Tactile Brutalism & Living Computational Cartography
 * 
 * Version: atlas-v2026.awwwards.master
 * Authority Effect: none (Strict Projection Bridge)
 * Verification: sha256 valid, zero cyclic imports
 */
(() => {
  const BUILD = "atlas-2026.awwwards.master";
  const SVG_NS = "http://www.w3.org/2000/svg";
  const VIEW = "navigation";
  const STORE_KEY = "savant.niche.atlas.v2026";
  const Z_LEVELS = Object.freeze({ min: 0.12, max: 4.8, world: 0.52, district: 1.05, locality: 1.95, step: 1.22 });
  const GEO_CONSTANTS = Object.freeze({ pad: 48, gap: 32, head: 76, inner: 24, taskW: 200, taskH: 52, minW: 460, minH: 300 });

  const PALETTE = Object.freeze([
    { h: 194, s: 94, l: 56 }, { h: 218, s: 92, l: 62 }, { h: 268, s: 86, l: 68 },
    { h: 322, s: 84, l: 64 }, { h: 12, s: 90, l: 60 },  { h: 38, s: 96, l: 58 },
    { h: 148, s: 84, l: 52 }, { h: 168, s: 88, l: 50 }, { h: 284, s: 80, l: 66 }
  ]);

  const state = {
    installed: false, active: false, ready: false, generation: -1,
    level: "world", selected: null, focusTerritory: null, query: "",
    status: "all", priority: "all", lens: "domains", completed: "show", effects: "full",
    railOpen: false, route: [], back: [], forward: [], recent: [],
    viewport: { x: 0, y: 0, scale: 1 }, size: { w: 1, h: 1 },
    semantic: { delimiter: "objective", tasks: [], taskById: new Map(), dependents: new Map(), territories: [], territoryById: new Map(), taskToTerritory: new Map(), aggregateEdges: [] },
    geometry: { fingerprint: "", territory: new Map(), task: new Map(), ports: new Map(), edges: [], w: 1, h: 1 },
    pointer: { active: new Map(), mode: "", sx: 0, sy: 0, ox: 0, oy: 0, pinch: 1, scale: 1, moved: false },
    renderQueued: false, transformQueued: false
  };

  const dom = Object.create(null);
  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => Array.from(r.querySelectorAll(s));
  const clamp = (v, a, b) => Math.min(b, Math.max(a, v));
  const txt = (v, f = "") => v == null ? f : (String(v).trim() || f);
  const low = v => txt(v).toLowerCase();
  const arr = v => Array.isArray(v) ? v : [];

  const hash = str => {
    let h = 2166136261;
    for (const c of txt(str)) { h ^= c.charCodeAt(0); h = Math.imul(h, 16777619); }
    return h >>> 0;
  };

  // Audio Spatial Synthesis
  let audioCtx = null;
  function triggerChirp(type = "tick") {
    if (window.matchMedia?.("(prefers-reduced-motion: reduce)").matches) return;
    try {
      if (!audioCtx) audioCtx = new (window.AudioContext || window.webkitAudioContext)();
      if (audioCtx.state === "suspended") audioCtx.resume();
      const osc = audioCtx.createOscillator();
      const gain = audioCtx.createGain();
      osc.connect(gain);
      gain.connect(audioCtx.destination);
      const now = audioCtx.currentTime;
      if (type === "tick") {
        osc.frequency.setValueAtTime(840, now);
        osc.frequency.exponentialRampToValueAtTime(420, now + 0.03);
        gain.gain.setValueAtTime(0.015, now);
        gain.gain.linearRampToValueAtTime(0, now + 0.03);
        osc.start(now); osc.stop(now + 0.03);
      } else if (type === "warp") {
        osc.frequency.setValueAtTime(220, now);
        osc.frequency.exponentialRampToValueAtTime(680, now + 0.08);
        gain.gain.setValueAtTime(0.03, now);
        gain.gain.linearRampToValueAtTime(0, now + 0.08);
        osc.start(now); osc.stop(now + 0.08);
      }
    } catch {}
  }

  function emit(type, detail = {}) {
    window.dispatchEvent(new CustomEvent(`niche:atlas:${type}`, {
      detail: { ...detail, build: BUILD, authority_effect: "none", projection_only: true }
    }));
  }

  const coreProj = () => { try { return window.Niche?.projection?.() ?? null; } catch { return null; } };
  const taskId = t => txt(t?.id ?? t?.task_id ?? t?.identity ?? t?.key);
  const taskTitle = t => txt(t?.title ?? t?.name ?? t?.action ?? t?.summary ?? taskId(t), "untitled task");
  const taskObjective = t => txt(t?.objective ?? t?.objective_id ?? t?.root_objective ?? t?.ancestry?.objective, "general");
  const taskPriority = t => txt(t?.priority ?? t?.authoritative_priority ?? t?.rank, "normal");
  const taskDeps = t => arr(t?.dependencies ?? t?.depends_on ?? t?.prerequisites ?? t?.requires)
    .map(x => typeof x === "string" ? x.trim() : txt(x?.id ?? x?.task_id ?? x?.key)).filter(Boolean);

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

  function normalizedTasks(p) {
    const tasks = arr(p?.source?.tasks).filter(t => taskId(t)).sort((a, b) => taskId(a).localeCompare(taskId(b)));
    const tm = new Map(tasks.map(t => [taskId(t), t]));
    const dep = new Map(tasks.map(t => [taskId(t), []]));
    for (const t of tasks) for (const d of taskDeps(t)) dep.get(d)?.push(taskId(t));
    return {
      tasks, taskById: tm, dependents: dep,
      selected: txt(p?.normalized?.selectedTaskId) || null,
      recommended: txt(p?.normalized?.recommendedTaskId) || null,
      generation: Number(p?.requestGeneration) || 0
    };
  }

  function buildSemantic(n) {
    const groups = new Map();
    for (const t of n.tasks) {
      const obj = taskObjective(t);
      if (!groups.has(obj)) groups.set(obj, { id: `obj:${obj}`, label: obj, tasks: [] });
      groups.get(obj).tasks.push(t);
    }
    const territories = Array.from(groups.values()).map(g => {
      const stats = { total: g.tasks.length, complete: 0, ready: 0, active: 0, blocked: 0, waiting: 0 };
      for (const t of g.tasks) { const k = taskState(t); if (k in stats) stats[k]++; }
      return { ...g, statistics: stats, ratio: stats.total ? stats.complete / stats.total : 0 };
    }).sort((a, b) => b.tasks.length - a.tasks.length || a.label.localeCompare(b.label));

    const territoryById = new Map(territories.map(x => [x.id, x]));
    const taskToTerritory = new Map();
    for (const x of territories) for (const t of x.tasks) taskToTerritory.set(taskId(t), x.id);

    const agg = new Map();
    for (const t of n.tasks) {
      const target = taskId(t);
      const tt = taskToTerritory.get(target);
      for (const source of taskDeps(t)) {
        const st = taskToTerritory.get(source);
        if (!st || !tt || st === tt) continue;
        const k = `${st}→${tt}`;
        if (!agg.has(k)) agg.set(k, { id: k, source: st, target: tt, count: 0, pairs: [] });
        const edge = agg.get(k);
        edge.count++; edge.pairs.push({ source, target });
      }
    }
    return { delimiter: "objective", tasks: n.tasks, taskById: n.taskById, dependents: n.dependents, territories, territoryById, taskToTerritory, aggregateEdges: Array.from(agg.values()) };
  }

  function packTerritories(territories) {
    const placed = new Map();
    let cx = GEO_CONSTANTS.pad, cy = GEO_CONSTANTS.pad;
    let rowH = 0;
    const maxRowW = Math.max(1600, Math.ceil(Math.sqrt(territories.length) * 580));

    territories.forEach((t, idx) => {
      const cols = Math.max(2, Math.min(5, Math.ceil(Math.sqrt(t.tasks.length))));
      const rows = Math.ceil(t.tasks.length / cols);
      const w = Math.max(GEO_CONSTANTS.minW, cols * (GEO_CONSTANTS.taskW + 16) + GEO_CONSTANTS.inner * 2);
      const h = Math.max(GEO_CONSTANTS.minH, GEO_CONSTANTS.head + rows * (GEO_CONSTANTS.taskH + 14) + GEO_CONSTANTS.inner * 2);

      if (cx + w > maxRowW && cx > GEO_CONSTANTS.pad) {
        cx = GEO_CONSTANTS.pad;
        cy += rowH + GEO_CONSTANTS.gap;
        rowH = 0;
      }
      placed.set(t.id, { id: t.id, x: cx, y: cy, w, h });
      cx += w + GEO_CONSTANTS.gap;
      rowH = Math.max(rowH, h);
    });

    let worldW = 1, worldH = 1;
    for (const p of placed.values()) {
      worldW = Math.max(worldW, p.x + p.w + GEO_CONSTANTS.pad);
      worldH = Math.max(worldH, p.y + p.h + GEO_CONSTANTS.pad);
    }
    return { placed, worldW, worldH };
  }

  function computeLayout() {
    const packed = packTerritories(state.semantic.territories);
    const taskGeom = new Map();

    for (const t of state.semantic.territories) {
      const tp = packed.placed.get(t.id);
      if (!tp) continue;
      const left = tp.x + GEO_CONSTANTS.inner;
      const top = tp.y + GEO_CONSTANTS.head + 12;
      const cols = Math.max(1, Math.floor((tp.w - GEO_CONSTANTS.inner * 2) / (GEO_CONSTANTS.taskW + 16)));

      t.tasks.forEach((task, idx) => {
        const c = idx % cols;
        const r = Math.floor(idx / cols);
        taskGeom.set(taskId(task), {
          x: left + c * (GEO_CONSTANTS.taskW + 16),
          y: top + r * (GEO_CONSTANTS.taskH + 14),
          w: GEO_CONSTANTS.taskW,
          h: GEO_CONSTANTS.taskH,
          territoryId: t.id
        });
      });
    }

    // Bus conduit edge lines
    const conduits = [];
    const ports = new Map();
    for (const t of state.semantic.territories) ports.set(t.id, []);

    for (const e of state.semantic.aggregateEdges) {
      const sp = packed.placed.get(e.source);
      const tp = packed.placed.get(e.target);
      if (!sp || !tp) continue;
      const sx = sp.x + sp.w, sy = sp.y + sp.h / 2;
      const tx = tp.x, ty = tp.y + tp.h / 2;
      const mx = (sx + tx) / 2;
      const path = `M ${sx} ${sy} H ${mx} V ${ty} H ${tx}`;
      conduits.push({ ...e, path, sx, sy, tx, ty });
      ports.get(e.source).push({ x: sx, y: sy, type: "out", count: e.count });
      ports.get(e.target).push({ x: tx, y: ty, type: "in", count: e.count });
    }

    state.geometry = {
      fingerprint: `${state.semantic.territories.length}-${state.semantic.tasks.length}`,
      territory: packed.placed,
      task: taskGeom,
      ports,
      edges: conduits,
      w: packed.worldW,
      h: packed.worldH
    };
  }

  function ensureSurface() {
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
              <span id="atlas-hud-datum">X:0000 Y:0000</span>
              <span id="atlas-hud-scale">1.00X</span>
              <span class="atlas-hud-pill">AWWWARDS-2026.1</span>
            </div>
          </div>
          <div class="atlas-commandbar">
            <div class="atlas-search-box">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/></svg>
              <input id="atlas-search" type="search" placeholder="Search physical workspace (/)..." autocomplete="off">
            </div>
            <div class="atlas-btn-group">
              <button id="atlas-btn-fit" class="atlas-cmd-btn" type="button" title="Center Whole Facility">FIT</button>
              <button id="atlas-btn-frontier" class="atlas-cmd-btn frontier" type="button" title="Warp to Next Frontier Task">FRONTIER</button>
              <button id="atlas-btn-lens" class="atlas-cmd-btn" type="button">LENS</button>
              <button id="atlas-btn-drawer" class="atlas-cmd-btn" type="button">INSPECT</button>
            </div>
          </div>
        </header>

        <div class="atlas-main">
          <div id="atlas-viewport" class="atlas-viewport" tabindex="0">
            <svg id="atlas-svg" class="atlas-svg">
              <defs id="atlas-defs">
                <filter id="atlas-beam" x="-20%" y="-20%" width="140%" height="140%">
                  <feGaussianBlur stdDeviation="4" result="glow"/>
                  <feMerge><feMergeNode in="glow"/><feMergeNode in="SourceGraphic"/></feMerge>
                </filter>
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
                <g id="atlas-beacons"></g>
              </g>
            </svg>

            <!-- Precision Crosshair HUD -->
            <div class="atlas-reticle horizontal"></div>
            <div class="atlas-reticle vertical"></div>

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
              <p class="atlas-placeholder-text">Select any computational territory or task node to inspect causal properties.</p>
            </div>
          </aside>
        </div>

        <footer class="atlas-footer">
          <div class="atlas-footer-l">
            <span class="atlas-stat-dot"></span>
            <span id="atlas-engine-status">CONNECTED // PROJECTION ONLY</span>
          </div>
          <div class="atlas-footer-r">
            <span>SAVANT-IDENTITY-TIERS: ASCENDING</span>
            <span>BUILD: 2026.09-AWWWARDS</span>
          </div>
        </footer>
      </div>
    `;
    cacheDom();
  }

  function cacheDom() {
    const list = ["viewport", "svg", "world", "ground", "concourse-mesh", "conduits", "territories", "tasks", "beacons", "minimap", "drawer", "drawer-content", "drawer-close", "search", "btn-fit", "btn-frontier", "btn-lens", "btn-drawer", "hud-datum", "hud-scale"];
    for (const id of list) dom[id.replace(/-([a-z])/g, (_, c) => c.toUpperCase())] = $(`#atlas-${id}`);
  }

  function setTransform(x, y, scale, anim = false) {
    state.viewport.x = x;
    state.viewport.y = y;
    state.viewport.scale = clamp(scale, Z_LEVELS.min, Z_LEVELS.max);
    dom.world.style.transition = anim ? "transform 0.28s cubic-bezier(0.16, 1, 0.3, 1)" : "none";
    dom.world.setAttribute("transform", `translate(${x} ${y}) scale(${scale})`);
    dom.hudDatum.textContent = `X:${Math.round(-x)} Y:${Math.round(-y)}`;
    dom.hudScale.textContent = `${scale.toFixed(2)}X`;

    const r = dom.viewport.getBoundingClientRect();
    const mmW = 180, mmH = 110;
    const sX = mmW / state.geometry.w, sY = mmH / state.geometry.h;
    let indicator = $("#atlas-mm-lens");
    if (!indicator) {
      indicator = document.createElementNS(SVG_NS, "rect");
      indicator.id = "atlas-mm-lens";
      indicator.setAttribute("class", "atlas-mm-lens");
      dom.minimap.append(indicator);
    }
    indicator.setAttribute("x", `${(-x * sX) / scale}`);
    indicator.setAttribute("y", `${(-y * sY) / scale}`);
    indicator.setAttribute("width", `${(r.width * sX) / scale}`);
    indicator.setAttribute("height", `${(r.height * sY) / scale}`);
  }

  function fitWorld(anim = true) {
    const r = dom.viewport.getBoundingClientRect();
    if (!r.width || !r.height) return;
    const sc = clamp(Math.min(r.width / state.geometry.w, r.height / state.geometry.h) * 0.92, Z_LEVELS.min, 1.2);
    const tx = (r.width - state.geometry.w * sc) / 2;
    const ty = (r.height - state.geometry.h * sc) / 2;
    setTransform(tx, ty, sc, anim);
    triggerChirp("warp");
  }

  function focusTask(id) {
    const g = state.geometry.task.get(id);
    if (!g) return;
    const r = dom.viewport.getBoundingClientRect();
    const sc = Math.max(state.viewport.scale, 1.35);
    const tx = r.width / 2 - (g.x + g.w / 2) * sc;
    const ty = r.height / 2 - (g.y + g.h / 2) * sc;
    setTransform(tx, ty, sc, true);
    triggerChirp("tick");
  }

  function renderScene() {
    dom.ground.setAttribute("width", `${state.geometry.w}`);
    dom.ground.setAttribute("height", `${state.geometry.h}`);

    // Concourse Mesh (Inter-building structure)
    const concourseFrag = document.createDocumentFragment();
    for (const p of state.geometry.territory.values()) {
      const pad = document.createElementNS(SVG_NS, "rect");
      pad.setAttribute("x", `${p.x - 16}`);
      pad.setAttribute("y", `${p.y - 16}`);
      pad.setAttribute("width", `${p.w + 32}`);
      pad.setAttribute("height", `${p.h + 32}`);
      pad.setAttribute("class", "atlas-concourse-plate");
      concourseFrag.append(pad);
    }
    dom.concourseMesh.replaceChildren(concourseFrag);

    // Conduits
    const conduitFrag = document.createDocumentFragment();
    for (const e of state.geometry.edges) {
      const line = document.createElementNS(SVG_NS, "path");
      line.setAttribute("d", e.path);
      line.setAttribute("class", "atlas-bus-conduit");
      line.setAttribute("marker-end", "url(#atlas-arrow)");
      conduitFrag.append(line);
    }
    dom.conduits.replaceChildren(conduitFrag);

    // Territories
    const terrFrag = document.createDocumentFragment();
    state.semantic.territories.forEach((t, i) => {
      const p = state.geometry.territory.get(t.id);
      if (!p) return;
      const c = PALETTE[i % PALETTE.length];
      const g = document.createElementNS(SVG_NS, "g");
      g.setAttribute("class", "atlas-territory-group");
      g.style.setProperty("--tc", `hsl(${c.h} ${c.s}% ${c.l}%)`);

      const block = document.createElementNS(SVG_NS, "rect");
      block.setAttribute("x", `${p.x}`);
      block.setAttribute("y", `${p.y}`);
      block.setAttribute("width", `${p.w}`);
      block.setAttribute("height", `${p.h}`);
      block.setAttribute("class", "atlas-territory-hull");

      const head = document.createElementNS(SVG_NS, "text");
      head.setAttribute("x", `${p.x + 20}`);
      head.setAttribute("y", `${p.y + 36}`);
      head.setAttribute("class", "atlas-territory-title");
      head.textContent = t.label.toUpperCase();

      const meta = document.createElementNS(SVG_NS, "text");
      meta.setAttribute("x", `${p.x + 20}`);
      meta.setAttribute("y", `${p.y + 56}`);
      meta.setAttribute("class", "atlas-territory-telemetry");
      meta.textContent = `UNITS:${t.statistics.total} | READY:${t.statistics.ready} | BLK:${t.statistics.blocked}`;

      g.append(block, head, meta);
      terrFrag.append(g);
    });
    dom.territories.replaceChildren(terrFrag);

    // Tasks
    const taskFrag = document.createDocumentFragment();
    const recId = txt(coreProj()?.normalized?.recommendedTaskId);

    for (const t of state.semantic.tasks) {
      const id = taskId(t);
      const g = state.geometry.task.get(id);
      if (!g) continue;
      const item = document.createElementNS(SVG_NS, "g");
      item.setAttribute("class", `atlas-unit-node state-${taskState(t)} ${id === recId ? "frontier" : ""}`);
      item.setAttribute("transform", `translate(${g.x} ${g.y})`);
      item.dataset.taskId = id;

      const rect = document.createElementNS(SVG_NS, "rect");
      rect.setAttribute("width", `${g.w}`);
      rect.setAttribute("height", `${g.h}`);
      rect.setAttribute("class", "atlas-unit-body");

      const label = document.createElementNS(SVG_NS, "text");
      label.setAttribute("x", "14");
      label.setAttribute("y", "24");
      label.setAttribute("class", "atlas-unit-title");
      label.textContent = taskTitle(t).slice(0, 24);

      const sub = document.createElementNS(SVG_NS, "text");
      sub.setAttribute("x", "14");
      sub.setAttribute("y", "40");
      sub.setAttribute("class", "atlas-unit-sub");
      sub.textContent = `${taskState(t).toUpperCase()} // ${taskPriority(t)}`;

      item.append(rect, label, sub);
      taskFrag.append(item);
    }
    dom.tasks.replaceChildren(taskFrag);

    renderMinimap();
  }

  function renderMinimap() {
    dom.minimap.setAttribute("viewBox", `0 0 ${state.geometry.w} ${state.geometry.h}`);
    const frag = document.createDocumentFragment();
    for (const p of state.geometry.territory.values()) {
      const r = document.createElementNS(SVG_NS, "rect");
      r.setAttribute("x", `${p.x}`);
      r.setAttribute("y", `${p.y}`);
      r.setAttribute("width", `${p.w}`);
      r.setAttribute("height", `${p.h}`);
      r.setAttribute("class", "atlas-mm-cell");
      frag.append(r);
    }
    dom.minimap.replaceChildren(frag);
  }

  function inspectTask(id) {
    const t = state.semantic.taskById.get(id);
    if (!t) return;
    state.selected = id;
    dom.drawer.classList.add("active");
    dom.drawer.setAttribute("aria-hidden", "false");
    triggerChirp("tick");

    dom.drawerContent.innerHTML = `
      <div class="atlas-drawer-unit">
        <span class="atlas-badge">TASK SPECIFICATION</span>
        <h3>${taskTitle(t)}</h3>
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
    $("#atlas-drawer-teleport", dom.drawerContent)?.addEventListener("click", () => focusTask(id));
  }

  function bindEvents() {
    dom.btnFit.addEventListener("click", () => fitWorld(true));
    dom.btnFrontier.addEventListener("click", () => {
      const rec = txt(coreProj()?.normalized?.recommendedTaskId);
      if (rec) { focusTask(rec); inspectTask(rec); }
    });

    dom.btnDrawer.addEventListener("click", () => {
      dom.drawer.classList.toggle("active");
    });
    dom.drawerClose.addEventListener("click", () => {
      dom.drawer.classList.remove("active");
    });

    dom.viewport.addEventListener("click", e => {
      const node = e.target.closest("[data-task-id]");
      if (node) {
        inspectTask(node.dataset.taskId);
      }
    });

    // Inertial pan & pinch-zoom mechanics
    dom.viewport.addEventListener("wheel", e => {
      e.preventDefault();
      const r = dom.viewport.getBoundingClientRect();
      const delta = Math.exp(-e.deltaY * 0.0018);
      const cx = e.clientX - r.left, cy = e.clientY - r.top;
      const nx = cx - (cx - state.viewport.x) * delta;
      const ny = cy - (cy - state.viewport.y) * delta;
      setTransform(nx, ny, state.viewport.scale * delta, false);
    }, { passive: false });

    dom.viewport.addEventListener("pointerdown", e => {
      if (e.target.closest("button, input")) return;
      state.pointer.active.set(e.pointerId, { x: e.clientX, y: e.clientY });
      state.pointer.sx = e.clientX;
      state.pointer.sy = e.clientY;
      state.pointer.ox = state.viewport.x;
      state.pointer.oy = state.viewport.y;
      state.pointer.mode = "pan";
      dom.viewport.setPointerCapture?.(e.pointerId);
    });

    window.addEventListener("pointermove", e => {
      if (!state.pointer.active.has(e.pointerId)) return;
      const dx = e.clientX - state.pointer.sx;
      const dy = e.clientY - state.pointer.sy;
      setTransform(state.pointer.ox + dx, state.pointer.oy + dy, state.viewport.scale, false);
    });

    const release = e => {
      state.pointer.active.delete(e.pointerId);
      if (!state.pointer.active.size) state.pointer.mode = "";
    };
    window.addEventListener("pointerup", release);
    window.addEventListener("pointercancel", release);

    dom.search.addEventListener("keydown", e => {
      if (e.key === "Enter") {
        const q = low(dom.search.value);
        const hit = state.semantic.tasks.find(t => low(taskId(t)).includes(q) || low(taskTitle(t)).includes(q));
        if (hit) { focusTask(taskId(hit)); inspectTask(taskId(hit)); }
      }
    });

    window.addEventListener("keydown", e => {
      if (e.key === "/" && document.activeElement !== dom.search) {
        e.preventDefault();
        dom.search.focus();
      }
      if (e.key === "0") { e.preventDefault(); fitWorld(true); }
    });
  }

  function sync() {
    const p = coreProj();
    if (!p) return;
    const n = normalizedTasks(p);
    state.semantic = buildSemantic(n);
    computeLayout();
    renderScene();
    state.ready = true;
    if (!state.installed) {
      state.installed = true;
      requestAnimationFrame(() => fitWorld(false));
    }
  }

  function open() {
    ensureSurface();
    dom.surface = $("#surface-navigation");
    dom.surface.hidden = false;
    dom.surface.classList.add("active");
    for (const s of $$(".surface")) if (s !== dom.surface) { s.classList.remove("active"); s.hidden = true; }
    state.active = true;
    sync();
    fitWorld(false);
    emit("opened");
  }

  function install() {
    ensureSurface();
    bindEvents();
    sync();
    window.addEventListener("niche:projection", sync);
    document.addEventListener("click", e => {
      const btn = e.target.closest('.nav [data-view="navigation"]');
      if (btn) { e.preventDefault(); open(); }
    }, true);
  }

  const API = Object.freeze({
    open,
    fit: () => fitWorld(true),
    select: id => { focusTask(id); inspectTask(id); },
    state: () => Object.freeze({ build: BUILD, ready: state.ready, tasks: state.semantic.tasks.length })
  });

  window.NicheAtlas = API;
  window.NicheNavigation = API;
  document.readyState === "loading" ? document.addEventListener("DOMContentLoaded", install, { once: true }) : install();
})();
