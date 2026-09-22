"use strict";
(() => {
  "use strict";

  const SVG = "http://www.w3.org/2000/svg";
  const VIEW = "navigation";
  const STORE = "savant.niche.atlas.v1";
  const LEVEL = Object.freeze({world:"world",district:"district",locality:"locality",detail:"detail"});
  const Z = Object.freeze({min:.16,max:4.8,world:.54,district:1,locality:1.85,step:1.2});
  const G = Object.freeze({pad:88,gap:52,head:70,inner:28,taskW:186,taskH:50,taskGapX:18,taskGapY:15,minW:440,minH:290});
  const palette = Object.freeze([
    [188,92,58],[213,94,62],[267,88,66],[319,86,62],[8,88,59],[36,94,59],
    [67,80,56],[143,82,52],[166,86,54],[235,86,68],[287,78,65],[343,84,62]
  ]);

  const state = {
    installed:false, active:false, ready:false, generation:-1, renderQueued:false, transformQueued:false,
    level:LEVEL.world, selected:null, focusTerritory:null, query:"", status:"all", lens:"domains",
    completed:"fade", effects:"full", route:[], back:[], recent:[],
    viewport:{x:0,y:0,scale:1}, size:{w:1,h:1},
    semantic:{delimiter:"objective",tasks:[],taskById:new Map(),dependents:new Map(),territories:[],territoryById:new Map(),taskToTerritory:new Map(),aggregateEdges:[]},
    geometry:{fingerprint:"",territory:new Map(),task:new Map(),ports:new Map(),edges:[],w:1,h:1},
    pointer:{active:new Map(),mode:"",sx:0,sy:0,ox:0,oy:0,pinch:1,scale:1,cx:0,cy:0},
    resizeObserver:null, firstFit:false
  };
  const dom = Object.create(null);

  const $ = (s,r=document) => r.querySelector(s);
  const $$ = (s,r=document) => Array.from(r.querySelectorAll(s));
  const txt = (v,f="") => v == null ? f : (String(v).trim() || f);
  const low = v => txt(v).toLocaleLowerCase();
  const arr = v => Array.isArray(v) ? v : [];
  const clamp = (v,a,b) => Math.min(b,Math.max(a,v));
  const hash = input => {
    let h = 2166136261;
    for (const ch of txt(input)) { h ^= ch.charCodeAt(0); h = Math.imul(h,16777619); }
    return h >>> 0;
  };
  const sread = () => { try { const x=localStorage.getItem(STORE); return x?JSON.parse(x):null; } catch { return null; } };
  const swrite = () => { try { localStorage.setItem(STORE,JSON.stringify({
    viewport:state.viewport,query:state.query,status:state.status,lens:state.lens,
    completed:state.completed,effects:state.effects,focusTerritory:state.focusTerritory
  })); } catch {} };
  const emit = (type,detail={}) => window.dispatchEvent(new CustomEvent(`niche:atlas:${type}`,{detail:{...detail,authority_effect:"none",projection_only:true}}));

  function coreProjection() {
    try { return window.Niche?.projection?.() ?? null; } catch { return null; }
  }
  function coreState() {
    try { return window.Niche?.state?.() ?? {}; } catch { return {}; }
  }
  const taskId = t => txt(t?.id ?? t?.task_id ?? t?.identity ?? t?.key);
  const taskTitle = t => txt(t?.title ?? t?.name ?? t?.action ?? t?.summary ?? taskId(t),"untitled task");
  const taskObjective = t => txt(t?.objective ?? t?.objective_id ?? t?.root_objective ?? t?.ancestry?.objective,"unknown objective");
  const taskDomain = t => txt(t?.domain ?? t?.domain_id ?? t?.area ?? t?.scope?.domain);
  const taskOwner = t => txt(t?.owner ?? t?.owner_id ?? t?.task_owner ?? t?.assignee);
  const taskRubric = t => txt(t?.rubric ?? t?.rubric_id ?? t?.program_surface ?? t?.surface);
  const taskCabal = t => txt(t?.cabal ?? t?.cabal_id ?? t?.shared_scope);
  const taskPriority = t => txt(t?.priority ?? t?.authoritative_priority ?? t?.rank,"unknown");
  const taskParent = t => txt(t?.parent ?? t?.parent_id ?? t?.parent_task_id ?? t?.ancestry?.parent);
  const taskDependencies = t => arr(t?.dependencies ?? t?.depends_on ?? t?.prerequisites ?? t?.requires)
    .map(x => typeof x === "string" ? x.trim() : txt(x?.id ?? x?.task_id ?? x?.key)).filter(Boolean);
  function taskState(t) {
    const r=low(t?.state ?? t?.status ?? t?.lifecycle_state);
    if (r.includes("complete")||r==="done"||r==="closed") return "complete";
    if (r.includes("block")||r==="failed") return "blocked";
    if (r.includes("active")||r.includes("progress")||r==="started"||r==="leased") return "active";
    if (r.includes("review")||r.includes("verify")||r.includes("evidence")) return "review";
    if (r.includes("wait")||r.includes("pending")||r.includes("defer")) return "waiting";
    if (t?.ready===true||t?.is_ready===true||low(t?.readiness)==="ready") return "ready";
    return r||"unknown";
  }
  function taskAuthority(t) {
    const r=low(t?.authority_effect ?? t?.authority ?? t?.authority_owner ?? t?.task_authority_owner);
    if (r.includes("authoritative")||r==="authority") return "authoritative";
    if (r.includes("derived")) return "derived";
    if (r.includes("projection")||r==="none") return "projected";
    return "unknown";
  }
  const critical = t => t?.critical_path===true||t?.on_critical_path===true||t?.critical===true||low(t?.path_class)==="critical";

  function recommendationId(p) {
    return txt(p?.normalized?.recommendedTaskId ?? coreState()?.recommendedTaskId) || null;
  }
  function normalized(p) {
    const tasks=arr(p?.source?.tasks).filter(t=>taskId(t)).slice().sort((a,b)=>taskId(a).localeCompare(taskId(b)));
    const tm=p?.normalized?.taskById instanceof Map ? new Map(p.normalized.taskById) : new Map(tasks.map(t=>[taskId(t),t]));
    let dep;
    if (p?.normalized?.dependents instanceof Map) dep=new Map(Array.from(p.normalized.dependents.entries(),([k,v])=>[k,arr(v).slice()]));
    else {
      dep=new Map(tasks.map(t=>[taskId(t),[]]));
      for (const t of tasks) for (const d of taskDependencies(t)) dep.get(d)?.push(taskId(t));
      for (const x of dep.values()) x.sort();
    }
    return {tasks,taskById:tm,dependents:dep,selected:txt(p?.normalized?.selectedTaskId)||null,recommended:recommendationId(p),generation:Number(p?.requestGeneration)};
  }

  const delimiters = [
    ["domain",taskDomain,5],["rubric",taskRubric,4],["cabal",taskCabal,3],["objective",taskObjective,2],["owner",taskOwner,1]
  ];
  function chooseDelimiter(tasks) {
    const max=Math.max(18,Math.ceil(Math.sqrt(Math.max(1,tasks.length))*2.4));
    const scored=delimiters.map(([id,get,pref])=>{
      const vals=tasks.map(get).filter(Boolean), n=new Set(vals).size, coverage=vals.length/Math.max(1,tasks.length);
      const cq=n>=2&&n<=max?1:n===1?.25:.55;
      return {id,get,pref,n,coverage,score:coverage*.6+cq*.3+pref*.02};
    }).filter(x=>x.coverage>=.72&&x.n>=2).sort((a,b)=>b.score-a.score||b.pref-a.pref||a.id.localeCompare(b.id));
    return scored[0] ?? {id:"objective",get:taskObjective,pref:2};
  }
  function stats(tasks) {
    const s={total:tasks.length,complete:0,ready:0,active:0,review:0,waiting:0,blocked:0,unknown:0};
    for (const t of tasks) { const k=taskState(t); (k in s?s[k]++:s.unknown++); }
    s.completionRatio=s.total?s.complete/s.total:0;
    return s;
  }
  function buildSemantic(n) {
    const d=chooseDelimiter(n.tasks), groups=new Map();
    for (const t of n.tasks) {
      const label=d.get(t)||`unknown ${d.id}`, id=`${d.id}:${label}`;
      if(!groups.has(id)) groups.set(id,{id,label,delimiter:d.id,tasks:[]});
      groups.get(id).tasks.push(t);
    }
    const territories=Array.from(groups.values()).map(x=>({
      ...x,tasks:x.tasks.slice().sort((a,b)=>taskObjective(a).localeCompare(taskObjective(b))||taskTitle(a).localeCompare(taskTitle(b))||taskId(a).localeCompare(taskId(b))),
      statistics:stats(x.tasks),
      objectives:Array.from(new Set(x.tasks.map(taskObjective).filter(Boolean))).sort()
    })).sort((a,b)=>b.tasks.length-a.tasks.length||a.label.localeCompare(b.label));
    const territoryById=new Map(territories.map(x=>[x.id,x])), taskToTerritory=new Map();
    for (const x of territories) for (const t of x.tasks) taskToTerritory.set(taskId(t),x.id);
    const agg=new Map();
    for (const t of n.tasks) {
      const target=taskId(t), tt=taskToTerritory.get(target);
      for (const source of taskDependencies(t)) {
        const st=taskToTerritory.get(source); if(!st||!tt||st===tt) continue;
        const key=`${st}→${tt}`;
        if(!agg.has(key)) agg.set(key,{id:key,source:st,target:tt,count:0,taskEdges:[]});
        const r=agg.get(key); r.count++; r.taskEdges.push({source,target});
      }
    }
    return {delimiter:d.id,tasks:n.tasks,taskById:n.taskById,dependents:n.dependents,territories,territoryById,taskToTerritory,aggregateEdges:Array.from(agg.values()).sort((a,b)=>b.count-a.count||a.id.localeCompare(b.id))};
  }

  const shapes=["rect","wide","tall","l-right","l-left","step-right","step-left","u","offset"];
  function shapeFor(t,i) {
    if(t.tasks.length<=4) return "rect";
    if(t.objectives.length>=4&&t.tasks.length>=12) return hash(t.id)%2?"l-left":"l-right";
    if(t.tasks.length>=28) return i%2?"offset":"u";
    if(t.tasks.length>=18) return i%2?"step-left":"step-right";
    if(t.tasks.length>=10) return "wide";
    return shapes[hash(t.id)%shapes.length];
  }
  function dims(t,shape) {
    const rows=Math.ceil(t.tasks.length/Math.max(2,Math.min(6,Math.ceil(Math.sqrt(Math.max(1,t.tasks.length))))));
    let w=Math.max(G.minW,420+Math.min(520,t.tasks.length*16));
    let h=Math.max(G.minH,G.head+G.inner*2+rows*(G.taskH+G.taskGapY));
    if(["wide","u"].includes(shape)){w*=1.25;h*=.9}
    if(shape==="tall"){w*=.82;h*=1.23}
    if(shape.startsWith("l-")||shape.startsWith("step-")||shape==="offset"){w*=1.12;h*=1.08}
    return {w:Math.round(w),h:Math.round(h)};
  }
  function polygon(x,y,w,h,shape) {
    const c=Math.max(44,Math.min(w,h)*.17), i=Math.max(78,Math.min(w,h)*.28);
    const p={
      rect:[[x+c,y],[x+w-c,y],[x+w,y+c],[x+w,y+h-c],[x+w-c,y+h],[x+c,y+h],[x,y+h-c],[x,y+c]],
      wide:[[x+c,y],[x+w-c*1.5,y],[x+w,y+c],[x+w,y+h-c],[x+w-c,y+h],[x+c,y+h],[x,y+h-c],[x,y+c]],
      tall:[[x+c,y],[x+w-c,y],[x+w,y+c],[x+w,y+h-c*1.5],[x+w-c,y+h],[x+c,y+h],[x,y+h-c],[x,y+c]],
      "l-right":[[x+c,y],[x+w-c,y],[x+w,y+c],[x+w,y+h-i],[x+w-i,y+h-i],[x+w-i,y+h],[x+c,y+h],[x,y+h-c],[x,y+c]],
      "l-left":[[x+c,y],[x+w-c,y],[x+w,y+c],[x+w,y+h-c],[x+w-c,y+h],[x+i,y+h],[x+i,y+h-i],[x,y+h-i],[x,y+c]],
      "step-right":[[x+c,y],[x+w-i,y],[x+w-i,y+i*.55],[x+w,y+i*.55],[x+w,y+h-c],[x+w-c,y+h],[x+c,y+h],[x,y+h-c],[x,y+c]],
      "step-left":[[x+c,y],[x+w-c,y],[x+w,y+c],[x+w,y+h-c],[x+w-c,y+h],[x+c,y+h],[x,y+h-i*.55],[x+i,y+h-i*.55],[x+i,y+i*.55],[x,y+i*.55],[x,y+c]],
      u:[[x+c,y],[x+w-c,y],[x+w,y+c],[x+w,y+h-c],[x+w-c,y+h],[x+w*.62,y+h],[x+w*.62,y+h-i],[x+w*.38,y+h-i],[x+w*.38,y+h],[x+c,y+h],[x,y+h-c],[x,y+c]],
      offset:[[x+c,y],[x+w*.66,y],[x+w*.66,y+i*.45],[x+w-c,y+i*.45],[x+w,y+i*.45+c],[x+w,y+h-c],[x+w-c,y+h],[x+c,y+h],[x,y+h-c],[x,y+c]]
    };
    return p[shape]??p.rect;
  }
  const pstr=p=>p.map(([x,y])=>`${Math.round(x)},${Math.round(y)}`).join(" ");
  function inside(pt,poly) {
    let yes=false;
    for(let a=0,b=poly.length-1;a<poly.length;b=a++){
      const [xi,yi]=poly[a],[xj,yj]=poly[b];
      const hit=(yi>pt.y)!==(yj>pt.y)&&pt.x<(xj-xi)*(pt.y-yi)/(yj-yi||1e-9)+xi;
      if(hit) yes=!yes;
    }
    return yes;
  }
  function pack(territories) {
    const aspect=clamp(state.size.w/Math.max(1,state.size.h),.65,1.9);
    const items=territories.map((t,i)=>{const shape=shapeFor(t,i);return {t,shape,...dims(t,shape)}})
      .sort((a,b)=>b.w*b.h-a.w*a.h||a.t.id.localeCompare(b.t.id));
    const area=items.reduce((s,x)=>s+x.w*x.h,0), target=Math.max(1200,Math.sqrt(area*aspect)*1.12), shelves=[], out=new Map();
    for(const item of items){
      let best=null,waste=Infinity;
      for(const s of shelves) if(s.x+item.w<=target&&item.h<=s.h*1.35){const x=target-(s.x+item.w);if(x<waste){waste=x;best=s}}
      if(!best){const y=shelves.reduce((m,s)=>Math.max(m,s.y+s.h+G.gap),G.pad);best={x:G.pad,y,h:item.h};shelves.push(best)}
      const x=best.x,y=best.y; out.set(item.t.id,{id:item.t.id,x,y,w:item.w,h:item.h,shape:item.shape,points:polygon(x,y,item.w,item.h,item.shape)});
      best.x+=item.w+G.gap;best.h=Math.max(best.h,item.h);
    }
    let w=1,h=1;
    for(const p of out.values()){w=Math.max(w,p.x+p.w+G.pad);h=Math.max(h,p.y+p.h+G.pad)}
    return {out,w,h};
  }
  function taskLayout(t,p) {
    const map=new Map(), left=p.x+G.inner,top=p.y+G.head+G.inner,right=p.x+p.w-G.inner,bottom=p.y+p.h-G.inner;
    const cols=Math.max(1,Math.floor((right-left+G.taskGapX)/(G.taskW+G.taskGapX)));
    let idx=0;
    for(const task of t.tasks){
      let done=false,guard=0;
      while(!done&&guard<t.tasks.length*10+60){
        const c=idx%cols,r=Math.floor(idx/cols),x=left+c*(G.taskW+G.taskGapX),y=top+r*(G.taskH+G.taskGapY);idx++;guard++;
        if(y+G.taskH>bottom) break;
        const samples=[[x,y],[x+G.taskW,y],[x,y+G.taskH],[x+G.taskW,y+G.taskH],[x+G.taskW/2,y+G.taskH/2]].map(([x,y])=>({x,y}));
        if(samples.every(q=>inside(q,p.points))){map.set(taskId(task),{x,y,w:G.taskW,h:G.taskH,territoryId:t.id});done=true}
      }
      if(!done){const n=map.size;map.set(taskId(task),{x:left+(n%cols)*25,y:top+Math.floor(n/cols)*25,w:20,h:20,territoryId:t.id,compact:true})}
    }
    return map;
  }
  function edgeGeometry(edges,placements) {
    const out=[],ports=new Map(Array.from(placements.keys(),k=>[k,[]]));
    for(const e of edges){
      const a=placements.get(e.source),b=placements.get(e.target); if(!a||!b)continue;
      const ac={x:a.x+a.w/2,y:a.y+a.h/2},bc={x:b.x+b.w/2,y:b.y+b.h/2};
      const horizontal=Math.abs(bc.x-ac.x)>=Math.abs(bc.y-ac.y);
      const sp=horizontal?{x:bc.x>=ac.x?a.x+a.w:a.x,y:ac.y}:{x:ac.x,y:bc.y>=ac.y?a.y+a.h:a.y};
      const tp=horizontal?{x:bc.x>=ac.x?b.x:b.x+b.w,y:bc.y}:{x:bc.x,y:bc.y>=ac.y?b.y:b.y+b.h};
      const mx=(sp.x+tp.x)/2,my=(sp.y+tp.y)/2;
      const path=horizontal?`M ${sp.x} ${sp.y} L ${mx} ${sp.y} L ${mx} ${tp.y} L ${tp.x} ${tp.y}`:`M ${sp.x} ${sp.y} L ${sp.x} ${my} L ${tp.x} ${my} L ${tp.x} ${tp.y}`;
      out.push({...e,sp,tp,path});ports.get(e.source)?.push({...sp,direction:"out",edge:e});ports.get(e.target)?.push({...tp,direction:"in",edge:e});
    }
    return {out,ports};
  }
  function geometryFingerprint() {
    return `${state.semantic.delimiter}|${state.semantic.territories.map(t=>`${t.id}:${t.tasks.map(taskId).join(",")}`).join("|")}|${state.size.w<640?"n":state.size.w<1100?"m":"w"}`;
  }
  function ensureGeometry() {
    const fp=geometryFingerprint(); if(fp===state.geometry.fingerprint)return;
    const p=pack(state.semantic.territories), tm=new Map();
    for(const t of state.semantic.territories){const g=p.out.get(t.id);if(!g)continue;for(const [id,v] of taskLayout(t,g))tm.set(id,v)}
    const eg=edgeGeometry(state.semantic.aggregateEdges,p.out);
    state.geometry={fingerprint:fp,territory:p.out,task:tm,ports:eg.ports,edges:eg.out,w:p.w,h:p.h};
  }

  function hue(id) {
    const n=hash(id), base=palette[n%palette.length], off=((n>>>8)%13)-6;
    return {h:(base[0]+off+360)%360,s:base[1],l:base[2]};
  }
  const color=(c,a=1)=>a===1?`hsl(${c.h} ${c.s}% ${c.l}%)`:`hsl(${c.h} ${c.s}% ${c.l}% / ${a})`;
  function levelFor(scale) { return scale<=Z.world?LEVEL.world:scale<=Z.district?LEVEL.district:scale<=Z.locality?LEVEL.locality:LEVEL.detail; }
  function svg(name,attrs={}) { const e=document.createElementNS(SVG,name);for(const[k,v]of Object.entries(attrs))if(v!=null)e.setAttribute(k,String(v));return e; }

  function ensureSurface() {
    let s=$("#surface-navigation");
    if(!s){
      const parent=$(".surfaces")??$("main")??document.body;s=document.createElement("section");
      s.id="surface-navigation";s.className="surface niche-navigation-surface atlas-surface";s.dataset.surface=VIEW;s.hidden=true;
      const causal=$("#surface-causal");causal&&causal.parentElement===parent?parent.insertBefore(s,causal):parent.append(s);
    }
    s.classList.add("atlas-surface");
    s.innerHTML=`
      <div class="atlas-shell">
        <header class="atlas-header">
          <div class="atlas-brand"><span>SAVANT</span><h1>ATLAS</h1><p>LIVING TOPOLOGY OF WORK</p></div>
          <div class="atlas-metrics">
            <div><span>TASKS</span><strong id="atlas-m-tasks">0</strong></div>
            <div><span>TERRITORIES</span><strong id="atlas-m-territories">0</strong></div>
            <div><span>REPRESENTED</span><strong id="atlas-m-represented">0</strong></div>
            <div><span>FILTERED</span><strong id="atlas-m-filtered">0</strong></div>
          </div>
          <input id="atlas-search" class="atlas-input" type="search" autocomplete="off" placeholder="Search tasks, objectives, territories…" aria-label="Search Atlas">
        </header>
        <div class="atlas-main">
          <section class="atlas-map-column">
            <div id="atlas-viewport" class="atlas-viewport" tabindex="0" data-semantic-level="world" data-effects="full" aria-label="SAVANT Atlas spatial topology">
              <svg id="atlas-svg" class="atlas-svg" role="application" aria-label="Atlas map">
                <defs id="atlas-defs"></defs>
                <g id="atlas-world">
                  <g id="atlas-substrate"></g><g id="atlas-corridors"></g><g id="atlas-territories"></g>
                  <g id="atlas-task-edges"></g><g id="atlas-tasks"></g><g id="atlas-overlays"></g><g id="atlas-labels"></g>
                </g>
              </svg>
              <div class="atlas-map-controls">
                <button id="atlas-fit" type="button">FIT</button><button id="atlas-local" type="button">LOCAL</button>
                <button id="atlas-plus" type="button">+</button><button id="atlas-minus" type="button">−</button>
              </div>
              <div class="atlas-orientation"><span id="atlas-zoom">100%</span><strong id="atlas-level">WORLD</strong><span id="atlas-location">OVERVIEW</span></div>
              <div id="atlas-state" class="atlas-state" hidden></div>
            </div>
            <div id="atlas-breadcrumb" class="atlas-breadcrumb" aria-label="Atlas breadcrumb"></div>
            <div class="atlas-selected-strip">
              <div><span>SELECTED TASK</span><strong id="atlas-selected-title">No task selected</strong><small id="atlas-selected-meta">Select a represented task.</small></div>
              <div class="atlas-selected-actions">
                <button id="atlas-open-task" type="button">OPEN</button><button id="atlas-focus-task" type="button">FOCUS</button>
                <button id="atlas-frontier" type="button">FRONTIER</button><button id="atlas-back" type="button" disabled>BACK</button>
              </div>
            </div>
          </section>
          <aside class="atlas-rail">
            <section class="atlas-panel"><div class="atlas-panel-heading"><h2>OVERALL TOPOLOGY</h2><span id="atlas-delimiter">objective</span></div><svg id="atlas-minimap" class="atlas-minimap" aria-label="Atlas minimap"></svg></section>
            <section class="atlas-panel"><div class="atlas-panel-heading"><h2>VIEW LENS</h2></div><div id="atlas-lenses" class="atlas-lenses">
              <button data-lens="domains" class="active" type="button">TERRITORIES</button><button data-lens="heatmap" type="button">HEATMAP</button>
              <button data-lens="dependencies" type="button">DEPENDENCIES</button><button data-lens="authority" type="button">AUTHORITY</button>
            </div></section>
            <section class="atlas-panel"><div class="atlas-panel-heading"><h2>FILTERS</h2><button id="atlas-reset" type="button">RESET</button></div>
              <select id="atlas-status" class="atlas-select"><option value="all">All states</option><option value="ready">Ready</option><option value="active">Active</option><option value="review">Review</option><option value="waiting">Waiting</option><option value="blocked">Blocked</option><option value="complete">Complete</option><option value="unknown">Unknown</option></select>
              <select id="atlas-completed" class="atlas-select"><option value="fade">Fade completed</option><option value="show">Show completed</option><option value="hide">Hide completed</option></select>
              <select id="atlas-effects" class="atlas-select"><option value="full">Full effects</option><option value="reduced">Reduced effects</option></select>
            </section>
            <section class="atlas-panel"><div class="atlas-panel-heading"><h2>ROUTE</h2></div><input id="atlas-route-input" class="atlas-input" type="search" placeholder="Destination task…"><button id="atlas-route-go" class="atlas-wide" type="button">FIND REPRESENTED ROUTE</button><div id="atlas-route" class="atlas-route"></div></section>
            <section class="atlas-panel"><div class="atlas-panel-heading"><h2>LEGEND</h2></div><div id="atlas-legend" class="atlas-legend"></div></section>
            <section class="atlas-panel atlas-help"><div class="atlas-panel-heading"><h2>QUICK HELP</h2></div><dl><dt>Click / tap</dt><dd>Select</dd><dt>Drag</dt><dd>Pan</dd><dt>Pinch / wheel</dt><dd>Zoom</dd><dt>Double click</dt><dd>Focus</dd><dt>0</dt><dd>Fit world</dd><dt>/</dt><dd>Search</dd><dt>Esc</dt><dd>Step outward</dd></dl></section>
            <section class="atlas-panel"><div class="atlas-panel-heading"><h2>ACCESSIBLE INDEX</h2></div><div id="atlas-index" class="atlas-index"></div></section>
          </aside>
        </div>
        <footer class="atlas-footer"><span>PROJECTION ONLY</span><span>AUTHORITY EFFECT: NONE</span><span id="atlas-footer-status">ATLAS READY</span></footer>
        <div id="atlas-live" class="sr-only" aria-live="polite" aria-atomic="true"></div>
      </div>`;
    return s;
  }
  function ensureNav() {
    const nav=$(".nav");if(!nav)return null;let b=$(`.nav [data-view="${VIEW}"]`);
    if(!b){b=document.createElement("button");b.type="button";b.dataset.view=VIEW;const c=$('.nav [data-view="causal"]');c?nav.insertBefore(b,c):nav.append(b)}
    b.textContent="Atlas";b.setAttribute("aria-label","Open Atlas");return b;
  }
  function cache() {
    const ids=["surface","viewport","svg","defs","world","substrate","corridors","territories","task-edges","tasks","overlays","labels","state","search","fit","local","plus","minus","zoom","level","location","breadcrumb","selected-title","selected-meta","open-task","focus-task","frontier","back","minimap","delimiter","lenses","status","completed","effects","reset","route-input","route-go","route","legend","index","footer-status","live","m-tasks","m-territories","m-represented","m-filtered"];
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
    const s=taskState(t);if(state.completed==="hide"&&s==="complete")return false;if(state.status!=="all"&&s!==state.status)return false;
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
    dom.viewport.dataset.semanticLevel=state.level;dom.viewport.dataset.effects=state.effects;
  }
  function queueTransform() { if(state.transformQueued)return;state.transformQueued=true;requestAnimationFrame(()=>{state.transformQueued=false;applyTransform();renderMiniViewport()}); }
  function setViewport(v,persist=true) {
    const old=state.level;state.viewport={x:Number.isFinite(v.x)?v.x:state.viewport.x,y:Number.isFinite(v.y)?v.y:state.viewport.y,scale:clamp(Number.isFinite(v.scale)?v.scale:state.viewport.scale,Z.min,Z.max)};
    state.level=levelFor(state.viewport.scale);if(persist)swrite();old!==state.level?queueRender():queueTransform();
  }
  function fitBounds(b) {
    if(!measure())return;const pad=state.size.w<640?24:48,scale=clamp(Math.min((state.size.w-pad*2)/Math.max(1,b.w),(state.size.h-pad*2)/Math.max(1,b.h)),Z.min,Z.max);
    setViewport({x:(state.size.w-b.w*scale)/2-b.x*scale,y:(state.size.h-b.h*scale)/2-b.y*scale,scale});
  }
  const fitWorld=()=>fitBounds({x:0,y:0,w:state.geometry.w,h:state.geometry.h});
  function fitTerritory(id){const p=state.geometry.territory.get(id);if(p)fitBounds({x:p.x-24,y:p.y-24,w:p.w+48,h:p.h+48})}
  function focusTask(id) {
    const p=state.geometry.task.get(id);if(!p||!measure())return;const scale=clamp(Math.max(1.3,state.viewport.scale),Z.min,Z.max);
    setViewport({x:state.size.w/2-(p.x+p.w/2)*scale,y:state.size.h/2-(p.y+p.h/2)*scale,scale});
  }
  function zoomAt(f,cx,cy) {
    const r=dom.viewport.getBoundingClientRect(),lx=cx-r.left,ly=cy-r.top,old=state.viewport.scale,next=clamp(old*f,Z.min,Z.max),wx=(lx-state.viewport.x)/old,wy=(ly-state.viewport.y)/old;
    setViewport({x:lx-wx*next,y:ly-wy*next,scale:next});
  }
  function zoomCenter(f){const r=dom.viewport.getBoundingClientRect();zoomAt(f,r.left+r.width/2,r.top+r.height/2)}

  function renderSubstrate() {
    dom.substrate.replaceChildren(svg("rect",{x:0,y:0,width:state.geometry.w,height:state.geometry.h,class:"atlas-world-bg"}),svg("rect",{x:0,y:0,width:state.geometry.w,height:state.geometry.h,fill:"url(#atlas-grid)",class:"atlas-world-grid"}));
  }
  function renderCorridors(ids) {
    const f=document.createDocumentFragment();
    for(const e of state.geometry.edges){if(!ids.has(e.source)||!ids.has(e.target))continue;const p=svg("path",{d:e.path,class:"atlas-corridor","vector-effect":"non-scaling-stroke","marker-end":"url(#atlas-arrow)","data-count":e.count});p.style.setProperty("--weight",String(Math.min(5,1+Math.log2(e.count+1))));f.append(p)}
    dom.corridors.replaceChildren(f);
  }
  function heat(t){const k=taskState(t);return k==="blocked"?1:k==="active"?.82:k==="ready"?.68:k==="review"?.55:.18}
  function renderTerritories(ts) {
    const f=document.createDocumentFragment();
    for(const t of ts){
      const p=state.geometry.territory.get(t.id);if(!p||!intersects(p.x,p.y,p.w,p.h,320))continue;
      const c=hue(t.id),g=svg("g",{class:"atlas-territory","data-territory-id":t.id,"data-shape":p.shape,tabindex:0,role:"button","aria-label":`${t.label}. ${t.statistics.total} represented tasks.`});
      g.style.setProperty("--tc",color(c));g.style.setProperty("--tcs",color(c,.18));
      if(state.focusTerritory===t.id)g.classList.add("focused");
      if(state.selected&&state.semantic.taskToTerritory.get(state.selected)===t.id)g.classList.add("selected-territory");
      if(state.lens==="heatmap")g.dataset.heat=String(Math.round((t.tasks.reduce((s,x)=>s+heat(x),0)/Math.max(1,t.tasks.length))*4));
      const inner=p.points.map(([x,y])=>{const cx=p.x+p.w/2,cy=p.y+p.h/2;return[cx+(x-cx)*.972,cy+(y-cy)*.972]});
      const title=svg("text",{x:p.x+28,y:p.y+35,class:"atlas-territory-title"});title.textContent=t.label;
      const meta=svg("text",{x:p.x+28,y:p.y+56,class:"atlas-territory-meta"});meta.textContent=`${t.statistics.total} tasks · ${t.statistics.ready} ready · ${t.statistics.blocked} blocked`;
      const count=svg("text",{x:p.x+p.w-34,y:p.y+37,class:"atlas-territory-count","text-anchor":"middle"});count.textContent=String(t.statistics.total);
      g.append(svg("polygon",{points:pstr(p.points),class:"atlas-territory-outer"}),svg("polygon",{points:pstr(inner),class:"atlas-territory-inner"}),svg("line",{x1:p.x+22,y1:p.y+G.head-14,x2:p.x+Math.min(p.w-22,410),y2:p.y+G.head-14,class:"atlas-territory-header","vector-effect":"non-scaling-stroke"}),title,meta,svg("circle",{cx:p.x+p.w-34,cy:p.y+32,r:17,class:"atlas-territory-count-circle"}),count);
      const track=svg("line",{x1:p.x+28,y1:p.y+p.h-20,x2:p.x+p.w-28,y2:p.y+p.h-20,class:"atlas-progress-track","vector-effect":"non-scaling-stroke"});
      const prog=svg("line",{x1:p.x+28,y1:p.y+p.h-20,x2:p.x+28+(p.w-56)*t.statistics.completionRatio,y2:p.y+p.h-20,class:"atlas-progress","vector-effect":"non-scaling-stroke"});
      g.append(track,prog);f.append(g);
    }
    dom.territories.replaceChildren(f);
  }
  function localIds() {
    const set=new Set();if(!state.selected)return set;const t=state.semantic.taskById.get(state.selected);if(!t)return set;
    set.add(state.selected);for(const d of taskDependencies(t))set.add(d);for(const d of state.semantic.dependents.get(state.selected)??[])set.add(d);
    const p=taskParent(t);if(p)set.add(p);for(const x of state.semantic.tasks)if(taskParent(x)===state.selected)set.add(taskId(x));return set;
  }
  function renderTasks(ts) {
    if(state.level===LEVEL.world){dom.tasks.replaceChildren();dom.taskEdges.replaceChildren();return}
    const f=document.createDocumentFragment(), visible=new Set(), locality=state.level===LEVEL.locality&&state.selected?localIds():null;let labels=96;
    const rec=recommendationId(coreProjection());
    for(const terr of ts){
      const tg=state.geometry.territory.get(terr.id);if(!tg||!intersects(tg.x,tg.y,tg.w,tg.h,220))continue;
      for(const t of terr.tasks){
        const id=taskId(t);if(!filtered(t)||locality&&!locality.has(id))continue;const p=state.geometry.task.get(id);if(!p||!intersects(p.x,p.y,p.w,p.h,90))continue;visible.add(id);
        const g=svg("g",{class:`atlas-task atlas-task-${taskState(t)}`,"data-task-id":id,transform:`translate(${p.x} ${p.y})`,tabindex:0,role:"button","aria-label":`${taskTitle(t)}. ${taskState(t)}. ${taskPriority(t)} priority.`});
        if(id===state.selected)g.classList.add("selected");if(id===rec)g.classList.add("frontier");if(state.route.includes(id))g.classList.add("route");if(state.completed==="fade"&&taskState(t)==="complete")g.classList.add("completion-faded");if(state.lens==="authority")g.dataset.authority=taskAuthority(t);
        g.append(svg("rect",{width:p.w,height:p.h,rx:p.compact?3:5,class:"atlas-task-body"}),svg("rect",{x:8,y:p.h/2-5,width:10,height:10,rx:2,class:"atlas-task-glyph"}));
        if(p.w>=120&&labels>0){const a=svg("text",{x:26,y:21,class:"atlas-task-title"});a.textContent=taskTitle(t).slice(0,state.level===LEVEL.detail?40:26);const b=svg("text",{x:26,y:39,class:"atlas-task-meta"});b.textContent=state.lens==="authority"?taskAuthority(t):`${taskState(t)} · ${taskPriority(t)}`;g.append(a,b);labels--}
        if(id===state.selected)g.append(svg("path",{d:"M -8 -8 L 18 -8 M -8 -8 L -8 18",class:"atlas-here","vector-effect":"non-scaling-stroke"}));f.append(g);
      }
    }
    dom.tasks.replaceChildren(f);renderTaskEdges(visible);
  }
  function renderTaskEdges(visible) {
    if(![LEVEL.locality,LEVEL.detail].includes(state.level)){dom.taskEdges.replaceChildren();return}
    const f=document.createDocumentFragment();
    for(const t of state.semantic.tasks){const target=taskId(t);if(!visible.has(target))continue;const b=state.geometry.task.get(target);if(!b)continue;
      for(const source of taskDependencies(t)){if(!visible.has(source))continue;const a=state.geometry.task.get(source);if(!a||state.semantic.taskToTerritory.get(source)!==state.semantic.taskToTerritory.get(target))continue;
        const sx=a.x+a.w,sy=a.y+a.h/2,tx=b.x,ty=b.y+b.h/2,m=(sx+tx)/2;f.append(svg("path",{d:`M ${sx} ${sy} L ${m} ${sy} L ${m} ${ty} L ${tx} ${ty}`,class:"atlas-task-edge","vector-effect":"non-scaling-stroke","marker-end":"url(#atlas-arrow)"}));
      }
    }dom.taskEdges.replaceChildren(f);
  }
  function renderOverlays(ts) {
    const f=document.createDocumentFragment();
    for(const t of ts)for(const p of state.geometry.ports.get(t.id)??[])f.append(svg("circle",{cx:p.x,cy:p.y,r:7,class:`atlas-port atlas-port-${p.direction}`,"data-territory-id":t.id,"data-count":p.edge.count,tabindex:0,role:"button","aria-label":`${p.direction==="out"?"Outgoing":"Incoming"} territory relationship. ${p.edge.count} represented task relationships.`}));
    const rec=recommendationId(coreProjection()),g=state.geometry.task.get(rec);if(g){const b=svg("g",{class:"atlas-frontier-beacon",transform:`translate(${g.x+g.w/2-12} ${g.y-34})`,"data-task-id":rec});b.append(svg("use",{href:"#atlas-frontier-symbol",width:24,height:24}));f.append(b)}
    dom.overlays.replaceChildren(f);dom.labels.replaceChildren();
    if(state.level===LEVEL.detail&&state.selected){const q=state.geometry.task.get(state.selected);if(q){const x=svg("text",{x:q.x,y:q.y-16,class:"atlas-here-label"});x.textContent="YOU ARE HERE";dom.labels.append(x)}}
  }
  function renderMap() {
    if(!state.ready)return;const ts=visibleTerritories(),ids=new Set(ts.map(t=>t.id));renderSubstrate();renderCorridors(ids);renderTerritories(ts);renderTasks(ts);renderOverlays(ts);applyTransform();
  }
  function queueRender(){if(state.renderQueued)return;state.renderQueued=true;requestAnimationFrame(()=>{state.renderQueued=false;renderAll()})}

  function selectedTask(){return state.semantic.taskById.get(state.selected)??null}
  function renderMetrics() {
    const kept=state.semantic.tasks.filter(filtered).length;
    dom.mTasks.textContent=String(state.semantic.tasks.length);dom.mTerritories.textContent=String(state.semantic.territories.length);dom.mRepresented.textContent=String(state.semantic.tasks.length);dom.mFiltered.textContent=String(state.semantic.tasks.length-kept);dom.delimiter.textContent=state.semantic.delimiter;
  }
  function renderSelected() {
    const t=selectedTask();if(!t){dom.selectedTitle.textContent="No task selected";dom.selectedMeta.textContent="Select a represented task.";dom.location.textContent=state.focusTerritory?state.semantic.territoryById.get(state.focusTerritory)?.label??"TERRITORY":"OVERVIEW";return}
    dom.selectedTitle.textContent=taskTitle(t);dom.selectedMeta.textContent=`${taskState(t)} · ${taskPriority(t)} · ${taskObjective(t)}`;dom.location.textContent=taskTitle(t);
  }
  function renderBreadcrumb() {
    dom.breadcrumb.replaceChildren();const a=document.createElement("button");a.type="button";a.textContent="atlas";a.onclick=()=>{state.focusTerritory=null;state.selected=null;state.route=[];fitWorld();queueRender()};dom.breadcrumb.append(a);
    const t=selectedTask(),tid=t?state.semantic.taskToTerritory.get(taskId(t)):state.focusTerritory,terr=state.semantic.territoryById.get(tid);
    if(terr){const s=document.createElement("span");s.textContent="›";const b=document.createElement("button");b.type="button";b.textContent=terr.label;b.onclick=()=>{state.focusTerritory=terr.id;state.selected=null;fitTerritory(terr.id);queueRender()};dom.breadcrumb.append(s,b)}
    if(t){const s=document.createElement("span");s.textContent="›";const o=document.createElement("span");o.textContent=taskObjective(t);const s2=document.createElement("span");s2.textContent="›";const c=document.createElement("strong");c.textContent=taskTitle(t);dom.breadcrumb.append(s,o,s2,c)}
  }
  function graph(){const g=new Map(state.semantic.tasks.map(t=>[taskId(t),new Set()]));for(const t of state.semantic.tasks){const id=taskId(t);for(const d of taskDependencies(t)){g.get(d)?.add(id);g.get(id)?.add(d)}}return g}
  function route(a,b){if(!state.semantic.taskById.has(a)||!state.semantic.taskById.has(b))return[];const g=graph(),prev=new Map([[a,null]]),q=[a];while(q.length){const c=q.shift();if(c===b){const p=[];let x=b;while(x!==null){p.push(x);x=prev.get(x)}return p.reverse()}for(const n of Array.from(g.get(c)??[]).sort())if(!prev.has(n)){prev.set(n,c);q.push(n)}}return[]}
  function resolveTask(v){const q=low(v);if(!q)return null;return state.semantic.tasks.find(t=>low(taskId(t))===q||low(taskTitle(t))===q)??state.semantic.tasks.find(t=>low(taskTitle(t)).includes(q)||low(taskId(t)).includes(q))??null}
  function renderRoute() {
    dom.route.replaceChildren();if(!state.route.length){const p=document.createElement("p");p.textContent=state.selected?"Choose a represented destination. Route is relational, not execution order.":"Select a starting task first.";dom.route.append(p);return}
    state.route.forEach((id,i)=>{const t=state.semantic.taskById.get(id);if(!t)return;const b=document.createElement("button");b.type="button";b.textContent=`${i+1}. ${taskTitle(t)}`;b.onclick=()=>select(id,true,"route");dom.route.append(b)});
  }
  function renderLegend() {
    const rows=[["territory",`${state.semantic.delimiter} territory`],["task","represented task"],["selected","selected task"],["ready","ready"],["active","active"],["blocked","blocked"],["complete","complete"],["dependency","represented dependency"],["frontier","executable frontier"],["projection","geometry is projection only"]];
    dom.legend.replaceChildren();for(const [k,label] of rows){const r=document.createElement("div"),s=document.createElement("span"),t=document.createElement("span");s.className=`atlas-legend-${k}`;t.textContent=label;r.append(s,t);dom.legend.append(r)}
  }
  function renderIndex() {
    const f=document.createDocumentFragment();for(const terr of visibleTerritories()){const sec=document.createElement("section"),h=document.createElement("button");h.type="button";h.className="atlas-index-territory";h.textContent=`${terr.label} · ${terr.statistics.total}`;h.onclick=()=>{state.focusTerritory=terr.id;fitTerritory(terr.id);queueRender()};sec.append(h);
      if(state.level!==LEVEL.world)for(const t of terr.tasks){if(!filtered(t))continue;const b=document.createElement("button");b.type="button";b.className="atlas-index-task";b.textContent=`${taskTitle(t)} · ${taskState(t)}`;b.onclick=()=>select(taskId(t),true,"index");sec.append(b)}f.append(sec)}dom.index.replaceChildren(f);
  }
  function renderMinimap() {
    dom.minimap.replaceChildren();dom.minimap.setAttribute("viewBox",`0 0 ${state.geometry.w} ${state.geometry.h}`);
    for(const t of state.semantic.territories){const p=state.geometry.territory.get(t.id);if(!p)continue;const x=svg("polygon",{points:pstr(p.points),class:"atlas-mini-territory","data-territory-id":t.id});x.style.fill=color(hue(t.id),.55);dom.minimap.append(x)}renderMiniViewport();
  }
  function renderMiniViewport(){if(!dom.minimap)return;$(".atlas-mini-viewport",dom.minimap)?.remove();const s=state.viewport.scale;dom.minimap.append(svg("rect",{x:-state.viewport.x/s,y:-state.viewport.y/s,width:state.size.w/s,height:state.size.h/s,class:"atlas-mini-viewport"}))}
  function show(kind,title,detail){dom.state.hidden=false;dom.state.dataset.kind=kind;dom.state.innerHTML=`<strong>${title}</strong><span>${detail}</span>`}
  function renderState(){if(!state.ready)return show("loading","LOADING ATLAS PROJECTION","Waiting for the shared Niche semantic projection.");if(!state.semantic.tasks.length)return show("empty","NO REPRESENTED TASKS","Atlas has no represented task substance to spatialize.");if(!visibleTerritories().length)return show("filtered","NO TERRITORIES MATCH CURRENT FILTERS","Reset search or filters to restore the represented world.");dom.state.hidden=true;dom.state.textContent=""}
  function renderAll(){renderState();if(!state.ready)return;renderMetrics();renderSelected();renderBreadcrumb();renderRoute();renderLegend();renderIndex();renderMap();renderMinimap();dom.footerStatus.textContent=`ATLAS ${state.level.toUpperCase()}`}
  function announce(x){dom.live.textContent="";requestAnimationFrame(()=>dom.live.textContent=x)}

  function select(id,focus=false,source="atlas") {
    if(!state.semantic.taskById.has(id))return;if(state.selected&&state.selected!==id){state.back.push(state.selected);state.back=state.back.slice(-50)}state.selected=id;state.focusTerritory=state.semantic.taskToTerritory.get(id)??null;state.route=[];state.recent=[id,...state.recent.filter(x=>x!==id)].slice(0,12);dom.back.disabled=!state.back.length;queueRender();if(focus)focusTask(id);window.Niche?.task?.(id);emit("selection",{task_id:id,source});
  }
  function goBack(){const x=state.back.pop();if(!x)return;state.selected=x;state.focusTerritory=state.semantic.taskToTerritory.get(x)??null;dom.back.disabled=!state.back.length;focusTask(x);queueRender();window.Niche?.task?.(x)}
  function frontier(){const id=recommendationId(coreProjection());if(!id||!state.semantic.taskById.has(id))return announce("No executable frontier is represented.");select(id,true,"frontier")}
  function routeInput(){if(!state.selected)return announce("Select a starting task first.");const t=resolveTask(dom.routeInput.value);if(!t){state.route=[];queueRender();return announce("Destination is not represented.")}state.route=route(state.selected,taskId(t));queueRender();announce(state.route.length?`Represented relationship route contains ${state.route.length} locations. It is not execution order.`:"No represented relationship route was found.")}

  function sync() {
    const p=coreProjection();if(!p){state.ready=false;show("degraded","ATLAS DEGRADED","The shared Niche projection is unavailable. Execute remains independent.");dom.footerStatus.textContent="ATLAS DEGRADED";return}
    const n=normalized(p);if(Number.isFinite(n.generation)&&n.generation<state.generation)return;if(Number.isFinite(n.generation))state.generation=n.generation;
    state.selected=n.selected;state.semantic=buildSemantic(n);state.ready=true;ensureGeometry();queueRender();
  }
  function activateFallback(){for(const s of $$(".surface")){const a=s===dom.surface;s.hidden=!a;s.classList.toggle("active",a)}for(const b of $$(".nav [data-view]"))b.classList.toggle("active",b===dom.nav)}
  function open(){install();state.active=true;try{window.Niche?.view?.(VIEW)}catch{activateFallback()}dom.surface.hidden=false;requestAnimationFrame(onActivate)}
  function onActivate(){state.active=true;if(!measure())return requestAnimationFrame(onActivate);sync();if(!state.firstFit){state.firstFit=true;fitWorld()}else applyTransform();emit("activated")}
  function onDeactivate(){state.active=false;swrite();emit("deactivated")}
  function onResize(){const old=state.size.w<640?"n":state.size.w<1100?"m":"w";if(!measure())return;const now=state.size.w<640?"n":state.size.w<1100?"m":"w";if(old!==now){state.geometry.fingerprint="";ensureGeometry();queueRender()}else queueTransform()}

  function bindMap() {
    dom.viewport.addEventListener("wheel",e=>{e.preventDefault();zoomAt(Math.exp(-e.deltaY*.00125),e.clientX,e.clientY)},{passive:false});
    dom.viewport.addEventListener("click",e=>{const t=e.target.closest?.("[data-task-id]");if(t?.dataset.taskId)return select(t.dataset.taskId,false,"map");const x=e.target.closest?.("[data-territory-id]");if(x?.dataset.territoryId&&state.semantic.territoryById.has(x.dataset.territoryId)){state.focusTerritory=x.dataset.territoryId;state.selected=null;fitTerritory(x.dataset.territoryId);queueRender()}});
    dom.viewport.addEventListener("dblclick",e=>{const t=e.target.closest?.("[data-task-id]");if(t?.dataset.taskId)select(t.dataset.taskId,true,"double-click")});
    dom.viewport.addEventListener("pointerdown",e=>{dom.viewport.setPointerCapture?.(e.pointerId);state.pointer.active.set(e.pointerId,{x:e.clientX,y:e.clientY});if(state.pointer.active.size===1){state.pointer.mode="pan";state.pointer.sx=e.clientX;state.pointer.sy=e.clientY;state.pointer.ox=state.viewport.x;state.pointer.oy=state.viewport.y}else if(state.pointer.active.size===2){const p=Array.from(state.pointer.active.values());state.pointer.mode="pinch";state.pointer.pinch=Math.hypot(p[1].x-p[0].x,p[1].y-p[0].y);state.pointer.scale=state.viewport.scale;state.pointer.cx=(p[0].x+p[1].x)/2;state.pointer.cy=(p[0].y+p[1].y)/2}});
    dom.viewport.addEventListener("pointermove",e=>{if(!state.pointer.active.has(e.pointerId))return;state.pointer.active.set(e.pointerId,{x:e.clientX,y:e.clientY});if(state.pointer.mode==="pan"&&state.pointer.active.size===1)return setViewport({x:state.pointer.ox+e.clientX-state.pointer.sx,y:state.pointer.oy+e.clientY-state.pointer.sy,scale:state.viewport.scale});if(state.pointer.active.size===2){const p=Array.from(state.pointer.active.values()),d=Math.max(1,Math.hypot(p[1].x-p[0].x,p[1].y-p[0].y));zoomAt((state.pointer.scale*(d/Math.max(1,state.pointer.pinch)))/state.viewport.scale,state.pointer.cx,state.pointer.cy)}});
    const done=e=>{state.pointer.active.delete(e.pointerId);if(!state.pointer.active.size)state.pointer.mode=""};dom.viewport.addEventListener("pointerup",done);dom.viewport.addEventListener("pointercancel",done);
    dom.viewport.addEventListener("keydown",e=>{if(e.key==="0"){e.preventDefault();fitWorld()}else if(e.key==="+"){e.preventDefault();zoomCenter(Z.step)}else if(e.key==="-"){e.preventDefault();zoomCenter(1/Z.step)}else if(e.key==="/"){e.preventDefault();dom.search.focus()}else if(e.key==="Escape"){e.preventDefault();if(state.selected){state.selected=null;queueRender()}else if(state.focusTerritory){state.focusTerritory=null;fitWorld();queueRender()}}});
  }
  function bindControls() {
    dom.nav.addEventListener("click",open);dom.fit.onclick=fitWorld;dom.local.onclick=()=>state.selected?focusTask(state.selected):state.focusTerritory?fitTerritory(state.focusTerritory):fitWorld();
    dom.plus.onclick=()=>zoomCenter(Z.step);dom.minus.onclick=()=>zoomCenter(1/Z.step);dom.back.onclick=goBack;dom.frontier.onclick=frontier;dom.focusTask.onclick=()=>state.selected&&focusTask(state.selected);dom.openTask.onclick=()=>state.selected&&window.Niche?.task?.(state.selected);
    dom.search.addEventListener("input",()=>{state.query=dom.search.value.trim();swrite();queueRender()});
    dom.search.addEventListener("keydown",e=>{if(e.key!=="Enter")return;const t=resolveTask(dom.search.value);if(t){e.preventDefault();return select(taskId(t),true,"search")}const terr=state.semantic.territories.find(x=>low(x.label).includes(low(dom.search.value)));if(terr){e.preventDefault();state.focusTerritory=terr.id;fitTerritory(terr.id);queueRender()}});
    dom.status.onchange=()=>{state.status=dom.status.value;swrite();queueRender()};dom.completed.onchange=()=>{state.completed=dom.completed.value;swrite();queueRender()};dom.effects.onchange=()=>{state.effects=dom.effects.value;swrite();queueRender()};
    dom.reset.onclick=()=>{state.query="";state.status="all";state.completed="fade";dom.search.value="";dom.status.value="all";dom.completed.value="fade";swrite();queueRender()};
    dom.lenses.addEventListener("click",e=>{const b=e.target.closest?.("[data-lens]");if(!b)return;state.lens=b.dataset.lens;for(const x of $$("[data-lens]",dom.lenses))x.classList.toggle("active",x===b);swrite();queueRender()});
    dom.routeGo.onclick=routeInput;dom.routeInput.addEventListener("keydown",e=>{if(e.key==="Enter"){e.preventDefault();routeInput()}});
    dom.minimap.addEventListener("click",e=>{const r=dom.minimap.getBoundingClientRect();if(!r.width||!r.height)return;const x=(e.clientX-r.left)/r.width*state.geometry.w,y=(e.clientY-r.top)/r.height*state.geometry.h;setViewport({x:state.size.w/2-x*state.viewport.scale,y:state.size.h/2-y*state.viewport.scale,scale:state.viewport.scale})});
    bindMap();
  }
  function restore() {
    const x=sread();if(!x)return;if(x.viewport&&Number.isFinite(x.viewport.x)&&Number.isFinite(x.viewport.y)&&Number.isFinite(x.viewport.scale)){state.viewport={x:x.viewport.x,y:x.viewport.y,scale:clamp(x.viewport.scale,Z.min,Z.max)};state.level=levelFor(state.viewport.scale)}
    state.query=txt(x.query);state.status=txt(x.status,"all");state.lens=txt(x.lens,"domains");state.completed=txt(x.completed,"fade");state.effects=txt(x.effects,"full");state.focusTerritory=txt(x.focusTerritory)||null;
  }
  function applyPrefs(){dom.search.value=state.query;dom.status.value=state.status;dom.completed.value=state.completed;dom.effects.value=state.effects;for(const b of $$("[data-lens]",dom.lenses))b.classList.toggle("active",b.dataset.lens===state.lens)}
  function bindCore(){for(const n of ["niche:projection","niche:task-selected"])window.addEventListener(n,sync);window.addEventListener("niche:view",e=>{const v=txt(e.detail?.view);if(v===VIEW){state.active=true;requestAnimationFrame(onActivate)}else if(state.active)onDeactivate()})}
  function resize(){if(state.resizeObserver||!dom.viewport)return;if("ResizeObserver"in window){state.resizeObserver=new ResizeObserver(()=>requestAnimationFrame(onResize));state.resizeObserver.observe(dom.viewport)}else window.addEventListener("resize",onResize,{passive:true})}
  function install() {
    if(state.installed)return true;restore();ensureSurface();ensureNav();cache();if(!dom.surface||!dom.viewport||!dom.world)return false;defs();applyPrefs();bindControls();bindCore();resize();state.installed=true;sync();emit("installed");return true;
  }

  const api=Object.freeze({
    open,
    select:(id,o={})=>{install();select(txt(id),Boolean(o.focus),txt(o.source,"api"))},
    fit:fitWorld,
    fitTerritory:id=>{install();fitTerritory(txt(id))},
    frontier,
    back:goBack,
    sync,
    state:()=>Object.freeze({
      installed:state.installed,active:state.active,ready:state.ready,selectedTaskId:state.selected,
      focusedTerritoryId:state.focusTerritory,semanticLevel:state.level,delimiter:state.semantic.delimiter,
      representedTaskCount:state.semantic.tasks.length,representedTerritoryCount:state.semantic.territories.length,
      lens:state.lens,viewport:Object.freeze({...state.viewport}),projectionGeneration:state.generation,
      authorityEffect:"none",projectionOnly:true
    })
  });
  window.NicheAtlas=api;
  window.NicheNavigation=api;

  document.readyState==="loading"
    ? document.addEventListener("DOMContentLoaded",()=>install(),{once:true})
    : install();
})();
