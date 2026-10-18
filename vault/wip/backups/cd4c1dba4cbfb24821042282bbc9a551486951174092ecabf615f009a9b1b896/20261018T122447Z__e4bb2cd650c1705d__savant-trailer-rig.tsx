import {useEffect,useLayoutEffect,useRef} from "react"
import type {MutableRefObject} from "react"
import {useFrame} from "@react-three/fiber"
import type {ArtDirection} from "./savant-art-direction"
import {Color,DirectionalLight,HemisphereLight,Object3D,RectAreaLight,SpotLight} from "three"
import {damp} from "./savant-motion"
import {RectAreaLightUniformsLib} from "three/addons/lights/RectAreaLightUniformsLib.js"

let initialized=false
function initializeAreaLighting(){
 if(initialized)return
 RectAreaLightUniformsLib.init()
 initialized=true
}

/** Four stock light types; one shaded pass, five motivated lamps, no shadow maps or recurring reflection captures. */
export function SavantTrailerRig({time,moving,profile}:{
 time:MutableRefObject<number>;moving:boolean;profile:ArtDirection
}){
 const key=useRef<RectAreaLight>(null)
 const rear=useRef<RectAreaLight>(null)
 const spot=useRef<SpotLight>(null)
 const rim=useRef<DirectionalLight>(null)
 const fill=useRef<HemisphereLight>(null)
 const target=useRef<Object3D>(null)
 const ready=useRef(false)
 const palette=useRef([new Color(),new Color(),new Color(),new Color()])

 useLayoutEffect(()=>{
  initializeAreaLighting()
  if(key.current)key.current.lookAt(0,.12,0)
  if(rear.current)rear.current.lookAt(0,0,0)
  if(spot.current&&target.current)spot.current.target=target.current
  if(rim.current&&target.current)rim.current.target=target.current
  ready.current=true
 },[])
 useEffect(()=>()=>{ready.current=false},[])

 useFrame((_,delta)=>{
  if(!ready.current)return
  const t=moving?time.current:0
  const blend=moving?damp(0,1,8,delta):1
  const artist=profile.kind>=0
  const colors=palette.current
  colors[0].set(artist?profile.paper:"#eef5ff")
  colors[1].set(artist?profile.accent:"#dfc196")
  colors[2].set(artist?profile.secondary:"#a1c8e5")
  colors[3].set(artist?profile.ink:"#30292a")
  key.current?.color.lerp(colors[0],blend);rear.current?.color.lerp(colors[2],blend)
  spot.current?.color.lerp(colors[1],blend);rim.current?.color.lerp(colors[2],.12)
  fill.current?.color.lerp(colors[0],.12);fill.current?.groundColor.lerp(colors[3],blend)
  // Analytic cosine envelopes have zero velocity at their sweep endpoints.
  // There are no random peaks, strobes or abrupt light/color changes.
  const sweep=.5-.5*Math.cos(t*.31)
  const breath=.5-.5*Math.cos(t*.19)
  if(key.current){
   key.current.position.set(-2.7+sweep*.28,2.15+breath*.15,3.7)
   key.current.intensity=(3.2+breath*.45)*profile.energy
   key.current.width=artist?2+profile.softness*8:2.5
   key.current.lookAt(0,.12,0)
  }
  if(rear.current){
   rear.current.position.set(1.7+Math.sin(t*.23)*.4,1.3,-3.2)
   rear.current.intensity=(2.1+breath*.35)*profile.energy
   rear.current.lookAt(0,0,0)
  }
  if(spot.current){
   spot.current.position.set(2.5, .4+sweep*.5, 2.45)
   spot.current.intensity=(11+sweep*2)*profile.energy
  }
  if(rim.current)rim.current.intensity=(1.1+breath*.2)*profile.energy
  if(fill.current)fill.current.intensity=.12
 },-2)

 return <group name="savant-trailer-lighting">
  <object3D ref={target} position={[0,.1,0]}/>
  <rectAreaLight ref={key} name="savant-softbox-key" color="#eef5ff"
   intensity={3.2} width={2.5} height={4.2} position={[-2.7,2.15,3.7]}/>
  <rectAreaLight ref={rear} name="savant-back-softbox" color="#e7c78b"
   intensity={2.1} width={2.2} height={3.8} position={[1.7,1.3,-3.2]}/>
  <spotLight ref={spot} name="savant-gold-graze" color="#dfc196"
   intensity={11} position={[2.5,.4,2.45]} distance={10}
   angle={.58} penumbra={1} decay={2} castShadow={false}/>
  <directionalLight ref={rim} name="savant-cold-rim" color="#a1c8e5"
   intensity={1.1} position={[1.5,1.3,-3.8]} castShadow={false}/>
  <hemisphereLight ref={fill} name="savant-mineral-fill"
   color="#b3c5d3" groundColor="#30292a" intensity={.12}/>
 </group>
}
