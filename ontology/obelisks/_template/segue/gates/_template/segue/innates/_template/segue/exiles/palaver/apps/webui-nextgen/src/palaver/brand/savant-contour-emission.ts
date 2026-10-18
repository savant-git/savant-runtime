/** Reproducible emission clocks; no timers or mutable random generators. */
export const contourEmitterCount=4
export const contourFlamesPerEmitter=18
export const contourSmokePerEmitter=7
export const contourSparksPerEmitter=20
export function emissionHash(n:number){
 const x=Math.sin(n*127.1+311.7)*43758.5453;return x-Math.floor(x)
}
export function contourPhase(side:number,tracer:number,time:number,speed:number){
 const phase=time*speed*(side===0?.16:-.145)+tracer*.5+side*.13
 return ((phase%1)+1)%1
}
export function sparkPeriod(id:number){return .36+emissionHash(id+119)*.42}
export function sparkAge(id:number,time:number){
 const period=sparkPeriod(id)
 return ((time+emissionHash(id+31)*period)%period+period)%period
}
export function sparkVelocity(id:number){
 const angle=emissionHash(id+97)*Math.PI*2
 const speed=.28+emissionHash(id+63)*.52
 return {x:Math.cos(angle)*speed,y:Math.sin(angle)*speed+.2,z:(emissionHash(id+43)*.5+.2)*speed}
}
