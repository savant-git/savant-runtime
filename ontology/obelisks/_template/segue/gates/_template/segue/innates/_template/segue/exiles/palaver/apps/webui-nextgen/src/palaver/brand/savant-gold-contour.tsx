import {useEffect,useLayoutEffect,useMemo,useRef} from "react"
import type {MutableRefObject} from "react"
import {useFrame} from "@react-three/fiber"
import {CatmullRomCurve3,Color,DynamicDrawUsage,InstancedMesh,MeshPhysicalMaterial,Object3D,SphereGeometry,TubeGeometry,Vector3} from "three"
import type {ArtDirection} from "./savant-art-direction"
import {titleContours} from "./savant-title-contours"
import {installTitleGlitch,warpTitlePoint} from "./savant-title-motion"
import type {TitleGlitch} from "./savant-title-motion"
import {ContourCombustion} from "./savant-contour-combustion"
import {contourPhase} from "./savant-contour-emission"

export function SavantGoldContour({time,glitch,profile}:{
 time:MutableRefObject<number>;glitch:TitleGlitch;profile:ArtDirection
}){
 const heads=useRef<InstancedMesh>(null)
 const resources=useMemo(()=>{
  const curves=titleContours.map(points=>{
   const curve=new CatmullRomCurve3(points.map(p=>new Vector3(p[0],p[1],p[2])),true,"catmullrom",.5)
   curve.arcLengthDivisions=2048;curve.updateArcLengths();return curve
  })
  const rails=curves.map(curve=>new TubeGeometry(curve,768,.0055,10,true))
  const edge=new MeshPhysicalMaterial({color:"#d6b45f",metalness:.9,roughness:.24,
   clearcoat:.8,clearcoatRoughness:.16,emissive:"#bd8d46",emissiveIntensity:.18,dithering:true})
  const head=new MeshPhysicalMaterial({color:"#fff0c9",metalness:.7,roughness:.17,
   clearcoat:1,emissive:"#ffd58b",emissiveIntensity:2.8,dithering:true})
  installTitleGlitch(edge,glitch)
  return {curves,rails,edge,head,sphere:new SphereGeometry(1,16,12),dummy:new Object3D(),point:new Vector3()}
 },[glitch])
 useLayoutEffect(()=>{
  resources.edge.color.set("#d6b45f").lerp(new Color(profile.accent),.15)
  heads.current?.instanceMatrix.setUsage(DynamicDrawUsage)
 },[resources,profile])
 useEffect(()=>()=>{resources.rails.forEach(g=>g.dispose());resources.sphere.dispose()
  resources.edge.dispose();resources.head.dispose()},[resources])
 useFrame(()=>{
  if(!heads.current)return
  const {dummy,point,curves}=resources,t=time.current
  resources.edge.emissiveIntensity=.14+.06*(.5+.5*Math.sin(t*1.4))
  let index=0
  for(let side=0;side<curves.length;side++)for(let tracer=0;tracer<2;tracer++){
   curves[side].getPointAt(contourPhase(side,tracer,t,profile.speed),point)
   const warp=warpTitlePoint(point.x,point.y,point.z,t,glitch.amount.value)
   dummy.position.set(warp[0],warp[1],warp[2]);dummy.scale.setScalar(.018)
   dummy.updateMatrix();heads.current.setMatrixAt(index++,dummy.matrix)
  }
  heads.current.instanceMatrix.needsUpdate=true
 },-1)
 return <group name="savant-front-back-contour-combustion">
  {resources.rails.map((geometry,i)=><mesh key={i} geometry={geometry} material={resources.edge} frustumCulled={false}/>)}
  <instancedMesh ref={heads} args={[resources.sphere,resources.head,4]} frustumCulled={false} dispose={null}/>
  <ContourCombustion curves={resources.curves} time={time} glitch={glitch} profile={profile}/>
 </group>
}
