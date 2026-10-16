import {ease,seeded} from "./savant-motion"
export type SceneEvent="rain"|"arcs"|"mist"|"meteors"|"sand"|"hologram"|"aurora"|"freeze"|"mercury"|"interference"|"paint"|"bubbles"|"robot"|"creature"|"ion"|"datastream"|"prism"|"solar"|"ash"|"gravity"
export const sceneEvents:SceneEvent[]=["rain","arcs","mist","meteors","sand","hologram","aurora","freeze","mercury","interference","paint","bubbles","robot","creature","ion","datastream","prism","solar","ash","gravity"]
export function eventState(time:number,style:number){
 const clock=Number.isFinite(time)?Math.max(0,time):0
 const index=Number.isFinite(style)?Math.max(0,Math.floor(style)):0
 const period=21+index%5,epoch=Math.floor(clock/period),local=clock-epoch*period
 const start=3+seeded(epoch+index*41+201)*4
 const age=local-start,duration=9+index%3
 const strength=ease(age/.9)*(1-ease((age-duration)/1.3))
 return {kind:sceneEvents[index]||"rain",age,epoch,strength,
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
