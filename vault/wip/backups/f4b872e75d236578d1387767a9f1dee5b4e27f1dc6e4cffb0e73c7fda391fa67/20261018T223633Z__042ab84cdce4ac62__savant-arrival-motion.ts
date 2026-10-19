export const minimumDisplayMs=10_000
export type ArrivalPhase="waiting"|"ready"|"entering"|"entered"
export type ArrivalRect={left:number;top:number;width:number;height:number}
export function advanceExposure(elapsed:number,delta:number,visible:boolean){
 return Math.min(minimumDisplayMs,Math.max(0,elapsed)+(visible?Math.max(0,Math.min(delta,250)):0))
}
export function canEnter(phase:ArrivalPhase,elapsed:number){
 return phase==="ready"&&elapsed>=minimumDisplayMs
}
export function preloadRect(width:number,height:number,anchor:ArrivalRect):ArrivalRect{
 const aspect=Math.max(.5,Math.min(1.6,anchor.width/Math.max(anchor.height,1)))
 const copyBudget=height<=540?160:205
 const h=Math.max(80,Math.min(height*.57,width*.78/aspect,620,height-copyBudget-24))
 const w=h*aspect
 return {left:(width-w)/2,top:Math.max(8,(height-h-copyBudget)/2),width:w,height:h}
}
export function rectOf(element:Element):ArrivalRect{
 const r=element.getBoundingClientRect()
 return {left:r.left,top:r.top,width:r.width,height:r.height}
}
export function rectTransform(rect:ArrivalRect,source:ArrivalRect){
 return `translate3d(${rect.left}px,${rect.top}px,0) scale(${rect.width/source.width},${rect.height/source.height})`
}
export function arrivalTargets(root:HTMLElement){
 const selectors=[
  ".topbar-brand > div:not(.palaver-arrival-anchor)",
  ".topbar-command-strip",".palaver-header-controls",".chat-hero",
  ".chat-thread",".chat-composer",".terminal-observatory",
  ".workstation-statusbar",
 ]
 const found=Array.from(root.querySelectorAll<HTMLElement>(selectors.join(",")))
  .filter(node=>{const r=node.getBoundingClientRect();return r.width>0&&r.height>0})
 // Never compound the entrance transform on both a parent and its children.
 const targets=found.filter(node=>!found.some(other=>other!==node&&other.contains(node)))
 if(!targets.some(node=>node.matches(".chat-thread,.terminal-observatory"))){
  const fallback=root.querySelector<HTMLElement>(".workspace-surface,.palaver-center")
  if(fallback&&!targets.some(node=>fallback.contains(node)))targets.push(fallback)
 }
 return targets.slice(0,14)
}
