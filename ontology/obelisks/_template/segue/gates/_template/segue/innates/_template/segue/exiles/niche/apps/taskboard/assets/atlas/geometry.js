export function installGeometry(ctx) {
  const {state,G,ELK_PROVENANCE,hash,txt,arr,clamp,taskId,taskTitle,taskObjective,taskDependencies,LEVEL,Z,SVG} = ctx;
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
    const baseW=Math.max(1040,Math.sqrt(area*aspect)*.94);
    const candidates=[];
    for(const multiplier of [1,1.08,1.16,1.26]){
      const targetW=Math.ceil(baseW*multiplier);
      const targetH=Math.ceil(Math.max(740,area/targetW*1.16));
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

  Object.assign(ctx,{crossingWeight,shapeFor,dims,polygon,pstr,inside,territoryCentrality,orderedTerritories,packScore,splitFreeRect,pruneFreeRects,maxRectsCandidate,pack,taskLayout,loadElk,localDependencyEdges,elkTaskLayout,scheduleElkRefinement,edgeGeometry,geometryFingerprint,ensureGeometry,hue,levelFor,svg});
  return ctx;
}
