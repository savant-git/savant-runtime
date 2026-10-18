import {useEffect,useMemo,useRef} from "react"
import type {MutableRefObject} from "react"
import {useFrame} from "@react-three/fiber"
import {CatmullRomCurve3,DynamicDrawUsage,InstancedMesh,MeshPhysicalMaterial,Object3D,SphereGeometry,TubeGeometry,Vector3} from "three"
import {titleContours} from "./savant-title-contours"
import {installTitleGlitch,warpTitlePoint} from "./savant-title-motion"
import type {TitleGlitch} from "./savant-title-motion"

/** Smooth closed splines; baked control points include measured depth clearance. */
function contourCurve(source:readonly (readonly number[])[]){
 const curve=new CatmullRomCurve3(source.map(p=>new Vector3(p[0],p[1],p[2])),true,"catmullrom",.5)
 curve.arcLengthDivisions=2048
 curve.updateArcLengths()
 return curve
}

/** Actual GLB-derived front/back contour, opaque gold PBR and two instanced tracer draws. */
export function SavantGoldContour({time,glitch}:{
 time:MutableRefObject<number>;glitch:TitleGlitch
}){
 const heads=useRef<InstancedMesh>(null),tails=useRef<InstancedMesh>(null)
 const resources=useMemo(()=>{
  const curves=titleContours.map(points=>contourCurve(points))
  const rails=curves.map(curve=>new TubeGeometry(curve,768,.007,12,true))
  const gold=new MeshPhysicalMaterial({
   name:"savant-neon-gold-edge",color:"#e3bf71",metalness:.88,roughness:.19,
   clearcoat:.8,clearcoatRoughness:.15,emissive:"#e5af42",emissiveIntensity:.65,
   envMapIntensity:1.3,dithering:true,
  })
  installTitleGlitch(gold,glitch)
  const headMaterial=new MeshPhysicalMaterial({
   color:"#fff3cb",metalness:.85,roughness:.12,clearcoat:1,
   emissive:"#ffdb83",emissiveIntensity:2.2,dithering:true,
  })
  const tailMaterial=new MeshPhysicalMaterial({
   color:"#e7bb61",metalness:.85,roughness:.2,clearcoat:.7,
   emissive:"#e8ac39",emissiveIntensity:.9,dithering:true,
  })
  return {curves,rails,gold,headMaterial,tailMaterial,
   sphere:new SphereGeometry(1,12,8),dummy:new Object3D(),point:new Vector3()}
 },[glitch])
 useEffect(()=>{
  heads.current?.instanceMatrix.setUsage(DynamicDrawUsage)
  tails.current?.instanceMatrix.setUsage(DynamicDrawUsage)
  return()=>{
   resources.rails.forEach(g=>g.dispose());resources.sphere.dispose()
   resources.gold.dispose();resources.headMaterial.dispose();resources.tailMaterial.dispose()
  }
 },[resources])
 useFrame(()=>{
  if(!heads.current||!tails.current)return
  const t=time.current,{curves,point,dummy}=resources
  resources.gold.emissiveIntensity=.58+.18*(.5+.5*Math.sin(t*1.7))
  let headIndex=0,tailIndex=0
  for(let side=0;side<curves.length;side++){
   for(let tracer=0;tracer<2;tracer++){
    const phase=t*(side===0?.16:-.145)+tracer*.5+side*.13
    for(let j=0;j<=16;j++){
     curves[side].getPointAt(((phase-j*.0028)%1+1)%1,point)
     const warped=warpTitlePoint(point.x,point.y,point.z,t,glitch.amount.value)
     dummy.position.set(warped[0],warped[1],warped[2])
     const radius=j===0?.017:.012*(1-j/18)
     dummy.scale.setScalar(radius);dummy.updateMatrix()
     if(j===0)heads.current.setMatrixAt(headIndex++,dummy.matrix)
     else tails.current.setMatrixAt(tailIndex++,dummy.matrix)
    }
   }
  }
  heads.current.instanceMatrix.needsUpdate=true
  tails.current.instanceMatrix.needsUpdate=true
 },-1)
 return <group name="savant-front-back-contour">
  {resources.rails.map((geometry,i)=><mesh key={i} geometry={geometry} material={resources.gold} frustumCulled={false}/>)}
  <instancedMesh ref={heads} args={[resources.sphere,resources.headMaterial,4]} frustumCulled={false}/>
  <instancedMesh ref={tails} args={[resources.sphere,resources.tailMaterial,64]} frustumCulled={false}/>
 </group>
}
