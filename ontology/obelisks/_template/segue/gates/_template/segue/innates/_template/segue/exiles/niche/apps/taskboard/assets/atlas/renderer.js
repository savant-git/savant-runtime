export function installRenderer(ctx) {
  const {state,dom,$,$$,txt,low,arr,clamp,G,Z,LEVEL,ELK_PROVENANCE,svg,pstr,inside,hue,ensureGeometry,visibleTerritories,intersects,applyTransform,queueTransform,setViewport,fitBounds,fitWorld,fitTerritory,focusTask,zoomAt,zoomCenter,taskId,taskTitle,taskObjective,taskDomain,taskOwner,taskPriority,taskDependencies,taskState,taskAuthority,critical,recommendationId,coreProjection,coreState,emit,scheduleElkRefinement} = ctx;
  function renderSubstrate() {
    const f=document.createDocumentFragment();
    f.append(svg("rect",{x:0,y:0,width:state.geometry.w,height:state.geometry.h,class:"atlas-world-bg"}));

    const territories=Array.from(state.geometry.territory.values());
    const centers=new Map(territories.map(p=>[p.id,{x:p.x+p.w/2,y:p.y+p.h/2,p}]));

    // A presentation-only facility circulation mesh. It is derived from actual packed
    // territory positions and represented aggregate crossings. It asserts no authority.
    const circulation=svg("g",{class:"atlas-facility-circulation","aria-hidden":"true"});
    for(const p of territories){
      circulation.append(
        svg("rect",{x:p.x-20,y:p.y-20,width:p.w+40,height:p.h+40,rx:16,class:"atlas-concourse-pad"}),
        svg("rect",{x:p.x-9,y:p.y-9,width:p.w+18,height:p.h+18,rx:10,class:"atlas-concourse-seam"})
      );
    }
    for(const e of state.semantic.aggregateEdges){
      const a=centers.get(e.source),b=centers.get(e.target);if(!a||!b)continue;
      const mx=(a.x+b.x)/2;
      const d=Math.abs(a.x-b.x)>Math.abs(a.y-b.y)
        ?`M ${a.x} ${a.y} L ${mx} ${a.y} L ${mx} ${b.y} L ${b.x} ${b.y}`
        :`M ${a.x} ${a.y} L ${a.x} ${(a.y+b.y)/2} L ${b.x} ${(a.y+b.y)/2} L ${b.x} ${b.y}`;
      const weight=Math.min(26,10+Math.log2(e.count+1)*4);
      const path=svg("path",{d,class:"atlas-facility-concourse","vector-effect":"non-scaling-stroke"});
      path.style.setProperty("--concourse-width",String(weight));
      circulation.append(path);
    }
    f.append(circulation);

    // Deterministic orientation ticks make the world read as one engineered facility.
    const ticks=svg("g",{class:"atlas-world-ticks","aria-hidden":"true"});
    for(let x=64;x<state.geometry.w;x+=160){
      ticks.append(svg("line",{x1:x,y1:24,x2:x,y2:38,class:"atlas-world-tick","vector-effect":"non-scaling-stroke"}));
    }
    for(let y=64;y<state.geometry.h;y+=160){
      ticks.append(svg("line",{x1:24,y1:y,x2:38,y2:y,class:"atlas-world-tick","vector-effect":"non-scaling-stroke"}));
    }
    f.append(ticks);
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
      g.style.setProperty("--tc",color(c));g.style.setProperty("--tcs",color(c,.24));
      if(state.focusTerritory===t.id)g.classList.add("focused");
      if(state.selected&&state.semantic.taskToTerritory.get(state.selected)===t.id)g.classList.add("selected-territory");
      if(state.lens==="heatmap")g.dataset.heat=String(Math.round((t.tasks.reduce((s,x)=>s+heat(x),0)/Math.max(1,t.tasks.length))*4));

      const inset=(factor)=>p.points.map(([x,y])=>{const cx=p.x+p.w/2,cy=p.y+p.h/2;return[cx+(x-cx)*factor,cy+(y-cy)*factor]});
      const seam1=inset(.976), seam2=inset(.946), floor=inset(.918);

      const title=svg("text",{x:p.x+34,y:p.y+40,class:"atlas-territory-title"});title.textContent=t.label;
      const meta=svg("text",{x:p.x+34,y:p.y+61,class:"atlas-territory-meta"});
      meta.textContent=`${t.statistics.total} TASKS  ·  ${t.statistics.ready} READY  ·  ${t.statistics.blocked} BLOCKED`;
      const count=svg("text",{x:p.x+p.w-39,y:p.y+42,class:"atlas-territory-count","text-anchor":"middle"});count.textContent=String(t.statistics.total);

      g.append(
        svg("polygon",{points:pstr(p.points),class:"atlas-territory-outer"}),
        svg("polygon",{points:pstr(seam1),class:"atlas-territory-seam atlas-territory-seam-a"}),
        svg("polygon",{points:pstr(seam2),class:"atlas-territory-seam atlas-territory-seam-b"}),
        svg("polygon",{points:pstr(floor),class:"atlas-territory-inner"})
      );

      // Structural title bay and datum rail make each territory read as a facility unit.
      const plaque=svg("path",{
        d:`M ${p.x+20} ${p.y+18} H ${Math.min(p.x+p.w-82,p.x+390)} L ${Math.min(p.x+p.w-66,p.x+406)} ${p.y+34} H ${p.x+20} Z`,
        class:"atlas-territory-plaque"
      });
      g.append(plaque);

      renderSubzones(g,t,p);
      renderTerritoryCircuitry(g,t,p);

      g.append(
        svg("line",{x1:p.x+26,y1:p.y+G.head-10,x2:p.x+Math.min(p.w-28,430),y2:p.y+G.head-10,class:"atlas-territory-header","vector-effect":"non-scaling-stroke"}),
        title,meta,
        svg("circle",{cx:p.x+p.w-39,cy:p.y+37,r:20,class:"atlas-territory-count-circle"}),
        svg("circle",{cx:p.x+p.w-39,cy:p.y+37,r:13,class:"atlas-territory-count-ring"}),
        count
      );

      // Edge registration marks and compact state rack.
      const rackX=p.x+p.w-28,rackY=p.y+78;
      const states=[
        ["ready",t.statistics.ready],["active",t.statistics.active],
        ["blocked",t.statistics.blocked],["complete",t.statistics.complete]
      ].filter(x=>x[1]>0);
      states.slice(0,4).forEach(([name,value],i)=>{
        const mark=svg("rect",{x:rackX-8,y:rackY+i*18,width:8,height:8,rx:1,class:`atlas-state-rack atlas-state-rack-${name}`});
        mark.setAttribute("aria-hidden","true");g.append(mark);
      });

      const track=svg("line",{x1:p.x+30,y1:p.y+p.h-24,x2:p.x+p.w-30,y2:p.y+p.h-24,class:"atlas-progress-track","vector-effect":"non-scaling-stroke"});
      const prog=svg("line",{x1:p.x+30,y1:p.y+p.h-24,x2:p.x+30+(p.w-60)*t.statistics.completionRatio,y2:p.y+p.h-24,class:"atlas-progress","vector-effect":"non-scaling-stroke"});
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
    if(!mask.task){dom.tasks.replaceChildren();dom.taskEdges.replaceChildren();return}
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
    const ts=visibleTerritories(),ids=new Set(ts.map(t=>t.id)),mask=ctx.modus.forLevel(state.level);
    if(dom.viewport)dom.viewport.dataset.mood=ctx.moods.current().name;
    state.renderStageToken+=1;
    renderSubstrate();
    renderCorridors(ids);
    renderTerritories(ts);
    applyTransform();
    if(!mask.task){
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
  function renderAll(){renderState();if(!state.ready)return;renderMetrics();renderSelected();renderBreadcrumb();renderMap();renderMinimap();queueSecondary();dom.footerStatus.textContent=`ATLAS R13 · ${state.level.toUpperCase()}`}
  function announce(x){dom.live.textContent="";requestAnimationFrame(()=>dom.live.textContent=x)}

  function select(id,focus=false,source="atlas") {
    if(!state.semantic.taskById.has(id))return;if(state.selected&&state.selected!==id){state.back.push(state.selected);state.back=state.back.slice(-50);state.forward=[]}state.selected=id;state.focusTerritory=state.semantic.taskToTerritory.get(id)??null;state.route=[];state.recent=[id,...state.recent.filter(x=>x!==id)].slice(0,12);dom.back.disabled=!state.back.length;queueRender();if(focus)focusTask(id);window.Niche?.task?.(id);if(state.size.w<720)ctx.setRailOpen?.(false);emit("selection",{task_id:id,source});
  }
  function goBack(){const x=state.back.pop();if(!x)return;if(state.selected)state.forward.push(state.selected);state.selected=x;state.focusTerritory=state.semantic.taskToTerritory.get(x)??null;dom.back.disabled=!state.back.length;focusTask(x);queueRender();window.Niche?.task?.(x)}
  function goForward(){const x=state.forward.pop();if(!x)return;if(state.selected)state.back.push(state.selected);state.selected=x;state.focusTerritory=state.semantic.taskToTerritory.get(x)??null;focusTask(x);queueRender();window.Niche?.task?.(x)}
  function frontier(){const id=ctx.segues.recommendationToTask();if(!id)return announce("No executable frontier is represented.");select(id,true,"frontier")}
  function routeInput(){if(!state.selected)return announce("Select a starting task first.");const t=resolveTask(dom.routeInput.value);if(!t){state.route=[];queueRender();return announce("Destination is not represented.")}state.route=route(state.selected,taskId(t));queueRender();announce(state.route.length?`Represented relationship route contains ${state.route.length} locations. It is not execution order.`:"No represented relationship route was found.")}

  Object.assign(ctx,{renderSubstrate,renderCorridors,heat,subzones,renderSubzones,renderTerritoryCircuitry,renderTerritories,localIds,renderTasks,renderTaskEdges,renderRouteEdges,renderSelectedNeighborhood,renderOverlays,scheduleStage,renderMap,queueRender,selectedTask,renderDetail,renderMetrics,renderSelected,renderBreadcrumb,graph,route,resolveTask,renderRoute,renderLegend,renderIndex,renderMinimap,renderMiniViewport,show,renderState,renderSecondary,queueSecondary,renderAll,announce,select,goBack,goForward,frontier,routeInput});
  return ctx;
}
