import {useEffect,useRef} from "react"
import {useFrame,useThree} from "@react-three/fiber"

/* Frame-time budget controls only derived presentation quality. It never
 * mutates application state, materials, or authoritative Savant data. */
export function SceneBudget({active}:{active:boolean}){
 const {setDpr,gl}=useThree()
 const visible=useRef(true)
 const stats=useRef({elapsed:0,frames:0,slow:0,fast:0,cooldown:0,
  cap:Math.min(2,typeof window==="undefined"?1:window.devicePixelRatio||1)})
 useEffect(()=>{
  const refresh=()=>{
   stats.current.cap=Math.min(2,window.devicePixelRatio||1)
  }
  const visibility=()=>{visible.current=!document.hidden;stats.current.elapsed=0;stats.current.frames=0}
  window.addEventListener("resize",refresh,{passive:true})
  document.addEventListener("visibilitychange",visibility)
  return ()=>{window.removeEventListener("resize",refresh);document.removeEventListener("visibilitychange",visibility)}
 },[])
 useFrame((_,delta)=>{
  const s=stats.current
  if(!active||!visible.current){s.elapsed=0;s.frames=0;s.slow=0;s.fast=0;return}
  if(delta<=0||delta>.12){s.elapsed=0;s.frames=0;return}
  s.elapsed+=delta;s.frames++;s.cooldown+=delta
  if(s.elapsed<3||s.frames<45)return
  const average=s.elapsed/s.frames
  s.elapsed=0;s.frames=0
  s.slow=average>.027?s.slow+1:0
  s.fast=average<.017?s.fast+1:0
  if(s.cooldown<5)return
  const current=gl.getPixelRatio()
  if(current>s.cap+.025){setDpr(s.cap);s.cooldown=0;return}
  let next=current
  if(s.slow>=2)next=Math.max(.75,current-.2)
  else if(s.fast>=4&&s.cooldown>=12)next=Math.min(s.cap,current+.15)
  if(Math.abs(next-current)>.025){
   setDpr(next);s.cooldown=0;s.slow=0;s.fast=0
  }
 },-1)
 return null
}
