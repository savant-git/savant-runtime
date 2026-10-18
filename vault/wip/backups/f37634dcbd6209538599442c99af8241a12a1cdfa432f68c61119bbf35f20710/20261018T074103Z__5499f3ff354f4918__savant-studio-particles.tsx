import {useEffect,useLayoutEffect,useMemo,useRef} from "react"
import type {MutableRefObject} from "react"
import {useFrame} from "@react-three/fiber"
import {Color,CylinderGeometry,DynamicDrawUsage,InstancedMesh,MeshStandardMaterial,Object3D,Quaternion,SphereGeometry,Vector3} from "three"

const turn=Math.PI*2,segments=14,trailSeconds=.75
const hash=(n:number)=>{const v=Math.sin(n*127.1+311.7)*43758.5453123;return v-Math.floor(v)}
const smooth=(v:number)=>{const t=Math.min(1,Math.max(0,v));return t*t*(3-2*t)}
function helix(id:number,time:number,count:number,out:Vector3){
 const pair=Math.floor(id*.5),side=id%2===0?1:-1
 const pairs=Math.max(1,Math.ceil(count*.5))
 const phase=time*.095+pair/pairs,major=phase*turn*3,minor=major*3
 const radius=.72+.065*Math.sin(minor)
 return out.set(side*Math.cos(major)*radius,((phase%1+1)%1-.5)*2.65+.035*Math.cos(minor),side*Math.sin(major)*radius)
}

/** Three bounded instanced draws. Stock PBR, no point sprites or injected shaders. */
export function StudioParticles({time,count,active}:{time:MutableRefObject<number>;count:number;active:boolean}){
 const heads=useRef<InstancedMesh>(null),trails=useRef<InstancedMesh>(null),burst=useRef<InstancedMesh>(null)
 const resources=useMemo(()=>({
  head:new SphereGeometry(1,10,8),trail:new CylinderGeometry(1,1,1,5,1,true),
  metal:new MeshStandardMaterial({color:"#9eadae",metalness:1,roughness:.32,dithering:true}),
  warm:new MeshStandardMaterial({color:"#aa8e61",metalness:1,roughness:.36,dithering:true}),
  dummy:new Object3D(),a:new Vector3(),b:new Vector3(),direction:new Vector3(),up:new Vector3(0,1,0),rotation:new Quaternion(),
 }),[])
 useLayoutEffect(()=>{
  for(const mesh of [heads.current,trails.current,burst.current])mesh?.instanceMatrix.setUsage(DynamicDrawUsage)
  for(let i=0;i<count;i++)heads.current?.setColorAt(i,new Color(i%3===0?"#b59b73":"#bac6c7"))
  if(heads.current?.instanceColor)heads.current.instanceColor.needsUpdate=true
 },[count])
 useEffect(()=>()=>{resources.head.dispose();resources.trail.dispose();resources.metal.dispose();resources.warm.dispose()},[resources])
 useFrame(()=>{
  if(!heads.current||!trails.current||!burst.current)return
  const {dummy,a,b,direction,up,rotation}=resources
  const t=time.current,clock=Math.max(0,t-2),epoch=Math.floor(clock/4.8),age=clock%4.8
  const chosen=active&&t>2?Math.floor(hash(epoch+903)*count):-1
  for(let id=0;id<count;id++){
   const visibility=id===chosen?smooth((age-3)/.75):1
   helix(id,t,count,a)
   dummy.position.copy(a)
   dummy.rotation.set(t*(.3+hash(id)*.6),t*(.4+hash(id+9)),id)
   dummy.scale.setScalar(.018*visibility);dummy.scale.y*=1.6;dummy.updateMatrix()
   heads.current.setMatrixAt(id,dummy.matrix)
   const span=trailSeconds*(.45+.55*hash(id+301))
   for(let k=0;k<segments;k++){
    const lag=k/segments*span,next=(k+1)/segments*span
    helix(id,t-lag,count,a);helix(id,t-next,count,b)
    const sameCycle=Math.floor((t-lag)*.095+Math.floor(id*.5)/Math.ceil(count*.5))===Math.floor((t-next)*.095+Math.floor(id*.5)/Math.ceil(count*.5))
    direction.subVectors(b,a)
    const length=direction.length()
    dummy.position.copy(a).add(b).multiplyScalar(.5)
    if(length>.000001)rotation.setFromUnitVectors(up,direction.multiplyScalar(1/length))
    dummy.quaternion.copy(rotation)
    const width=.0035*Math.pow(1-(k+.5)/segments,.7)*visibility
    dummy.scale.set(width,sameCycle?length:0,width);dummy.updateMatrix()
    trails.current.setMatrixAt(id*segments+k,dummy.matrix)
   }
  }
  const exploding=chosen>=0&&age<.6
  burst.current.count=exploding?8:0
  if(exploding){
   helix(chosen,t-age,count,a)
   for(let piece=0;piece<8;piece++){
    const theta=hash(epoch*17+piece)*turn,z=hash(piece+epoch*41+7)*2-1
    const radial=Math.sqrt(Math.max(0,1-z*z))
    direction.set(Math.cos(theta)*radial,z,Math.sin(theta)*radial)
    dummy.position.copy(a).addScaledVector(direction,age*(1.5+hash(piece+8)))
    dummy.rotation.set(age*12+piece,age*9+piece,age*15)
    dummy.scale.setScalar(.012*(1-smooth(age/.6)));dummy.updateMatrix()
    burst.current.setMatrixAt(piece,dummy.matrix)
   }
   burst.current.instanceMatrix.needsUpdate=true
  }
  heads.current.instanceMatrix.needsUpdate=true;trails.current.instanceMatrix.needsUpdate=true
 },-2)
 return <>
  <instancedMesh ref={heads} args={[resources.head,resources.metal,count]} frustumCulled={false} dispose={null}/>
  <instancedMesh ref={trails} args={[resources.trail,resources.warm,count*segments]} frustumCulled={false} dispose={null}/>
  <instancedMesh ref={burst} args={[resources.head,resources.warm,8]} frustumCulled={false} dispose={null}/>
 </>
}
