import {useEffect,useMemo,useRef} from "react"
import type {MutableRefObject} from "react"
import {useFrame} from "@react-three/fiber"
import {Curve,DynamicDrawUsage,InstancedMesh,MeshPhysicalMaterial,Object3D,SphereGeometry,TubeGeometry,Vector3} from "three"
import {titleContours} from "./savant-title-contours"
import {installTitleGlitch,warpTitlePoint} from "./savant-title-motion"
import type {TitleGlitch} from "./savant-title-motion"

/** Piecewise interpolation preserves measured depth clearance without spline overshoot. */
class ContourCurve extends Curve<Vector3>{
 readonly points:Vector3[]
 readonly lengths:number[]=[0]
 readonly total:number
 constructor(source:readonly (readonly number[])[]){
  super()
  this.points=source.map(p=>new Vector3(p[0],p[1],p[2]))
  for(let i=0;i<this.points.length;i++){
   this.lengths.push(this.lengths[i]+this.points[i].distanceTo(this.points[(i+1)%this.points.length]))
  }
  this.total=this.lengths[this.lengths.length-1]
 }
 getPoint(t:number,target=new Vector3()){
  const distance=((t%1)+1)%1*this.total
  let lo=0,hi=this.points.length-1
  while(lo<hi){
   const mid=(lo+hi+1)>>1
   if(this.lengths[mid]<=distance)lo=mid;else hi=mid-1
  }
  const next=(lo+1)%this.points.length
  const fraction=(distance-this.lengths[lo])/(this.lengths[lo+1]-this.lengths[lo])
  return target.copy(this.points[lo]).lerp(this.points[next],fraction)
 }
 // Already parameterized by true arc length.
 getPointAt(u:number,target?:Vector3){return this.getPoint(u,target)}
}

/** Actual GLB-derived front/back contour, opaque gold PBR and two instanced tracer draws. */
export function SavantGoldContour({time,glitch}:{
 time:MutableRefObject<number>;glitch:TitleGlitch
}){
 const heads=useRef<InstancedMesh>(null),tails=useRef<InstancedMesh>(null)
 const resources=useMemo(()=>{
  const curves=titleContours.map(points=>new ContourCurve(points))
  const rails=curves.map(curve=>new TubeGeometry(curve,1024,.009,8,true))
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
    for(let j=0;j<=10;j++){
     curves[side].getPoint(phase-j*.003,point)
     const warped=warpTitlePoint(point.x,point.y,point.z,t,glitch.amount.value)
     dummy.position.set(warped[0],warped[1],warped[2])
     const radius=j===0?.015:.011*(1-j/12)
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
  <instancedMesh ref={tails} args={[resources.sphere,resources.tailMaterial,40]} frustumCulled={false}/>
 </group>
}
