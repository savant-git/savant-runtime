/** Pure frame-time policy. Hysteresis prevents rapid quality oscillation. */
export type RenderQuality={dpr:number;ceiling:number;mean:number;slow:number;fast:number;warm:number}
export function pixelCeiling(width:number,height:number,device:number){
 return Math.max(1,Math.min(2,Number.isFinite(device)?device:1,Math.sqrt(1200000/Math.max(1,width*height))))
}
export function createRenderQuality(ceiling:number):RenderQuality{
 return {dpr:ceiling,ceiling,mean:1/60,slow:0,fast:0,warm:0}
}
export function sampleRenderQuality(s:RenderQuality,delta:number){
 if(!Number.isFinite(delta)||delta<=0||delta>.2){s.slow=0;s.fast=0;return null}
 const dt=Math.min(delta,.1)
 s.warm+=dt;s.mean+=(dt-s.mean)*(1-Math.exp(-dt*2))
 if(s.warm<2)return null
 s.slow=s.mean>1/28?s.slow+dt:0
 s.fast=s.mean<1/52?s.fast+dt:0
 let next=s.dpr
 if(s.slow>2){next=Math.max(1,s.dpr*.85);s.slow=0;s.fast=0}
 else if(s.fast>10){next=Math.min(s.ceiling,s.dpr+.1);s.fast=0}
 next=Math.round(next*100)/100
 if(Math.abs(next-s.dpr)<.025)return null
 s.dpr=next;s.warm=0;return next
}
