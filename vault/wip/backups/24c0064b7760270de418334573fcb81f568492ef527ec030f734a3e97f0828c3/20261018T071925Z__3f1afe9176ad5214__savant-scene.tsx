import {useEffect,useLayoutEffect,useMemo,useRef} from "react"
import {useFrame,useThree} from "@react-three/fiber"
import {useGLTF} from "@react-three/drei"
import {Box3,BufferAttribute,BufferGeometry,Color,Group,MathUtils,Mesh,MeshStandardMaterial,Object3D,PerspectiveCamera,Vector3} from "three"
import type {MarkSceneProps} from "./savant-mark-types"
import {damp} from "./savant-motion"
import {SavantStudio} from "./savant-studio"
import {StudioParticles} from "./savant-studio-particles"
import {SavantTrailerRig} from "./savant-trailer-rig"

const turn=Math.PI*2
function prepareStudioModel(source:Object3D){
 const model=new Group(),clone=source.clone(true),geometries:BufferGeometry[]=[]
 const material=new MeshStandardMaterial({
  name:"savant-studio-copper-titanium",color:"#ffffff",vertexColors:true,
  metalness:.94,roughness:.34,envMapIntensity:.8,dithering:true,flatShading:false,
 })
 const sourceSize=new Box3().setFromObject(source).getSize(new Vector3())
 const unit=Math.max(sourceSize.x,sourceSize.y,sourceSize.z,.0001)
 const titanium=new Color("#9ba8ab"),copper=new Color("#9c826c"),patina=new Color("#718b83"),shade=new Color()
 clone.traverse(object=>{
  if(!(object instanceof Mesh))return
  const geometry=object.geometry.clone(),position=geometry.getAttribute("position")
  if(!position)throw new Error("savant logo has no position attribute")
  if(!geometry.getAttribute("normal"))geometry.computeVertexNormals()
  const colors=new Float32Array(position.count*3)
  for(let i=0;i<position.count;i++){
   const x=position.getX(i)/unit,y=position.getY(i)/unit,z=position.getZ(i)/unit
   const blend=.5+.22*Math.sin(x*5+y*3+z*2)
   shade.copy(titanium).lerp(copper,blend*.6).lerp(patina,.12+.06*Math.sin(y*4-x*3))
   colors[i*3]=shade.r;colors[i*3+1]=shade.g;colors[i*3+2]=shade.b
  }
  geometry.setAttribute("color",new BufferAttribute(colors,3))
  geometry.computeBoundingBox();geometry.computeBoundingSphere()
  object.geometry=geometry;object.material=material
  object.customDepthMaterial=undefined;object.castShadow=false;object.receiveShadow=false
  geometries.push(geometry)
 })
 model.add(clone);model.updateMatrixWorld(true)
 const bounds=new Box3().setFromObject(model)
 if(bounds.isEmpty())throw new Error("savant logo has empty bounds")
 const extent=bounds.getSize(new Vector3()),center=bounds.getCenter(new Vector3())
 const scale=2/Math.max(extent.x,extent.y,extent.z,.0001)
 model.scale.setScalar(scale);model.position.copy(center).multiplyScalar(-scale)
 model.scale.z*=1.6;model.position.z*=1.6;model.updateMatrixWorld(true)
 return {model,material,geometries,bounds:new Box3().setFromObject(model)}
}

/** Stock PBR with a bounded four-type rig, no shadow passes or shader overrides. */
export function MarkScene({mode,active,reducedMotion,interaction,revision,requestFrame,framingScale}:MarkSceneProps){
 const gltf=useGLTF("/cinematic/savant_logo.glb")
 const {gl,scene,camera,size,invalidate,setDpr}=useThree()
 const group=useRef<Group>(null),time=useRef(0),speed=useRef(turn/8),home=useRef(4),perspective=useRef(0)
 const prepared=useMemo(()=>prepareStudioModel(gltf.scene),[gltf.scene])
 useEffect(()=>{requestFrame.current=invalidate;return()=>{requestFrame.current=null}},[requestFrame,invalidate])
 useLayoutEffect(()=>{
  // Retain MSAA and useful pixel density without allocating an enormous preloader.
  const cap=Math.max(1,Math.min(2,window.devicePixelRatio||1,Math.sqrt(700000/Math.max(1,size.width*size.height))))
  setDpr(cap)
 },[size.width,size.height,setDpr])
 useLayoutEffect(()=>{
  if(!(camera instanceof PerspectiveCamera))return
  const extent=prepared.bounds.getSize(new Vector3()),width=Math.hypot(extent.x,extent.z)
  const h=Math.max(size.height-32*framingScale,1),w=Math.max(size.width-50*framingScale,1)
  const visible=Math.max(extent.y,width/Math.max(w/h,.1))*1.1
  home.current=(visible/(2*Math.tan(MathUtils.degToRad(camera.fov/2)))+width/2)*size.height/h
  camera.position.set(0,0,home.current)
  camera.setViewOffset(size.width,size.height,25*framingScale,16*framingScale,size.width,size.height)
  camera.lookAt(0,0,0);camera.updateProjectionMatrix();invalidate()
 },[camera,prepared.bounds,size.width,size.height,framingScale,invalidate])
 useEffect(()=>{invalidate()},[active,reducedMotion,revision,invalidate])
 useEffect(()=>{
  const previous=gl.shadowMap.enabled
  gl.shadowMap.enabled=false
  return()=>{gl.shadowMap.enabled=previous}
 },[gl])
 useEffect(()=>()=>{prepared.material.dispose();prepared.geometries.forEach(geometry=>geometry.dispose())},[prepared])
 useFrame((_,delta)=>{
  if(!group.current)return
  const dt=Math.min(Math.max(delta,0),.1)
  if(active&&!reducedMotion){
   time.current+=dt
   speed.current=damp(speed.current,interaction.current.dragging?0:turn/8,8,dt)
   if(!interaction.current.dragging)interaction.current.yaw+=speed.current*dt
   invalidate()
  }
  if(!interaction.current.dragging){
   interaction.current.pitch=damp(interaction.current.pitch,0,5,dt)
   if(Math.abs(interaction.current.pitch)<.0001)interaction.current.pitch=0
  }
  group.current.rotation.set(interaction.current.pitch,interaction.current.yaw%turn,0)
  // Move a filtered environment, never repaint/re-capture it during animation.
  scene.environmentRotation.set(0,time.current*.12,0)
  if(camera instanceof PerspectiveCamera){
   const local=time.current%14
   const target=active&&!reducedMotion&&!interaction.current.dragging&&local>8&&local<12?Math.sin((local-8)/4*Math.PI)**2:0
   perspective.current=damp(perspective.current,target,5,dt)
   camera.position.set(Math.sin(time.current*.8)*.72*perspective.current,Math.cos(time.current*.6)*.28*perspective.current,home.current*(1-perspective.current*.065))
   camera.lookAt(0,0,0)
  }
  if(active&&Math.abs(interaction.current.pitch)>.0001)invalidate()
 },-3)
 return <>
  <SavantStudio/>
  <SavantTrailerRig time={time} moving={active&&!reducedMotion}/>
  <group ref={group}>
   <primitive object={prepared.model} dispose={null}/>
   <StudioParticles time={time} count={mode==="preloader"?22:14} active={active&&!reducedMotion}/>
  </group>
 </>
}
