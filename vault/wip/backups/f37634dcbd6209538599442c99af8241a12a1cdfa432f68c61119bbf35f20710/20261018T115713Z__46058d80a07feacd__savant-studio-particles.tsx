import {useEffect,useLayoutEffect,useMemo,useRef} from "react"
import type {MutableRefObject} from "react"
import {useFrame} from "@react-three/fiber"
import {BoxGeometry,ConeGeometry,OctahedronGeometry,TorusGeometry,Color,CylinderGeometry,DynamicDrawUsage,InstancedMesh,MeshStandardMaterial,Object3D,PointLight,Quaternion,SphereGeometry,Vector3} from "three"
import type {ArtDirection} from "./savant-art-direction"
import {installTrailSurface,setTrailPalette,trailAgeAttribute} from "./savant-trail-surface"
import {emitterLife,emitterVisibility,helixPhase,hotSpark,sparkEase,sparkHash,sparkHelix,sparkLightCount,sparksPerEmitter,sparkTrailSegments} from "./savant-spark-motion"

const segments=sparkTrailSegments
/** Four instanced draws and four fixed moving lights; no reflection recapture or shadow pass. */
export function StudioParticles({time,count,active,profile}:{
 time:MutableRefObject<number>;count:number;active:boolean;profile:ArtDirection
}){
 const heads=useRef<InstancedMesh>(null),trails=useRef<InstancedMesh>(null)
 const sparks=useRef<InstancedMesh>(null),burst=useRef<InstancedMesh>(null)
 const lights=useRef<(PointLight|null)[]>([])
 const resources=useMemo(()=>{
  const data={
  shapes:{sphere:new SphereGeometry(1,14,10),shard:new ConeGeometry(.65,2.2,5),
   crystal:new OctahedronGeometry(1,0),ring:new TorusGeometry(.75,.18,8,16),
   leaf:new SphereGeometry(1,10,6),tile:new BoxGeometry(1.5,.25,1.5),
   ribbon:new BoxGeometry(.5,2,.15)},
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
 }
  data.trail.setAttribute("aSavantTrailAge",trailAgeAttribute(count,segments))
  installTrailSurface(data.warm)
  installTrailSurface(data.hot,true)
  return data
 },[count,resources])
 useLayoutEffect(()=>{
  for(const mesh of [heads.current,trails.current,sparks.current,burst.current]){
   mesh?.instanceMatrix.setUsage(DynamicDrawUsage)
  }
  for(let i=0;i<count;i++)heads.current?.setColorAt(i,new Color("#ffffff"))
  if(heads.current?.instanceColor)heads.current.instanceColor.needsUpdate=true
  for(let i=0;i<count*sparksPerEmitter;i++)sparks.current?.setColorAt(i,new Color("#ffffff"))
  if(sparks.current?.instanceColor){
   sparks.current.instanceColor.setUsage(DynamicDrawUsage)
   sparks.current.instanceColor.needsUpdate=true
  }
 },[count])
 useLayoutEffect(()=>{
  const artistic=profile.kind>=0
  resources.metal.color.set(artistic?profile.paper:"#b5a594")
  resources.metal.emissive.set(artistic?profile.accent:"#ff4911")
  resources.metal.emissiveIntensity=artistic?profile.emission:2.2
  resources.metal.metalness=artistic?profile.metal:.9
  resources.metal.roughness=artistic?profile.rough:.24
  resources.hot.emissiveIntensity=artistic?.15+profile.emission*.9:4
  resources.hot.roughness=artistic?.5:.3
  setTrailPalette(resources.warm,artistic?profile.paper:"#d6b45f",artistic?profile.secondary:"#ff2f9d")
  setTrailPalette(resources.hot,artistic?profile.accent:"#d6b45f",artistic?profile.secondary:"#ff2f9d")
 },[profile,resources])
 useEffect(()=>()=>{Object.values(resources.shapes).forEach(g=>g.dispose());resources.trail.dispose();resources.chip.dispose()
  resources.metal.dispose();resources.warm.dispose();resources.hot.dispose()},[resources])
 useFrame(()=>{
  if(!heads.current||!trails.current||!sparks.current||!burst.current)return
  const {dummy,a,b,direction,up,rotation,color}=resources,t=time.current*profile.speed
  const {chosen,age,epoch}=emitterLife(t,count,active)
  for(let id=0;id<count;id++){
   const visibility=emitterVisibility(id,t,count,chosen,age)
   sparkHelix(id,t,count,a)
   dummy.position.copy(a)
   dummy.rotation.set(t*(.3+sparkHash(id)*.6)*profile.spin,t*(.4+sparkHash(id+9))*profile.spin,id)
   const breath=.9+.1*Math.sin(t*5.1+id*1.7)
   dummy.scale.setScalar(.02*visibility*breath*profile.size);dummy.scale.y*=profile.stretch
   if(profile.shape==="leaf"){dummy.scale.z*=.22;dummy.scale.x*=1.4}
   dummy.updateMatrix();heads.current.setMatrixAt(id,dummy.matrix)
   const span=.85+.4*sparkHash(id+301)
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
    if(profile.kind<0)color.setRGB(1,.12+.7*cooling,.025+.3*cooling)
    else color.setRGB(1,1,1)
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
   lamp.color.set(profile.kind>=0?profile.accent:"#ff5422")
   lamp.intensity=active?(.22+.25*heat)*visibility*profile.energy:0
  }
  heads.current.instanceMatrix.needsUpdate=true
  trails.current.instanceMatrix.needsUpdate=true;sparks.current.instanceMatrix.needsUpdate=true
  if(sparks.current.instanceColor)sparks.current.instanceColor.needsUpdate=true
 },-2)
 return <group name="savant-hot-spark-helix-v1">
  <instancedMesh ref={heads} args={[resources.shapes[profile.shape],resources.metal,count]} frustumCulled={false} dispose={null}/>
  <instancedMesh ref={trails} args={[resources.trail,resources.warm,count*segments]} frustumCulled={false} dispose={null}/>
  <instancedMesh ref={sparks} args={[resources.chip,resources.hot,count*sparksPerEmitter]} frustumCulled={false} dispose={null}/>
  <instancedMesh ref={burst} args={[resources.chip,resources.hot,8]} frustumCulled={false} dispose={null}/>
  {Array.from({length:sparkLightCount},(_,i)=><pointLight key={i}
   ref={node=>{lights.current[i]=node}} color="#ff5422" intensity={0}
   distance={1.65} decay={2} castShadow={false}/>)}
 </group>
}
