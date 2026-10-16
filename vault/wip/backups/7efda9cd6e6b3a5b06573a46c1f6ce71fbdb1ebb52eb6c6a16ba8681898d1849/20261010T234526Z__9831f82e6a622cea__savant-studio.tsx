import React,{useRef} from "react"
import {useFrame} from "@react-three/fiber"
import {Group} from "three"
import type {MaterialPreset} from "./savant-surfaces"

/* Visible geometry adds parallax, contact cues and genuine depth behind the mark.
 * Its materials derive from the same appearance registry as the logo. */
export function StudioEnvironment({time,preset}:{
 time:React.MutableRefObject<number>;preset:MaterialPreset
}){
 const stage=useRef<Group>(null)
 useFrame(()=>{
  if(stage.current)stage.current.rotation.z=Math.sin(time.current*.15)*.035
 },-2)
 return <group ref={stage} position={[0,0,-2.1]}>
  <mesh position={[0,0,-.3]} rotation={[.22,preset.scene.tilt,0]} receiveShadow>
   <torusGeometry args={[1.48,.035,12,96]}/>
   <meshPhysicalMaterial color={preset.accent2} metalness={preset.stroke.metalness}
    roughness={preset.stroke.roughness} clearcoat={1} envMapIntensity={preset.scene.energy}/>
  </mesh>
  {[-1,1].map(side=><group key={side}>
   <mesh position={[side*1.8,0,-.2]} rotation={[0,side*.35,side*.08]}>
    <boxGeometry args={[.1,4,.5]}/>
    <meshPhysicalMaterial color={preset.stroke.color} metalness={preset.stroke.metalness}
     roughness={.28} clearcoat={1} envMapIntensity={preset.scene.energy}/>
   </mesh>
   <pointLight position={[side*1.4,.4,.5]} color={side<0?preset.accent:preset.accent2}
    intensity={preset.scene.energy*2} distance={4} decay={2}/>
  </group>)}
 </group>
}
