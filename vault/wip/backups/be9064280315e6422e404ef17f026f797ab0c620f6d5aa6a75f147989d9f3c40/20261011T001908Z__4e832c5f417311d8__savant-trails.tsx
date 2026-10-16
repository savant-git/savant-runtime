import React,{useEffect,useLayoutEffect,useMemo,useRef} from "react"
import {InstancedBufferAttribute,InstancedMesh,Matrix4,CylinderGeometry,MeshPhysicalMaterial} from "three"
import type {IUniform} from "three"
import {applyAppearance} from "./savant-surfaces"
import type {MaterialPreset} from "./savant-surfaces"
import {motion,trajectoryGLSL} from "./savant-motion"

/* One instanced draw: connected, lit tubes rather than dotted billboard tails.
 * Fixed geometry and analytic motion avoid rebuilding buffers every frame. */
export function PhysicalTrails({count,preset,uniforms}:{
 count:number;preset:MaterialPreset;uniforms:Record<string,IUniform>
}){
 const mesh=useRef<InstancedMesh>(null)
 const geometry=useMemo(()=>{
  const g=new CylinderGeometry(1,1,1,8,96,true)
  g.setAttribute("aEmitter",new InstancedBufferAttribute(Float32Array.from({length:count},(_,i)=>i),1))
  return g
 },[count])
 const material=useMemo(()=>{
  const m=new MeshPhysicalMaterial()
  m.onBeforeCompile=shader=>{
   Object.assign(shader.uniforms,uniforms)
   shader.vertexShader=shader.vertexShader.replace("#include <common>","#include <common>\n"+trajectoryGLSL+`
    attribute float aEmitter;varying float vTrailAlpha;
    vec3 trailPoint(float id,float lag){
     float sampleTime=max(0.0,uTime-lag);
     vec3 p=helix(id,sampleTime,lag);
     // Unwrap height across a reset; never connect bottom to top through the logo.
     float cycleDelta=floor(travelAt(id,sampleTime))-floor(travelAt(id,uTime));
     return p+axisRotate(vec3(0.0,cycleDelta*${motion.height.toFixed(8)},0.0));
    }
    mat3 trailFrame(float id,float lag){
     vec3 t=normalize(trailPoint(id,lag+.012)-trailPoint(id,max(0.0,lag-.012))+vec3(0.0,.000001,0.0));
     vec3 ref=abs(t.y)<.92?vec3(0,1,0):vec3(1,0,0);
     vec3 n=normalize(cross(t,ref)),b=cross(t,n);
     return mat3(n,t,b);
    }`)
    .replace("#include <beginnormal_vertex>",`#include <beginnormal_vertex>
     float trailLag=(1.0-uv.y)*${motion.trailSeconds.toFixed(8)};
     mat3 frame=trailFrame(aEmitter,trailLag);
     objectNormal=frame*objectNormal;`)
    .replace("#include <begin_vertex>",`#include <begin_vertex>
     float ageFraction=trailLag/${motion.trailSeconds.toFixed(8)};
     float width=(.005+mod(uEffect,4.0)*.001)*pow(1.0-ageFraction,.65);
     transformed=trailPoint(aEmitter,trailLag)+frame*vec3(position.x*width,0.0,position.z*width);
     float sameCycle=1.0-step(.5,abs(floor(travelAt(aEmitter,uTime))-floor(travelAt(aEmitter,max(0.0,uTime-trailLag)))));
     float wake=.55+.45*sin(uTime*.9+aEmitter*2.3);
     vTrailAlpha=pow(1.0-ageFraction,1.25)*life(aEmitter).y*sameCycle*
      smoothstep(trailLag,trailLag+.15,uTime)*wake*uMoving;`)
   shader.fragmentShader=shader.fragmentShader.replace("#include <common>",
    "#include <common>\nvarying float vTrailAlpha;")
    .replace("#include <color_fragment>",`#include <color_fragment>
     diffuseColor.a*=vTrailAlpha;
     if(diffuseColor.a<.018)discard;`)
  }
  m.customProgramCacheKey=()=>"savant-physical-corkscrew-028"
  return m
 },[uniforms])
 useLayoutEffect(()=>{
  const identity=new Matrix4()
  for(let i=0;i<count;i++)mesh.current?.setMatrixAt(i,identity)
  if(mesh.current)mesh.current.instanceMatrix.needsUpdate=true
  applyAppearance(material,preset,true)
  // Thin trails use the matching reflective coat, avoiding a second transmission pass.
  material.transmission=0;material.dispersion=0;material.transparent=true
  material.depthWrite=false;material.opacity=.88
  material.emissive.set(preset.accent);material.emissiveIntensity=.12
  material.needsUpdate=true
 },[count,preset,material])
 useEffect(()=>()=>geometry.dispose(),[geometry])
 useEffect(()=>()=>material.dispose(),[material])
 return <instancedMesh ref={mesh} args={[undefined,undefined,count]} frustumCulled={false}>
  <primitive object={geometry} attach="geometry" dispose={null}/>
  <primitive object={material} attach="material" dispose={null}/>
 </instancedMesh>
}
