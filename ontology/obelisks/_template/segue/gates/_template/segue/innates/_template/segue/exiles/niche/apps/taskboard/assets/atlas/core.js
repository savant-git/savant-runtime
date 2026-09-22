export function createAtlasContext() {
  const SVG = "http://www.w3.org/2000/svg";
  const VIEW = "navigation";
  const BUILD = "atlas-r13.4-entry-activation";
  const VISUAL_SYSTEM = "atlas-facility-r13";
  const STORE = "savant.niche.atlas.v1";
  const LEVEL = Object.freeze({world:"world",district:"district",locality:"locality",detail:"detail"});
  const Z = Object.freeze({min:.16,max:4.8,world:.54,district:1,locality:1.85,step:1.2});
  const G = Object.freeze({pad:34,gap:10,head:84,inner:22,taskW:176,taskH:48,taskGapX:12,taskGapY:12,minW:420,minH:270});
  const ELK_PROVENANCE = Object.freeze({name:"elkjs",version:"0.12.0",license:"EPL-2.0 OR GPL-3.0-or-later",source:"https://cdn.jsdelivr.net/npm/elkjs@0.12.0/lib/elk.bundled.js",purpose:"optional internal directed task layout and orthogonal topology refinement",authority_effect:"none"});
  const palette = Object.freeze([
    [188,92,58],[213,94,62],[267,88,66],[319,86,62],[8,88,59],[36,94,59],
    [67,80,56],[143,82,52],[166,86,54],[235,86,68],[287,78,65],[343,84,62]
  ]);

  const state = {
    installed:false, active:false, ready:false, generation:-1, renderQueued:false, transformQueued:false,
    level:LEVEL.world, selected:null, focusTerritory:null, query:"", status:"all", priority:"all", lens:"domains",
    completed:"show", effects:"full", railOpen:false, route:[], back:[], forward:[], recent:[], detail:null, filterTouched:false, viewportAnimation:null,
    viewport:{x:0,y:0,scale:1}, size:{w:1,h:1},
    semantic:{delimiter:"objective",tasks:[],taskById:new Map(),dependents:new Map(),territories:[],territoryById:new Map(),taskToTerritory:new Map(),aggregateEdges:[]},
    geometry:{fingerprint:"",territory:new Map(),task:new Map(),ports:new Map(),edges:[],w:1,h:1},
    pointer:{active:new Map(),mode:"",sx:0,sy:0,ox:0,oy:0,pinch:1,scale:1,cx:0,cy:0},
    resizeObserver:null, firstFit:false, suppressClick:false, secondaryQueued:false, secondaryToken:0, renderStageToken:0, gestureMoved:false, railMode:"more", elk:null, elkStatus:"idle", elkPromise:null, elkLayouts:new Map(), elkAppliedFingerprint:""
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
    viewport:state.viewport,query:state.query,status:state.status,priority:state.priority,lens:state.lens,
    completed:state.completed,effects:state.effects,focusTerritory:state.focusTerritory,filterTouched:state.filterTouched
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

  const shapes=["rect","wide","tall","l-right","l-left","step-right","step-left","u","offset","inverted-l","t-bay","dual-wing","corner-cut","double-chamfer","spine-wing","hook-left","hook-right","triple-bay","courtyard","fork","long-concourse"];
  const lifecycle = new Set();
  const masks = Object.freeze({
    world: Object.freeze({territory:true,task:false,edges:false,labels:false}),
    district: Object.freeze({territory:true,task:true,edges:false,labels:false}),
    locality: Object.freeze({territory:true,task:true,edges:true,labels:true}),
    detail: Object.freeze({territory:true,task:true,edges:true,labels:true})
  });
  const moods = Object.freeze({
    restrained: Object.freeze({effects:"reduced"}),
    focused: Object.freeze({focus:true}),
    degraded: Object.freeze({degraded:true}),
    mobile: Object.freeze({mobile:true})
  });
  const onDispose = fn => { if (typeof fn === "function") lifecycle.add(fn); return fn; };
  const dispose = () => { for (const fn of Array.from(lifecycle)) { try { fn(); } catch {} } lifecycle.clear(); };
  return {SVG,VIEW,BUILD,VISUAL_SYSTEM,STORE,LEVEL,Z,G,ELK_PROVENANCE,palette,state,dom,$,$$,txt,low,arr,clamp,hash,sread,swrite,emit,coreProjection,coreState,taskId,taskTitle,taskObjective,taskDomain,taskOwner,taskRubric,taskCabal,taskPriority,taskParent,taskDependencies,taskState,taskAuthority,critical,recommendationId,normalized,chooseDelimiter,stats,buildSemantic,masks,moods,onDispose,dispose};
}
