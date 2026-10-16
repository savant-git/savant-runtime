import { Canvas, useFrame } from "@react-three/fiber"
import { useEffect, useMemo, useRef, useState } from "react"
import { IcosahedronGeometry, LineSegments } from "three"

function Topology({motion}:{motion:boolean}) {
 const ref=useRef<LineSegments>(null)
 const geometry=useMemo(()=>new IcosahedronGeometry(2.5,3),[])
 useEffect(()=>()=>geometry.dispose(),[geometry])
 useFrame(({clock})=>{
  if(!ref.current||!motion)return
  ref.current.rotation.y=clock.elapsedTime*.02
  ref.current.rotation.x=clock.elapsedTime*.01
 })
 return <lineSegments ref={ref}>
  <edgesGeometry args={[geometry]}/>
  <lineBasicMaterial color="#76b4a7" transparent opacity={.075} depthWrite={false}/>
 </lineSegments>
}
export default function TopologyField(){
 const [motion,setMotion]=useState(false)
 const [visible,setVisible]=useState(true)
 const host=useRef<HTMLDivElement>(null)
 useEffect(()=>{
  const query=window.matchMedia("(prefers-reduced-motion: reduce)")
  const update=()=>setMotion(!query.matches)
  update();query.addEventListener("change",update)
  return ()=>query.removeEventListener("change",update)
 },[])
 useEffect(()=>{
  if(!host.current||typeof IntersectionObserver==="undefined")return
  const observer=new IntersectionObserver(entries=>setVisible(entries[0]?.isIntersecting??true),{threshold:0})
  observer.observe(host.current)
  return ()=>observer.disconnect()
 },[])
 return <div ref={host} className="savant-topology-field" aria-hidden="true"><Canvas camera={{position:[0,0,6]}} frameloop={motion&&visible?"always":"demand"}
  dpr={[1,Math.min(1.5,typeof window==="undefined"?1:window.devicePixelRatio||1)]}
  gl={{antialias:false,alpha:true,powerPreference:"low-power"}}>
  <Topology motion={motion&&visible}/>
 </Canvas></div>
}
