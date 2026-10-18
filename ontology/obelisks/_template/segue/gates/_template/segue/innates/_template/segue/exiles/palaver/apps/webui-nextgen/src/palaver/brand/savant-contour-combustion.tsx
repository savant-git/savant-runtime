import {useEffect,useLayoutEffect,useMemo,useRef} from "react"
import type {MutableRefObject} from "react"
import {useFrame} from "@react-three/fiber"
import {AdditiveBlending,CatmullRomCurve3,Color,CylinderGeometry,FrontSide,DynamicDrawUsage,InstancedBufferAttribute,InstancedMesh,MeshStandardMaterial,NormalBlending,Object3D,PlaneGeometry,PointLight,ShaderMaterial,Vector3} from "three"
import type {ArtDirection} from "./savant-art-direction"
import type {TitleGlitch} from "./savant-title-motion"
import {warpTitlePoint} from "./savant-title-motion"
import {combustionVertex,flameFragment,smokeFragment} from "./savant-combustion-shaders"
import {contourPhase,emissionHash,sparkAge,sparkPeriod,sparkVelocity,contourEmitterCount,contourFlamesPerEmitter,contourSmokePerEmitter,contourSparksPerEmitter} from "./savant-contour-emission"

const flameCount=contourEmitterCount*contourFlamesPerEmitter
const smokeCount=contourEmitterCount*contourSmokePerEmitter
const sparkCount=contourEmitterCount*contourSparksPerEmitter
function spriteGeometry(count:number){
 const geometry=new PlaneGeometry(1,1)
 const age=new InstancedBufferAttribute(new Float32Array(count),1)
 age.setUsage(DynamicDrawUsage)
 geometry.setAttribute("aAge",age)
 geometry.setAttribute("aSeed",new InstancedBufferAttribute(Float32Array.from({length:count},(_,i)=>emissionHash(i+991)),1))
 return {geometry,age}
}
export function ContourCombustion({curves,time,glitch,profile}:{
 curves:readonly CatmullRomCurve3[];time:MutableRefObject<number>;glitch:TitleGlitch;profile:ArtDirection
}){
 const fire=useRef<InstancedMesh>(null),smoke=useRef<InstancedMesh>(null),sparks=useRef<InstancedMesh>(null)
 const lamps=useRef<(PointLight|null)[]>([])
 const resources=useMemo(()=>{
  const flame=spriteGeometry(flameCount),vapor=spriteGeometry(smokeCount)
  const fireMaterial=new ShaderMaterial({
   vertexShader:combustionVertex,fragmentShader:flameFragment,
   transparent:true,depthWrite:false,depthTest:true,side:FrontSide,blending:AdditiveBlending,
   uniforms:{uTime:{value:0},uGold:{value:new Color("#ffc96d")},uPink:{value:new Color("#ff2f9d")}}
  })
  const smokeMaterial=new ShaderMaterial({
   vertexShader:combustionVertex,fragmentShader:smokeFragment,
   transparent:true,depthWrite:false,depthTest:true,side:FrontSide,blending:NormalBlending,
   uniforms:{uTime:{value:0},uSmoke:{value:new Color("#253139")},uLight:{value:new Color("#8d9a9d")}}
  })
  const sparkMaterial=new MeshStandardMaterial({
   color:"#ffdc9a",metalness:.7,roughness:.25,emissive:"#ff6b17",emissiveIntensity:3.8,dithering:true
  })
  return {flame,vapor,fireMaterial,smokeMaterial,sparkMaterial,
   chip:new CylinderGeometry(1,.35,1,5),dummy:new Object3D(),point:new Vector3(),
   tangent:new Vector3(),direction:new Vector3(),up:new Vector3(0,1,0),
   heatColor:new Color(),lifetimes:Array.from({length:sparkCount},(_,i)=>sparkPeriod(i)),
   velocities:Array.from({length:sparkCount},(_,i)=>sparkVelocity(i))}
 },[])
 useLayoutEffect(()=>{
  fire.current?.instanceMatrix.setUsage(DynamicDrawUsage)
  smoke.current?.instanceMatrix.setUsage(DynamicDrawUsage)
  sparks.current?.instanceMatrix.setUsage(DynamicDrawUsage)
  for(let i=0;i<sparkCount;i++)sparks.current?.setColorAt(i,resources.heatColor.setRGB(1,1,1))
  sparks.current?.instanceColor?.setUsage(DynamicDrawUsage)
  resources.fireMaterial.uniforms.uGold.value.set("#ffc96d").lerp(new Color(profile.accent),.12)
  resources.smokeMaterial.uniforms.uSmoke.value.set("#253139").lerp(new Color(profile.ink),.35)
  resources.smokeMaterial.uniforms.uLight.value.set("#a3a9a5").lerp(new Color(profile.secondary),.18)
 },[resources,profile])
 useEffect(()=>()=>{resources.flame.geometry.dispose();resources.vapor.geometry.dispose();resources.chip.dispose()
  resources.fireMaterial.dispose();resources.smokeMaterial.dispose();resources.sparkMaterial.dispose()},[resources])
 useFrame(()=>{
  if(!fire.current||!smoke.current||!sparks.current||curves.length<2)return
  const t=time.current,{dummy,point,tangent,direction,up}=resources
  resources.fireMaterial.uniforms.uTime.value=t
  resources.smokeMaterial.uniforms.uTime.value=t
  for(let emitter=0;emitter<contourEmitterCount;emitter++){
   const side=Math.floor(emitter/2),tracer=emitter%2,sign=side===0?1:-1,curve=curves[side]
   for(let j=0;j<contourFlamesPerEmitter;j++){
    const i=emitter*contourFlamesPerEmitter+j,age=j/(contourFlamesPerEmitter-1),lag=age*.94
    curve.getPointAt(contourPhase(side,tracer,t-lag,profile.speed),point)
    const warp=warpTitlePoint(point.x,point.y,point.z,t,glitch.amount.value)
    dummy.position.set(warp[0]+Math.sin(age*11-t*2+emitter)*.014*age,
     warp[1]+age*.09,warp[2]+sign*(.019+age*.045))
    const flicker=.88+.12*Math.sin(t*7.1+i*1.9)
    dummy.scale.set((.056+age*.025)*flicker,(.10+age*.09)*flicker,1)
    dummy.rotation.set(0,0,0);dummy.updateMatrix();fire.current.setMatrixAt(i,dummy.matrix)
    resources.flame.age.setX(i,age)
   }
   for(let j=0;j<contourSmokePerEmitter;j++){
    const i=emitter*contourSmokePerEmitter+j,age=(j+.5)/contourSmokePerEmitter
    const lag=.38+age*1.25
    curve.getPointAt(contourPhase(side,tracer,t-lag,profile.speed),point)
    const warp=warpTitlePoint(point.x,point.y,point.z,t,glitch.amount.value)
    dummy.position.set(warp[0]+Math.sin(age*8-t*.8+emitter)*.075*age,
     warp[1]+.08+age*.22,warp[2]+sign*(.035+age*.10))
    dummy.scale.set(.10+age*.20,.12+age*.24,1);dummy.updateMatrix()
    smoke.current.setMatrixAt(i,dummy.matrix);resources.vapor.age.setX(i,age)
   }
   for(let j=0;j<contourSparksPerEmitter;j++){
    const i=emitter*contourSparksPerEmitter+j,age=sparkAge(i,t),v=resources.velocities[i]
    const phase=contourPhase(side,tracer,t-age,profile.speed)
    curve.getPointAt(phase,point);curve.getTangentAt(phase,tangent)
    const warp=warpTitlePoint(point.x,point.y,point.z,t,glitch.amount.value)
    dummy.position.set(warp[0]+(v.x+tangent.x*.15)*age,
     warp[1]+(v.y+tangent.y*.15)*age-.65*age*age,
     warp[2]+sign*(.025+v.z*age))
    direction.set(v.x+tangent.x*.15,v.y+tangent.y*.15-1.3*age,sign*v.z).normalize()
    dummy.quaternion.setFromUnitVectors(up,direction)
    const fade=Math.max(0,1-age/resources.lifetimes[i])*Math.min(1,age/.018)
    dummy.scale.set(.0045*fade,(.018+age*.03)*fade,.0045*fade)
    dummy.updateMatrix();sparks.current.setMatrixAt(i,dummy.matrix)
    resources.heatColor.setRGB(1,.12+.76*fade,.025+.42*fade)
    sparks.current.setColorAt(i,resources.heatColor)
   }
  }
  for(let i=0;i<lamps.current.length;i++){
   const lamp=lamps.current[i];if(!lamp)continue
   const side=i,curve=curves[side]
   curve.getPointAt(contourPhase(side,0,t,profile.speed),point)
   const warp=warpTitlePoint(point.x,point.y,point.z,t,glitch.amount.value)
   lamp.position.set(warp[0],warp[1],warp[2]+(side===0?.08:-.08))
   lamp.intensity=(.75+.18*Math.sin(t*6.1+i*2))*profile.energy
  }
  fire.current.instanceMatrix.needsUpdate=true;smoke.current.instanceMatrix.needsUpdate=true
  sparks.current.instanceMatrix.needsUpdate=true
  if(sparks.current.instanceColor)sparks.current.instanceColor.needsUpdate=true
  resources.flame.age.needsUpdate=true;resources.vapor.age.needsUpdate=true
 },-1)
 return <group name="savant-contour-combustion-v1">
  <instancedMesh ref={smoke} args={[resources.vapor.geometry,resources.smokeMaterial,smokeCount]} frustumCulled={false} renderOrder={1} dispose={null}/>
  <instancedMesh ref={fire} args={[resources.flame.geometry,resources.fireMaterial,flameCount]} frustumCulled={false} renderOrder={2} dispose={null}/>
  <instancedMesh ref={sparks} args={[resources.chip,resources.sparkMaterial,sparkCount]} frustumCulled={false} dispose={null}/>
  {[0,1].map(i=><pointLight key={i} ref={node=>{lamps.current[i]=node}} color="#ffb65a" intensity={0} distance={1.8} decay={2} castShadow={false}/>)}
 </group>
}
