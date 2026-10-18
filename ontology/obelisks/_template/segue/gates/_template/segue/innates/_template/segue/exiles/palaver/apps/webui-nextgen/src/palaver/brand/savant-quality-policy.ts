/** Pure presentation policy. Effects are reduced before crispness; recovery is slower. */
export type SceneQualityTier="economy"|"balanced"|"cinematic"
export type QualitySample={elapsed:number;frames:number;slow:number;fast:number;cooldown:number}
export const qualityLimits={minimumDpr:1,maximumDpr:2,maximumPixels:700000,sampleSeconds:1.5} as const
export function pixelRatioCap(width:number,height:number,device:number){
 const pixels=Math.max(1,width)*Math.max(1,height)
 return Math.max(1,Math.min(2,Number.isFinite(device)?device:1,Math.sqrt(qualityLimits.maximumPixels/pixels)))
}
export function qualityTier(dpr:number,cap:number):SceneQualityTier{
 const ratio=dpr/Math.max(1,cap)
 return ratio<.7?"economy":ratio<.9?"balanced":"cinematic"
}
export function evaluateQuality(s:QualitySample,delta:number,tier:SceneQualityTier,dpr:number,cap:number){
 if(!Number.isFinite(delta)||delta<=0||delta>.5)return null
 s.elapsed+=delta;s.frames++;s.cooldown+=delta
 // Time, rather than a large minimum-frame count, also handles very slow devices.
 if(s.elapsed<qualityLimits.sampleSeconds||s.frames<3)return null
 const average=s.elapsed/s.frames
 s.elapsed=0;s.frames=0
 s.slow=average>.026?s.slow+1:0;s.fast=average<.018?s.fast+1:0
 if(s.cooldown<3)return null
 let nextTier=tier,nextDpr=dpr
 if(s.slow>=2){
  if(tier!=="economy")nextTier=tier==="cinematic"?"balanced":"economy"
  else nextDpr=Math.max(1,dpr-.15)
 }else if(s.fast>=5&&s.cooldown>=12){
  if(dpr<cap-.025)nextDpr=Math.min(cap,dpr+.1)
  else if(tier!=="cinematic")nextTier=tier==="economy"?"balanced":"cinematic"
 }
 if(nextTier===tier&&Math.abs(nextDpr-dpr)<.025)return null
 s.slow=0;s.fast=0;s.cooldown=0
 return {tier:nextTier,dpr:nextDpr}
}
