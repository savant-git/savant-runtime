/** Presentation projection only; existing workspace state remains with its owner. */
export const minimumDisplayMs=10_000
export type ArrivalPhase="waiting"|"ready"|"entering"|"entered"
export type ArrivalRect={left:number;top:number;width:number;height:number}
export type ArrivalRole="brand"|"navigation"|"hero"|"content"|"composer"|"rail"|"status"
export const arrivalEase="cubic-bezier(.12,.86,.16,1)"
export const flightDurationMs=1780
export const arrivalRoles:readonly ArrivalRole[]=["brand","navigation","hero","rail","content","composer","status"]
export function advanceExposure(elapsed:number,delta:number,visible:boolean){
 const before=Number.isFinite(elapsed)?Math.max(0,elapsed):0
 const step=Number.isFinite(delta)?Math.max(0,Math.min(delta,250)):0
 return Math.min(minimumDisplayMs,before+(visible?step:0))
}
export function canEnter(phase:ArrivalPhase,elapsed:number){
 return phase==="ready"&&elapsed>=minimumDisplayMs
}
export function preloadRect(width:number,height:number,anchor:ArrivalRect):ArrivalRect{
 const aspect=Math.max(.5,Math.min(1.6,anchor.width/Math.max(anchor.height,1)))
 const copyBudget=height<=540?160:205
 const h=Math.max(80,Math.min(height*.53,width*.74/aspect,580,height-copyBudget-32))
 const w=h*aspect
 return {left:(width-w)/2,top:Math.max(8,(height-h-copyBudget)/2),width:w,height:h}
}
export function rectOf(element:Element):ArrivalRect{
 const r=element.getBoundingClientRect()
 return {left:r.left,top:r.top,width:r.width,height:r.height}
}
export function rectTransform(rect:ArrivalRect,source:ArrivalRect){
 return "translate3d("+rect.left+"px,"+rect.top+"px,0) scale("+
  rect.width/Math.max(source.width,1)+","+rect.height/Math.max(source.height,1)+")"
}
const roles:readonly [string,ArrivalRole][]=[
 [".topbar-brand > div:not(.palaver-arrival-anchor)","brand"],
 [".topbar-command-strip,.palaver-header-controls,.savant-material-picker","navigation"],
 [".chat-hero,.terminal-hero,.terminal-header","hero"],
 [".chat-thread,.terminal-observatory,.workspace-surface","content"],
 [".chat-composer,.chat-composer-shell,.chat-composer-wrap","composer"],
 [".observatory-rail,.context-panel,.observatory-panel","rail"],
 [".workstation-statusbar","status"],
]
/** Select a non-overlapping DOM frontier of existing components.
 * data-savant-arrival opts a component into a presentation role.
 * data-savant-arrival-group keeps a subtree together. Neither creates graph authority. */
export function arrivalTargets(root:HTMLElement){
 const found=new Map<HTMLElement,ArrivalRole>()
 const visible=(node:HTMLElement)=>{
  const r=node.getBoundingClientRect()
  return r.width>0&&r.height>0&&r.bottom>0&&r.top<window.innerHeight&&
   r.right>0&&r.left<window.innerWidth&&getComputedStyle(node).display!=="none"
 }
 for(const [selector,role] of roles)
  root.querySelectorAll<HTMLElement>(selector).forEach(node=>{if(visible(node))found.set(node,role)})
 root.querySelectorAll<HTMLElement>("[data-savant-arrival]").forEach(node=>{
  const value=node.dataset.savantArrival as ArrivalRole
  if(visible(node))found.set(node,arrivalRoles.includes(value)?value:"content")
 })
 const outer=[...found.keys()].filter(node=>![...found.keys()].some(other=>other!==node&&other.contains(node)))
 if(!outer.length){
  const fallback=root.querySelector<HTMLElement>(".palaver-center,.palaver-layout")
  if(fallback&&visible(fallback)){outer.push(fallback);found.set(fallback,"content")}
 }
 const parts:{node:HTMLElement;role:ArrivalRole}[]=[]
 const split=(node:HTMLElement,role:ArrivalRole,depth:number)=>{
  if(node.dataset.savantArrivalGroup!==undefined||node.matches("button,input,textarea,select,pre,.xterm,.chat-message")||depth>=3){
   parts.push({node,role});return
  }
  const children=Array.from(node.children).filter((child):child is HTMLElement=>
   child instanceof HTMLElement&&visible(child)&&!child.matches("script,style,.palaver-arrival-anchor"))
  const ownText=Array.from(node.childNodes).some(child=>child.nodeType===Node.TEXT_NODE&&!!child.textContent?.trim())
  if(!children.length||ownText||children.length>18){parts.push({node,role});return}
  children.forEach(child=>split(child,found.get(child)||role,depth+1))
 }
 outer.forEach(node=>split(node,found.get(node)||"content",0))
 return parts
}
export function entranceSpec(role:ArrivalRole,index:number,reduced:boolean){
 const order=arrivalRoles.indexOf(role)
 const delay=reduced?0:140+Math.max(order,0)*65+Math.min(index,16)*24
 const duration=reduced?140:role==="content"?1260:role==="composer"?1160:1080
 const y=role==="brand"?-22:role==="navigation"?-18:role==="composer"?54:role==="status"?18:42
 const x=role==="rail"?-24:0
 const frames:Keyframe[]=reduced?[{opacity:0},{opacity:1}]:[
  {opacity:0,translate:x+"px "+y+"px 0",scale:role==="content"?".986":"1",offset:0},
  {opacity:1,translate:(-x*.025)+"px "+(-Math.sign(y)*1.4)+"px 0",scale:"1",offset:.82},
  {opacity:1,translate:"0px 0px 0px",scale:"1",offset:1},
 ]
 return {frames,options:{duration,delay,easing:arrivalEase,fill:"both" as FillMode}}
}
