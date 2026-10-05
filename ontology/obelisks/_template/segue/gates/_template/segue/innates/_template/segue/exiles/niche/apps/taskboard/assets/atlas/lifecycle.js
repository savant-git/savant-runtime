export function installLifecycle(ctx) {
  const {state,dom,$,$$,txt,low,clamp,VIEW,VISUAL_SYSTEM,BUILD,Z,sread,swrite,emit,coreProjection,normalized,buildSemantic,ensureGeometry,queueRender,renderSecondary,renderAll,renderState,measure,fitWorld,fitTerritory,focusTask,zoomAt,zoomCenter,hideTooltip,showTooltip,applyTransform,queueTransform,setViewport,select,goBack,goForward,frontier,routeInput,resolveTask,taskId,levelFor,svg,cache,defs,ensureSurface,ensureNav} = ctx;
  function sync() {
    const p=coreProjection();if(!p){state.ready=false;show("degraded","Atlas unavailable","The shared Niche projection is unavailable. Execute remains independent.");dom.footerStatus.textContent="ATLAS R13 · DEGRADED";return}
    const transition=ctx.segues.projectionToSemantic(p),n=transition.normalized;if(Number.isFinite(n.generation)&&n.generation<state.generation)return;if(Number.isFinite(n.generation))state.generation=n.generation;
    state.selected=n.selected;state.semantic=transition.semantic;state.ready=true;ensureGeometry();queueRender();
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

    /* Atlas is a dynamically attached projection surface. The core view registry may
       not know the Atlas view name, so direct surface activation is the deterministic
       compatibility boundary. Core delegation remains advisory for installations that
       have learned the view. */
    activateFallback();
    dom.surface.hidden=false;
    dom.surface.dataset.visualSystem=VISUAL_SYSTEM;

    requestAnimationFrame(()=>{
      if(!atlasIsVisiblyActive())activateFallback();
      onActivate();
      emit("focus",{source:delegated?"core-view+atlas-activation":"atlas-activation"});
    });
    return true;
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
      if(!(e.ctrlKey||e.metaKey)) {
        hideTooltip();
        return;
      }
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

  }
  function resize(){if(state.resizeObserver||!dom.viewport)return;if("ResizeObserver"in window){state.resizeObserver=new ResizeObserver(()=>requestAnimationFrame(onResize));state.resizeObserver.observe(dom.viewport)}else window.addEventListener("resize",onResize,{passive:true})}
  Object.assign(ctx,{sync,activateFallback,atlasIsVisiblyActive,open,onActivate,onDeactivate,onResize,bindMap,setRailMode,setRailOpen,bindControls,restore,populateThemeControl,applyPrefs,bindCore,resize});
  return ctx;
}
