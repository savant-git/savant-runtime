import {ease,seeded} from "./savant-motion"
export type SceneEvent="rain"|"arcs"|"mist"|"meteors"|"sand"|"hologram"|"aurora"|"freeze"|"mercury"|"interference"|"paint"|"bubbles"|"robot"|"creature"|"ion"|"datastream"|"prism"|"solar"|"ash"|"gravity"
export const sceneEvents:SceneEvent[]=["rain","arcs","mist","meteors","sand","hologram","aurora","freeze","mercury","interference","paint","bubbles","robot","creature","ion","datastream","prism","solar","ash","gravity"]
export function eventState(time:number,style:number){
 const period=21+style%5,epoch=Math.floor(time/period),local=time-epoch*period
 const start=3+seeded(epoch+style*41+201)*4
 const age=local-start,duration=9+style%3
 const strength=ease(age/.9)*(1-ease((age-duration)/1.3))
 return {kind:sceneEvents[style]||"rain",age,epoch,strength,
 progress:Math.max(0,Math.min(1,age/duration))}
}

/* A derived signal: callers share the existing epoch and cannot drift apart. */
export function electricalPulse(time:number,style:number){
 const state=eventState(time,style)
 const phase=state.age-1.2
 const envelope=phase>=0&&phase<.7
  ? Math.pow(Math.max(0,Math.sin(phase*37)),5)*(1-phase/.7)
  : 0
 return {epoch:state.epoch,phase,strength:state.strength*envelope}
}
