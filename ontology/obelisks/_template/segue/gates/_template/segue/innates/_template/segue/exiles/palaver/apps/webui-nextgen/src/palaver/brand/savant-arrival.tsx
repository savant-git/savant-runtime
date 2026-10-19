import React,{createContext,memo,useCallback,useContext,useEffect,useLayoutEffect,useRef,useState} from "react"
import SavantMark from "./savant-mark"
import {advanceExposure,arrivalEase,canEnter,flightDurationMs,minimumDisplayMs,preloadRect,rectOf,rectTransform} from "./savant-arrival-motion"
import type {ArrivalPhase,ArrivalRect} from "./savant-arrival-motion"
import "./savant-arrival.css"
import {animateArrival} from "./savant-arrival-choreography"
import {ArrowRight} from "../components/savant-glyphs"

type AnchorContext={register:(node:HTMLDivElement|null)=>void}
const ArrivalContext=createContext<AnchorContext|null>(null)
const PersistentMark=memo(SavantMark)
const sameRect=(a:ArrivalRect|null,b:ArrivalRect)=>!!a&&
 Math.abs(a.left-b.left)<.25&&Math.abs(a.top-b.top)<.25&&
 Math.abs(a.width-b.width)<.25&&Math.abs(a.height-b.height)<.25

/* Placeholder owns normal header layout. Exactly one live logo owns WebGL. */
export function SavantArrivalAnchor(){
 const context=useContext(ArrivalContext)
 if(!context)return <SavantMark mode="header" state="idle" label="savant"/>
 return <div ref={context.register} className="savant-mark savant-mark--header palaver-arrival-anchor" aria-hidden="true"/>
}
export default function SavantArrival({children}:{children:React.ReactNode}){
 const [phase,setPhase]=useState<ArrivalPhase>("waiting")
 const phaseRef=useRef<ArrivalPhase>("waiting")
 const [anchor,setAnchor]=useState<HTMLDivElement|null>(null)
 const register=useCallback((node:HTMLDivElement|null)=>setAnchor(node),[])
 const [box,setBox]=useState<ArrivalRect|null>(null)
 const [frameScale,setFrameScale]=useState(1)
 const [seconds,setSeconds]=useState(0)
 const [reduced,setReduced]=useState(()=>typeof window!=="undefined"&&window.matchMedia("(prefers-reduced-motion: reduce)").matches)
 const workspace=useRef<HTMLDivElement>(null),host=useRef<HTMLDivElement>(null)
 const gate=useRef<HTMLElement>(null),heading=useRef<HTMLHeadingElement>(null)
 const enterButton=useRef<HTMLButtonElement>(null),meter=useRef<HTMLSpanElement>(null)
 const elapsed=useRef(0),boxRef=useRef<ArrivalRect|null>(null)
 const retarget=useRef<(()=>void)|null>(null)
 const changePhase=useCallback((next:ArrivalPhase)=>{phaseRef.current=next;setPhase(next)},[])
 const place=useCallback((next:ArrivalRect,scale:number)=>{
  boxRef.current=next
  setBox(previous=>sameRect(previous,next)?previous:next)
  setFrameScale(previous=>Math.abs(previous-scale)<.0001?previous:scale)
 },[])

 useEffect(()=>{
  const query=window.matchMedia("(prefers-reduced-motion: reduce)")
  const update=()=>setReduced(query.matches)
  query.addEventListener("change",update)
  return()=>query.removeEventListener("change",update)
 },[])
 useEffect(()=>{
  if(phase==="entered")return
  const before=document.body.style.overflow
  document.body.style.overflow="hidden"
  return()=>{document.body.style.overflow=before}
 },[phase])
 useEffect(()=>{
  heading.current?.focus({preventScroll:true})
  let raf=0,last=performance.now(),announced=-1
  const reset=()=>{last=performance.now()}
  const tick=(now:number)=>{
   const visible=!document.hidden&&!!boxRef.current
   elapsed.current=advanceExposure(elapsed.current,now-last,visible);last=now
   if(meter.current)meter.current.style.transform=`scaleX(${elapsed.current/minimumDisplayMs})`
   const current=Math.floor(elapsed.current/1000)
   if(current!==announced){announced=current;setSeconds(current)}
   if(elapsed.current>=minimumDisplayMs){
    changePhase("ready")
    return
   }
   raf=requestAnimationFrame(tick)
  }
  document.addEventListener("visibilitychange",reset);raf=requestAnimationFrame(tick)
  return()=>{cancelAnimationFrame(raf);document.removeEventListener("visibilitychange",reset)}
 },[changePhase])

 useLayoutEffect(()=>{
  if(!anchor)return
  let raf=0
  const measure=()=>{
   raf=0
   const destination=rectOf(anchor)
   if(destination.width<1||destination.height<1)return
   if(phaseRef.current==="entering"){retarget.current?.();return}
   if(phaseRef.current==="entered"){place(destination,1);return}
   const viewport=window.visualViewport
   const width=viewport?.width||window.innerWidth,height=viewport?.height||window.innerHeight
   const next=preloadRect(width,height,destination)
   next.left+=viewport?.offsetLeft||0;next.top+=viewport?.offsetTop||0
   place(next,next.width/destination.width)
  }
  const schedule=()=>{if(!raf)raf=requestAnimationFrame(measure)}
  const observer=typeof ResizeObserver==="undefined"?null:new ResizeObserver(schedule)
  observer?.observe(anchor)
  window.addEventListener("resize",schedule);window.addEventListener("scroll",schedule,true)
  window.visualViewport?.addEventListener("resize",schedule)
  window.visualViewport?.addEventListener("scroll",schedule)
  // Fonts can alter both header width and the destination position.
  let disposed=false
  document.fonts?.ready.then(()=>{if(!disposed)schedule()})
  measure()
  return()=>{
   disposed=true;cancelAnimationFrame(raf);observer?.disconnect()
   window.removeEventListener("resize",schedule);window.removeEventListener("scroll",schedule,true)
   window.visualViewport?.removeEventListener("resize",schedule)
   window.visualViewport?.removeEventListener("scroll",schedule)
  }
 },[anchor,place])

 useEffect(()=>{
  if(phase!=="ready")return
  if(document.activeElement===heading.current||document.activeElement===document.body)
   enterButton.current?.focus({preventScroll:true})
 },[phase])

 useLayoutEffect(()=>{
  if(phase!=="entering"||!anchor||!host.current||!workspace.current||!boxRef.current)return
  const carrier=host.current,root=workspace.current,source=boxRef.current
  const entrance=animateArrival(root,reduced)
  let disposed=false,flight:Animation|null=null,token=0,watchdog=0
  let resolveFlight:()=>void=()=>{}
  const flightDone=new Promise<void>(resolve=>{resolveFlight=resolve})
  const duration=reduced?160:flightDurationMs,deadline=performance.now()+duration
  const finish=()=>{
   if(disposed||phaseRef.current!=="entering")return
   const destination=rectOf(anchor)
   place(destination,1)
   changePhase("entered")
  }
  const launch=()=>{
   const destination=rectOf(anchor)
   if(destination.width<1||destination.height<1){resolveFlight();return}
   const from=getComputedStyle(carrier).transform
   const final=rectTransform(destination,source)
   token++;const mine=token
   flight?.cancel()
   if(typeof carrier.animate!=="function"){resolveFlight();return}
   flight=carrier.animate([
    {transform:from==="none"?rectTransform(source,source):from},
    {transform:final},
   ],{duration:Math.max(100,deadline-performance.now()),easing:arrivalEase,fill:"both"})
   flight.finished.then(()=>{if(mine===token&&!disposed)resolveFlight()}).catch(()=>{})
  }
  retarget.current=launch
  launch()
  Promise.all([flightDone,entrance.finished]).then(finish).catch(finish)
  // A cancellation or browser animation failure must not strand the interface.
  watchdog=window.setTimeout(finish,reduced?600:3600)
  return()=>{
   disposed=true;token++;window.clearTimeout(watchdog)
   retarget.current=null;flight?.cancel();entrance.cancel()
  }
 },[phase,anchor,place,changePhase,reduced])

 useLayoutEffect(()=>{
  if(phase!=="entered")return
  const raf=requestAnimationFrame(()=>{
   const root=workspace.current
   const target=root?.querySelector<HTMLElement>(".chat-composer textarea:not(:disabled)")
    ||root?.querySelector<HTMLElement>(".xterm-helper-textarea")
    ||root?.querySelector<HTMLElement>(".topbar-actions button")
   target?.focus({preventScroll:true})
   window.dispatchEvent(new Event("resize"))
  })
  return()=>cancelAnimationFrame(raf)
 },[phase])

 const enter=()=>{
  if(!canEnter(phaseRef.current,elapsed.current))return
  changePhase("entering")
 }
 const trapKeys=(event:React.KeyboardEvent)=>{
  if(phase==="entered")return
  event.stopPropagation()
  if(event.key!=="Tab")return
  const nodes=Array.from(gate.current?.querySelectorAll<HTMLElement>("button:not(:disabled),[tabindex='0']")||[])
   .filter(node=>node.getClientRects().length>0)
  if(!nodes.length){event.preventDefault();heading.current?.focus();return}
  const at=nodes.indexOf(document.activeElement as HTMLElement)
  if(event.shiftKey&&(at<=0)){event.preventDefault();nodes.at(-1)?.focus()}
  else if(!event.shiftKey&&(at<0||at===nodes.length-1)){event.preventDefault();nodes[0].focus()}
 }
 const locked=phase!=="entered"
 return <ArrivalContext.Provider value={{register}}>
  <div className="palaver-arrival-workspace" ref={workspace}
   data-arrival-phase={phase} inert={locked} aria-hidden={locked?true:undefined}>
   {children}
  </div>
  <section ref={gate} className="palaver-arrival-layer" data-arrival-phase={phase}
   role={locked?"dialog":undefined} aria-modal={locked?true:undefined}
   aria-labelledby={locked?"palaver-arrival-title":undefined} onKeyDown={trapKeys}>

   {phase!=="entered"&&<div className="palaver-arrival-scrim" aria-hidden="true">
    <div className="palaver-arrival-horizon"/>
   </div>}
   {phase!=="entered"&&box&&<div className="palaver-arrival-aperture" aria-hidden="true"
    style={{left:box.left,top:box.top,width:box.width,height:box.height}}>
    <svg viewBox="0 0 200 200">
     <circle className="arrival-orbit arrival-orbit--outer" cx="100" cy="100" r="93"/>
     <circle className="arrival-orbit arrival-orbit--inner" cx="100" cy="100" r="82"/>
     <path className="arrival-crosshair" d="M100 1v9m0 180v9M1 100h9m180 0h9M34 34l6 6m120 120 6 6M34 166l6-6m120-120 6-6"/>
    </svg>
   </div>}
   <div ref={host} className="palaver-arrival-logo" style={{
    visibility:box?"visible":"hidden",
    width:box?.width||1,height:box?.height||1,
    transform:box?`translate3d(${box.left}px,${box.top}px,0)`:"none",
    "--savant-arrival-scale":frameScale,
   } as React.CSSProperties}>
    <PersistentMark mode="header" state="idle" label="savant" arrivalPhase={phase}
     controls={phase==="entered"} controlsTarget={anchor?.closest<HTMLElement>("header.workstation-topbar")||null}
     framingScale={frameScale}/>
   </div>
   {phase!=="entered"&&<div className="palaver-arrival-copy" style={{
    top:box?box.top+box.height+22:"65%",
   }}>
    <p className="palaver-arrival-eyebrow">savant / cognitive instrument</p>
    <h1 id="palaver-arrival-title" ref={heading} tabIndex={-1}>palaver</h1>
    <p className="palaver-arrival-instruction" role="status" aria-live="polite">
     {phase==="waiting"?"A moment before the conversation.":phase==="ready"?"Choose when to begin.":"Entering palaver."}
    </p>
    <div className="palaver-arrival-meter" role="progressbar" aria-label="Minimum display time"
     aria-valuemin={0} aria-valuemax={10} aria-valuenow={seconds}>
     <span ref={meter}/>
    </div>
    <div className="palaver-arrival-action" aria-busy={phase==="entering"}>
     {phase==="waiting"&&<span aria-hidden="true">{Math.max(0,10-seconds)}s</span>}
     {(phase==="ready"||phase==="entering")&&<button ref={enterButton} type="button" onClick={enter} disabled={phase==="entering"}
      className="palaver-arrival-enter">
      {phase==="entering"?"entering":"enter palaver"} <ArrowRight size={20}/>
     </button>}
    </div>
   </div>}
  </section>
 </ArrivalContext.Provider>
}
