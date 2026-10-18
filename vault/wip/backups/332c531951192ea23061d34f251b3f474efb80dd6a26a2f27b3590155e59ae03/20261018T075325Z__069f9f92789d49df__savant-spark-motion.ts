import type {Vector3} from "three"
export const sparkTrailSegments=16
export const sparksPerEmitter=6
export const sparkLightCount=4
const tau=Math.PI*2
export const wrap01=(v:number)=>((v%1)+1)%1
export function sparkHash(n:number){const v=Math.sin(n*127.1+311.7)*43758.5453123;return v-Math.floor(v)}
export function sparkEase(v:number){const x=Math.max(0,Math.min(v,1));return x*x*(3-2*x)}
export function helixPhase(id:number,t:number,count:number){
 const pair=Math.floor(id*.5),pairs=Math.max(1,Math.ceil(count*.5))
 const flow=t*(.95+.1*sparkHash(id+90))+
  .045*Math.sin(t*.81+id)+.022*Math.sin(t*2.17+id*.7)
 return flow*.095+pair/pairs
}
export function sparkHelix(id:number,t:number,count:number,out:Vector3){
 const side=id%2===0?1:-1,phase=helixPhase(id,t,count)
 const major=phase*tau*3,minor=major*3
 const radius=.70+.05*Math.sin(minor)+.008*Math.sin(t*3.4+id)
 return out.set(side*Math.cos(major)*radius,
  (wrap01(phase)-.5)*2.65+.03*Math.cos(minor),side*Math.sin(major)*radius)
}
export function emitterLife(t:number,count:number,active:boolean){
 const clock=Math.max(0,t-2),epoch=Math.floor(clock/4.8),age=clock%4.8
 return {chosen:active&&t>2?Math.floor(sparkHash(epoch+903)*count):-1,age,epoch}
}
export function emitterVisibility(id:number,t:number,count:number,chosen:number,age:number){
 const phase=wrap01(helixPhase(id,t,count))
 return sparkEase(phase/.06)*sparkEase((1-phase)/.06)*
  (id===chosen?sparkEase((age-3)/.75):1)
}
/** Ballistic chips originate from the emitter's actual earlier position. */
export function hotSpark(id:number,piece:number,t:number,count:number,
 out:Vector3,velocity:Vector3){
 const period=.48+.18*sparkHash(id*13+piece)
 const shifted=t+sparkHash(id*29+piece+7)*period
 const cycle=Math.floor(shifted/period),age=wrap01(shifted/period)*period
 const seed=id*137+piece*31+cycle*71
 const az=sparkHash(seed+1)*tau,z=sparkHash(seed+2)*2-1
 const radial=Math.sqrt(Math.max(0,1-z*z)),speed=.6+.8*sparkHash(seed+3)
 sparkHelix(id,t-age,count,out)
 velocity.set(Math.cos(az)*radial*speed,z*speed,Math.sin(az)*radial*speed)
 out.addScaledVector(velocity,age)
 out.y-=1.2*age*age
 velocity.y-=2.4*age
 const life=.23+.15*sparkHash(seed+4)
 return {age,life,visibility:sparkEase(age/.018)*sparkEase((life-age)/.13)}
}

