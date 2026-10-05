"use strict";
(() => {
  "use strict";

  const SVG = "http://www.w3.org/2000/svg";
  const VIEW = "navigation";
  const VISUAL_SYSTEM = "niche-restraint";
  const STORE = "savant.niche.atlas.v1";
  const LEVEL = Object.freeze({world:"world",district:"district",locality:"locality",detail:"detail"});
  const Z = Object.freeze({min:.16,max:4.8,world:.54,district:1,locality:1.85,step:1.2});
  const G = Object.freeze({pad:58,gap:28,head:70,inner:28,taskW:186,taskH:50,taskGapX:18,taskGapY:15,minW:440,minH:290});
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
  function crossingWeight(t) {
    return state.semantic.aggregateEdges.reduce((sum,e)=>sum+(e.source===t.id||e.target===t.id?e.count:0),0);
  }
  function shapeFor(t,i) {
    const crossings=crossingWeight(t), objectives=t.objectives.length, count=t.tasks.length, seed=hash(t.id);
    const depth=Math.max(1,...t.tasks.map(x=>taskDependencies(x).length+1));
    if(count<=4) return "rect";
    if(count>=34&&objectives>=6) return seed%2?"courtyard":"triple-bay";
    if(count>=30&&depth>=4) return seed%2?"long-concourse":"spine-wing";
    if(objectives>=5&&count>=18) return seed%3===0?"fork":seed%2?"dual-wing":"spine-wing";
    if(crossings>=12&&count>=14) return seed%3===0?"hook-right":seed%2?"t-bay":"double-chamfer";
    if(objectives>=4&&count>=12) return seed%3===0?"inverted-l":seed%2?"l-left":"l-right";
    if(count>=24) return seed%3===0?"offset":seed%2?"u":"triple-bay";
    if(count>=18) return seed%2?"step-left":"step-right";
    if(count>=12) return seed%3===0?"corner-cut":"wide";
    if(count>=8&&crossings>=4) return seed%2?"tall":"hook-left";
    return shapes[(seed+i)%shapes.length];
  }
  function dims(t,shape) {
    const rows=Math.ceil(t.tasks.length/Math.max(2,Math.min(6,Math.ceil(Math.sqrt(Math.max(1,t.tasks.length))))));
    let w=Math.max(G.minW,420+Math.min(520,t.tasks.length*16));
    let h=Math.max(G.minH,G.head+G.inner*2+rows*(G.taskH+G.taskGapY));
    if(["wide","u"].includes(shape)){w*=1.25;h*=.9}
    if(shape==="tall"){w*=.82;h*=1.23}
    if(shape.startsWith("l-")||shape.startsWith("step-")||["offset","inverted-l","t-bay","dual-wing","corner-cut","double-chamfer","spine-wing"].includes(shape)){w*=1.12;h*=1.08}
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
      offset:[[x+c,y],[x+w*.66,y],[x+w*.66,y+i*.45],[x+w-c,y+i*.45],[x+w,y+i*.45+c],[x+w,y+h-c],[x+w-c,y+h],[x+c,y+h],[x,y+h-c],[x,y+c]],
      "inverted-l":[[x+c,y],[x+w-c,y],[x+w,y+c],[x+w,y+h-c],[x+w-c,y+h],[x,y+h],[x,y+h*.45],[x+i,y+h*.45],[x+i,y+c],[x,y+c]],
      "t-bay":[[x+w*.28,y],[x+w*.72,y],[x+w*.72,y+i*.38],[x+w-c,y+i*.38],[x+w,y+i*.38+c],[x+w,y+h-c],[x+w-c,y+h],[x+c,y+h],[x,y+h-c],[x,y+i*.38+c],[x+c,y+i*.38],[x+w*.28,y+i*.38]],
      "dual-wing":[[x+c,y],[x+w*.42,y],[x+w*.42,y+i*.4],[x+w*.58,y+i*.4],[x+w*.58,y],[x+w-c,y],[x+w,y+c],[x+w,y+h-c],[x+w-c,y+h],[x+w*.58,y+h],[x+w*.58,y+h-i*.4],[x+w*.42,y+h-i*.4],[x+w*.42,y+h],[x+c,y+h],[x,y+h-c],[x,y+c]],
      "corner-cut":[[x+i,y],[x+w-c,y],[x+w,y+c],[x+w,y+h-c],[x+w-c,y+h],[x+c,y+h],[x,y+h-c],[x,y+i]],
      "double-chamfer":[[x+i,y],[x+w-i,y],[x+w,y+i],[x+w,y+h-i],[x+w-i,y+h],[x+i,y+h],[x,y+h-i],[x,y+i]],
      "spine-wing":[[x+c,y],[x+w*.58,y],[x+w*.58,y+h*.32],[x+w-c,y+h*.32],[x+w,y+h*.32+c],[x+w,y+h*.68-c],[x+w-c,y+h*.68],[x+w*.58,y+h*.68],[x+w*.58,y+h],[x+c,y+h],[x,y+h-c],[x,y+c]],
      "hook-left":[[x+c,y],[x+w-c,y],[x+w,y+c],[x+w,y+h*.44],[x+w*.58,y+h*.44],[x+w*.58,y+h-c],[x+w*.58-c,y+h],[x+c,y+h],[x,y+h-c],[x,y+c]],
      "hook-right":[[x+c,y],[x+w-c,y],[x+w,y+c],[x+w,y+h-c],[x+w-c,y+h],[x+w*.42,y+h],[x+w*.42,y+h*.44],[x,y+h*.44],[x,y+c]],
      "triple-bay":[[x+c,y],[x+w*.30,y],[x+w*.30,y+i*.38],[x+w*.42,y+i*.38],[x+w*.42,y],[x+w*.58,y],[x+w*.58,y+i*.38],[x+w*.70,y+i*.38],[x+w*.70,y],[x+w-c,y],[x+w,y+c],[x+w,y+h-c],[x+w-c,y+h],[x+c,y+h],[x,y+h-c],[x,y+c]],
      "courtyard":[[x+c,y],[x+w-c,y],[x+w,y+c],[x+w,y+h-c],[x+w-c,y+h],[x+w*.64,y+h],[x+w*.64,y+h*.62],[x+w*.36,y+h*.62],[x+w*.36,y+h],[x+c,y+h],[x,y+h-c],[x,y+c]],
      "fork":[[x+c,y],[x+w*.38,y],[x+w*.38,y+h*.34],[x+w*.48,y+h*.34],[x+w*.48,y],[x+w*.62,y],[x+w*.62,y+h*.34],[x+w*.72,y+h*.34],[x+w*.72,y],[x+w-c,y],[x+w,y+c],[x+w,y+h-c],[x+w-c,y+h],[x+c,y+h],[x,y+h-c],[x,y+c]],
      "long-concourse":[[x+c,y],[x+w-c,y],[x+w,y+c],[x+w,y+h*.72-c],[x+w-c,y+h*.72],[x+w*.66,y+h*.72],[x+w*.66,y+h-c],[x+w*.66-c,y+h],[x+w*.22+c,y+h],[x+w*.22,y+h-c],[x+w*.22,y+h*.72],[x+c,y+h*.72],[x,y+h*.72-c],[x,y+c]]
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
  function territoryCentrality(id) {
    return state.semantic.aggregateEdges.reduce((sum,e)=>sum+(e.source===id||e.target===id?e.count:0),0);
  }
  function orderedTerritories(territories) {
    return territories.slice().sort((a,b)=>territoryCentrality(b.id)-territoryCentrality(a.id)||b.tasks.length-a.tasks.length||a.id.localeCompare(b.id));
  }
  function packScore(rect,item,placed) {
    const leftoverH=Math.max(0,rect.h-item.h), leftoverW=Math.max(0,rect.w-item.w);
    const shortSide=Math.min(leftoverW,leftoverH), longSide=Math.max(leftoverW,leftoverH);
    let relationPenalty=0;
    const related=state.semantic.aggregateEdges.filter(e=>e.source===item.t.id||e.target===item.t.id);
    if(related.length&&placed.size){
      const cx=rect.x+item.w/2,cy=rect.y+item.h/2;
      let weighted=0,total=0;
      for(const e of related){
        const other=e.source===item.t.id?e.target:e.source;
        const pg=placed.get(other); if(!pg)continue;
        const ox=pg.x+pg.w/2,oy=pg.y+pg.h/2;
        weighted+=Math.hypot(cx-ox,cy-oy)*e.count;
        total+=e.count;
      }
      if(total)relationPenalty=weighted/total*.12;
    }
    return shortSide*6+longSide*1.35+relationPenalty;
  }
  function splitFreeRect(free,used) {
    const out=[];
    const fx2=free.x+free.w, fy2=free.y+free.h, ux2=used.x+used.w, uy2=used.y+used.h;
    if(used.x>=fx2||ux2<=free.x||used.y>=fy2||uy2<=free.y)return[free];
    if(used.x>free.x)out.push({x:free.x,y:free.y,w:used.x-free.x,h:free.h});
    if(ux2<fx2)out.push({x:ux2,y:free.y,w:fx2-ux2,h:free.h});
    if(used.y>free.y)out.push({x:free.x,y:free.y,w:free.w,h:used.y-free.y});
    if(uy2<fy2)out.push({x:free.x,y:uy2,w:free.w,h:fy2-uy2});
    return out.filter(r=>r.w>=80&&r.h>=80);
  }
  function pruneFreeRects(rects) {
    return rects.filter((a,i)=>!rects.some((b,j)=>i!==j&&a.x>=b.x&&a.y>=b.y&&a.x+a.w<=b.x+b.w&&a.y+a.h<=b.y+b.h));
  }
  function maxRectsCandidate(items,targetW,targetH) {
    let free=[{x:G.pad,y:G.pad,w:targetW-G.pad*2,h:targetH-G.pad*2}], placed=new Map(), failed=false;
    for(const item of items){
      let best=null,bestScore=Infinity;
      for(const r of free){
        if(item.w>r.w||item.h>r.h)continue;
        const candidate={x:r.x,y:r.y,w:item.w,h:item.h};
        const score=packScore(r,item,placed);
        if(score<bestScore){bestScore=score;best=candidate}
      }
      if(!best){failed=true;break}
      placed.set(item.t.id,{id:item.t.id,x:best.x,y:best.y,w:item.w,h:item.h,shape:item.shape,points:polygon(best.x,best.y,item.w,item.h,item.shape)});
      free=pruneFreeRects(free.flatMap(r=>splitFreeRect(r,best)));
    }
    if(failed)return null;
    let w=1,h=1;
    for(const p of placed.values()){w=Math.max(w,p.x+p.w+G.pad);h=Math.max(h,p.y+p.h+G.pad)}
    const worldArea=w*h, usedArea=items.reduce((s,x)=>s+x.w*x.h,0);
    const aspect=w/Math.max(1,h), desired=clamp(state.size.w/Math.max(1,state.size.h),.72,1.9);
    const score=(worldArea-usedArea)+Math.abs(Math.log(aspect/desired))*usedArea*.6;
    return {out:placed,w,h,score};
  }
  function pack(territories) {
    const aspect=clamp(state.size.w/Math.max(1,state.size.h),.72,1.9);
    const items=orderedTerritories(territories).map((t,i)=>{const shape=shapeFor(t,i);return {t,shape,...dims(t,shape)}})
      .sort((a,b)=>b.w*b.h-a.w*a.h||territoryCentrality(b.t.id)-territoryCentrality(a.t.id)||a.t.id.localeCompare(b.t.id));
    const area=items.reduce((s,x)=>s+x.w*x.h,0);
    const baseW=Math.max(1400,Math.sqrt(area*aspect)*1.08);
    const candidates=[];
    for(const multiplier of [1,1.08,1.16,1.26]){
      const targetW=Math.ceil(baseW*multiplier);
      const targetH=Math.ceil(Math.max(1000,area/targetW*1.55));
      const c=maxRectsCandidate(items,targetW,targetH);
      if(c)candidates.push(c);
    }
    if(candidates.length)return candidates.sort((a,b)=>a.score-b.score||a.w-b.w)[0];

    const out=new Map();let x=G.pad,y=G.pad,rowH=0,target=baseW;
    for(const item of items){
      if(x+item.w>target&&x>G.pad){x=G.pad;y+=rowH+G.gap;rowH=0}
      out.set(item.t.id,{id:item.t.id,x,y,w:item.w,h:item.h,shape:item.shape,points:polygon(x,y,item.w,item.h,item.shape)});
      x+=item.w+G.gap;rowH=Math.max(rowH,item.h);
    }
    let w=1,h=1;for(const p of out.values()){w=Math.max(w,p.x+p.w+G.pad);h=Math.max(h,p.y+p.h+G.pad)}
    return {out,w,h};
  }
  function taskLayout(t,p) {
    const map=new Map(), left=p.x+G.inner,top=p.y+G.head+G.inner,right=p.x+p.w-G.inner,bottom=p.y+p.h-G.inner;
    const cols=Math.max(1,Math.floor((right-left+G.taskGapX)/(G.taskW+G.taskGapX)));
    let idx=0;
    for(const task of t.tasks.slice().sort((a,b)=>taskObjective(a).localeCompare(taskObjective(b))||taskTitle(a).localeCompare(taskTitle(b))||taskId(a).localeCompare(taskId(b)))){
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
  function loadElk() {
    if(state.elkStatus==="ready"&&state.elk)return Promise.resolve(state.elk);
    if(state.elkPromise)return state.elkPromise;
    if(window.ELK){
      state.elk=new window.ELK();
      state.elkStatus="ready";
      return Promise.resolve(state.elk);
    }
    state.elkStatus="loading";
    state.elkPromise=new Promise(resolve=>{
      const existing=document.querySelector('script[data-atlas-elk="0.12.0"]');
      if(existing){
        existing.addEventListener("load",()=>{state.elk=window.ELK?new window.ELK():null;state.elkStatus=state.elk?"ready":"fallback";resolve(state.elk)},{once:true});
        existing.addEventListener("error",()=>{state.elkStatus="fallback";resolve(null)},{once:true});
        return;
      }
      const script=document.createElement("script");
      script.src=ELK_PROVENANCE.source;
      script.async=true;
      script.dataset.atlasElk="0.12.0";
      script.crossOrigin="anonymous";
      script.addEventListener("load",()=>{
        state.elk=window.ELK?new window.ELK():null;
        state.elkStatus=state.elk?"ready":"fallback";
        emit("layout-library",{library:"elkjs",version:"0.12.0",status:state.elkStatus});
        resolve(state.elk);
      },{once:true});
      script.addEventListener("error",()=>{
        state.elkStatus="fallback";
        emit("layout-library",{library:"elkjs",version:"0.12.0",status:"fallback"});
        resolve(null);
      },{once:true});
      document.head.append(script);
    });
    return state.elkPromise;
  }
  function localDependencyEdges(t) {
    const ids=new Set(t.tasks.map(taskId)), edges=[];
    for(const task of t.tasks){
      const target=taskId(task);
      for(const source of taskDependencies(task))if(ids.has(source))edges.push({source,target});
    }
    return edges.sort((a,b)=>a.source.localeCompare(b.source)||a.target.localeCompare(b.target));
  }
  async function elkTaskLayout(t,p) {
    const elk=await loadElk();
    if(!elk||t.tasks.length<5)return null;
    const edges=localDependencyEdges(t);
    if(!edges.length)return null;
    const graph={
      id:`atlas:${t.id}`,
      layoutOptions:{
        "elk.algorithm":"layered",
        "elk.direction":p.w>=p.h?"RIGHT":"DOWN",
        "elk.edgeRouting":"ORTHOGONAL",
        "elk.layered.considerModelOrder.strategy":"NODES_AND_EDGES",
        "elk.spacing.nodeNode":"28",
        "elk.layered.spacing.nodeNodeBetweenLayers":"44",
        "elk.padding":"[top=20,left=20,bottom=20,right=20]"
      },
      children:t.tasks.slice().sort((a,b)=>taskId(a).localeCompare(taskId(b))).map(task=>({id:taskId(task),width:G.taskW,height:G.taskH})),
      edges:edges.map((e,i)=>({id:`e${i}:${e.source}>${e.target}`,sources:[e.source],targets:[e.target]}))
    };
    try{
      const result=await elk.layout(graph);
      const left=p.x+G.inner,top=p.y+G.head+G.inner;
      const availW=Math.max(1,p.w-G.inner*2),availH=Math.max(1,p.h-G.head-G.inner*2);
      const rw=Math.max(1,result.width||availW),rh=Math.max(1,result.height||availH);
      const scale=Math.min(1,availW/rw,availH/rh);
      const map=new Map();
      for(const node of result.children||[]){
        const x=left+(node.x||0)*scale,y=top+(node.y||0)*scale;
        const w=G.taskW*scale,h=G.taskH*scale;
        const samples=[[x,y],[x+w,y],[x,y+h],[x+w,y+h],[x+w/2,y+h/2]].map(([sx,sy])=>({x:sx,y:sy}));
        if(samples.every(q=>inside(q,p.points)))map.set(node.id,{x,y,w,h,territoryId:t.id,elk:true});
      }
      return map.size>=Math.max(3,Math.floor(t.tasks.length*.65))?map:null;
    }catch{
      state.elkStatus="fallback";
      return null;
    }
  }
  function scheduleElkRefinement() {
    if(!state.active||!state.ready||state.level===LEVEL.world)return;
    const fp=state.geometry.fingerprint;
    if(state.elkAppliedFingerprint===fp)return;
    state.elkAppliedFingerprint=fp;
    const visible=visibleTerritories().filter(t=>{
      const p=state.geometry.territory.get(t.id);
      return p&&intersects(p.x,p.y,p.w,p.h,420)&&t.tasks.length>=5;
    });
    if(!visible.length)return;
    Promise.all(visible.map(async t=>{
      const p=state.geometry.territory.get(t.id);
      const layout=await elkTaskLayout(t,p);
      if(layout)state.elkLayouts.set(t.id,layout);
    })).then(()=>{
      if(fp!==state.geometry.fingerprint)return;
      let changed=false;
      for(const t of visible){
        const layout=state.elkLayouts.get(t.id);
        if(!layout)continue;
        for(const [id,g] of layout){state.geometry.task.set(id,g);changed=true}
      }
      if(changed){
        emit("layout-refined",{library:"elkjs",version:"0.12.0",territories:visible.length});
        queueRender();
      }
    });
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
    state.elkLayouts.clear();state.elkAppliedFingerprint="";
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
          <div class="atlas-commandbar" aria-label="Atlas commands">
            <input id="atlas-search" class="atlas-input atlas-command-search" type="search" autocomplete="off" placeholder="Find work…" aria-label="Search Atlas">
            <button id="atlas-view-toggle" class="atlas-command" type="button" aria-controls="atlas-rail">VIEW</button>
            <button id="atlas-filter-toggle" class="atlas-command" type="button" aria-controls="atlas-rail">FILTER</button>
            <button id="atlas-fit" class="atlas-command" type="button" title="Fit full represented world">FIT</button>
            <button id="atlas-frontier" class="atlas-command atlas-command-frontier" type="button" title="Take me to the executable frontier">NEXT</button>
            <select id="atlas-theme" class="atlas-select atlas-theme-select" aria-label="Atlas theme"></select>
            <button id="atlas-rail-toggle" class="atlas-command atlas-rail-toggle" type="button" aria-expanded="false" aria-controls="atlas-rail">MORE</button>
          </div>
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
              <div class="atlas-map-controls atlas-map-zoom" aria-label="Atlas zoom controls">
                <button id="atlas-plus" type="button" title="Zoom in" aria-label="Zoom in">+</button><button id="atlas-minus" type="button" title="Zoom out" aria-label="Zoom out">−</button>
              </div>
              <div class="atlas-orientation"><span id="atlas-zoom">100%</span><strong id="atlas-level">WORLD</strong><span id="atlas-location">OVERVIEW</span></div>
              <div id="atlas-state" class="atlas-state" hidden></div>
            </div>
            <div id="atlas-breadcrumb" class="atlas-breadcrumb" aria-label="Atlas breadcrumb"></div>
            <div class="atlas-selected-strip">
              <div><span>SELECTED TASK</span><strong id="atlas-selected-title">No task selected</strong><small id="atlas-selected-meta">Select a represented task.</small></div>
              <div class="atlas-selected-actions">
                <button id="atlas-open-task" type="button">OPEN</button><button id="atlas-focus-task" type="button">FOCUS</button>
                <button id="atlas-back" type="button" disabled>BACK</button><button id="atlas-forward" type="button" disabled>FORWARD</button>
              </div>
            </div>
          </section>
          <aside class="atlas-rail" id="atlas-rail" data-rail-mode="more">
            <section class="atlas-panel"><div class="atlas-panel-heading"><h2>OVERALL TOPOLOGY</h2><span id="atlas-delimiter">objective</span></div><svg id="atlas-minimap" class="atlas-minimap" aria-label="Atlas minimap"></svg></section>
            <section class="atlas-panel atlas-panel-view" data-rail-section="view"><div class="atlas-panel-heading"><h2>VIEW</h2></div><div id="atlas-lenses" class="atlas-lenses">
              <button data-lens="domains" class="active" type="button">WORLD</button><button data-lens="heatmap" type="button">HEAT</button>
              <button data-lens="dependencies" type="button">FLOW</button><button data-lens="authority" type="button">AUTHORITY</button>
            </div></section>
            <section class="atlas-panel atlas-panel-filter" data-rail-section="filter"><div class="atlas-panel-heading"><h2>FILTER</h2><button id="atlas-reset" type="button">RESET</button></div>
              <select id="atlas-status" class="atlas-select"><option value="all">All states</option><option value="ready">Ready</option><option value="active">Active</option><option value="review">Review</option><option value="waiting">Waiting</option><option value="blocked">Blocked</option><option value="complete">Complete</option><option value="unknown">Unknown</option></select><select id="atlas-priority" class="atlas-select"><option value="all">All priorities</option><option value="critical">Critical</option><option value="high">High</option><option value="medium">Medium</option><option value="low">Low</option><option value="unknown">Unknown</option></select>
              <select id="atlas-completed" class="atlas-select"><option value="fade">Fade completed</option><option value="show">Show completed</option><option value="hide">Hide completed</option></select>
              <select id="atlas-effects" class="atlas-select"><option value="full">Full effects</option><option value="reduced">Reduced effects</option></select>
            </section>
            <section class="atlas-panel atlas-detail-panel" data-rail-section="more"><div class="atlas-panel-heading"><h2>LOCATION DETAIL</h2></div><div id="atlas-detail" class="atlas-detail"><p>Select a territory, port, or task.</p></div></section><section class="atlas-panel" data-rail-section="more"><div class="atlas-panel-heading"><h2>ROUTE</h2></div><input id="atlas-route-input" class="atlas-input" type="search" placeholder="Destination task…"><button id="atlas-route-go" class="atlas-wide" type="button">TRACE ROUTE</button><div id="atlas-route" class="atlas-route"></div></section>
            <section class="atlas-panel" data-rail-section="more"><div class="atlas-panel-heading"><h2>LEGEND</h2></div><div id="atlas-legend" class="atlas-legend"></div></section>
            <section class="atlas-panel atlas-help" data-rail-section="more"><div class="atlas-panel-heading"><h2>QUICK HELP</h2></div><dl><dt>Click / tap</dt><dd>Select</dd><dt>Drag</dt><dd>Pan</dd><dt>Pinch / wheel</dt><dd>Zoom</dd><dt>Double click</dt><dd>Focus</dd><dt>0</dt><dd>Fit world</dd><dt>/</dt><dd>Search</dd><dt>Esc</dt><dd>Step outward</dd></dl></section>
            <section class="atlas-panel" data-rail-section="more"><div class="atlas-panel-heading"><h2>ACCESSIBLE INDEX</h2></div><div id="atlas-index" class="atlas-index"></div></section>
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
  function queueTransform() { if(state.transformQueued)return;state.transformQueued=true;requestAnimationFrame(()=>{state.transformQueued=false;applyTransform();renderMiniViewport()}); }
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

  function renderSubstrate() {
    const f=document.createDocumentFragment();
    f.append(svg("rect",{x:0,y:0,width:state.geometry.w,height:state.geometry.h,class:"atlas-world-bg"}));
    for(const p of state.geometry.territory.values()){
      f.append(svg("rect",{x:p.x-12,y:p.y-12,width:p.w+24,height:p.h+24,rx:8,class:"atlas-concourse-pad"}));
    }
    f.append(svg("rect",{x:0,y:0,width:state.geometry.w,height:state.geometry.h,fill:"url(#atlas-grid)",class:"atlas-world-grid"}));
    dom.substrate.replaceChildren(f);
  }
  function renderCorridors(ids) {
    const f=document.createDocumentFragment();
    for(const e of state.geometry.edges){if(!ids.has(e.source)||!ids.has(e.target))continue;const base=svg("path",{d:e.path,class:"atlas-corridor-base","vector-effect":"non-scaling-stroke"});const p=svg("path",{d:e.path,class:"atlas-corridor","vector-effect":"non-scaling-stroke","marker-end":"url(#atlas-arrow)","data-count":e.count});p.style.setProperty("--weight",String(Math.min(5,1+Math.log2(e.count+1))));f.append(base,p)}
    dom.corridors.replaceChildren(f);
  }
  function heat(t){const k=taskState(t);return k==="blocked"?1:k==="active"?.82:k==="ready"?.68:k==="review"?.55:.18}
  function subzones(t,p) {
    const groups=new Map();
    for(const task of t.tasks){const o=taskObjective(task);if(!groups.has(o))groups.set(o,[]);groups.get(o).push(task)}
    const items=Array.from(groups.entries()).sort((a,b)=>b[1].length-a[1].length||a[0].localeCompare(b[0]));
    const x=p.x+G.inner,y=p.y+G.head+6,w=Math.max(1,p.w-G.inner*2),h=Math.max(1,p.h-G.head-G.inner-28),total=Math.max(1,t.tasks.length);
    let cursor=x;
    return items.map(([objective,tasks],i)=>{
      const remaining=x+w-cursor, proportional=w*(tasks.length/total);
      const width=i===items.length-1?remaining:Math.max(40,Math.min(remaining,proportional));
      const z={objective,count:tasks.length,x:cursor,y,w:width,h};cursor+=width;return z;
    });
  }
  function renderSubzones(g,t,p) {
    if(![LEVEL.district,LEVEL.locality,LEVEL.detail].includes(state.level))return;
    for(const z of subzones(t,p)){
      g.append(svg("rect",{x:z.x,y:z.y,width:Math.max(0,z.w-4),height:z.h,rx:4,class:"atlas-objective-zone","data-objective":z.objective}));
      if(state.level===LEVEL.detail&&z.w>=96){const label=svg("text",{x:z.x+8,y:z.y+16,class:"atlas-objective-zone-label"});label.textContent=`${z.objective} · ${z.count}`;g.append(label)}
    }
  }

  function renderTerritoryCircuitry(g,t,p){
    if(state.level===LEVEL.world)return;
    const coreX=p.x+p.w*.5,coreY=p.y+Math.min(p.h*.56,G.head+Math.max(100,(p.h-G.head)*.45));
    const ring=svg("circle",{cx:coreX,cy:coreY,r:state.level===LEVEL.detail?24:18,class:"atlas-territory-core"});
    g.append(ring,svg("circle",{cx:coreX,cy:coreY,r:5,class:"atlas-territory-core-dot"}));
    const candidates=t.tasks.map(task=>state.geometry.task.get(taskId(task))).filter(Boolean).slice(0,state.level===LEVEL.detail?18:10);
    for(const q of candidates){
      const tx=q.x+q.w/2,ty=q.y+q.h/2,mx=coreX+(tx-coreX)*.55;
      g.append(svg("path",{d:`M ${coreX} ${coreY} L ${mx} ${coreY} L ${mx} ${ty} L ${tx} ${ty}`,class:"atlas-territory-circuit","vector-effect":"non-scaling-stroke"}));
    }
    const mark=18;
    for(const [x,y,sx,sy] of [[p.x+16,p.y+16,1,1],[p.x+p.w-16,p.y+16,-1,1],[p.x+16,p.y+p.h-16,1,-1],[p.x+p.w-16,p.y+p.h-16,-1,-1]]){
      g.append(svg("path",{d:`M ${x} ${y+sy*mark} L ${x} ${y} L ${x+sx*mark} ${y}`,class:"atlas-territory-corner","vector-effect":"non-scaling-stroke"}));
    }
  }

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
      g.append(svg("polygon",{points:pstr(p.points),class:"atlas-territory-outer"}),svg("polygon",{points:pstr(inner),class:"atlas-territory-inner"}));renderSubzones(g,t,p);renderTerritoryCircuitry(g,t,p);g.append(svg("line",{x1:p.x+22,y1:p.y+G.head-14,x2:p.x+Math.min(p.w-22,410),y2:p.y+G.head-14,class:"atlas-territory-header","vector-effect":"non-scaling-stroke"}),title,meta,svg("circle",{cx:p.x+p.w-34,cy:p.y+32,r:17,class:"atlas-territory-count-circle"}),count);
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
        g.append(svg("rect",{width:p.w,height:p.h,rx:p.compact?3:5,class:"atlas-task-body"}),svg("rect",{x:8,y:p.h/2-5,width:10,height:10,rx:2,class:"atlas-task-glyph"}));if(taskState(t)==="blocked")g.append(svg("path",{d:`M 2 ${p.h-2} L ${p.w-2} 2`,class:"atlas-task-blocked-slash","vector-effect":"non-scaling-stroke"}));
        if(p.w*state.viewport.scale>=86&&p.h*state.viewport.scale>=28&&labels>0){const a=svg("text",{x:26,y:21,class:"atlas-task-title"});a.textContent=taskTitle(t).slice(0,state.level===LEVEL.detail?40:26);const b=svg("text",{x:26,y:39,class:"atlas-task-meta"});b.textContent=state.lens==="authority"?taskAuthority(t):`${taskState(t)} · ${taskPriority(t)}`;g.append(a,b);labels--}
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
  function renderRouteEdges(layer) {
    for(let i=0;i<state.route.length-1;i++){
      const a=state.geometry.task.get(state.route[i]),b=state.geometry.task.get(state.route[i+1]);if(!a||!b)continue;
      const sx=a.x+a.w/2,sy=a.y+a.h/2,tx=b.x+b.w/2,ty=b.y+b.h/2,m=(sx+tx)/2;
      layer.append(svg("path",{d:`M ${sx} ${sy} L ${m} ${sy} L ${m} ${ty} L ${tx} ${ty}`,class:"atlas-route-edge","vector-effect":"non-scaling-stroke","marker-end":"url(#atlas-arrow)"}));
    }
  }
  function renderSelectedNeighborhood(layer) {
    if(!state.selected||![LEVEL.locality,LEVEL.detail].includes(state.level))return;
    const t=state.semantic.taskById.get(state.selected),a=state.geometry.task.get(state.selected);if(!t||!a)return;
    const ids=new Set([...taskDependencies(t),...(state.semantic.dependents.get(state.selected)??[])]);
    for(const id of ids){const b=state.geometry.task.get(id);if(!b)continue;
      layer.append(svg("path",{d:`M ${a.x+a.w/2} ${a.y+a.h/2} L ${b.x+b.w/2} ${b.y+b.h/2}`,class:"atlas-selected-neighborhood-edge","vector-effect":"non-scaling-stroke"}));
    }
  }

  function renderOverlays(ts) {
    const f=document.createDocumentFragment();
    for(const t of ts)for(const p of state.geometry.ports.get(t.id)??[]){f.append(svg("circle",{cx:p.x,cy:p.y,r:7,class:`atlas-port atlas-port-${p.direction}`,"data-territory-id":t.id,"data-port-direction":p.direction,"data-edge-source":p.edge.source,"data-edge-target":p.edge.target,"data-count":p.edge.count,tabindex:0,role:"button","aria-label":`${p.direction==="out"?"Outgoing":"Incoming"} territory relationship. ${p.edge.count} represented task relationships.`}))}
    const rec=recommendationId(coreProjection()),g=state.geometry.task.get(rec);if(g){const b=svg("g",{class:"atlas-frontier-beacon",transform:`translate(${g.x+g.w/2-12} ${g.y-34})`,"data-task-id":rec});b.append(svg("use",{href:"#atlas-frontier-symbol",width:24,height:24}));f.append(b)}
    dom.overlays.replaceChildren(f);renderRouteEdges(dom.overlays);renderSelectedNeighborhood(dom.overlays);dom.labels.replaceChildren();
    if(state.level===LEVEL.detail&&state.selected){const q=state.geometry.task.get(state.selected);if(q){const x=svg("text",{x:q.x,y:q.y-16,class:"atlas-here-label"});x.textContent="YOU ARE HERE";dom.labels.append(x)}}
  }
  function scheduleStage(fn,timeout=72){
    const token=state.renderStageToken;
    const run=()=>{if(token!==state.renderStageToken||!state.active)return;fn()};
    if("requestIdleCallback" in window)window.requestIdleCallback(run,{timeout});
    else setTimeout(run,16);
  }
  function renderMap() {
    if(!state.ready)return;
    const ts=visibleTerritories(),ids=new Set(ts.map(t=>t.id));
    state.renderStageToken+=1;
    renderSubstrate();
    renderCorridors(ids);
    renderTerritories(ts);
    applyTransform();
    if(state.level===LEVEL.world){
      dom.tasks.replaceChildren();
      dom.taskEdges.replaceChildren();
      renderOverlays(ts);
      return;
    }
    scheduleStage(()=>{
      renderTasks(ts);
      renderOverlays(ts);
      scheduleElkRefinement();
    },52);
  }
  function queueRender(){if(state.renderQueued)return;state.renderQueued=true;requestAnimationFrame(()=>{state.renderQueued=false;renderAll()})}

  function selectedTask(){return state.semantic.taskById.get(state.selected)??null}
  function renderDetail() {
    if(!dom.detail)return;
    const task=selectedTask();
    if(task){
      const id=taskId(task),terrId=state.semantic.taskToTerritory.get(id),terr=state.semantic.territoryById.get(terrId);
      const requires=taskDependencies(task).filter(x=>state.semantic.taskById.has(x)).length;
      const dependents=(state.semantic.dependents.get(id)??[]).length;
      dom.detail.innerHTML=`<dl><dt>task</dt><dd>${taskTitle(task)}</dd><dt>state</dt><dd>${taskState(task)}</dd><dt>priority</dt><dd>${taskPriority(task)}</dd><dt>territory</dt><dd>${terr?.label??"unknown"}</dd><dt>objective</dt><dd>${taskObjective(task)}</dd><dt>requires</dt><dd>${requires}</dd><dt>dependents</dt><dd>${dependents}</dd><dt>authority</dt><dd>${taskAuthority(task)}</dd></dl>`;
      return;
    }
    if(state.detail?.type==="port"){
      const d=state.detail;
      dom.detail.innerHTML=`<dl><dt>port</dt><dd>${d.direction}</dd><dt>relationships</dt><dd>${d.count}</dd><dt>source</dt><dd>${d.sourceLabel}</dd><dt>destination</dt><dd>${d.targetLabel}</dd><dt>meaning</dt><dd>represented dependency crossing</dd></dl>`;
      return;
    }
    const terr=state.semantic.territoryById.get(state.focusTerritory);
    if(terr){
      const crossings=state.semantic.aggregateEdges.filter(e=>e.source===terr.id||e.target===terr.id).reduce((s,e)=>s+e.count,0);
      dom.detail.innerHTML=`<dl><dt>${terr.delimiter}</dt><dd>${terr.label}</dd><dt>tasks</dt><dd>${terr.statistics.total}</dd><dt>ready</dt><dd>${terr.statistics.ready}</dd><dt>active</dt><dd>${terr.statistics.active}</dd><dt>blocked</dt><dd>${terr.statistics.blocked}</dd><dt>complete</dt><dd>${terr.statistics.complete}</dd><dt>objectives</dt><dd>${terr.objectives.length}</dd><dt>boundary crossings</dt><dd>${crossings}</dd><dt>geometry</dt><dd>projection only</dd></dl>`;
      return;
    }
    dom.detail.innerHTML="<p>Select a territory, port, or task.</p>";
  }

  function renderMetrics() {
    const kept=state.semantic.tasks.filter(filtered).length;
    dom.mTasks.textContent=String(state.semantic.tasks.length);dom.mTerritories.textContent=String(state.semantic.territories.length);dom.mRepresented.textContent=String(state.semantic.tasks.length);dom.mFiltered.textContent=String(state.semantic.tasks.length-kept);dom.delimiter.textContent=state.semantic.delimiter;
  }
  function renderSelected() {
    const t=selectedTask();if(!t){dom.selectedTitle.textContent="No task selected";dom.selectedMeta.textContent="Select a represented task.";dom.forward.disabled=!state.forward.length;dom.location.textContent=state.focusTerritory?state.semantic.territoryById.get(state.focusTerritory)?.label??"TERRITORY":"OVERVIEW";return}
    dom.selectedTitle.textContent=taskTitle(t);dom.selectedMeta.textContent=`${taskState(t)} · ${taskPriority(t)} · ${taskObjective(t)}`;dom.forward.disabled=!state.forward.length;dom.location.textContent=taskTitle(t);
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
    for(const t of state.semantic.territories){const p=state.geometry.territory.get(t.id);if(!p)continue;const x=svg("polygon",{points:pstr(p.points),class:"atlas-mini-territory","data-territory-id":t.id});x.style.fill=color(hue(t.id),.55);dom.minimap.append(x)}
    const selectedGeometry=state.geometry.task.get(state.selected);if(selectedGeometry)dom.minimap.append(svg("circle",{cx:selectedGeometry.x+selectedGeometry.w/2,cy:selectedGeometry.y+selectedGeometry.h/2,r:18,class:"atlas-mini-selected"}));
    const frontierGeometry=state.geometry.task.get(recommendationId(coreProjection()));if(frontierGeometry)dom.minimap.append(svg("circle",{cx:frontierGeometry.x+frontierGeometry.w/2,cy:frontierGeometry.y+frontierGeometry.h/2,r:14,class:"atlas-mini-frontier"}));
    renderMiniViewport();
  }
  function renderMiniViewport(){if(!dom.minimap)return;$(".atlas-mini-viewport",dom.minimap)?.remove();const s=state.viewport.scale;dom.minimap.append(svg("rect",{x:-state.viewport.x/s,y:-state.viewport.y/s,width:state.size.w/s,height:state.size.h/s,class:"atlas-mini-viewport"}))}
  function show(kind,title,detail){dom.state.hidden=false;dom.state.dataset.kind=kind;dom.state.innerHTML=`<strong>${title}</strong><span>${detail}</span>`}
  function renderState(){
    if(!coreProjection())return show("unavailable","Atlas unavailable","The shared Niche projection is not currently available.");
    if(!state.ready)return show("loading","Loading Atlas","Preparing the represented work topology.");
    if(!state.semantic.tasks.length)return show("empty","No represented work","Atlas has no represented task substance to spatialize.");
    if(!visibleTerritories().length)return show("filtered","No territories match current filters","Reset search or filters to restore the represented world.");
    dom.state.hidden=true;
    dom.state.textContent="";
  }
  function renderSecondary(){
    if(!state.ready)return;
    renderDetail();renderRoute();renderLegend();
    if(state.size.w>720||state.railOpen)renderIndex();else dom.index.replaceChildren();
  }
  function queueSecondary(){
    const token=++state.secondaryToken;
    if(state.secondaryQueued)return;
    state.secondaryQueued=true;
    const run=()=>{state.secondaryQueued=false;if(token!==state.secondaryToken&&!state.railOpen)return;renderSecondary()};
    if("requestIdleCallback" in window)window.requestIdleCallback(run,{timeout:120});
    else setTimeout(run,24);
  }
  function renderAll(){renderState();if(!state.ready)return;renderMetrics();renderSelected();renderBreadcrumb();renderMap();renderMinimap();queueSecondary();dom.footerStatus.textContent=`ATLAS ${state.level.toUpperCase()}`}
  function announce(x){dom.live.textContent="";requestAnimationFrame(()=>dom.live.textContent=x)}

  function select(id,focus=false,source="atlas") {
    if(!state.semantic.taskById.has(id))return;if(state.selected&&state.selected!==id){state.back.push(state.selected);state.back=state.back.slice(-50);state.forward=[]}state.selected=id;state.focusTerritory=state.semantic.taskToTerritory.get(id)??null;state.route=[];state.recent=[id,...state.recent.filter(x=>x!==id)].slice(0,12);dom.back.disabled=!state.back.length;queueRender();if(focus)focusTask(id);window.Niche?.task?.(id);if(state.size.w<720)setRailOpen(false);emit("selection",{task_id:id,source});
  }
  function goBack(){const x=state.back.pop();if(!x)return;if(state.selected)state.forward.push(state.selected);state.selected=x;state.focusTerritory=state.semantic.taskToTerritory.get(x)??null;dom.back.disabled=!state.back.length;focusTask(x);queueRender();window.Niche?.task?.(x)}
  function goForward(){const x=state.forward.pop();if(!x)return;if(state.selected)state.back.push(state.selected);state.selected=x;state.focusTerritory=state.semantic.taskToTerritory.get(x)??null;focusTask(x);queueRender();window.Niche?.task?.(x)}
  function frontier(){const id=recommendationId(coreProjection());if(!id||!state.semantic.taskById.has(id))return announce("No executable frontier is represented.");select(id,true,"frontier")}
  function routeInput(){if(!state.selected)return announce("Select a starting task first.");const t=resolveTask(dom.routeInput.value);if(!t){state.route=[];queueRender();return announce("Destination is not represented.")}state.route=route(state.selected,taskId(t));queueRender();announce(state.route.length?`Represented relationship route contains ${state.route.length} locations. It is not execution order.`:"No represented relationship route was found.")}

  function sync() {
    const p=coreProjection();if(!p){state.ready=false;show("degraded","Atlas unavailable","The shared Niche projection is unavailable. Execute remains independent.");dom.footerStatus.textContent="ATLAS DEGRADED";return}
    const n=normalized(p);if(Number.isFinite(n.generation)&&n.generation<state.generation)return;if(Number.isFinite(n.generation))state.generation=n.generation;
    state.selected=n.selected;state.semantic=buildSemantic(n);state.ready=true;ensureGeometry();queueRender();
    if(state.active&&!state.firstFit&&state.geometry.w>1&&state.geometry.h>1&&measure()){state.firstFit=true;requestAnimationFrame(fitWorld)}
  }
  function activateFallback(){
    for(const s of $$(".surface")){
      const active=s===dom.surface;
      s.classList.toggle("active",active);
      if(active)s.hidden=false;
    }
    for(const b of $$(".nav [data-view]")){
      const active=b.dataset.view===VIEW;
      b.classList.toggle("active",active);
      if(active)b.setAttribute("aria-current","page");
      else b.removeAttribute("aria-current");
    }
    document.documentElement.dataset.nicheView=VIEW;
  }

  function atlasIsVisiblyActive(){
    return Boolean(
      dom.surface &&
      !dom.surface.hidden &&
      dom.surface.classList.contains("active") &&
      document.documentElement.dataset.nicheView===VIEW
    );
  }

  function open(){
    install();
    state.active=true;

    let delegated=false;
    try{
      if(window.Niche&&typeof window.Niche.view==="function"){
        window.Niche.view(VIEW);
        delegated=true;
      }
    }catch(error){
      emit("error",{stage:"view-delegation",message:txt(error?.message,"Atlas view delegation failed.")});
    }

    dom.surface.hidden=false;dom.surface.dataset.visualSystem=VISUAL_SYSTEM;

    requestAnimationFrame(()=>{
      if(!atlasIsVisiblyActive())activateFallback();
      onActivate();
      emit("focus",{source:delegated?"core-view":"atlas-fallback"});
    });
  }
  function onActivate(){state.active=true;if(!measure())return requestAnimationFrame(onActivate);sync();if(state.firstFit)applyTransform();emit("activated")}
  function onDeactivate(){state.active=false;if(state.viewportAnimation)cancelAnimationFrame(state.viewportAnimation);state.viewportAnimation=null;hideTooltip();swrite();emit("deactivated")}
  function onResize(){const old=state.size.w<640?"n":state.size.w<1100?"m":"w";if(!measure())return;const now=state.size.w<640?"n":state.size.w<1100?"m":"w";if(old!==now){state.geometry.fingerprint="";ensureGeometry();queueRender()}else queueTransform()}

  function bindMap() {
    const interactiveControl=target=>Boolean(target?.closest?.("button,input,select,textarea,a"));
    const point=e=>({x:e.clientX,y:e.clientY});

    const begin=e=>{
      if(interactiveControl(e.target)||e.button>0||!state.active)return;
      e.preventDefault();
      hideTooltip();
      if(state.viewportAnimation)cancelAnimationFrame(state.viewportAnimation);
      state.viewportAnimation=null;
      state.pointer.active.set(e.pointerId,point(e));
      state.gestureMoved=false;
      state.suppressClick=false;
      try{dom.viewport.setPointerCapture?.(e.pointerId)}catch{}

      if(state.pointer.active.size===1){
        state.pointer.mode="candidate";
        state.pointer.sx=e.clientX;
        state.pointer.sy=e.clientY;
        state.pointer.ox=state.viewport.x;
        state.pointer.oy=state.viewport.y;
      }else if(state.pointer.active.size===2){
        const p=Array.from(state.pointer.active.values());
        state.pointer.mode="pinch";
        state.pointer.pinch=Math.max(1,Math.hypot(p[1].x-p[0].x,p[1].y-p[0].y));
        state.pointer.scale=state.viewport.scale;
        state.pointer.cx=(p[0].x+p[1].x)/2;
        state.pointer.cy=(p[0].y+p[1].y)/2;
        state.suppressClick=true;
        state.gestureMoved=true;
      }
    };

    const move=e=>{
      if(!state.pointer.active.has(e.pointerId))return;
      state.pointer.active.set(e.pointerId,point(e));

      if(state.pointer.active.size===2){
        const p=Array.from(state.pointer.active.values());
        const d=Math.max(1,Math.hypot(p[1].x-p[0].x,p[1].y-p[0].y));
        const cx=(p[0].x+p[1].x)/2;
        const cy=(p[0].y+p[1].y)/2;
        state.pointer.mode="pinch";
        state.suppressClick=true;
        state.gestureMoved=true;
        e.preventDefault();
        zoomAt((state.pointer.scale*(d/state.pointer.pinch))/state.viewport.scale,cx,cy,false);
        return;
      }

      if(state.pointer.active.size!==1)return;
      const dx=e.clientX-state.pointer.sx;
      const dy=e.clientY-state.pointer.sy;

      if(state.pointer.mode==="candidate"&&Math.hypot(dx,dy)>=5){
        state.pointer.mode="pan";
        state.suppressClick=true;
        state.gestureMoved=true;
      }

      if(state.pointer.mode!=="pan")return;
      e.preventDefault();
      setViewport({
        x:state.pointer.ox+dx,
        y:state.pointer.oy+dy,
        scale:state.viewport.scale
      },false);
    };

    const done=e=>{
      if(!state.pointer.active.has(e.pointerId))return;
      state.pointer.active.delete(e.pointerId);
      try{dom.viewport.releasePointerCapture?.(e.pointerId)}catch{}

      if(state.pointer.active.size===1){
        const [p]=state.pointer.active.values();
        state.pointer.mode="candidate";
        state.pointer.sx=p.x;
        state.pointer.sy=p.y;
        state.pointer.ox=state.viewport.x;
        state.pointer.oy=state.viewport.y;
        state.pointer.scale=state.viewport.scale;
        return;
      }

      if(!state.pointer.active.size){
        const moved=state.gestureMoved;
        state.pointer.mode="";
        state.gestureMoved=false;
        swrite();
        if(moved)requestAnimationFrame(()=>requestAnimationFrame(()=>{state.suppressClick=false}));
        else state.suppressClick=false;
      }
    };

    dom.viewport.addEventListener("pointerdown",begin,{capture:true,passive:false});
    window.addEventListener("pointermove",move,{capture:true,passive:false});
    window.addEventListener("pointerup",done,{capture:true,passive:true});
    window.addEventListener("pointercancel",done,{capture:true,passive:true});

    dom.viewport.addEventListener("pointerover",e=>{
      if(state.pointer.mode)return;
      const target=e.target.closest?.("[data-task-id],[data-territory-id]");
      if(target)showTooltip(e,target);
    });
    dom.viewport.addEventListener("pointerout",e=>{
      if(e.target.closest?.("[data-task-id],[data-territory-id]"))hideTooltip();
    });

    dom.viewport.addEventListener("wheel",e=>{
      e.preventDefault();
      hideTooltip();
      zoomAt(Math.exp(-e.deltaY*.00125),e.clientX,e.clientY,false);
      swrite();
    },{passive:false});

    dom.viewport.addEventListener("click",e=>{
      if(state.suppressClick||state.gestureMoved)return;
      const t=e.target.closest?.("[data-task-id]");
      if(t?.dataset.taskId)return select(t.dataset.taskId,false,"map");

      const port=e.target.closest?.("[data-port-direction]");
      if(port){
        const source=state.semantic.territoryById.get(port.dataset.edgeSource);
        const target=state.semantic.territoryById.get(port.dataset.edgeTarget);
        state.detail={
          type:"port",
          direction:port.dataset.portDirection,
          count:Number(port.dataset.count)||0,
          sourceLabel:source?.label??port.dataset.edgeSource,
          targetLabel:target?.label??port.dataset.edgeTarget
        };
        renderSecondary();
        return;
      }

      const x=e.target.closest?.("[data-territory-id]");
      if(x?.dataset.territoryId&&state.semantic.territoryById.has(x.dataset.territoryId)){
        state.focusTerritory=x.dataset.territoryId;
        state.selected=null;
        state.detail=null;
        fitTerritory(x.dataset.territoryId);
        queueRender();
      }
    });

    dom.viewport.addEventListener("dblclick",e=>{
      if(state.suppressClick)return;
      const t=e.target.closest?.("[data-task-id]");
      if(t?.dataset.taskId)select(t.dataset.taskId,true,"double-click");
    });

    dom.viewport.addEventListener("keydown",e=>{
      if(e.key==="0"){e.preventDefault();fitWorld()}
      else if(e.key==="+"){e.preventDefault();zoomCenter(Z.step)}
      else if(e.key==="-"){e.preventDefault();zoomCenter(1/Z.step)}
      else if(e.key==="/"){e.preventDefault();dom.search.focus()}
      else if(e.key==="Escape"){
        e.preventDefault();
        if(state.selected){state.selected=null;queueRender()}
        else if(state.focusTerritory){state.focusTerritory=null;fitWorld();queueRender()}
      }
    });
  }
  function setRailMode(mode="more",open=true) {
    state.railMode=["view","filter","more"].includes(mode)?mode:"more";
    state.railOpen=Boolean(open);
    dom.rail?.classList.toggle("open",state.railOpen);
    if(dom.rail)dom.rail.dataset.railMode=state.railMode;
    dom.railToggle?.setAttribute("aria-expanded",state.railOpen?"true":"false");
    dom.viewToggle?.setAttribute("aria-expanded",state.railOpen&&state.railMode==="view"?"true":"false");
    dom.filterToggle?.setAttribute("aria-expanded",state.railOpen&&state.railMode==="filter"?"true":"false");
    document.documentElement.classList.toggle("atlas-rail-open",state.railOpen);
    if(state.railOpen){renderSecondary();queueRender()}
  }
  function setRailOpen(open){setRailMode(state.railMode,open)}

  function bindControls() {
    dom.nav?.addEventListener("click",open);
    dom.railToggle?.addEventListener("click",()=>setRailMode("more",!(state.railOpen&&state.railMode==="more")));
    dom.viewToggle?.addEventListener("click",()=>setRailMode("view",!(state.railOpen&&state.railMode==="view")));
    dom.filterToggle?.addEventListener("click",()=>setRailMode("filter",!(state.railOpen&&state.railMode==="filter")));
    dom.fit.onclick=fitWorld;
    dom.plus.onclick=()=>zoomCenter(Z.step);dom.minus.onclick=()=>zoomCenter(1/Z.step);dom.theme?.addEventListener("change",()=>window.NicheThemes?.apply?.(dom.theme.value));dom.back.onclick=goBack;dom.forward.onclick=goForward;dom.frontier.onclick=frontier;dom.focusTask.onclick=()=>state.selected&&focusTask(state.selected);dom.openTask.onclick=()=>state.selected&&window.Niche?.task?.(state.selected);
    dom.search.addEventListener("input",()=>{state.filterTouched=true;state.query=dom.search.value.trim();swrite();queueRender()});
    dom.search.addEventListener("keydown",e=>{if(e.key!=="Enter")return;const t=resolveTask(dom.search.value);if(t){e.preventDefault();return select(taskId(t),true,"search")}const terr=state.semantic.territories.find(x=>low(x.label).includes(low(dom.search.value)));if(terr){e.preventDefault();state.focusTerritory=terr.id;fitTerritory(terr.id);queueRender()}});
    dom.status.onchange=()=>{state.filterTouched=true;state.status=dom.status.value;swrite();queueRender()};dom.priority.onchange=()=>{state.filterTouched=true;state.priority=dom.priority.value;swrite();queueRender()};dom.completed.onchange=()=>{state.filterTouched=true;state.completed=dom.completed.value;swrite();queueRender()};dom.effects.onchange=()=>{state.effects=dom.effects.value;swrite();queueRender()};
    dom.reset.onclick=()=>{state.query="";state.status="all";state.priority="all";state.completed="show";state.filterTouched=false;state.focusTerritory=null;dom.search.value="";dom.status.value="all";dom.priority.value="all";dom.completed.value="show";swrite();queueRender()};
    dom.lenses.addEventListener("click",e=>{const b=e.target.closest?.("[data-lens]");if(!b)return;state.lens=b.dataset.lens;for(const x of $$("[data-lens]",dom.lenses))x.classList.toggle("active",x===b);swrite();queueRender()});
    dom.routeGo.onclick=routeInput;dom.routeInput.addEventListener("keydown",e=>{if(e.key==="Enter"){e.preventDefault();routeInput()}});
    let miniDrag=false;
    const miniMove=e=>{const r=dom.minimap.getBoundingClientRect();if(!r.width||!r.height)return;const x=(e.clientX-r.left)/r.width*state.geometry.w,y=(e.clientY-r.top)/r.height*state.geometry.h;setViewport({x:state.size.w/2-x*state.viewport.scale,y:state.size.h/2-y*state.viewport.scale,scale:state.viewport.scale})};
    dom.minimap.addEventListener("pointerdown",e=>{miniDrag=true;dom.minimap.setPointerCapture?.(e.pointerId);miniMove(e)});
    dom.minimap.addEventListener("pointermove",e=>{if(miniDrag)miniMove(e)});
    dom.minimap.addEventListener("pointerup",()=>{miniDrag=false});
    dom.minimap.addEventListener("pointercancel",()=>{miniDrag=false});
    dom.minimap.addEventListener("click",miniMove);
    bindMap();
  }
  function restore() {
    const x=sread();
    if(x?.viewport&&Number.isFinite(x.viewport.x)&&Number.isFinite(x.viewport.y)&&Number.isFinite(x.viewport.scale)){
      state.viewport={x:x.viewport.x,y:x.viewport.y,scale:clamp(x.viewport.scale,Z.min,Z.max)};
      state.level=levelFor(state.viewport.scale);
    }
    state.query="";
    state.status="all";
    state.priority="all";
    state.completed="show";
    state.filterTouched=false;
    state.focusTerritory=null;
    state.lens=["domains","heatmap","dependencies","authority"].includes(x?.lens)?x.lens:"domains";
    state.effects=["full","reduced"].includes(x?.effects)?x.effects:"full";
  }
  function populateThemeControl(){
    if(!dom.theme)return;
    const themes=window.NicheThemes?.themes?.()??[];
    const f=document.createDocumentFragment();
    for(const item of themes){const o=document.createElement("option");o.value=item.value;o.textContent=item.label;f.append(o)}
    dom.theme.replaceChildren(f);
    const current=window.NicheThemes?.current?.()??document.documentElement.dataset.nicheTheme;
    if(current)dom.theme.value=current;
  }
  function applyPrefs(){dom.search.value=state.query;dom.status.value=state.status;dom.priority.value=state.priority;dom.completed.value=state.completed;dom.effects.value=state.effects;for(const b of $$("[data-lens]",dom.lenses))b.classList.toggle("active",b.dataset.lens===state.lens);populateThemeControl()}
  function bindCore(){
    for(const n of ["niche:projection","niche:task-selected"])window.addEventListener(n,sync);window.addEventListener("niche:theme-will-change",hideTooltip);window.addEventListener("niche:theme-change",()=>{if(state.installed){if(dom.theme)dom.theme.value=window.NicheThemes?.current?.()??document.documentElement.dataset.nicheTheme;queueRender();queueTransform();emit("theme",{theme:document.documentElement.dataset.nicheTheme})}});
    window.addEventListener("niche:view",e=>{
      const v=txt(e.detail?.view);
      if(v===VIEW){
        state.active=true;
        dom.surface.hidden=false;
        requestAnimationFrame(()=>{
          if(!atlasIsVisiblyActive())activateFallback();
          onActivate();
        });
      }else if(state.active){
        onDeactivate();
      }
    });

    document.addEventListener("click",event=>{
      const button=event.target.closest?.('.nav [data-view="navigation"]');
      if(!button)return;
      dom.nav=button;
      open();
    },true);
  }
  function resize(){if(state.resizeObserver||!dom.viewport)return;if("ResizeObserver"in window){state.resizeObserver=new ResizeObserver(()=>requestAnimationFrame(onResize));state.resizeObserver.observe(dom.viewport)}else window.addEventListener("resize",onResize,{passive:true})}
  function install() {
    if(state.installed)return true;
    restore();
    ensureSurface();
    ensureNav();
    cache();
    if(!dom.surface||!dom.viewport||!dom.world)return false;
    defs();
    applyPrefs();
    bindControls();
    bindCore();
    resize();
    state.installed=true;
    sync();
    emit("installed");
    return true;
  }

  const api=Object.freeze({
    open,
    select:(id,o={})=>{install();select(txt(id),Boolean(o.focus),txt(o.source,"api"))},
    fit:fitWorld,
    fitTerritory:id=>{install();fitTerritory(txt(id))},
    frontier,
    back:goBack,
    forward:goForward,
    sync,
    state:()=>Object.freeze({
      installed:state.installed,active:state.active,ready:state.ready,selectedTaskId:state.selected,
      focusedTerritoryId:state.focusTerritory,semanticLevel:state.level,delimiter:state.semantic.delimiter,
      representedTaskCount:state.semantic.tasks.length,representedTerritoryCount:state.semantic.territories.length,
      lens:state.lens,priorityFilter:state.priority,forwardHistoryCount:state.forward.length,effectsMode:state.effects,recentLocations:Object.freeze(state.recent.slice()),viewport:Object.freeze({...state.viewport}),projectionGeneration:state.generation,
      layoutLibrary:Object.freeze({name:"elkjs",version:"0.12.0",status:state.elkStatus,authorityEffect:"none"}),authorityEffect:"none",projectionOnly:true
    })
  });
  window.NicheAtlas=api;
  window.NicheNavigation=api;

  document.readyState==="loading"
    ? document.addEventListener("DOMContentLoaded",()=>install(),{once:true})
    : install();
})();
