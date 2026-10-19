import {arrivalTargets,entranceSpec} from "./savant-arrival-motion"
/** Own only animations started here; leave Framer, terminal and app effects alone. */
export function animateArrival(root:HTMLElement,reduced:boolean){
 const animations:Animation[]=[]
 const counts=new Map<string,number>()
 const settled:Promise<unknown>[]=[]
 for(const {node,role} of arrivalTargets(root)){
  if(typeof node.animate!=="function")continue
  const index=counts.get(role)||0;counts.set(role,index+1)
  const {frames,options}=entranceSpec(role,index,reduced)
  try{
   const animation=node.animate(frames,options)
   animations.push(animation);settled.push(animation.finished.catch(()=>{}))
  }catch{/* An unsupported effect must never strand entry. */}
 }
 return {finished:Promise.all(settled),cancel:()=>animations.forEach(animation=>animation.cancel())}
}
