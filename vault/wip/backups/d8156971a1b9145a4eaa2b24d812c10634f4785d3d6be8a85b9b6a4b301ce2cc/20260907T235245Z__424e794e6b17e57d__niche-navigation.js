"use strict";

/*
 * savant / niche / atlas
 * asset: niche-navigation.js
 * owner: exile:niche
 * authority_effect: none
 * projection_only: true
 * build: r12-nav-resilient
 */

(() => {
  const BUILD_VERSION = "r12-nav-resilient";
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
    viewport: { x: 0, y: 0, scale: 1 },
    size: { w: 1, h: 1 },
    semantic: { delimiter: "objective", tasks: [], taskById: new Map(), dependents: new Map(), territories: [], territoryById: new Map(), taskToTerritory: new Map(), aggregateEdges: [] },
    geometry: { fingerprint: "", territory: new Map(), task: new Map(), ports: new Map(), edges: [], w: 1, h: 1 },
    pointer: { active: new Map(), mode: "", sx: 0, sy: 0, ox: 0, oy: 0 },
    firstFit: false
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

  function normalized(p) {
    const tasks = arr(p?.source?.tasks).filter(t => taskId(t)).slice().sort((a, b) => taskId(a).localeCompare(taskId(b)));
    const tm = p?.normalized?.taskById instanceof Map ? new Map(p.normalized.taskById) : new Map(tasks.map(t => [taskId(t), t]));
    const dep = new Map(tasks.map(t => [taskId(t), []]));
    for (const t of tasks) for (const d of taskDependencies(t)) dep.get(d)?.push(taskId(t));
    return {
      tasks,
      taskById: tm,
      dependents: dep,
      selected: txt(p?.normalized?.selectedTaskId) || null,
      recommended: txt(p?.normalized?.recommendedTaskId ?? coreState()?.recommendedTaskId) || null
    };
  }

  const delimiters = [
    ["domain", taskDomain, 5],
    ["rubric", taskRubric, 4],
    ["cabal", taskCabal, 3],
    ["objective", taskObjective, 2],
    ["owner", taskOwner, 1]
  ];

  function chooseDelimiter(tasks) {
    const scored = delimiters
      .map(([id, get, pref]) => {
        const vals = tasks.map(get).filter(Boolean);
        const n = new Set(vals).size;
        const coverage = vals.length / Math.max(1, tasks.length);
        return { id, get, pref, n, coverage, score: coverage * 0.6 + (n >= 2 ? 0.3 : 0) + pref * 0.02 };
      })
      .filter(x => x.coverage >= 0.5 && x.n >= 1)
      .sort((a, b) => b.score - a.score || a.id.localeCompare(b.id));
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
        tasks: x.tasks.slice().sort((a, b) => taskTitle(a).localeCompare(taskTitle(b))),
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
        if (!agg.has(key)) agg.set(key, { id: key, source: st, target: tt, count: 0 });
        agg.get(key).count++;
      }
    }
    return { delimiter: d.id, tasks: n.tasks, taskById: n.taskById, dependents: n.dependents, territories, territoryById, taskToTerritory, aggregateEdges: Array.from(agg.values()) };
  }

  function polygon(x, y, w, h, shape) {
    const c = Math.max(32, Math.min(w, h) * 0.15);
    const i = Math.max(64, Math.min(w, h) * 0.25);
    const p = {
      rect: [[x + c, y], [x + w - c, y], [x + w, y + c], [x + w, y + h - c], [x + w - c, y + h], [x + c, y + h], [x, y + h - c], [x, y + c]],
      "l-right": [[x + c, y], [x + w - c, y], [x + w, y + c], [x + w, y + h - i], [x + w - i, y + h - i], [x + w - i, y + h], [x + c, y + h], [x, y + h - c], [x, y + c]],
      "l-left": [[x + c, y], [x + w - c, y], [x + w, y + c], [x + w, y + h - c], [x + w - c, y + h], [x + i, y + h], [x + i, y + h - i], [x, y + h - i], [x, y + c]],
      u: [[x + c, y], [x + w - c, y], [x + w, y + c], [x + w, y + h - c], [x + w - c, y + h], [x + w * 0.65, y + h], [x + w * 0.65, y + h - i], [x + w * 0.35, y + h - i], [x + w * 0.35, y + h], [x + c, y + h], [x, y + h - c], [x, y + c]]
    };
    return p[shape] ?? p.rect;
  }

  const pstr = p => p.map(([x, y]) => `${Math.round(x)},${Math.round(y)}`).join(" ");

  function packFloorplan(territories) {
    const placed = new Map();
    const shapes = ["rect", "l-right", "l-left", "u"];

    let cols = Math.max(2, Math.min(4, Math.ceil(Math.sqrt(territories.length || 1))));
    let curX = G.pad;
    let curY = G.pad;
    let rowH = 0;
    let colIndex = 0;

    for (let i = 0; i < territories.length; i++) {
      const t = territories[i];
      const shape = shapes[(hash(t.id) + i) % shapes.length];
      const taskCount = t.tasks.length;
      const w = Math.max(G.minW, 400 + Math.min(450, taskCount * 12));
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
    for (const e of edges) {
      const a = placements.get(e.source);
      const b = placements.get(e.target);
      if (!a || !b) continue;
      const ac = { x: a.x + a.w / 2, y: a.y + a.h / 2 };
      const bc = { x: b.x + b.w / 2, y: b.y + b.h / 2 };
      const mx = (ac.x + bc.x) / 2;
      const path = `M ${ac.x} ${ac.y} L ${mx} ${ac.y} L ${mx} ${bc.y} L ${bc.x} ${bc.y}`;
      out.push({ ...e, path });
    }
    return out;
  }

  function ensureGeometry() {
    const fp = `${state.semantic.delimiter}|${state.semantic.territories.map(t => `${t.id}:${t.tasks.length}`).join("|")}`;
    if (fp === state.geometry.fingerprint) return;
    const p = packFloorplan(state.semantic.territories);
    const tm = new Map();
    for (const t of state.semantic.territories) {
      const g = p.out.get(t.id);
      if (!g) continue;
      for (const [id, v] of taskLayout(t, g)) tm.set(id, v);
    }
    state.geometry = { fingerprint: fp, territory: p.out, task: tm, edges: edgeGeometry(state.semantic.aggregateEdges, p.out), w: p.w, h: p.h };
  }

  function hue(id) {
    const n = hash(id);
    const base = palette[n % palette.length];
    return { h: base[0], s: base[1], l: base[2] };
  }
  const color = (c, a = 1) => (a === 1 ? `hsl(${c.h} ${c.s}% ${c.l}%)` : `hsl(${c.h} ${c.s}% ${c.l}% / ${a})`);

  function svg(name, attrs = {}) {
    const e = document.createElementNS(SVG, name);
    for (const [k, v] of Object.entries(attrs)) if (v != null) e.setAttribute(k, String(v));
    return e;
  }

  function ensureNavButton() {
    let nav = $(".nav");
    if (!nav) nav = $(".topbar");
    if (!nav) return;

    let b = $(`[data-view="${VIEW}"]`);
    if (!b) {
      b = document.createElement("button");
      b.type = "button";
      b.dataset.view = VIEW;
      b.textContent = "ATLAS";
      b.className = "nav-button";
      const causal = $('[data-view="causal"]');
      if (causal && causal.parentElement === nav) {
        nav.insertBefore(b, causal);
      } else {
        nav.append(b);
      }
    }
    b.onclick = () => open();
    dom.nav = b;
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
            <input id="atlas-search" class="atlas-command-search" type="search" placeholder="Find work…" aria-label="Search Atlas">
            <button id="atlas-fit" class="atlas-command" type="button">FIT</button>
            <button id="atlas-frontier" class="atlas-command atlas-command-frontier" type="button">NEXT</button>
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
              </g>
            </svg>
            <div class="atlas-map-zoom">
              <button id="atlas-plus" type="button">+</button>
              <button id="atlas-minus" type="button">−</button>
            </div>
            <div class="atlas-orientation">
              <strong id="atlas-level">WORLD</strong>
              <span id="atlas-zoom">100%</span>
            </div>
            <div class="atlas-selected-strip">
              <div>
                <span>SELECTED WORK</span>
                <strong id="atlas-selected-title">No task selected</strong>
                <small id="atlas-selected-meta">Select a task on the floorplan.</small>
              </div>
              <div class="atlas-selected-actions">
                <button id="atlas-open-task" type="button">INSPECT</button>
              </div>
            </div>
            <div id="atlas-state-overlay" class="atlas-state" hidden></div>
          </div>
          <aside class="atlas-rail" id="atlas-rail">
            <section class="atlas-panel">
              <div class="atlas-panel-heading"><h2>OVERALL TOPOLOGY</h2><span id="atlas-delimiter">objective</span></div>
              <svg id="atlas-minimap" class="atlas-minimap"></svg>
            </section>
            <section class="atlas-panel">
              <div class="atlas-panel-heading"><h2>DETAIL</h2></div>
              <div id="atlas-detail" class="atlas-detail"><p>Select a territory or task node.</p></div>
            </section>
          </aside>
        </main>
        <footer class="atlas-footer">
          <span>PROJECTION ONLY · AUTHORITY EFFECT: NONE</span>
          <span id="atlas-footer-status">ATLAS R12-RESILIENT</span>
        </footer>
      </div>`;
    return s;
  }

  function cache() {
    const ids = [
      "surface", "viewport", "svg", "defs", "world", "substrate", "corridors", "territories",
      "task-edges", "tasks", "search", "rail", "rail-toggle", "fit", "plus", "minus", "zoom",
      "level", "selected-title", "selected-meta", "open-task", "frontier", "minimap",
      "delimiter", "detail", "footer-status", "state-overlay"
    ];
    for (const id of ids) dom[id.replace(/-([a-z])/g, (_, c) => c.toUpperCase())] = $("#atlas-" + id);
    dom.surface = $("#surface-navigation");
  }

  function defs() {
    dom.defs.innerHTML = `
      <pattern id="atlas-grid" width="48" height="48" patternUnits="userSpaceOnUse"><path d="M48 0H0V48" fill="none" stroke="rgba(85,216,255,0.08)" stroke-width="1"/></pattern>
      <marker id="atlas-arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto"><path d="M0 0L10 5L0 10z" fill="rgba(85,216,255,0.7)"/></marker>`;
  }

  function measure() {
    const r = dom.viewport?.getBoundingClientRect();
    if (!r || r.width < 50 || r.height < 50) return false;
    state.size = { w: r.width, h: r.height };
    dom.svg.setAttribute("viewBox", `0 0 ${r.width} ${r.height}`);
    return true;
  }

  function applyTransform() {
    dom.world.setAttribute("transform", `translate(${state.viewport.x} ${state.viewport.y}) scale(${state.viewport.scale})`);
    dom.zoom.textContent = `${Math.round(state.viewport.scale * 100)}%`;
    dom.level.textContent = state.level.toUpperCase();
  }

  function setViewport(v) {
    state.viewport = {
      x: Number.isFinite(v.x) ? v.x : state.viewport.x,
      y: Number.isFinite(v.y) ? v.y : state.viewport.y,
      scale: clamp(Number.isFinite(v.scale) ? v.scale : state.viewport.scale, Z.min, Z.max)
    };
    state.level = state.viewport.scale <= Z.world ? LEVEL.world : state.viewport.scale <= Z.district ? LEVEL.district : LEVEL.detail;
    applyTransform();
  }

  function fitWorld() {
    if (!measure() || state.geometry.w <= 1) return;
    const pad = 40;
    const scale = clamp(Math.min((state.size.w - pad * 2) / state.geometry.w, (state.size.h - pad * 2) / state.geometry.h), Z.min, Z.max);
    setViewport({
      x: (state.size.w - state.geometry.w * scale) / 2,
      y: (state.size.h - state.geometry.h * scale) / 2,
      scale
    });
  }

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
      f.append(svg("path", { d: e.path, class: "atlas-corridor", "marker-end": "url(#atlas-arrow)" }));
    }
    dom.corridors.replaceChildren(f);
  }

  function renderTerritories() {
    const f = document.createDocumentFragment();
    for (const t of state.semantic.territories) {
      const p = state.geometry.territory.get(t.id);
      if (!p) continue;
      const c = hue(t.id);
      const g = svg("g", { class: "atlas-territory", "data-territory-id": t.id });
      g.style.setProperty("--tc", color(c));

      g.append(
        svg("polygon", { points: pstr(p.points), class: "atlas-territory-outer" }),
        svg("polygon", { points: pstr(p.points), class: "atlas-territory-inner", transform: "scale(0.95)", "transform-origin": `${p.x + p.w / 2} ${p.y + p.h / 2}` })
      );

      const title = svg("text", { x: p.x + 24, y: p.y + 36, class: "atlas-territory-title" });
      title.textContent = t.label;

      const meta = svg("text", { x: p.x + 24, y: p.y + 54, class: "atlas-territory-meta" });
      meta.textContent = `${t.statistics.total} TASKS · ${t.statistics.ready} READY`;

      g.append(title, meta);
      f.append(g);
    }
    dom.territories.replaceChildren(f);
  }

  function renderTasks() {
    const f = document.createDocumentFragment();
    for (const t of state.semantic.tasks) {
      const id = taskId(t);
      const p = state.geometry.task.get(id);
      if (!p) continue;

      const g = svg("g", { class: `atlas-task atlas-task-${taskState(t)}`, "data-task-id": id, transform: `translate(${p.x} ${p.y})` });
      if (id === state.selected) g.classList.add("selected");

      g.append(svg("rect", { width: p.w, height: p.h, rx: 4, class: "atlas-task-body" }));

      const title = svg("text", { x: 12, y: 22, class: "atlas-task-title" });
      title.textContent = taskTitle(t).slice(0, 24);

      const meta = svg("text", { x: 12, y: 40, class: "atlas-task-meta" });
      meta.textContent = `${taskState(t)} · ${taskPriority(t)}`;

      g.append(title, meta);
      f.append(g);
    }
    dom.tasks.replaceChildren(f);
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
  }

  function renderAll() {
    if (!state.semantic.tasks.length) {
      dom.stateOverlay.hidden = false;
      dom.stateOverlay.innerHTML = "<strong>Task projection unavailable</strong><p>Waiting for authoritative backend connection or active task projection.</p>";
      return;
    }
    dom.stateOverlay.hidden = true;
    renderSubstrate();
    renderCorridors();
    renderTerritories();
    renderTasks();
    renderMinimap();
    applyTransform();
  }

  function select(id) {
    state.selected = id;
    renderAll();
    window.Niche?.task?.(id);
  }

  function bindControls() {
    dom.fit.onclick = fitWorld;
    dom.plus.onclick = () => setViewport({ scale: state.viewport.scale * Z.step });
    dom.minus.onclick = () => setViewport({ scale: state.viewport.scale / Z.step });
    dom.railToggle.onclick = () => dom.rail.classList.toggle("open");

    const begin = e => {
      if (e.target.closest("button, input, select")) return;
      state.pointer.mode = "pan";
      state.pointer.sx = e.clientX;
      state.pointer.sy = e.clientY;
      state.pointer.ox = state.viewport.x;
      state.pointer.oy = state.viewport.y;
      dom.viewport.setPointerCapture?.(e.pointerId);
    };

    const move = e => {
      if (state.pointer.mode !== "pan") return;
      const dx = e.clientX - state.pointer.sx;
      const dy = e.clientY - state.pointer.sy;
      setViewport({ x: state.pointer.ox + dx, y: state.pointer.oy + dy, scale: state.viewport.scale });
    };

    const done = e => {
      state.pointer.mode = "";
      try { dom.viewport.releasePointerCapture?.(e.pointerId); } catch {}
    };

    dom.viewport.addEventListener("pointerdown", begin, { capture: true });
    window.addEventListener("pointermove", move, { capture: true });
    window.addEventListener("pointerup", done, { capture: true });

    dom.viewport.addEventListener("click", e => {
      const t = e.target.closest("[data-task-id]");
      if (t?.dataset.taskId) select(t.dataset.taskId);
    });
  }

  function sync() {
    ensureNavButton();
    const p = coreProjection();
    if (!p || !p.source?.tasks) {
      renderAll();
      return;
    }
    const n = normalized(p);
    state.semantic = buildSemantic(n);
    ensureGeometry();
    renderAll();
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
    for (const b of $$(".nav button, .topbar button")) b.classList.toggle("active", b.dataset.view === VIEW);
    sync();
  }

  function install() {
    if (state.installed) return true;
    ensureNavButton();
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
      active: state.active
    })
  });
  window.NicheNavigation = window.NicheAtlas;

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", install, { once: true });
  } else {
    install();
  }
  // Periodically ensure nav button is not lost during client-side redraws
  setInterval(ensureNavButton, 1000);
})();
