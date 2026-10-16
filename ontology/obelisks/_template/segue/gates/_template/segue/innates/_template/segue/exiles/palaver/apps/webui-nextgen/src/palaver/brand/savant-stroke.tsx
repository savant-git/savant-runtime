import React,{useEffect,useLayoutEffect,useMemo,useRef} from "react"
import {useFrame} from "@react-three/fiber"
import {BufferGeometry,Color,CylinderGeometry,InstancedBufferAttribute,InstancedMesh,Matrix4,MeshPhysicalMaterial,Quaternion,Vector3} from "three"
import type {MaterialPreset} from "./savant-surfaces"

/* A separate physical border, with arc-length illumination on each closed loop.
 * This intentionally remains a solid frame during local surface fragmentation. */
export function IlluminatedStroke({geometry,time,preset}:{
 geometry:BufferGeometry;time:React.MutableRefObject<number>;preset:MaterialPreset
}){
 const mesh=useRef<InstancedMesh>(null)
 const segments=useMemo(()=>{
  const p=geometry.attributes.position,path=geometry.attributes.path
  return Array.from({length:p.count/2},(_,i)=>({
   a:new Vector3().fromBufferAttribute(p,i*2),b:new Vector3().fromBufferAttribute(p,i*2+1),
   start:path.getX(i*2),end:path.getX(i*2+1)
  }))
 },[geometry])
 const tube=useMemo(()=>{
  const g=new CylinderGeometry(1,1,1,10,1,true)
  g.setAttribute("aArc",new InstancedBufferAttribute(
   Float32Array.from(segments.flatMap(e=>[e.start,e.end])),2))
  return g
 },[segments])
 const uniforms=useMemo(()=>({uTime:{value:0},uSpeed:{value:.7},
  uLight:{value:new Color()},uPower:{value:2}}),[])
 const material=useMemo(()=>{
  const m=new MeshPhysicalMaterial({clearcoat:1,clearcoatRoughness:.025})
  m.onBeforeCompile=shader=>{
   Object.assign(shader.uniforms,uniforms)
   shader.vertexShader=shader.vertexShader
    .replace("#include <common>","#include <common>\nattribute vec2 aArc; varying float vArc; varying vec2 vTube;")
    .replace("#include <begin_vertex>","#include <begin_vertex>\nvArc=mix(aArc.x,aArc.y,uv.y);vTube=uv;")
   shader.fragmentShader=shader.fragmentShader
    .replace("#include <common>","#include <common>\nuniform float uTime,uSpeed,uPower;uniform vec3 uLight;varying float vArc;varying vec2 vTube;")
    .replace("#include <emissivemap_fragment>",`#include <emissivemap_fragment>
     float phase=fract(vArc-uTime*uSpeed);
     float d=min(phase,1.0-phase);
     float pulse=exp(-d*d*1600.0)+pow(1.0-phase,18.0)*.35;
     float core=.25+.75*pow(abs(cos(vTube.x*6.2831853)),6.0);
     totalEmissiveRadiance+=uLight*uPower*(.035+pulse*core);`)
  }
  m.customProgramCacheKey=()=>"savant-physical-stroke-027"
  return m
 },[uniforms])
 useLayoutEffect(()=>{
  const matrix=new Matrix4(),rotation=new Quaternion(),up=new Vector3(0,1,0)
  segments.forEach((e,i)=>{
   const direction=e.b.clone().sub(e.a),length=direction.length()
   rotation.setFromUnitVectors(up,direction.normalize())
   matrix.compose(e.a.clone().add(e.b).multiplyScalar(.5),rotation,
    new Vector3(preset.stroke.width,length+.003,preset.stroke.width))
   mesh.current?.setMatrixAt(i,matrix)
  })
  if(mesh.current)mesh.current.instanceMatrix.needsUpdate=true
  material.color.set(preset.stroke.color);material.metalness=preset.stroke.metalness
  material.roughness=preset.stroke.roughness;material.envMapIntensity=preset.scene.energy
  uniforms.uLight.value.set(preset.stroke.light);uniforms.uSpeed.value=preset.stroke.speed
  uniforms.uPower.value=preset.stroke.power
 },[segments,preset,material,uniforms])
 useFrame(()=>{uniforms.uTime.value=time.current},-2)
 useEffect(()=>()=>tube.dispose(),[tube])
 useEffect(()=>()=>material.dispose(),[material])
 return <instancedMesh ref={mesh} args={[undefined,undefined,segments.length]}
  castShadow={preset.optics.transmission<.8} receiveShadow frustumCulled={false}>
  <primitive object={tube} attach="geometry" dispose={null}/>
  <primitive object={material} attach="material" dispose={null}/>
 </instancedMesh>
}
