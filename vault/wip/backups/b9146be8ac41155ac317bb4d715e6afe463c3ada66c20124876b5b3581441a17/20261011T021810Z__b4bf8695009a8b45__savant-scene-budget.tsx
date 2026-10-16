import {useRef} from "react"
import {useFrame,useThree} from "@react-three/fiber"
/* Slow hysteresis prevents resize thrash. Measures frame intervals, not exact
 * GPU time: telemetry is local and only controls derived rendering quality. */
export function SceneBudget({active}:{active:boolean}){
 const {setDpr,gl}=useThree()
 const stats=useRef({sum:0,count:0,cooldown:0,level:Math.min(1.75,typeof window==="undefined"?1:window.devicePixelRatio||1)})
 useFrame((_,delta)=>{
  if(!active||delta>.15)return
  const s=stats.current;s.cooldown+=delta;s.sum+=delta;s.count++
  if(s.count<120||s.cooldown<4)return
  const avg=s.sum/s.count,current=gl.getPixelRatio()
  let next=current
  if(avg>.028)next=Math.max(1,current-.25)
  else if(avg<.018&&s.cooldown>12)next=Math.min(s.level,current+.25)
  if(Math.abs(next-current)>.01){setDpr(next);s.cooldown=0}
  s.sum=0;s.count=0;s.cooldown=Math.min(s.cooldown,20)
 },-1)
 return null
}
