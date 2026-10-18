import {useEffect,useLayoutEffect,useMemo,useRef} from "react"
import {useFrame,useThree} from "@react-three/fiber"
import {useGLTF} from "@react-three/drei"
import {Box3,BufferGeometry,Group,MathUtils,Mesh,MeshPhysicalMaterial,Object3D,PerspectiveCamera,Vector3} from "three"
import type {MarkSceneProps} from "./savant-mark-types"
import {damp} from "./savant-motion"
import {SavantStudio} from "./savant-studio"
import {StudioParticles} from "./savant-studio-particles"
import {artDirectionFor} from "./savant-art-direction"
import {artUniforms,installArtSurface,setArtUniforms} from "./savant-art-surface"
import type {ArtUniforms} from "./savant-art-surface"
import {ArtAtmosphere} from "./savant-art-atmosphere"
import {applyLogoAppearance} from "./savant-material-picker"
import {SavantTrailerRig} from "./savant-trailer-rig"
import {SavantGoldContour} from "./savant-gold-contour"
import {advanceRotation,installTitleGlitch,titleGlitch} from "./savant-title-motion"
import type {TitleGlitch} from "./savant-title-motion"

const turn=Math.PI*2
function prepareStudioModel(source:Object3D,glitch:TitleGlitch,art:ArtUniforms){
 const model=new Group(),clone=source.clone(true),geometries:BufferGeometry[]=[]
 const material=new MeshPhysicalMaterial({
  name:"savant-black-chrome-r2",color:"#515963",
  metalness:1,roughness:.19,clearcoat:1,clearcoatRoughness:.13,
  envMapIntensity:1.35,dithering:true,flatShading:false,
 })
 clone.traverse(object=>{
  if(!(object instanceof Mesh))return
  const geometry=object.geometry.clone(),position=geometry.getAttribute("position")
  if(!position)throw new Error("savant logo has no position attribute")
  if(!geometry.getAttribute("normal"))geometry.computeVertexNormals()
  geometry.deleteAttribute("color")
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
 installTitleGlitch(material,glitch,scale,center.y,1.6)
 installArtSurface(material,art,scale,center.y)
 model.name="savant-black-chrome-r2"
 model.scale.setScalar(scale);model.position.copy(center).multiplyScalar(-scale)
 model.scale.z*=1.6;model.position.z*=1.6;model.updateMatrixWorld(true)
 return {model,material,geometries,bounds:new Box3().setFromObject(model)}
}

/** One persistent GLB instance; stock PBR reflections with rare vertex-only distortion. */
export function MarkScene({mode,preset,active,reducedMotion,interaction,revision,requestFrame,framingScale}:MarkSceneProps){
 const gltf=useGLTF("/cinematic/savant_logo.glb")
 const {gl,scene,camera,size,invalidate,setDpr}=useThree()
 const group=useRef<Group>(null),time=useRef(0),speed=useRef(1),home=useRef(4),perspective=useRef(0)
 const glitch=useMemo<TitleGlitch>(()=>({time:{value:0},amount:{value:0}}),[])
 const art=useMemo(()=>artUniforms(),[])
 const profile=useMemo(()=>artDirectionFor(preset),[preset])
 const prepared=useMemo(()=>prepareStudioModel(gltf.scene,glitch,art),[gltf.scene,glitch,art])
 useLayoutEffect(()=>{
  applyLogoAppearance(prepared.material,preset)
  setArtUniforms(art,profile)
  invalidate()
 },[prepared,preset,art,profile,invalidate])
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
   speed.current=interaction.current.dragging?0:damp(speed.current,1,5,dt)
   if(!interaction.current.dragging)interaction.current.yaw=advanceRotation(interaction.current.yaw,dt,speed.current)
   invalidate()
  }
  art.savantArtTime.value=time.current
  art.savantArtStrength.value=reducedMotion?1:damp(art.savantArtStrength.value,1,7,dt)
  glitch.time.value=time.current
  glitch.amount.value=active&&!reducedMotion&&!interaction.current.dragging?titleGlitch(time.current):0
  if(!interaction.current.dragging){
   interaction.current.pitch=damp(interaction.current.pitch,0,5,dt)
   if(Math.abs(interaction.current.pitch)<.0001)interaction.current.pitch=0
  }
  group.current.rotation.set(interaction.current.pitch,interaction.current.yaw%turn,0)
  // Move a filtered environment, never repaint/re-capture it during animation.
  scene.environmentRotation.set(.1*Math.sin(time.current*.41),time.current*profile.drift,.04*Math.sin(time.current*.27))
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
  <SavantStudio profile={profile}/>
  <ArtAtmosphere profile={profile} time={time} moving={active&&!reducedMotion}/>
  <SavantTrailerRig profile={profile} time={time} moving={active&&!reducedMotion}/>
  <group ref={group}>
   <primitive object={prepared.model} dispose={null}/>
   <SavantGoldContour time={time} glitch={glitch} profile={profile}/>
   <StudioParticles profile={profile} time={time} count={mode==="preloader"?22:14} active={active&&!reducedMotion}/>
  </group>
 </>
}
