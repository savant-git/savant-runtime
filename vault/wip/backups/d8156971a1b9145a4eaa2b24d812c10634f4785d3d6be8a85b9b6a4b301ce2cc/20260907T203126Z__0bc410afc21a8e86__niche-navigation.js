"use strict";

/*
 * savant / niche / atlas
 * asset: niche-navigation.js
 * owner: exile:niche
 * authority_effect: none
 * projection_only: true
 * build: r11-major-reconstruction
 */

(() => {
  const BUILD_VERSION = "r11-major-reconstruction";
  const SVG = "http://www.w3.org/2000/svg";
  const VIEW = "navigation";
  const STORE = "savant.niche.atlas.v2";
  const LEVEL = Object.freeze({ world: "world", district: "district", locality: "locality", detail: "detail" });
  const Z = Object.freeze({ min: 0.12, max: 5.0, world: 0.52, district: 0.98, locality: 1.85, step: 1.25 });
  const G = Object.freeze({ pad: 40, gap: 20, head: 72, inner: 24, taskW: 190, taskH: 52, taskGapX: 16, taskGapY: 14, minW: 460, minH: 300 });

  const palette = Object.freeze([
    [188, 92, 58], [213, 94, 62], [267, 88, 66], [319, 86, 62],
    [8, 88, 59], [36, 94, 59], [67, 80, 56], [143, 82, 52],
    [166, 86, 54], [235, 86, 68], [287, 78, 65], [343, 84, 62]
  ]);

  const state = {
    installed: false,
    active: false,
    ready: false,
    generation: -1,
    renderQueued: false,
    transformQueued: false,
    level: LEVEL.world,
    selected: null,
    focusTerritory: null,
    query: "",
    status: "all",
    priority: "all",
    lens: "domains",
    completed: "show",
    effects: "full",
    railOpen: false,
    route: [],
    back: [],
    forward: [],
    recent: [],
    detail: null,
    filterTouched: false,
    viewportAnimation: null,
    viewport: { x: 0, y: 0, scale: 1 },
    size: { w: 1, h: 1 },
    semantic: { delimiter: "objective", tasks: [], taskById: new Map(), dependents: new Map(), territories: [], territoryById: new Map(), taskToTerritory: new Map(), aggregateEdges: [] },
    geometry: { fingerprint: "", territory: new Map(), task: new Map(), ports: new Map(), edges: [], w: 1, h: 1 },
    pointer: { active: new Map(), mode: "", sx: 0, sy: 0, ox: 0, oy: 0, pinch: 1, scale: 1, cx: 0, cy: 0 },
    resizeObserver: null,
    firstFit: false,
    suppressClick: false,
    renderStageToken: 0,
    gestureMoved: false,
    railMode: "more"
  };

  const dom = Object.create(null);

  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => Array.from(r.querySelectorAll(s));
  const txt = (v, f = "") => (v == null ? f : String(v).trim() || f);
  const low = v => txt(v).toLocaleLowerCase();
  const arr = v => (Array.isArray(v) ? v : []);
  const clamp = (v, a, b) => Math.min(b, Math.max(a, v));

  const hash = input => {
    let h = 2166136261;
    for (const ch of txt(input)) {
      h ^= ch.charCodeAt(0);
      h = Math.imul(h, 16777619);
    }
    return h >>> 0;
  };

  const sread = () => {
    try {
      const x = localStorage.getItem(STORE);
      return x ? JSON.parse(x) : null;
    } catch {
      return null;
    }
  };

  const swrite = () => {
    try {
      localStorage.setItem(
        STORE,
        JSON.stringify({
          viewport: state.viewport,
          query: state.query,
          status: state.status,
          priority: state.priority,
          lens: state.lens,
          completed: state.completed,
          effects: state.effects,
          focusTerritory: state.focusTerritory
        })
      );
    } catch {}
  };

  const emit = (type, detail = {}) =>
    window.dispatchEvent(
      new CustomEvent(`niche:atlas:${type}`, {
        detail: { ...detail, authority_effect: "none", projection_only: true }
      })
    );

  function coreProjection() {
    try {
      return window.Niche?.projection?.() ?? null;
    } catch {
      return null;
    }
  }

  function coreState() {
    try {
      return window.Niche?.state?.() ?? {};
    } catch {
      return {};
    }
  }

  const taskId = t => txt(t?.id ?? t?.task_id ?? t?.identity ?? t?.key);
  const taskTitle = t => txt(t?.title ?? t?.name ?? t?.action ?? t?.summary ?? taskId(t), "untitled task");
  const taskObjective = t => txt(t?.objective ?? t?.objective_id ?? t?.root_objective ?? t?.ancestry?.objective, "unknown objective");
  const taskDomain = t => txt(t?.domain ?? t?.domain_id ?? t?.area ?? t?.scope?.domain);
  const taskOwner = t => txt(t?.owner ?? t?.owner_id ?? t?.task_owner ?? t?.assignee);
  const taskRubric = t => txt(t?.rubric ?? t?.rubric_id ?? t?.program_surface ?? t?.surface);
  const taskCabal = t => txt(t?.cabal ?? t?.cabal_id ?? t?.shared_scope);
  const taskPriority = t => txt(t?.priority ?? t?.authoritative_priority ?? t?.rank, "unknown");
  const taskParent = t => txt(t?.parent ?? t?.parent_id ?? t?.parent_task_id ?? t?.ancestry?.parent);

  const taskDependencies = t =>
    arr(t?.dependencies ?? t?.depends_on ?? t?.prerequisites ?? t?.requires)
      .map(x => (typeof x === "string" ? x.trim() : txt(x?.id ?? x?.task_id ?? x?.key)))
      .filter(Boolean);

  function taskState(t) {
    const r = low(t?.state ?? t?.status ?? t?.lifecycle_state);
    if (r.includes("complete") || r === "done" || r === "closed") return "complete";
    if (r.includes("block") || r === "failed") return "blocked";
    if (r.includes("active") || r.includes("progress") || r === "started" || r === "leased") return "active";
    if (r.includes("review") || r.includes("verify") || r.includes("evidence")) return "review";
    if (r.includes("wait") || r.includes("pending") || r.includes("defer")) return "waiting";
    if (t?.ready === true || t?.is_ready === true || low(t?.readiness) === "ready") return "ready";
    return r || "unknown";
  }

  function recommendationId(p) {
    return txt(p?.normalized?.recommendedTaskId ?? coreState()?.recommendedTaskId) || null;
  }

  function normalized(p) {
    const tasks = arr(p?.source?.tasks).filter(t => taskId(t)).slice().sort((a, b) => taskId(a).localeCompare(taskId(b)));
    const tm = p?.normalized?.taskById instanceof Map ? new Map(p.normalized.taskById) : new Map(tasks.map(t => [taskId(t), t]));
    let dep;
    if (p?.normalized?.dependents instanceof Map) {
      dep = new Map(Array.from(p.normalized.dependents.entries(), ([k, v]) => [k, arr(v).slice()]));
    } else {
      dep = new Map(tasks.map(t => [taskId(t), []]));
      for (const t of tasks) for (const d of taskDependencies(t)) dep.get(d)?.push(taskId(t));
      for (const x of dep.values()) x.sort();
    }
    return { tasks, taskById: tm, dependents: dep, selected: txt(p?.normalized?.selectedTaskId) || null, recommended: recommendationId(p), generation: Number(p?.requestGeneration) };
  }

  const delimiters = [
    ["domain", taskDomain, 5],
    ["rubric", taskRubric, 4],
    ["cabal", taskCabal, 3],
    ["objective", taskObjective, 2],
    ["owner", taskOwner, 1]
  ];

  function chooseDelimiter(tasks) {
    const max = Math.max(18, Math.ceil(Math.sqrt(Math.max(1, tasks.length)) * 2.4));
    const scored = delimiters
      .map(([id, get, pref]) => {
        const vals = tasks.map(get).filter(Boolean);
        const n = new Set(vals).size;
        const coverage = vals.length / Math.max(1, tasks.length);
        const cq = n >= 2 && n <= max ? 1 : n === 1 ? 0.25 : 0.55;
        return { id, get, pref, n, coverage, score: coverage * 0.6 + cq * 0.3 + pref * 0.02 };
      })
      .filter(x => x.coverage >= 0.72 && x.n >= 2)
      .sort((a, b) => b.score - a.score || b.pref - a.pref || a.id.localeCompare(b.id));
    return scored[0] ?? { id: "objective", get: taskObjective, pref: 2 };
  }

  function stats(tasks) {
    const s = { total: tasks.length, complete: 0, ready: 0, active: 0, review: 0, waiting: 0, blocked: 0, unknown: 0 };
    for (const t of tasks) {
      const k = taskState(t);
      if (k in s) s[k]++;
      else s.unknown++;
    }
    s.completionRatio = s.total ? s.complete / s.total : 0;
    return s;
  }

  function buildSemantic(n) {
    const d = chooseDelimiter(n.tasks);
    const groups = new Map();
    for (const t of n.tasks) {
      const label = d.get(t) || `unknown ${d.id}`;
      const id = `${d.id}:${label}`;
      if (!groups.has(id)) groups.set(id, { id, label, delimiter: d.id, tasks: [] });
      groups.get(id).tasks.push(t);
    }
    const territories = Array.from(groups.values())
      .map(x => ({
        ...x,
        tasks: x.tasks.slice().sort((a, b) => taskObjective(a).localeCompare(taskObjective(b)) || taskTitle(a).localeCompare(taskTitle(b)) || taskId(a).localeCompare(taskId(b))),
        statistics: stats(x.tasks),
        objectives: Array.from(new Set(x.tasks.map(taskObjective).filter(Boolean))).sort()
      }))
      .sort((a, b) => b.tasks.length - a.tasks.length || a.label.localeCompare(b.label));

    const territoryById = new Map(territories.map(x => [x.id, x]));
    const taskToTerritory = new Map();
    for (const x of territories) for (const t of x.tasks) taskToTerritory.set(taskId(t), x.id);

    const agg = new Map();
    for (const t of n.tasks) {
      const target = taskId(t);
      const tt = taskToTerritory.get(target);
      for (const source of taskDependencies(t)) {
        const st = taskToTerritory.get(source);
        if (!st || !tt || st === tt) continue;
        const key = `${st}→${tt}`;
        if (!agg.has(key)) agg.set(key, { id: key, source: st, target: tt, count: 0, taskEdges: [] });
        const r = agg.get(key);
        r.count++;
        r.taskEdges.push({ source, target });
      }
    }
    return { delimiter: d.id, tasks: n.tasks, taskById: n.taskById, dependents: n.dependents, territories, territoryById, taskToTerritory, aggregateEdges: Array.from(agg.values()).sort((a, b) => b.count - a.count || a.id.localeCompare(b.id)) };
  }

  function polygon(x, y, w, h, shape) {
    const c = Math.max(36, Math.min(w, h) * 0.16);
    const i = Math.max(72, Math.min(w, h) * 0.28);
    const p = {
      rect: [[x + c, y], [x + w - c, y], [x + w, y + c], [x + w, y + h - c], [x + w - c, y + h], [x + c, y + h], [x, y + h - c], [x, y + c]],
      "l-right": [[x + c, y], [x + w - c, y], [x + w, y + c], [x + w, y + h - i], [x + w - i, y + h - i], [x + w - i, y + h], [x + c, y + h], [x, y + h - c], [x, y + c]],
      "l-left": [[x + c, y], [x + w - c, y], [x + w, y + c], [x + w, y + h - c], [x + w - c, y + h], [x + i, y + h], [x + i, y + h - i], [x, y + h - i], [x, y + c]],
      "step-right": [[x + c, y], [x + w - i, y], [x + w - i, y + i * 0.5], [x + w, y + i * 0.5], [x + w, y + h - c], [x + w - c, y + h], [x + c, y + h], [x, y + h - c], [x, y + c]],
      u: [[x + c, y], [x + w - c, y], [x + w, y + c], [x + w, y + h - c], [x + w - c, y + h], [x + w * 0.62, y + h], [x + w * 0.62, y + h - i], [x + w * 0.38, y + h - i], [x + w * 0.38, y + h], [x + c, y + h], [x, y + h - c], [x, y + c]],
      "dual-wing": [[x + c, y], [x + w * 0.42, y], [x + w * 0.42, y + i * 0.4], [x + w * 0.58, y + i * 0.4], [x + w * 0.58, y], [x + w - c, y], [x + w, y + c], [x + w, y + h - c], [x + w - c, y + h], [x + w * 0.58, y + h], [x + w * 0.58, y + h - i * 0.4], [x + w * 0.42, y + h - i * 0.4], [x + w * 0.42, y + h], [x + c, y + h], [x, y + h - c], [x, y + c]]
    };
    return p[shape] ?? p.rect;
  }

  const pstr = p => p.map(([x, y]) => `${Math.round(x)},${Math.round(y)}`).join(" ");

  function inside(pt, poly) {
    let yes = false;
    for (let a = 0, b = poly.length - 1; a < poly.length; b = a++) {
      const [xi, yi] = poly[a], [xj, yj] = poly[b];
      const hit = yi > pt.y !== yj > pt.y && pt.x < ((xj - xi) * (pt.y - yi)) / (yj - yi || 1e-9) + xi;
      if (hit) yes = !yes;
    }
    return yes;
  }

  function packFloorplan(territories) {
    const aspect = clamp(state.size.w / Math.max(1, state.size.h), 0.8, 1.8);
    const placed = new Map();
    const shapes = ["rect", "l-right", "l-left", "step-right", "u", "dual-wing"];

    let cols = Math.ceil(Math.sqrt(territories.length * aspect));
    cols = Math.max(2, Math.min(5, cols));

    let curX = G.pad;
    let curY = G.pad;
    let rowH = 0;
    let colIndex = 0;

    for (let i = 0; i < territories.length; i++) {
      const t = territories[i];
      const shape = shapes[(hash(t.id) + i) % shapes.length];
      const taskCount = t.tasks.length;
      const w = Math.max(G.minW, 420 + Math.min(480, taskCount * 14));
      const h = Math.max(G.minH, G.head + G.inner * 2 + Math.ceil(taskCount / 3) * (G.taskH + G.taskGapY));

      if (colIndex >= cols) {
        curX = G.pad;
        curY += rowH + G.gap;
        rowH = 0;
        colIndex = 0;
      }

      placed.set(t.id, {
        id: t.id,
        x: curX,
        y: curY,
        w: Math.round(w),
        h: Math.round(h),
        shape,
        points: polygon(curX, curY, w, h, shape)
      });

      curX += w + G.gap;
      rowH = Math.max(rowH, h);
      colIndex++;
    }

    let maxW = 1;
    let maxH = 1;
    for (const p of placed.values()) {
      maxW = Math.max(maxW, p.x + p.w + G.pad);
      maxH = Math.max(maxH, p.y + p.h + G.pad);
    }
    return { out: placed, w: maxW, h: maxH };
  }

  function taskLayout(t, p) {
    const map = new Map();
    const left = p.x + G.inner;
    const top = p.y + G.head + G.inner;
    const right = p.x + p.w - G.inner;
    const cols = Math.max(1, Math.floor((right - left + G.taskGapX) / (G.taskW + G.taskGapX)));

    t.tasks.forEach((task, idx) => {
      const c = idx % cols;
      const r = Math.floor(idx / cols);
      const x = left + c * (G.taskW + G.taskGapX);
      const y = top + r * (G.taskH + G.taskGapY);
      map.set(taskId(task), { x, y, w: G.taskW, h: G.taskH, territoryId: t.id });
    });
    return map;
  }

  function edgeGeometry(edges, placements) {
    const out = [];
    const ports = new Map(Array.from(placements.keys(), k => [k, []]));
    for (const e of edges) {
      const a = placements.get(e.source);
      const b = placements.get(e.target);
      if (!a || !b) continue;
      const ac = { x: a.x + a.w / 2, y: a.y + a.h / 2 };
      const bc = { x: b.x + b.w / 2, y: b.y + b.h / 2 };
      const horizontal = Math.abs(bc.x - ac.x) >= Math.abs(bc.y - ac.y);
      const sp = horizontal ? { x: bc.x >= ac.x ? a.x + a.w : a.x, y: ac.y } : { x: ac.x, y: bc.y >= ac.y ? a.y + a.h : a.y };
      const tp = horizontal ? { x: bc.x >= ac.x ? b.x : b.x + b.w, y: bc.y } : { x: bc.x, y: bc.y >= ac.y ? b.y : b.y + b.h };
      const mx = (sp.x + tp.x) / 2;
      const my = (sp.y + tp.y) / 2;
      const path = horizontal ? `M ${sp.x} ${sp.y} L ${mx} ${sp.y} L ${mx} ${tp.y} L ${tp.x} ${tp.y}` : `M ${sp.x} ${sp.y} L ${sp.x} ${my} L ${tp.x} ${my} L ${tp.x} ${tp.y}`;
      out.push({ ...e, sp, tp, path });
      ports.get(e.source)?.push({ ...sp, direction: "out", edge: e });
      ports.get(e.target)?.push({ ...tp, direction: "in", edge: e });
    }
    return { out, ports };
  }

  function ensureGeometry() {
    const fp = `${state.semantic.delimiter}|${state.semantic.territories.map(t => `${t.id}:${t.tasks.length}`).join("|")}|${state.size.w}x${state.size.h}`;
    if (fp === state.geometry.fingerprint) return;
    const p = packFloorplan(state.semantic.territories);
    const tm = new Map();
    for (const t of state.semantic.territories) {
      const g = p.out.get(t.id);
      if (!g) continue;
      for (const [id, v] of taskLayout(t, g)) tm.set(id, v);
    }
    const eg = edgeGeometry(state.semantic.aggregateEdges, p.out);
    state.geometry = { fingerprint: fp, territory: p.out, task: tm, ports: eg.ports, edges: eg.out, w: p.w, h: p.h };
  }

  function hue(id) {
    const n = hash(id);
    const base = palette[n % palette.length];
    return { h: base[0], s: base[1], l: base[2] };
  }
  const color = (c, a = 1) => (a === 1 ? `hsl(${c.h} ${c.s}% ${c.l}%)` : `hsl(${c.h} ${c.s}% ${c.l}% / ${a})`);
  function levelFor(scale) {
    return scale <= Z.world ? LEVEL.world : scale <= Z.district ? LEVEL.district : scale <= Z.locality ? LEVEL.locality : LEVEL.detail;
  }

  function svg(name, attrs = {}) {
    const e = document.createElementNS(SVG, name);
    for (const [k, v] of Object.entries(attrs)) if (v != null) e.setAttribute(k, String(v));
    return e;
  }

  function ensureSurface() {
    let s = $("#surface-navigation");
    if (!s) {
      const parent = $(".surfaces") ?? $("main") ?? document.body;
      s = document.createElement("section");
      s.id = "surface-navigation";
      s.className = "surface niche-navigation-surface atlas-surface";
      s.dataset.surface = VIEW;
      s.hidden = true;
      parent.append(s);
    }
    s.innerHTML = `
      <div class="atlas-shell">
        <header class="atlas-header">
          <div class="atlas-brand">
            <span>SAVANT</span>
            <h1>ATLAS</h1>
          </div>
          <div class="atlas-commandbar">
            <input id="atlas-search" class="atlas-command-search" type="search" autocomplete="off" placeholder="Find work…" aria-label="Search Atlas">
            <button id="atlas-view-toggle" class="atlas-command" type="button">VIEW</button>
            <button id="atlas-filter-toggle" class="atlas-command" type="button">FILTER</button>
            <button id="atlas-fit" class="atlas-command" type="button">FIT</button>
            <button id="atlas-frontier" class="atlas-command atlas-command-frontier" type="button">NEXT</button>
            <select id="atlas-theme" class="atlas-theme-select" aria-label="Atlas theme"></select>
            <button id="atlas-rail-toggle" class="atlas-command" type="button">MORE</button>
          </div>
        </header>
        <main class="atlas-main">
          <div id="atlas-viewport" class="atlas-viewport" tabindex="0">
            <svg id="atlas-svg" class="atlas-svg" role="application">
              <defs id="atlas-defs"></defs>
              <g id="atlas-world">
                <g id="atlas-substrate"></g>
                <g id="atlas-corridors"></g>
                <g id="atlas-territories"></g>
                <g id="atlas-task-edges"></g>
                <g id="atlas-tasks"></g>
                <g id="atlas-overlays"></g>
              </g>
            </svg>
            <div class="atlas-map-zoom">
              <button id="atlas-plus" type="button" aria-label="Zoom in">+</button>
              <button id="atlas-minus" type="button" aria-label="Zoom out">−</button>
            </div>
            <div class="atlas-orientation">
              <strong id="atlas-level">WORLD</strong>
              <span id="atlas-zoom">100%</span>
            </div>
            <div id="atlas-breadcrumb" class="atlas-breadcrumb"></div>
            <div class="atlas-selected-strip">
              <div>
                <span>SELECTED WORK</span>
                <strong id="atlas-selected-title">No task selected</strong>
                <small id="atlas-selected-meta">Select a task on the floorplan.</small>
              </div>
              <div class="atlas-selected-actions">
                <button id="atlas-open-task" type="button">INSPECT</button>
                <button id="atlas-focus-task" type="button">FOCUS</button>
              </div>
            </div>
          </div>
          <aside class="atlas-rail" id="atlas-rail">
            <section class="atlas-panel">
              <div class="atlas-panel-heading"><h2>OVERALL TOPOLOGY</h2><span id="atlas-delimiter">objective</span></div>
              <svg id="atlas-minimap" class="atlas-minimap"></svg>
            </section>
            <section class="atlas-panel">
              <div class="atlas-panel-heading"><h2>VIEW LENSES</h2></div>
              <div id="atlas-lenses" class="atlas-lenses">
                <button data-lens="domains" class="active" type="button">FACILITY PLAN</button>
                <button data-lens="heatmap" type="button">ACTIVITY HEAT</button>
                <button data-lens="dependencies" type="button">CONDUITS</button>
              </div>
            </section>
            <section class="atlas-panel">
              <div class="atlas-panel-heading"><h2>FILTER</h2><button id="atlas-reset" type="button">RESET</button></div>
              <select id="atlas-status" class="atlas-command"><option value="all">All states</option><option value="ready">Ready</option><option value="active">Active</option><option value="blocked">Blocked</option><option value="complete">Complete</option></select>
            </section>
            <section class="atlas-panel">
              <div class="atlas-panel-heading"><h2>SELECTION DETAIL</h2></div>
              <div id="atlas-detail" class="atlas-detail"><p>Select a territory or task node.</p></div>
            </section>
          </aside>
        </main>
        <footer class="atlas-footer">
          <span>PROJECTION ONLY · AUTHORITY EFFECT: NONE</span>
          <span id="atlas-footer-status">ATLAS R11-RECONSTRUCTION</span>
        </footer>
      </div>`;
    return s;
  }

  function cache() {
    const ids = [
      "surface", "viewport", "svg", "defs", "world", "substrate", "corridors", "territories",
      "task-edges", "tasks", "overlays", "search", "theme", "rail", "rail-toggle", "view-toggle",
      "filter-toggle", "fit", "plus", "minus", "zoom", "level", "breadcrumb", "selected-title",
      "selected-meta", "open-task", "focus-task", "frontier", "minimap", "delimiter", "lenses",
      "status", "reset", "detail", "footer-status"
    ];
    for (const id of ids) dom[id.replace(/-([a-z])/g, (_, c) => c.toUpperCase())] = $("#atlas-" + id);
    dom.surface = $("#surface-navigation");
    dom.nav = $(`.nav [data-view="${VIEW}"]`);
  }

  function defs() {
    dom.defs.innerHTML = `
      <filter id="atlas-glow" x="-30%" y="-30%" width="160%" height="160%"><feGaussianBlur stdDeviation="5" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
      <pattern id="atlas-grid" width="48" height="48" patternUnits="userSpaceOnUse"><path d="M48 0H0V48" fill="none" stroke="rgba(85,216,255,0.1)" stroke-width="1"/></pattern>
      <marker id="atlas-arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto"><path d="M0 0L10 5L0 10z" fill="rgba(85,216,255,0.7)"/></marker>`;
  }

  function measure() {
    const r = dom.viewport?.getBoundingClientRect();
    if (!r || r.width < 100 || r.height < 100) return false;
    state.size = { w: r.width, h: r.height };
    dom.svg.setAttribute("viewBox", `0 0 ${r.width} ${r.height}`);
    return true;
  }

  function filtered(t) {
    const s = taskState(t);
    if (state.status !== "all" && s !== state.status) return false;
    const q = low(state.query);
    if (!q) return true;
    return [taskTitle(t), taskId(t), taskObjective(t), taskDomain(t)].some(v => low(v).includes(q));
  }

  function applyTransform() {
    dom.world.setAttribute("transform", `translate(${state.viewport.x} ${state.viewport.y}) scale(${state.viewport.scale})`);
    dom.zoom.textContent = `${Math.round(state.viewport.scale * 100)}%`;
    dom.level.textContent = state.level.toUpperCase();
  }

  function queueTransform() {
    if (state.transformQueued) return;
    state.transformQueued = true;
    requestAnimationFrame(() => {
      state.transformQueued = false;
      applyTransform();
      renderMiniViewport();
    });
  }

  function setViewport(v) {
    const oldLevel = state.level;
    state.viewport = {
      x: Number.isFinite(v.x) ? v.x : state.viewport.x,
      y: Number.isFinite(v.y) ? v.y : state.viewport.y,
      scale: clamp(Number.isFinite(v.scale) ? v.scale : state.viewport.scale, Z.min, Z.max)
    };
    state.level = levelFor(state.viewport.scale);
    swrite();
    if (oldLevel !== state.level) queueRender();
    else queueTransform();
  }

  function fitBounds(b) {
    if (!measure()) return;
    const pad = 48;
    const scale = clamp(Math.min((state.size.w - pad * 2) / Math.max(1, b.w), (state.size.h - pad * 2) / Math.max(1, b.h)), Z.min, Z.max);
    setViewport({
      x: (state.size.w - b.w * scale) / 2 - b.x * scale,
      y: (state.size.h - b.h * scale) / 2 - b.y * scale,
      scale
    });
  }

  const fitWorld = () => fitBounds({ x: 0, y: 0, w: state.geometry.w, h: state.geometry.h });

  function renderSubstrate() {
    const f = document.createDocumentFragment();
    f.append(svg("rect", { x: 0, y: 0, width: state.geometry.w, height: state.geometry.h, class: "atlas-world-bg" }));
    for (const p of state.geometry.territory.values()) {
      f.append(
        svg("rect", { x: p.x - 14, y: p.y - 14, width: p.w + 28, height: p.h + 28, rx: 8, class: "atlas-concourse-pad" }),
        svg("rect", { x: p.x - 6, y: p.y - 6, width: p.w + 12, height: p.h + 12, rx: 4, class: "atlas-concourse-seam" })
      );
    }
    f.append(svg("rect", { x: 0, y: 0, width: state.geometry.w, height: state.geometry.h, fill: "url(#atlas-grid)", class: "atlas-world-grid" }));
    dom.substrate.replaceChildren(f);
  }

  function renderCorridors() {
    const f = document.createDocumentFragment();
    for (const e of state.geometry.edges) {
      f.append(
        svg("path", { d: e.path, class: "atlas-corridor-base" }),
        svg("path", { d: e.path, class: "atlas-corridor", "marker-end": "url(#atlas-arrow)" })
      );
    }
    dom.corridors.replaceChildren(f);
  }

  function renderTerritories() {
    const f = document.createDocumentFragment();
    for (const t of state.semantic.territories) {
      const p = state.geometry.territory.get(t.id);
      if (!p) continue;
      const c = hue(t.id);
      const g = svg("g", { class: "atlas-territory", "data-territory-id": t.id, role: "button", tabindex: 0 });
      g.style.setProperty("--tc", color(c));

      if (state.focusTerritory === t.id) g.classList.add("focused");
      if (state.selected && state.semantic.taskToTerritory.get(state.selected) === t.id) g.classList.add("selected-territory");

      const inset = factor => p.points.map(([x, y]) => {
        const cx = p.x + p.w / 2, cy = p.y + p.h / 2;
        return [cx + (x - cx) * factor, cy + (y - cy) * factor];
      });

      g.append(
        svg("polygon", { points: pstr(p.points), class: "atlas-territory-outer" }),
        svg("polygon", { points: pstr(inset(0.96)), class: "atlas-territory-seam" }),
        svg("polygon", { points: pstr(inset(0.92)), class: "atlas-territory-inner" })
      );

      const title = svg("text", { x: p.x + 28, y: p.y + 36, class: "atlas-territory-title" });
      title.textContent = t.label;

      const meta = svg("text", { x: p.x + 28, y: p.y + 54, class: "atlas-territory-meta" });
      meta.textContent = `${t.statistics.total} UNITS · ${t.statistics.ready} READY · ${t.statistics.blocked} BLOCKED`;

      const count = svg("text", { x: p.x + p.w - 34, y: p.y + 38, class: "atlas-territory-count", "text-anchor": "middle" });
      count.textContent = String(t.statistics.total);

      g.append(
        title,
        meta,
        svg("circle", { cx: p.x + p.w - 34, cy: p.y + 34, r: 16, class: "atlas-territory-count-circle" }),
        count
      );

      f.append(g);
    }
    dom.territories.replaceChildren(f);
  }

  function renderTasks() {
    if (state.level === LEVEL.world) {
      dom.tasks.replaceChildren();
      dom.taskEdges.replaceChildren();
      return;
    }
    const f = document.createDocumentFragment();
    const ef = document.createDocumentFragment();
    const rec = recommendationId(coreProjection());

    for (const t of state.semantic.tasks) {
      const id = taskId(t);
      if (!filtered(t)) continue;
      const p = state.geometry.task.get(id);
      if (!p) continue;

      const g = svg("g", {
        class: `atlas-task atlas-task-${taskState(t)}`,
        "data-task-id": id,
        transform: `translate(${p.x} ${p.y})`
      });

      if (id === state.selected) g.classList.add("selected");
      if (id === rec) g.classList.add("frontier");

      g.append(
        svg("rect", { width: p.w, height: p.h, rx: 4, class: "atlas-task-body" }),
        svg("rect", { x: 8, y: p.h / 2 - 5, width: 10, height: 10, rx: 2, class: "atlas-task-glyph" })
      );

      const title = svg("text", { x: 26, y: 22, class: "atlas-task-title" });
      title.textContent = taskTitle(t).slice(0, 24);

      const meta = svg("text", { x: 26, y: 40, class: "atlas-task-meta" });
      meta.textContent = `${taskState(t)} · ${taskPriority(t)}`;

      g.append(title, meta);
      f.append(g);

      for (const depId of taskDependencies(t)) {
        const sourceP = state.geometry.task.get(depId);
        if (!sourceP) continue;
        const sx = sourceP.x + sourceP.w;
        const sy = sourceP.y + sourceP.h / 2;
        const tx = p.x;
        const ty = p.y + p.h / 2;
        ef.append(svg("path", { d: `M ${sx} ${sy} L ${(sx + tx) / 2} ${sy} L ${(sx + tx) / 2} ${ty} L ${tx} ${ty}`, class: "atlas-task-edge" }));
      }
    }
    dom.tasks.replaceChildren(f);
    dom.taskEdges.replaceChildren(ef);
  }

  function renderMinimap() {
    dom.minimap.replaceChildren();
    dom.minimap.setAttribute("viewBox", `0 0 ${state.geometry.w} ${state.geometry.h}`);
    for (const t of state.semantic.territories) {
      const p = state.geometry.territory.get(t.id);
      if (!p) continue;
      const x = svg("polygon", { points: pstr(p.points) });
      x.style.fill = color(hue(t.id), 0.45);
      dom.minimap.append(x);
    }
    renderMiniViewport();
  }

  function renderMiniViewport() {
    $(".atlas-mini-viewport", dom.minimap)?.remove();
    const s = state.viewport.scale;
    dom.minimap.append(
      svg("rect", {
        x: -state.viewport.x / s,
        y: -state.viewport.y / s,
        width: state.size.w / s,
        height: state.size.h / s,
        class: "atlas-mini-viewport"
      })
    );
  }

  function renderAll() {
    if (!state.ready) return;
    renderSubstrate();
    renderCorridors();
    renderTerritories();
    renderTasks();
    renderMinimap();
    applyTransform();

    const t = state.semantic.taskById.get(state.selected);
    if (t) {
      dom.selectedTitle.textContent = taskTitle(t);
      dom.selectedMeta.textContent = `${taskState(t)} · ${taskPriority(t)} · ${taskObjective(t)}`;
      dom.detail.innerHTML = `<p><strong>${taskTitle(t)}</strong></p><p>State: ${taskState(t)}</p><p>Objective: ${taskObjective(t)}</p>`;
    } else {
      dom.selectedTitle.textContent = "No task selected";
      dom.selectedMeta.textContent = "Select a task on the floorplan.";
      dom.detail.innerHTML = `<p>Select a territory or task node.</p>`;
    }
  }

  function queueRender() {
    if (state.renderQueued) return;
    state.renderQueued = true;
    requestAnimationFrame(() => {
      state.renderQueued = false;
      renderAll();
    });
  }

  function select(id) {
    state.selected = id;
    state.focusTerritory = state.semantic.taskToTerritory.get(id) ?? null;
    queueRender();
    window.Niche?.task?.(id);
    emit("selection", { task_id: id });
  }

  function bindControls() {
    dom.fit.onclick = fitWorld;
    dom.plus.onclick = () => setViewport({ scale: state.viewport.scale * Z.step });
    dom.minus.onclick = () => setViewport({ scale: state.viewport.scale / Z.step });
    dom.railToggle.onclick = () => dom.rail.classList.toggle("open");
    dom.frontier.onclick = () => {
      const rec = recommendationId(coreProjection());
      if (rec) select(rec);
    };
    dom.openTask.onclick = () => {
      if (state.selected) window.Niche?.task?.(state.selected);
    };
    dom.focusTask.onclick = () => {
      const p = state.geometry.task.get(state.selected);
      if (p) {
        setViewport({
          x: state.size.w / 2 - (p.x + p.w / 2) * 1.5,
          y: state.size.h / 2 - (p.y + p.h / 2) * 1.5,
          scale: 1.5
        });
      }
    };

    dom.search.addEventListener("input", () => {
      state.query = dom.search.value.trim();
      queueRender();
    });

    dom.status.onchange = () => {
      state.status = dom.status.value;
      queueRender();
    };

    dom.reset.onclick = () => {
      state.query = "";
      state.status = "all";
      dom.search.value = "";
      dom.status.value = "all";
      queueRender();
    };

    // Viewport Panning / Zooming
    const begin = e => {
      if (e.target.closest("button, input, select")) return;
      state.pointer.mode = "candidate";
      state.pointer.sx = e.clientX;
      state.pointer.sy = e.clientY;
      state.pointer.ox = state.viewport.x;
      state.pointer.oy = state.viewport.y;
      state.gestureMoved = false;
      dom.viewport.setPointerCapture?.(e.pointerId);
    };

    const move = e => {
      if (!state.pointer.mode) return;
      const dx = e.clientX - state.pointer.sx;
      const dy = e.clientY - state.pointer.sy;
      if (state.pointer.mode === "candidate" && Math.hypot(dx, dy) >= 5) {
        state.pointer.mode = "pan";
        state.gestureMoved = true;
      }
      if (state.pointer.mode === "pan") {
        setViewport({ x: state.pointer.ox + dx, y: state.pointer.oy + dy, scale: state.viewport.scale });
      }
    };

    const done = e => {
      state.pointer.mode = "";
      try { dom.viewport.releasePointerCapture?.(e.pointerId); } catch {}
    };

    dom.viewport.addEventListener("pointerdown", begin, { capture: true });
    window.addEventListener("pointermove", move, { capture: true });
    window.addEventListener("pointerup", done, { capture: true });

    dom.viewport.addEventListener("wheel", e => {
      e.preventDefault();
      const next = clamp(state.viewport.scale * Math.exp(-e.deltaY * 0.0012), Z.min, Z.max);
      setViewport({ scale: next });
    }, { passive: false });

    dom.viewport.addEventListener("click", e => {
      if (state.gestureMoved) return;
      const t = e.target.closest("[data-task-id]");
      if (t?.dataset.taskId) return select(t.dataset.taskId);
      const terr = e.target.closest("[data-territory-id]");
      if (terr?.dataset.territoryId) {
        state.focusTerritory = terr.dataset.territoryId;
        queueRender();
      }
    });
  }

  function sync() {
    const p = coreProjection();
    if (!p) return;
    const n = normalized(p);
    state.semantic = buildSemantic(n);
    state.ready = true;
    ensureGeometry();
    queueRender();
    if (!state.firstFit && measure()) {
      state.firstFit = true;
      fitWorld();
    }
  }

  function open() {
    install();
    state.active = true;
    dom.surface.hidden = false;
    dom.surface.classList.add("active");
    for (const s of $$(".surface")) if (s !== dom.surface) s.classList.remove("active");
    for (const b of $$(".nav [data-view]")) b.classList.toggle("active", b.dataset.view === VIEW);
    sync();
  }

  function install() {
    if (state.installed) return true;
    ensureSurface();
    cache();
    defs();
    bindControls();
    measure();
    window.addEventListener("niche:projection", sync);
    state.installed = true;
    sync();
    return true;
  }

  window.NicheAtlas = Object.freeze({
    open,
    select,
    fit: fitWorld,
    sync,
    state: () => Object.freeze({
      build: BUILD_VERSION,
      installed: state.installed,
      active: state.active,
      ready: state.ready,
      selectedTaskId: state.selected
    })
  });

  window.NicheNavigation = window.NicheAtlas;

  document.readyState === "loading" ? document.addEventListener("DOMContentLoaded", install, { once: true }) : install();
})();
