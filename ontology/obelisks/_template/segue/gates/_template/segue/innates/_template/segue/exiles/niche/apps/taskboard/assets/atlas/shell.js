export function installShell(ctx) {
  const {state,dom,$,$$,txt,low,arr,clamp,BUILD,VISUAL_SYSTEM,VIEW,Z,G,SVG,levelFor,svg,swrite,taskState,taskTitle,taskId,emit} = ctx;
  function ensureSurface() {
    let s=$("#surface-navigation");
    if(!s){
      const parent=$(".surfaces")??$("main")??document.body;
      s=document.createElement("section");
      s.id="surface-navigation";
      s.className="surface niche-navigation-surface atlas-surface";
      s.dataset.surface=VIEW;
      s.hidden=true;
      const causal=$("#surface-causal");
      causal&&causal.parentElement===parent?parent.insertBefore(s,causal):parent.append(s);
    }
    s.className="surface niche-navigation-surface atlas-surface atlas-r12";
    s.dataset.atlasBuild=BUILD;
    s.innerHTML=`
      <div class="atlas-shell" data-atlas-build="${BUILD}">
        <div class="atlas-mapframe">
          <div id="atlas-viewport" class="atlas-viewport" tabindex="0" data-semantic-level="world" data-effects="full" aria-label="SAVANT Atlas computational facility plan">
            <svg id="atlas-svg" class="atlas-svg" role="application" aria-label="Atlas represented work geography">
              <defs id="atlas-defs"></defs>
              <g id="atlas-world">
                <g id="atlas-substrate"></g>
                <g id="atlas-corridors"></g>
                <g id="atlas-territories"></g>
                <g id="atlas-task-edges"></g>
                <g id="atlas-tasks"></g>
                <g id="atlas-overlays"></g>
                <g id="atlas-labels"></g>
              </g>
            </svg>
            <div id="atlas-state" class="atlas-state" hidden></div>
          </div>

          <header class="atlas-brandplate">
            <div class="atlas-mark" aria-hidden="true"><span></span><i></i></div>
            <div><small>SAVANT</small><h1>ATLAS</h1><p>LIVING COMPUTATIONAL GEOGRAPHY</p></div>
          </header>

          <div class="atlas-commanddeck" aria-label="Atlas commands">
            <label class="atlas-searchbox"><span>SEARCH</span><input id="atlas-search" class="atlas-input" type="search" autocomplete="off" placeholder="tasks · objectives · territories" aria-label="Search Atlas"></label>
            <button id="atlas-view-toggle" class="atlas-command" type="button" aria-controls="atlas-rail">VIEW</button>
            <button id="atlas-filter-toggle" class="atlas-command" type="button" aria-controls="atlas-rail">FILTER</button>
            <button id="atlas-fit" class="atlas-command" type="button" title="Fit represented world">FIT</button>
            <button id="atlas-frontier" class="atlas-command atlas-command-frontier" type="button" title="Move to executable frontier">NEXT</button>
            <button id="atlas-rail-toggle" class="atlas-command" type="button" aria-expanded="false" aria-controls="atlas-rail">MORE</button>
            <select id="atlas-theme" class="atlas-select atlas-theme-select" aria-label="Atlas theme" title="Theme"></select>
          </div>

          <div class="atlas-vitals" aria-label="Atlas projection counts">
            <div><span>WORK</span><strong id="atlas-m-tasks">0</strong></div>
            <div><span>DISTRICTS</span><strong id="atlas-m-territories">0</strong></div>
            <div><span>SHOWN</span><strong id="atlas-m-represented">0</strong></div>
            <div><span>FILTERED</span><strong id="atlas-m-filtered">0</strong></div>
          </div>

          <div class="atlas-coordinateplate">
            <strong id="atlas-level">WORLD</strong><span id="atlas-location">OVERVIEW</span><span id="atlas-zoom">100%</span>
          </div>

          <div class="atlas-map-controls" aria-label="Atlas zoom controls">
            <button id="atlas-plus" type="button" title="Zoom in" aria-label="Zoom in">+</button>
            <button id="atlas-minus" type="button" title="Zoom out" aria-label="Zoom out">−</button>
          </div>

          <section class="atlas-minimapplate" aria-label="Atlas overview">
            <div><strong>FACILITY</strong><span id="atlas-delimiter">objective</span></div>
            <svg id="atlas-minimap" class="atlas-minimap" aria-label="Atlas minimap"></svg>
          </section>

          <div id="atlas-breadcrumb" class="atlas-breadcrumb" aria-label="Atlas breadcrumb"></div>

          <section class="atlas-selected-strip">
            <div class="atlas-selected-copy"><span>SELECTED LOCATION</span><strong id="atlas-selected-title">No task selected</strong><small id="atlas-selected-meta">Select represented work.</small></div>
            <div class="atlas-selected-actions">
              <button id="atlas-open-task" type="button">OPEN</button><button id="atlas-focus-task" type="button">FOCUS</button>
              <button id="atlas-back" type="button" disabled>BACK</button><button id="atlas-forward" type="button" disabled>FORWARD</button>
            </div>
          </section>

          <aside class="atlas-rail" id="atlas-rail" data-rail-mode="more" aria-label="Atlas instrument drawer">
            <div class="atlas-rail-head"><div><small>ATLAS INSTRUMENT</small><strong>CONTROL SURFACE</strong></div><button type="button" class="atlas-rail-close" aria-label="Close controls" onclick="document.getElementById('atlas-rail-toggle')?.click()">×</button></div>
            <section class="atlas-panel atlas-panel-view" data-rail-section="view"><div class="atlas-panel-heading"><h2>VIEW</h2></div><div id="atlas-lenses" class="atlas-lenses">
              <button data-lens="domains" class="active" type="button">GEOGRAPHY</button><button data-lens="heatmap" type="button">HEAT</button>
              <button data-lens="dependencies" type="button">CONDUITS</button><button data-lens="authority" type="button">AUTHORITY</button>
            </div></section>
            <section class="atlas-panel atlas-panel-filter" data-rail-section="filter"><div class="atlas-panel-heading"><h2>FILTER</h2><button id="atlas-reset" type="button">RESET</button></div>
              <select id="atlas-status" class="atlas-select"><option value="all">All states</option><option value="ready">Ready</option><option value="active">Active</option><option value="review">Review</option><option value="waiting">Waiting</option><option value="blocked">Blocked</option><option value="complete">Complete</option><option value="unknown">Unknown</option></select>
              <select id="atlas-priority" class="atlas-select"><option value="all">All priorities</option><option value="critical">Critical</option><option value="high">High</option><option value="medium">Medium</option><option value="low">Low</option><option value="unknown">Unknown</option></select>
              <select id="atlas-completed" class="atlas-select"><option value="fade">Fade completed</option><option value="show">Show completed</option><option value="hide">Hide completed</option></select>
              <select id="atlas-effects" class="atlas-select"><option value="full">Full effects</option><option value="reduced">Reduced effects</option></select>
            </section>
            <section class="atlas-panel atlas-detail-panel" data-rail-section="more"><div class="atlas-panel-heading"><h2>LOCATION</h2></div><div id="atlas-detail" class="atlas-detail"><p>Select a territory, port, or task.</p></div></section>
            <section class="atlas-panel" data-rail-section="more"><div class="atlas-panel-heading"><h2>ROUTE</h2></div><input id="atlas-route-input" class="atlas-input" type="search" placeholder="Destination task"><button id="atlas-route-go" class="atlas-wide" type="button">TRACE REPRESENTED ROUTE</button><div id="atlas-route" class="atlas-route"></div></section>
            <section class="atlas-panel" data-rail-section="more"><div class="atlas-panel-heading"><h2>LEGEND</h2></div><div id="atlas-legend" class="atlas-legend"></div></section>
            <section class="atlas-panel atlas-help" data-rail-section="more"><div class="atlas-panel-heading"><h2>GESTURE INDEX</h2></div><dl><dt>Click / tap</dt><dd>Select</dd><dt>Drag</dt><dd>Pan anywhere</dd><dt>Pinch / wheel</dt><dd>Zoom</dd><dt>Double click</dt><dd>Focus</dd><dt>0</dt><dd>Fit world</dd><dt>/</dt><dd>Search</dd><dt>Esc</dt><dd>Step outward</dd></dl></section>
            <section class="atlas-panel" data-rail-section="more"><div class="atlas-panel-heading"><h2>ACCESSIBLE INDEX</h2></div><div id="atlas-index" class="atlas-index"></div></section>
          </aside>

          <footer class="atlas-footer"><span>PROJECTION ONLY</span><span>AUTHORITY EFFECT: NONE</span><span id="atlas-footer-status">ATLAS R12</span><code>${BUILD}</code></footer>
          <div id="atlas-live" class="sr-only" aria-live="polite" aria-atomic="true"></div>
        </div>
      </div>`;
    return s;
  }
  function ensureNav() {
    const nav=$(".nav");if(!nav)return null;let b=$(`.nav [data-view="${VIEW}"]`);
    if(!b){b=document.createElement("button");b.type="button";b.dataset.view=VIEW;const c=$('.nav [data-view="causal"]');c?nav.insertBefore(b,c):nav.append(b)}
    b.textContent="Atlas";b.dataset.atlasBuild=BUILD;b.setAttribute("aria-label","Open Atlas");return b;
  }
  function cache() {
    const ids=["surface","viewport","svg","defs","world","substrate","corridors","territories","task-edges","tasks","overlays","labels","state","search","theme","rail","rail-toggle","view-toggle","filter-toggle","fit","plus","minus","zoom","level","location","breadcrumb","selected-title","selected-meta","open-task","focus-task","frontier","back","forward","minimap","delimiter","lenses","status","priority","completed","effects","reset","detail","route-input","route-go","route","legend","index","footer-status","live","m-tasks","m-territories","m-represented","m-filtered"];
    for(const id of ids) dom[id.replace(/-([a-z])/g,(_,c)=>c.toUpperCase())]=$("#atlas-"+id);
    dom.surface=$("#surface-navigation");dom.nav=$(`.nav [data-view="${VIEW}"]`);
  }
  function defs() {
    dom.defs.innerHTML=`
      <filter id="atlas-glow-soft" x="-40%" y="-40%" width="180%" height="180%"><feGaussianBlur stdDeviation="4" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
      <filter id="atlas-glow-focus" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="7" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
      <pattern id="atlas-grid" width="40" height="40" patternUnits="userSpaceOnUse"><path d="M40 0H0V40" class="atlas-grid-line"/></pattern>
      <marker id="atlas-arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="5" markerHeight="5" orient="auto"><path d="M0 0L10 5L0 10z" class="atlas-arrow"/></marker>
      <symbol id="atlas-frontier-symbol" viewBox="0 0 24 24"><path d="M12 2L22 21L12 16L2 21Z"/><path d="M12 7L16 15L12 13L8 15Z"/></symbol>`;
  }
  function measure() {
    const r=dom.viewport?.getBoundingClientRect();if(!r||r.width<160||r.height<200)return false;
    state.size={w:r.width,h:r.height};dom.svg.setAttribute("viewBox",`0 0 ${r.width} ${r.height}`);return true;
  }
  function filtered(t) {
    const s=taskState(t);if(state.completed==="hide"&&s==="complete")return false;if(state.status!=="all"&&s!==state.status)return false;if(state.priority!=="all"&&low(taskPriority(t))!==low(state.priority))return false;
    const q=low(state.query);if(!q)return true;const terr=state.semantic.territoryById.get(state.semantic.taskToTerritory.get(taskId(t)));
    return [taskTitle(t),taskId(t),taskObjective(t),taskDomain(t),taskOwner(t),taskRubric(t),taskCabal(t),terr?.label].filter(Boolean).some(v=>low(v).includes(q));
  }
  function visibleTerritories() {
    const q=low(state.query);return state.semantic.territories.filter(t=>(!state.focusTerritory||t.id===state.focusTerritory)&&(t.tasks.some(filtered)||low(t.label).includes(q)));
  }
  function bounds() { return {l:-state.viewport.x/state.viewport.scale,t:-state.viewport.y/state.viewport.scale,r:(state.size.w-state.viewport.x)/state.viewport.scale,b:(state.size.h-state.viewport.y)/state.viewport.scale}; }
  function intersects(x,y,w,h,m=180) { const b=bounds(),q=m/state.viewport.scale;return !(x+w<b.l-q||x>b.r+q||y+h<b.t-q||y>b.b+q); }
  function applyTransform() {
    dom.world.setAttribute("transform",`translate(${state.viewport.x} ${state.viewport.y}) scale(${state.viewport.scale})`);
    dom.zoom.textContent=`${Math.round(state.viewport.scale*100)}%`;dom.level.textContent=state.level.toUpperCase();
    dom.viewport.dataset.semanticLevel=state.level;dom.viewport.dataset.effects=state.effects;dom.viewport.dataset.lens=state.lens;
  }
  function queueTransform() { if(state.transformQueued)return;state.transformQueued=true;requestAnimationFrame(()=>{state.transformQueued=false;applyTransform();ctx.renderMiniViewport?.()}); }
  function setViewport(v,persist=true) {
    const old=state.level;state.viewport={x:Number.isFinite(v.x)?v.x:state.viewport.x,y:Number.isFinite(v.y)?v.y:state.viewport.y,scale:clamp(Number.isFinite(v.scale)?v.scale:state.viewport.scale,Z.min,Z.max)};
    state.level=levelFor(state.viewport.scale);if(persist)swrite();old!==state.level?queueRender():queueTransform();
  }
  function motionAllowed(){return !window.matchMedia?.("(prefers-reduced-motion: reduce)")?.matches}
  function animateViewport(target,duration=190){
    if(!motionAllowed()||!state.active)return setViewport(target);
    if(state.viewportAnimation)cancelAnimationFrame(state.viewportAnimation);
    const start={...state.viewport},t0=performance.now(),ease=t=>1-Math.pow(1-t,3);
    const frame=now=>{
      const p=clamp((now-t0)/duration,0,1),e=ease(p);
      setViewport({x:start.x+(target.x-start.x)*e,y:start.y+(target.y-start.y)*e,scale:start.scale+(target.scale-start.scale)*e},false);
      if(p<1)state.viewportAnimation=requestAnimationFrame(frame);
      else{state.viewportAnimation=null;swrite()}
    };
    state.viewportAnimation=requestAnimationFrame(frame);
  }
  function fitBounds(b) {
    if(!measure())return;const pad=state.size.w<640?24:48,scale=clamp(Math.min((state.size.w-pad*2)/Math.max(1,b.w),(state.size.h-pad*2)/Math.max(1,b.h)),Z.min,Z.max);
    animateViewport({x:(state.size.w-b.w*scale)/2-b.x*scale,y:(state.size.h-b.h*scale)/2-b.y*scale,scale});
  }
  const fitWorld=()=>fitBounds({x:0,y:0,w:state.geometry.w,h:state.geometry.h});
  function fitTerritory(id){const p=state.geometry.territory.get(id);if(p)fitBounds({x:p.x-24,y:p.y-24,w:p.w+48,h:p.h+48})}
  function focusTask(id) {
    const p=state.geometry.task.get(id);if(!p||!measure())return;const scale=clamp(Math.max(1.3,state.viewport.scale),Z.min,Z.max);
    animateViewport({x:state.size.w/2-(p.x+p.w/2)*scale,y:state.size.h/2-(p.y+p.h/2)*scale,scale},220);
  }
  function zoomAt(f,cx,cy,persist=true) {
    const r=dom.viewport.getBoundingClientRect(),lx=cx-r.left,ly=cy-r.top,old=state.viewport.scale,next=clamp(old*f,Z.min,Z.max),wx=(lx-state.viewport.x)/old,wy=(ly-state.viewport.y)/old;
    setViewport({x:lx-wx*next,y:ly-wy*next,scale:next},persist);
  }
  function zoomCenter(f){const r=dom.viewport.getBoundingClientRect();zoomAt(f,r.left+r.width/2,r.top+r.height/2)}

  function ensureTooltip(){
    let tip=document.getElementById("atlas-tooltip");
    if(!tip){tip=document.createElement("div");tip.id="atlas-tooltip";tip.className="atlas-tooltip";tip.hidden=true;tip.setAttribute("role","tooltip");dom.surface.append(tip)}
    return tip;
  }
  function hideTooltip(){const tip=ensureTooltip();tip.hidden=true}
  function showTooltip(event,target){
    const tip=ensureTooltip();let title="",meta="";
    if(target?.dataset?.taskId){
      const t=state.semantic.taskById.get(target.dataset.taskId);if(!t)return;
      title=taskTitle(t);meta=`${taskState(t)} · ${taskObjective(t)} · ${taskDependencies(t).length} dependencies`;
    }else if(target?.dataset?.territoryId){
      const t=state.semantic.territoryById.get(target.dataset.territoryId);if(!t)return;
      title=t.label;meta=`${t.statistics.total} tasks · ${t.statistics.ready} ready · ${t.statistics.blocked} blocked`;
    }else return;
    const strong=document.createElement("strong"),small=document.createElement("span");strong.textContent=title;small.textContent=meta;tip.replaceChildren(strong,small);
    const r=dom.surface.getBoundingClientRect();tip.style.transform=`translate(${Math.min(r.width-260,Math.max(8,event.clientX-r.left+14))}px,${Math.min(r.height-92,Math.max(8,event.clientY-r.top+14))}px)`;tip.hidden=false;
  }

  Object.assign(ctx,{ensureSurface,ensureNav,cache,defs,measure,filtered,visibleTerritories,bounds,intersects,applyTransform,queueTransform,setViewport,motionAllowed,animateViewport,fitBounds,fitWorld,fitTerritory,focusTask,zoomAt,zoomCenter,ensureTooltip,hideTooltip,showTooltip});
  return ctx;
}
