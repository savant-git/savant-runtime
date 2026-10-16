"use strict";
/**
 * SAVANT / NICHE / ATLAS — SIMPLIFIED RECONSTRUCTION CONTROLLER
 * Build: atlas-v2026.ultimate-simplified
 * Authority Effect: none (Projection-Only Interface)
 */
(() => {
  const BUILD = "atlas-v2026.ultimate-simplified";
  const SVG_NS = "http://www.w3.org/2000/svg";
  const VIEW = "navigation";
  const Z_LEVELS = Object.freeze({ min: 0.12, max: 4.8, world: 0.52, district: 1.05, locality: 1.95, step: 1.25 });
  const GEO = Object.freeze({ pad: 48, gap: 32, head: 72, inner: 20, taskW: 210, taskH: 54, minW: 460, minH: 300 });

  const PALETTE = Object.freeze([
    { h: 194, s: 94, l: 56 }, { h: 218, s: 92, l: 62 }, { h: 268, s: 86, l: 68 },
    { h: 322, s: 84, l: 64 }, { h: 12, s: 90, l: 60 },  { h: 38, s: 96, l: 58 },
    { h: 148, s: 84, l: 52 }, { h: 168, s: 88, l: 50 }, { h: 284, s: 80, l: 66 }
  ]);

  const state = {
    installed: false, active: false, ready: false,
    selected: null, lens: "domains", query: "",
    viewport: { x: 0, y: 0, scale: 1 },
    semantic: { delimiter: "objective", tasks: [], taskById: new Map(), dependents: new Map(), territories: [], edges: [] },
    geometry: { territory: new Map(), task: new Map(), conduits: [], w: 1, h: 1 },
    pointer: { active: new Map(), sx: 0, sy: 0, ox: 0, oy: 0, moved: false }
  };

  const dom = Object.create(null);
  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => Array.from(r.querySelectorAll(s));
  const clamp = (v, a, b) => Math.min(b, Math.max(a, v));
  const txt = (v, f = "") => (v == null ? f : (String(v).trim() || f));
  const low = v => txt(v).toLowerCase();
  const arr = v => (Array.isArray(v) ? v : []);

  // Web Audio Spatial Feedback
  let audioCtx = null;
  function triggerSound(type = "tick") {
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
        osc.frequency.setValueAtTime(800, now);
        osc.frequency.exponentialRampToValueAtTime(350, now + 0.025);
        gain.gain.setValueAtTime(0.015, now);
        gain.gain.linearRampToValueAtTime(0, now + 0.025);
        osc.start(now); osc.stop(now + 0.025);
      } else if (type === "warp") {
        osc.frequency.setValueAtTime(220, now);
        osc.frequency.exponentialRampToValueAtTime(650, now + 0.07);
        gain.gain.setValueAtTime(0.03, now);
        gain.gain.linearRampToValueAtTime(0, now + 0.07);
        osc.start(now); osc.stop(now + 0.07);
      }
    } catch {}
  }

  const coreProj = () => { try { return window.Niche?.projection?.() ?? null; } catch { return null; } };
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

  function transformProjection(projection) {
    const raw = arr(projection?.source?.tasks).filter(t => taskId(t)).sort((a, b) => taskId(a).localeCompare(taskId(b)));
    const taskById = new Map();
    const dependents = new Map();
    for (const t of raw) {
      taskById.set(taskId(t), t);
      dependents.set(taskId(t), []);
    }
    for (const t of raw) {
      const id = taskId(t);
      for (const d of taskDeps(t)) dependents.get(d)?.push(id);
    }

    const groups = new Map();
    for (const t of raw) {
      const obj = taskObjective(t);
      if (!groups.has(obj)) groups.set(obj, { id: `obj:${obj}`, label: obj, tasks: [] });
      groups.get(obj).tasks.push(t);
    }

    const territories = Array.from(groups.values()).map(g => {
      const stats = { total: g.tasks.length, complete: 0, ready: 0, active: 0, blocked: 0, waiting: 0 };
      for (const t of g.tasks) {
        const s = taskState(t);
        if (s in stats) stats[s]++;
      }
      return { ...g, statistics: stats };
    }).sort((a, b) => b.tasks.length - a.tasks.length || a.label.localeCompare(b.label));

    const taskToTerritory = new Map();
    for (const terr of territories) {
      for (const t of terr.tasks) taskToTerritory.set(taskId(t), terr.id);
    }

    const edgeMap = new Map();
    for (const t of raw) {
      const target = taskId(t);
      const tt = taskToTerritory.get(target);
      for (const source of taskDeps(t)) {
        const st = taskToTerritory.get(source);
        if (!st || !tt || st === tt) continue;
        const key = `${st}→${tt}`;
        if (!edgeMap.has(key)) edgeMap.set(key, { id: key, source: st, target: tt, count: 0 });
        edgeMap.get(key).count++;
      }
    }

    return {
      tasks: raw,
      taskById,
      dependents,
      territories,
      taskToTerritory,
      edges: Array.from(edgeMap.values()),
      recommended: txt(projection?.normalized?.recommendedTaskId)
    };
  }

  function computeLayout(semantic) {
    const placed = new Map();
    let cx = GEO.pad, cy = GEO.pad, rowH = 0;
    const targetRowW = Math.max(1600, Math.ceil(Math.sqrt(semantic.territories.length) * 580));

    for (const t of semantic.territories) {
      const cols = Math.max(2, Math.min(5, Math.ceil(Math.sqrt(t.tasks.length))));
      const rows = Math.ceil(t.tasks.length / cols);
      const w = Math.max(GEO.minW, cols * (GEO.taskW + 16) + GEO.inner * 2);
      const h = Math.max(GEO.minH, GEO.head + rows * (GEO.taskH + 14) + GEO.inner * 2);

      if (cx + w > targetRowW && cx > GEO.pad) {
        cx = GEO.pad;
        cy += rowH + GEO.gap;
        rowH = 0;
      }
      placed.set(t.id, { id: t.id, x: cx, y: cy, w, h });
      cx += w + GEO.gap;
      rowH = Math.max(rowH, h);
    }

    let worldW = 1, worldH = 1;
    for (const p of placed.values()) {
      worldW = Math.max(worldW, p.x + p.w + GEO.pad);
      worldH = Math.max(worldH, p.y + p.h + GEO.pad);
    }

    const tasksGeom = new Map();
    for (const t of semantic.territories) {
      const tp = placed.get(t.id);
      if (!tp) continue;
      const left = tp.x + GEO.inner;
      const top = tp.y + GEO.head + 10;
      const cols = Math.max(1, Math.floor((tp.w - GEO.inner * 2) / (GEO.taskW + 16)));

      t.tasks.forEach((task, idx) => {
        const c = idx % cols;
        const r = Math.floor(idx / cols);
        tasksGeom.set(taskId(task), {
          x: left + c * (GEO.taskW + 16),
          y: top + r * (GEO.taskH + 14),
          w: GEO.taskW,
          h: GEO.taskH,
          territoryId: t.id
        });
      });
    }

    const conduits = [];
    for (const edge of semantic.edges) {
      const sp = placed.get(edge.source);
      const tp = placed.get(edge.target);
      if (!sp || !tp) continue;
      const sx = sp.x + sp.w, sy = sp.y + sp.h / 2;
      const tx = tp.x, ty = tp.y + tp.h / 2;
      const mx = (sx + tx) / 2;
      conduits.push({ id: edge.id, path: `M ${sx} ${sy} H ${mx} V ${ty} H ${tx}` });
    }

    return { worldW, worldH, territory: placed, task: tasksGeom, conduits };
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
        <div class="atlas-control-island">
          <div class="atlas-island-brand">
            <span class="atlas-island-dot"></span>
            <strong>SAVANT ATLAS</strong>
            <small id="atlas-telemetry">100%</small>
          </div>
          <div class="atlas-island-actions">
            <button id="atlas-act-fit" class="atlas-pill-btn" type="button">FIT (0)</button>
            <button id="atlas-act-frontier" class="atlas-pill-btn highlight" type="button">NEXT TASK (F)</button>
            <button id="atlas-act-lens" class="atlas-pill-btn" type="button">LENS</button>
            <button id="atlas-act-search" class="atlas-pill-btn" type="button">FIND (/)</button>
          </div>
        </div>

        <div id="atlas-viewport" class="atlas-viewport" tabindex="0">
          <svg id="atlas-svg" class="atlas-svg">
            <defs>
              <pattern id="atlas-grid" width="48" height="48" patternUnits="userSpaceOnUse">
                <path d="M 48 0 L 0 0 0 48" fill="none" stroke="rgba(85,216,255,0.05)" stroke-width="1"/>
              </pattern>
              <marker id="atlas-arrow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto">
                <path d="M 0 1 L 10 5 L 0 9 z" fill="var(--a-accent)"/>
              </marker>
            </defs>
            <g id="atlas-world">
              <rect id="atlas-ground" class="atlas-ground" fill="url(#atlas-grid)"/>
              <g id="atlas-mesh"></g>
              <g id="atlas-conduits"></g>
              <g id="atlas-territories"></g>
              <g id="atlas-tasks"></g>
            </g>
          </svg>

          <div class="atlas-radar-hud">
            <svg id="atlas-minimap" class="atlas-minimap"></svg>
          </div>
        </div>

        <aside id="atlas-drawer" class="atlas-drawer" aria-hidden="true">
          <div class="atlas-drawer-header">
            <h3>TASK TELEMETRY</h3>
            <button id="atlas-drawer-close" type="button" aria-label="Close">×</button>
          </div>
          <div id="atlas-drawer-body" class="atlas-drawer-body">
            <p class="atlas-empty-tip">Select any computational unit to inspect.</p>
          </div>
        </aside>

        <!-- Command Palette Modal -->
        <div id="atlas-modal-search" class="atlas-search-modal" hidden>
          <div class="atlas-search-palette">
            <input id="atlas-search-input" type="search" placeholder="Search tasks, objectives, territories..." autocomplete="off">
            <div id="atlas-search-results" class="atlas-search-results"></div>
          </div>
        </div>
      </div>
    `;

    const list = ["viewport", "svg", "world", "ground", "mesh", "conduits", "territories", "tasks", "minimap", "drawer", "drawer-body", "drawer-close", "telemetry", "act-fit", "act-frontier", "act-lens", "act-search", "modal-search", "search-input", "search-results"];
    for (const id of list) dom[id.replace(/-([a-z])/g, (_, c) => c.toUpperCase())] = $(`#atlas-${id}`);
  }

  function setTransform(x, y, scale, animate = false) {
    state.viewport.x = x;
    state.viewport.y = y;
    state.viewport.scale = clamp(scale, Z_LEVELS.min, Z_LEVELS.max);
    dom.world.style.transition = animate ? "transform 0.28s cubic-bezier(0.16, 1, 0.3, 1)" : "none";
    dom.world.setAttribute("transform", `translate(${x} ${y}) scale(${state.viewport.scale})`);
    dom.telemetry.textContent = `${Math.round(state.viewport.scale * 100)}%`;

    if (state.geometry.worldW) {
      const r = dom.viewport.getBoundingClientRect();
      const sX = 160 / state.geometry.worldW, sY = 100 / state.geometry.worldH;
      let lens = $("#atlas-mm-lens");
      if (!lens) {
        lens = document.createElementNS(SVG_NS, "rect");
        lens.id = "atlas-mm-lens";
        lens.setAttribute("class", "atlas-mm-lens");
        dom.minimap.append(lens);
      }
      lens.setAttribute("x", `${(-x * sX) / state.viewport.scale}`);
      lens.setAttribute("y", `${(-y * sY) / state.viewport.scale}`);
      lens.setAttribute("width", `${(r.width * sX) / state.viewport.scale}`);
      lens.setAttribute("height", `${(r.height * sY) / state.viewport.scale}`);
    }
  }

  function fitWorld(animate = true) {
    if (!state.geometry.worldW) return;
    const r = dom.viewport.getBoundingClientRect();
    if (!r.width || !r.height) return;
    const sc = clamp(Math.min(r.width / state.geometry.worldW, r.height / state.geometry.worldH) * 0.92, Z_LEVELS.min, 1.2);
    const tx = (r.width - state.geometry.worldW * sc) / 2;
    const ty = (r.height - state.geometry.worldH * sc) / 2;
    setTransform(tx, ty, sc, animate);
    triggerSound("warp");
  }

  function focusTask(id) {
    const g = state.geometry.task.get(id);
    if (!g) return;
    const r = dom.viewport.getBoundingClientRect();
    const sc = Math.max(state.viewport.scale, 1.35);
    const tx = r.width / 2 - (g.x + g.w / 2) * sc;
    const ty = r.height / 2 - (g.y + g.h / 2) * sc;
    setTransform(tx, ty, sc, true);
    triggerSound("tick");
  }

  function inspectTask(id) {
    const t = state.semantic.taskById.get(id);
    if (!t) return;
    state.selected = id;
    dom.drawer.classList.add("active");
    dom.drawer.setAttribute("aria-hidden", "false");
    triggerSound("tick");

    dom.drawerBody.innerHTML = `
      <div class="atlas-card-detail">
        <span class="atlas-tag-badge">${taskObjective(t)}</span>
        <h4>${taskTitle(t)}</h4>
        <dl class="atlas-kv-list">
          <dt>ID</dt><dd>${id}</dd>
          <dt>STATE</dt><dd class="state-txt ${taskState(t)}">${taskState(t).toUpperCase()}</dd>
          <dt>PRIORITY</dt><dd>${taskPriority(t).toUpperCase()}</dd>
          <dt>DEPENDS ON</dt><dd>${taskDeps(t).length ? taskDeps(t).join(", ") : "None"}</dd>
        </dl>
        <button id="atlas-btn-teleport" class="atlas-warp-action">WARP VIEWPORT</button>
      </div>
    `;
    $("#atlas-btn-teleport", dom.drawerBody)?.addEventListener("click", () => focusTask(id));
  }

  function renderScene() {
    dom.ground.setAttribute("width", `${state.geometry.worldW}`);
    dom.ground.setAttribute("height", `${state.geometry.worldH}`);

    const meshFrag = document.createDocumentFragment();
    for (const p of state.geometry.territory.values()) {
      const pad = document.createElementNS(SVG_NS, "rect");
      pad.setAttribute("x", `${p.x - 14}`);
      pad.setAttribute("y", `${p.y - 14}`);
      pad.setAttribute("width", `${p.w + 28}`);
      pad.setAttribute("height", `${p.h + 28}`);
      pad.setAttribute("class", "atlas-concourse-pad");
      meshFrag.append(pad);
    }
    dom.mesh.replaceChildren(meshFrag);

    const conduitFrag = document.createDocumentFragment();
    for (const c of state.geometry.conduits) {
      const p = document.createElementNS(SVG_NS, "path");
      p.setAttribute("d", c.path);
      p.setAttribute("class", "atlas-bus-conduit");
      p.setAttribute("marker-end", "url(#atlas-arrow)");
      conduitFrag.append(p);
    }
    dom.conduits.replaceChildren(conduitFrag);

    const terrFrag = document.createDocumentFragment();
    state.semantic.territories.forEach((t, i) => {
      const p = state.geometry.territory.get(t.id);
      if (!p) return;
      const c = PALETTE[i % PALETTE.length];
      const g = document.createElementNS(SVG_NS, "g");
      g.setAttribute("class", "atlas-territory-group");
      g.style.setProperty("--tc", `hsl(${c.h} ${c.s}% ${c.l}%)`);

      const hull = document.createElementNS(SVG_NS, "rect");
      hull.setAttribute("x", `${p.x}`);
      hull.setAttribute("y", `${p.y}`);
      hull.setAttribute("width", `${p.w}`);
      hull.setAttribute("height", `${p.h}`);
      hull.setAttribute("class", "atlas-territory-hull");

      const title = document.createElementNS(SVG_NS, "text");
      title.setAttribute("x", `${p.x + 18}`);
      title.setAttribute("y", `${p.y + 36}`);
      title.setAttribute("class", "atlas-territory-title");
      title.textContent = t.label.toUpperCase();

      const meta = document.createElementNS(SVG_NS, "text");
      meta.setAttribute("x", `${p.x + 18}`);
      meta.setAttribute("y", `${p.y + 56}`);
      meta.setAttribute("class", "atlas-territory-meta");
      meta.textContent = `UNITS: ${t.statistics.total} | READY: ${t.statistics.ready} | BLOCKED: ${t.statistics.blocked}`;

      g.append(hull, title, meta);
      terrFrag.append(g);
    });
    dom.territories.replaceChildren(terrFrag);

    const taskFrag = document.createDocumentFragment();
    const recId = state.semantic.recommended;

    for (const t of state.semantic.tasks) {
      const id = taskId(t);
      const g = state.geometry.task.get(id);
      if (!g) continue;

      const node = document.createElementNS(SVG_NS, "g");
      node.setAttribute("class", `atlas-unit-node state-${taskState(t)} ${id === recId ? "frontier" : ""}`);
      node.setAttribute("transform", `translate(${g.x} ${g.y})`);
      node.dataset.taskId = id;

      const body = document.createElementNS(SVG_NS, "rect");
      body.setAttribute("width", `${g.w}`);
      body.setAttribute("height", `${g.h}`);
      body.setAttribute("class", "atlas-unit-body");

      const title = document.createElementNS(SVG_NS, "text");
      title.setAttribute("x", "12");
      title.setAttribute("y", "24");
      title.setAttribute("class", "atlas-unit-title");
      title.textContent = taskTitle(t).slice(0, 24);

      const sub = document.createElementNS(SVG_NS, "text");
      sub.setAttribute("x", "12");
      sub.setAttribute("y", "40");
      sub.setAttribute("class", "atlas-unit-sub");
      sub.textContent = `${taskState(t).toUpperCase()} // ${taskPriority(t)}`;

      node.append(body, title, sub);
      taskFrag.append(node);
    }
    dom.tasks.replaceChildren(taskFrag);

    // Minimap Radar
    dom.minimap.setAttribute("viewBox", `0 0 ${state.geometry.worldW} ${state.geometry.worldH}`);
    const mmFrag = document.createDocumentFragment();
    for (const p of state.geometry.territory.values()) {
      const r = document.createElementNS(SVG_NS, "rect");
      r.setAttribute("x", `${p.x}`);
      r.setAttribute("y", `${p.y}`);
      r.setAttribute("width", `${p.w}`);
      r.setAttribute("height", `${p.h}`);
      r.setAttribute("class", "atlas-mm-cell");
      mmFrag.append(r);
    }
    dom.minimap.replaceChildren(mmFrag);
  }

  function bindEvents() {
    dom.actFit.addEventListener("click", () => fitWorld(true));
    dom.actFrontier.addEventListener("click", () => {
      const rec = state.semantic.recommended;
      if (rec) { focusTask(rec); inspectTask(rec); }
    });
    dom.actLens.addEventListener("click", () => {
      state.lens = state.lens === "domains" ? "heatmap" : "domains";
      dom.actLens.textContent = `LENS (${state.lens.toUpperCase()})`;
      renderScene();
      triggerSound("tick");
    });
    dom.actSearch.addEventListener("click", () => openSearch());

    dom.drawerClose.addEventListener("click", () => dom.drawer.classList.remove("active"));

    dom.viewport.addEventListener("click", e => {
      const node = e.target.closest("[data-task-id]");
      if (node) inspectTask(node.dataset.taskId);
    });

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
      dom.viewport.setPointerCapture?.(e.pointerId);
    });

    window.addEventListener("pointermove", e => {
      if (!state.pointer.active.has(e.pointerId)) return;
      const dx = e.clientX - state.pointer.sx;
      const dy = e.clientY - state.pointer.sy;
      setTransform(state.pointer.ox + dx, state.pointer.oy + dy, state.viewport.scale, false);
    });

    const release = e => state.pointer.active.delete(e.pointerId);
    window.addEventListener("pointerup", release);
    window.addEventListener("pointercancel", release);

    window.addEventListener("keydown", e => {
      if (e.key === "0" && !dom.modalSearch.contains(document.activeElement)) {
        e.preventDefault();
        fitWorld(true);
      }
      if (e.key === "f" && !dom.modalSearch.contains(document.activeElement)) {
        e.preventDefault();
        if (state.semantic.recommended) {
          focusTask(state.semantic.recommended);
          inspectTask(state.semantic.recommended);
        }
      }
      if (e.key === "/" && !dom.modalSearch.contains(document.activeElement)) {
        e.preventDefault();
        openSearch();
      }
      if (e.key === "Escape") {
        dom.modalSearch.hidden = true;
        dom.drawer.classList.remove("active");
      }
    });

    // Modal Search handler
    dom.searchInput.addEventListener("input", () => {
      const q = low(dom.searchInput.value);
      if (!q) { dom.searchResults.replaceChildren(); return; }
      const hits = state.semantic.tasks.filter(t => low(taskId(t)).includes(q) || low(taskTitle(t)).includes(q)).slice(0, 8);
      const frag = document.createDocumentFragment();
      for (const h of hits) {
        const row = document.createElement("button");
        row.className = "atlas-search-row";
        row.innerHTML = `<strong>${taskTitle(h)}</strong><small>${taskId(h)} // ${taskObjective(h)}</small>`;
        row.addEventListener("click", () => {
          dom.modalSearch.hidden = true;
          focusTask(taskId(h));
          inspectTask(taskId(h));
        });
        frag.append(row);
      }
      dom.searchResults.replaceChildren(frag);
    });
  }

  function openSearch() {
    dom.modalSearch.hidden = false;
    dom.searchInput.value = "";
    dom.searchResults.replaceChildren();
    dom.searchInput.focus();
    triggerSound("warp");
  }

  function sync() {
    const raw = coreProj();
    if (!raw) return;
    state.semantic = transformProjection(raw);
    state.geometry = computeLayout(state.semantic);
    renderScene();
    state.ready = true;
    if (!state.installed) {
      state.installed = true;
      requestAnimationFrame(() => fitWorld(false));
    }
  }

  function open() {
    ensureSurface();
    const surf = $("#surface-navigation");
    surf.hidden = false;
    surf.classList.add("active");
    for (const s of $$(".surface")) {
      if (s !== surf) { s.classList.remove("active"); s.hidden = true; }
    }
    state.active = true;
    sync();
    fitWorld(false);
  }

  function install() {
    ensureSurface();
    bindEvents();
    sync();
    window.addEventListener("niche:projection", () => sync());
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
