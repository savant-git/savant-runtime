import {useEffect,useLayoutEffect,useRef} from "react"
import type {MutableRefObject} from "react"
import {useFrame} from "@react-three/fiber"
import {DirectionalLight,HemisphereLight,Object3D,RectAreaLight,SpotLight} from "three"
import {RectAreaLightUniformsLib} from "three/addons/lights/RectAreaLightUniformsLib.js"

let initialized=false
function initializeAreaLighting(){
 if(initialized)return
 RectAreaLightUniformsLib.init()
 initialized=true
}

/** Four stock light types; one shaded pass, no shadow maps, overlays or shader injection. */
export function SavantTrailerRig({time,moving}:{
 time:MutableRefObject<number>;moving:boolean
}){
 const key=useRef<RectAreaLight>(null)
 const spot=useRef<SpotLight>(null)
 const rim=useRef<DirectionalLight>(null)
 const fill=useRef<HemisphereLight>(null)
 const target=useRef<Object3D>(null)
 const ready=useRef(false)

 useLayoutEffect(()=>{
  initializeAreaLighting()
  if(key.current)key.current.lookAt(0,.12,0)
  if(spot.current&&target.current)spot.current.target=target.current
  if(rim.current&&target.current)rim.current.target=target.current
  ready.current=true
 },[])
 useEffect(()=>()=>{ready.current=false},[])

 useFrame(()=>{
  if(!ready.current)return
  const t=moving?time.current:0
  // Analytic cosine envelopes have zero velocity at their sweep endpoints.
  // There are no random peaks, strobes or abrupt light/color changes.
  const sweep=.5-.5*Math.cos(t*.31)
  const breath=.5-.5*Math.cos(t*.19)
  if(key.current){
   key.current.position.set(-2.7+sweep*.28,2.15+breath*.15,3.7)
   key.current.intensity=2.15+breath*.16
   key.current.lookAt(0,.12,0)
  }
  if(spot.current){
   spot.current.position.set(2.5, .4+sweep*.5, 2.45)
   spot.current.intensity=6.5+sweep*.7
  }
  if(rim.current)rim.current.intensity=.72+breath*.14
  if(fill.current)fill.current.intensity=.16
 },-2)

 return <group name="savant-trailer-lighting">
  <object3D ref={target} position={[0,.1,0]}/>
  <rectAreaLight ref={key} name="savant-softbox-key" color="#eef5ff"
   intensity={2.15} width={3.4} height={4.8} position={[-2.7,2.15,3.7]}/>
  <spotLight ref={spot} name="savant-gold-graze" color="#dfc196"
   intensity={6.5} position={[2.5,.4,2.45]} distance={10}
   angle={.58} penumbra={1} decay={2} castShadow={false}/>
  <directionalLight ref={rim} name="savant-cold-rim" color="#a1c8e5"
   intensity={.72} position={[1.5,1.3,-3.8]} castShadow={false}/>
  <hemisphereLight ref={fill} name="savant-mineral-fill"
   color="#b3c5d3" groundColor="#30292a" intensity={.16}/>
 </group>
}
