import {useEffect,useLayoutEffect,useMemo,useRef} from "react"
import type {MutableRefObject} from "react"
import {useFrame} from "@react-three/fiber"
import {Color,CylinderGeometry,DynamicDrawUsage,InstancedMesh,MeshStandardMaterial,Object3D,PointLight,Quaternion,SphereGeometry,Vector3} from "three"
import {emitterLife,emitterVisibility,helixPhase,hotSpark,sparkEase,sparkHash,sparkHelix,sparkLightCount,sparksPerEmitter,sparkTrailSegments} from "./savant-spark-motion"

const segments=sparkTrailSegments
/** Four instanced draws and four fixed moving lights; no reflection recapture or shadow pass. */
export function StudioParticles({time,count,active}:{
 time:MutableRefObject<number>;count:number;active:boolean
}){
 const heads=useRef<InstancedMesh>(null),trails=useRef<InstancedMesh>(null)
 const sparks=useRef<InstancedMesh>(null),burst=useRef<InstancedMesh>(null)
 const lights=useRef<(PointLight|null)[]>([])
 const resources=useMemo(()=>({
  head:new SphereGeometry(1,14,10),
  trail:new CylinderGeometry(1,1,1,6,1,true),
  chip:new SphereGeometry(1,8,6),
  metal:new MeshStandardMaterial({color:"#b5a594",metalness:.9,roughness:.24,
   emissive:"#ff4911",emissiveIntensity:2.2,dithering:true}),
  warm:new MeshStandardMaterial({color:"#b99a6a",metalness:.85,roughness:.3,
   emissive:"#bf3009",emissiveIntensity:.65,dithering:true}),
  hot:new MeshStandardMaterial({color:"#ffd49b",metalness:.55,roughness:.3,
   emissive:"#ff3107",emissiveIntensity:4,dithering:true}),
  dummy:new Object3D(),a:new Vector3(),b:new Vector3(),direction:new Vector3(),
  up:new Vector3(0,1,0),rotation:new Quaternion(),color:new Color(),
 }),[])
 useLayoutEffect(()=>{
  for(const mesh of [heads.current,trails.current,sparks.current,burst.current]){
   mesh?.instanceMatrix.setUsage(DynamicDrawUsage)
  }
  for(let i=0;i<count;i++)heads.current?.setColorAt(i,new Color(i%3===0?"#ffe5ba":"#da9d78"))
  if(heads.current?.instanceColor)heads.current.instanceColor.needsUpdate=true
  for(let i=0;i<count*sparksPerEmitter;i++)sparks.current?.setColorAt(i,new Color("#ffffff"))
  if(sparks.current?.instanceColor){
   sparks.current.instanceColor.setUsage(DynamicDrawUsage)
   sparks.current.instanceColor.needsUpdate=true
  }
 },[count])
 useEffect(()=>()=>{resources.head.dispose();resources.trail.dispose();resources.chip.dispose()
  resources.metal.dispose();resources.warm.dispose();resources.hot.dispose()},[resources])
 useFrame(()=>{
  if(!heads.current||!trails.current||!sparks.current||!burst.current)return
  const {dummy,a,b,direction,up,rotation,color}=resources,t=time.current
  const {chosen,age,epoch}=emitterLife(t,count,active)
  for(let id=0;id<count;id++){
   const visibility=emitterVisibility(id,t,count,chosen,age)
   sparkHelix(id,t,count,a)
   dummy.position.copy(a)
   dummy.rotation.set(t*(.3+sparkHash(id)*.6),t*(.4+sparkHash(id+9)),id)
   const breath=.9+.1*Math.sin(t*5.1+id*1.7)
   dummy.scale.setScalar(.02*visibility*breath);dummy.scale.y*=1.5
   dummy.updateMatrix();heads.current.setMatrixAt(id,dummy.matrix)
   const span=.56+.25*sparkHash(id+301)
   for(let k=0;k<segments;k++){
    const lag=k/segments*span,next=(k+1)/segments*span
    sparkHelix(id,t-lag,count,a);sparkHelix(id,t-next,count,b)
    const continuous=Math.floor(helixPhase(id,t-lag,count))===Math.floor(helixPhase(id,t-next,count))
    direction.subVectors(b,a);const length=direction.length()
    dummy.position.copy(a).add(b).multiplyScalar(.5)
    if(length>.000001)rotation.setFromUnitVectors(up,direction.multiplyScalar(1/length))
    dummy.quaternion.copy(rotation)
    const width=.0032*Math.pow(1-(k+.5)/segments,.8)*visibility
    dummy.scale.set(width,continuous?length:0,width)
    dummy.updateMatrix();trails.current.setMatrixAt(id*segments+k,dummy.matrix)
   }
   for(let piece=0;piece<sparksPerEmitter;piece++){
    const state=hotSpark(id,piece,t,count,a,direction)
    const on=active?state.visibility*visibility:0
    const length=direction.length()
    if(length>.00001)rotation.setFromUnitVectors(up,direction.multiplyScalar(1/length))
    dummy.position.copy(a);dummy.quaternion.copy(rotation)
    dummy.scale.set(.0025*on,(.014+state.age*.055)*on,.0025*on)
    dummy.updateMatrix();const index=id*sparksPerEmitter+piece
    sparks.current.setMatrixAt(index,dummy.matrix)
    const cooling=1-Math.min(1,state.age/state.life)
    color.setRGB(1,.12+.7*cooling,.025+.3*cooling)
    sparks.current.setColorAt(index,color)
   }
  }
  const exploding=chosen>=0&&age<.6
  burst.current.count=exploding?8:0
  if(exploding){
   sparkHelix(chosen,t-age,count,a)
   for(let piece=0;piece<8;piece++){
    const theta=sparkHash(epoch*17+piece)*Math.PI*2,z=sparkHash(piece+epoch*41+7)*2-1
    const radial=Math.sqrt(Math.max(0,1-z*z))
    direction.set(Math.cos(theta)*radial,z,Math.sin(theta)*radial)
    dummy.position.copy(a).addScaledVector(direction,age*(1.5+sparkHash(piece+8)))
    dummy.position.y-=1.2*age*age
    dummy.rotation.set(age*12+piece,age*9+piece,age*15)
    dummy.scale.setScalar(.009*(1-sparkEase(age/.6)))
    dummy.scale.y*=2;dummy.updateMatrix();burst.current.setMatrixAt(piece,dummy.matrix)
   }
   burst.current.instanceMatrix.needsUpdate=true
  }
  for(let slot=0;slot<sparkLightCount;slot++){
   const lamp=lights.current[slot]
   if(!lamp)continue
   const id=Math.floor(slot*count/sparkLightCount)
   sparkHelix(id,t,count,a);lamp.position.copy(a)
   const visibility=emitterVisibility(id,t,count,chosen,age)
   const heat=.5+.5*Math.sin(t*7+id*1.31)
   lamp.intensity=active?(.22+.25*heat)*visibility:0
  }
  heads.current.instanceMatrix.needsUpdate=true
  trails.current.instanceMatrix.needsUpdate=true;sparks.current.instanceMatrix.needsUpdate=true
  if(sparks.current.instanceColor)sparks.current.instanceColor.needsUpdate=true
 },-2)
 return <group name="savant-hot-spark-helix-v1">
  <instancedMesh ref={heads} args={[resources.head,resources.metal,count]} frustumCulled={false} dispose={null}/>
  <instancedMesh ref={trails} args={[resources.trail,resources.warm,count*segments]} frustumCulled={false} dispose={null}/>
  <instancedMesh ref={sparks} args={[resources.chip,resources.hot,count*sparksPerEmitter]} frustumCulled={false} dispose={null}/>
  <instancedMesh ref={burst} args={[resources.chip,resources.hot,8]} frustumCulled={false} dispose={null}/>
  {Array.from({length:sparkLightCount},(_,i)=><pointLight key={i}
   ref={node=>{lights.current[i]=node}} color="#ff5422" intensity={0}
   distance={1.65} decay={2} castShadow={false}/>)}
 </group>
}
