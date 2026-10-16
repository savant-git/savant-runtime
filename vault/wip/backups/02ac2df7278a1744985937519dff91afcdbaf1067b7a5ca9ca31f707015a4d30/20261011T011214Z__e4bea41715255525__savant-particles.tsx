import React, { useEffect, useLayoutEffect, useMemo, useRef } from "react"
import { useFrame, useThree } from "@react-three/fiber"
import { AdditiveBlending, Color, InstancedMesh, Matrix4, MeshPhysicalMaterial, InstancedBufferAttribute } from "three"
import { applyAppearance } from "./savant-surfaces"
import type { MaterialPreset } from "./savant-surfaces"
import { motion, trajectoryGLSL } from "./savant-motion"
import { PhysicalTrails } from "./savant-trails"
import { particleGeometry } from "./savant-particle-geometry"

const countFor=(mode:"header"|"preloader")=>mode==="header"?motion.headerParticles:motion.preloaderParticles
const samples=0 // Trails are now physical tubes; points contain bursts and glints only.
export function CinematicParticles({mode,time,preset,reflection=false,moving,angle,pitch}:{
 mode:"header"|"preloader";time:React.MutableRefObject<number>;preset:MaterialPreset
 reflection?:boolean;moving:boolean;angle:React.MutableRefObject<number>;pitch:number|React.MutableRefObject<{pitch:number}>
}) {
 const count=countFor(mode)
 const heads=useRef<InstancedMesh>(null)
 const {gl,size}=useThree()
 const geometry=useMemo(()=>{
  const g=particleGeometry(preset.shape)
  g.setAttribute("aEmitter",new InstancedBufferAttribute(Float32Array.from({length:count},(_,i)=>i),1))
  return g
 },[preset.shape,count])
 useEffect(()=>()=>geometry.dispose(),[geometry])
 const uniforms=useMemo(()=>({
  uEmitterCount:{value:count},uTime:{value:0},uYaw:{value:0},uPitch:{value:0},uMoving:{value:1},
  uEffect:{value:0},uRatio:{value:1},uHeadScale:{value:.038},uStretch:{value:1},uViewport:{value:128},uColor:{value:new Color()},
  uAccent:{value:new Color()},
 }),[])
 const data=useMemo(()=>{
  const total=count*(samples+9)
  const positions=new Float32Array(total*3), ids=new Float32Array(total),
   lag=new Float32Array(total), kind=new Float32Array(total), piece=new Float32Array(total)
  let at=0
  for(let id=0;id<count;id++){
   for(let j=0;j<samples;j++,at++){ids[at]=id;lag[at]=j/(samples-1)*motion.trailSeconds;}
   for(let j=0;j<8;j++,at++){ids[at]=id;kind[at]=1;piece[at]=j;}
   ids[at]=id;kind[at]=2;at++
  }
  return {positions,ids,lag,kind,piece,headIds:Float32Array.from({length:count},(_,i)=>i)}
 },[count])
 const material=useMemo(()=>{
  const m=new MeshPhysicalMaterial({metalness:1,roughness:.15,clearcoat:1,
   clearcoatRoughness:.03,envMapIntensity:1.8})
  m.onBeforeCompile=shader=>{
   Object.assign(shader.uniforms,uniforms)
   shader.vertexShader=shader.vertexShader.replace("#include <common>",
    "#include <common>\n"+trajectoryGLSL+"\nattribute float aEmitter; varying vec3 vParticleLocal; varying float vParticleGleam;")
    .replace("#include <beginnormal_vertex>",`#include <beginnormal_vertex>
     objectNormal=particleSpin(aEmitter)*normalize(objectNormal/vec3(1.0,uStretch,1.0));`)
    .replace("#include <begin_vertex>",`#include <begin_vertex>
     vParticleLocal=position;vParticleGleam=gleam(aEmitter);
     vec3 state=life(aEmitter);
     float visibility=smoothstep(0.0,.1,fract(travelAt(aEmitter,uTime)))*
      (1.0-smoothstep(.9,1.0,fract(travelAt(aEmitter,uTime))));
     float scale=uHeadScale*state.y*visibility*(1.0+gleam(aEmitter)*.3);
     transformed*=scale;
     transformed.y*=uStretch;
     if(abs(uEffect-5.0)<.5||abs(uEffect-17.0)<.5)
      transformed.x+=sin(position.y*5.0+uTime*6.0+aEmitter)*scale*.2*(position.y+1.0);
     transformed=particleSpin(aEmitter)*transformed;
     transformed+=helix(aEmitter,uTime,0.0);`)
   shader.fragmentShader=shader.fragmentShader.replace("#include <common>",
    "#include <common>\nuniform float uEffect,uTime; varying vec3 vParticleLocal; varying float vParticleGleam;")
    .replace("#include <emissivemap_fragment>",`#include <emissivemap_fragment>
     totalEmissiveRadiance+=vec3(1.0,.92,.76)*vParticleGleam*2.0;
     `)
  }
  m.customProgramCacheKey=()=>"savant-kinetic-heads-v3"
  return m
 },[uniforms])
 useEffect(()=>()=>material.dispose(),[material])
 useLayoutEffect(()=>{
  if(!heads.current)return
  const identity=new Matrix4(),color=new Color()
  for(let i=0;i<count;i++){
   heads.current.setMatrixAt(i,identity)
   color.set("#ffffff") // Base PBR color owns tint; avoid multiplying it twice.
   heads.current.setColorAt(i,color)
  }
  heads.current.instanceMatrix.needsUpdate=true
  if(heads.current.instanceColor)heads.current.instanceColor.needsUpdate=true
  applyAppearance(material,preset,true)
 },[count,preset,material])
 useFrame(()=>{
  uniforms.uTime.value=time.current;uniforms.uYaw.value=angle.current
  uniforms.uPitch.value=typeof pitch==="number"?pitch:pitch.current.pitch;uniforms.uMoving.value=moving?1:0
  uniforms.uEffect.value=preset.effect
  uniforms.uHeadScale.value=preset.particleScale;uniforms.uStretch.value=preset.particleStretch
  uniforms.uRatio.value=reflection?1:gl.getPixelRatio()
  uniforms.uViewport.value=reflection?(mode==="header"?256:512):size.height
  uniforms.uColor.value.set(preset.particle);uniforms.uAccent.value.set(preset.accent)
 },-2)
 return <>
  <PhysicalTrails count={count} preset={preset} uniforms={uniforms}/>
  {reflection&&<><ambientLight intensity={1}/><directionalLight position={[-3,4,4]} intensity={3}/></>}
  <instancedMesh ref={heads} args={[undefined,undefined,count]} frustumCulled={false}>
   <primitive object={geometry} attach="geometry" dispose={null}/>
   <primitive object={material} attach="material" dispose={null}/>
  </instancedMesh>
  <points frustumCulled={false} renderOrder={3}>
   <bufferGeometry>
    <bufferAttribute attach="attributes-position" args={[data.positions,3]}/>
    <bufferAttribute attach="attributes-aEmitter" args={[data.ids,1]}/>
    <bufferAttribute attach="attributes-aLag" args={[data.lag,1]}/>
    <bufferAttribute attach="attributes-aKind" args={[data.kind,1]}/>
    <bufferAttribute attach="attributes-aPiece" args={[data.piece,1]}/>
   </bufferGeometry>
   <shaderMaterial uniforms={uniforms} transparent depthWrite={false}
    blending={AdditiveBlending} toneMapped={false}
    vertexShader={trajectoryGLSL+`
     attribute float aEmitter,aLag,aKind,aPiece;
     varying float vAlpha,vEffect; varying vec3 vColor;
     void main(){
      vec3 state=life(aEmitter);
      vec3 p=helix(aEmitter,uTime-aLag,aLag);
      float travel=fract(travelAt(aEmitter,uTime));
      float epoch=floor(uTime/3.0);
      float before=smoothstep(.15,.65,phash(aEmitter*31.0+epoch-1.0));
      float after=smoothstep(.15,.65,phash(aEmitter*31.0+epoch));
      float tailWindow=mix(before,after,smoothstep(0.0,.2,fract(uTime/3.0)));
      float alpha=step(aLag,uTime)*pow(1.0-aLag/${(motion.trailSeconds+.1).toFixed(4)},1.2)*state.y*
       (1.0-step(.5,abs(floor(travelAt(aEmitter,uTime))-floor(travelAt(aEmitter,uTime-aLag)))))*tailWindow*uMoving;
      float size=3.0+mod(uEffect,4.0)*.75;
      if(aKind>.5&&aKind<1.5){
       float age=state.x;
       float alive=step(0.0,age)*(1.0-step(.75,age))*uMoving*state.z;
       float az=phash(aEmitter*19.0+aPiece)*6.2831853;
       float z=phash(aEmitter*71.0+aPiece+13.0)*2.0-1.0;
       float r=sqrt(max(0.0,1.0-z*z));
       float burstAge=max(age,0.0);
       float swirl=burstAge*(13.0+mod(uEffect,5.0)*1.9);
       float ca=cos(az+swirl),sa=sin(az+swirl);
       vec3 radial=vec3(ca*r,sa*r,z);
       vec3 tangent=vec3(-sa*r,ca*r,0.0);
       float expansion=burstAge*(2.4+mod(uEffect,4.0)*.38);
       float helixRadius=.16+.19*sin(min(burstAge/.5,1.0)*3.14159265);
       p=helix(aEmitter,uTime-burstAge,0.0)+
        radial*expansion+tangent*helixRadius*sin(swirl*1.6+aPiece);
       alpha=alive*pow(1.0-clamp(burstAge/.75,0.0,1.0),1.35);
       size=1.6+mod(uEffect,5.0)*.22;
      }
      if(aKind>1.5){
       p=helix(aEmitter,uTime,0.0);
       float burstAge=state.x;
       float flash=step(0.0,burstAge)*(1.0-smoothstep(0.0,.18,burstAge))*uMoving*state.z;
       alpha=gleam(aEmitter)*state.y+flash;
       size=3.0+flash*(12.0+mod(uEffect,6.0)*2.0);
      }
      if(aKind<.5)alpha*=smoothstep(0.0,.08,travel)*(1.0-smoothstep(.94,1.0,travel));
      vAlpha=alpha;vEffect=uEffect;
      vColor=mix(uColor,uAccent,step(.66,phash(aEmitter+17.0)));
      gl_Position=projectionMatrix*modelViewMatrix*vec4(p,1.0);
      float distanceScale=clamp(uViewport/(max(gl_Position.w,.1)*75.0),.65,2.5);
      gl_PointSize=clamp(uRatio*size*distanceScale,1.0,32.0);
     }`}
    fragmentShader={`
     varying float vAlpha,vEffect;varying vec3 vColor;
     void main(){
      vec2 p=(gl_PointCoord-.5)*2.0;float r=length(p);
      float angle=atan(p.y,p.x),s=vEffect,shape=0.0;
      float fw=max(fwidth(r),.025);
      float disc=1.0-smoothstep(.65-fw,.65+fw,r);
      float ring=1.0-smoothstep(.045,.045+fw,abs(r-.58));
      if(s<.5)shape=ring*(.45+.55*pow(max(0.0,cos(angle*3.0)),2.0));
      else if(s<1.5)shape=max(ring*.55,
       (1.0-smoothstep(.08,.08+fw,min(abs(p.x),abs(p.y))))*(1.0-smoothstep(.7,.95,r));
      else if(s<2.5)shape=pow(max(0.0,1.0-abs(p.x)-abs(p.y)),2.0);
      else if(s<3.5)shape=pow(max(0.0,1.0-abs(p.x)*1.7-abs(p.y)*.7),2.0);
      else if(s<4.5)shape=exp(-r*r*5.0)*(.65+.35*cos(angle*3.0+r*5.0));
      else if(s<5.5)shape=exp(-p.x*p.x*5.0-p.y*p.y*2.0)*(1.0-smoothstep(.4,1.0,p.y));
      else if(s<6.5)shape=pow(max(0.0,1.0-abs(p.x)*3.0-abs(p.y)),2.0);
      else if(s<7.5)shape=pow(max(0.0,cos(angle*6.0)),8.0)*(1.0-smoothstep(.4,.9,r));
      else if(s<8.5)shape=max(exp(-r*r*10.0),exp(-abs(p.x*p.y)*80.0)*max(0.0,1.0-r));
      else if(s<9.5)shape=exp(-pow(r-.4-.06*sin(angle*3.0),2.0)*90.0);
      else if(s<10.5)shape=disc*exp(-p.y*p.y*2.0);
      else if(s<11.5)shape=ring*(.2+.8*pow(max(0.0,cos(angle-2.0)),4.0));
      else if(s<12.5)shape=1.0-smoothstep(.45,.45+fw,max(abs(p.x),abs(p.y)));
      else if(s<13.5)shape=exp(-r*r*5.0)*(.6+.4*cos(angle*5.0));
      else if(s<14.5)shape=exp(-p.x*p.x*22.0-p.y*p.y*2.0);
      else if(s<15.5)shape=exp(-pow(p.x-.2*sin(p.y*5.0),2.0)*45.0-p.y*p.y*2.0);
      else if(s<16.5)shape=1.0-smoothstep(.65,.65+fw,abs(p.x)+abs(p.y));
      else if(s<17.5)shape=exp(-r*r*3.0)*(.7+.3*sin(angle*2.0+r*4.0));
      else if(s<18.5)shape=exp(-p.x*p.x*30.0-p.y*p.y*4.0);
      else shape=exp(-pow(p.x+.3*sin(p.y*4.0),2.0)*30.0-p.y*p.y*2.0)*.55;
      float alpha=clamp(shape*vAlpha,0.0,1.0);
      if(alpha<.01)discard;
      gl_FragColor=vec4(vColor*(1.0+vAlpha*.7),alpha);
      #include <colorspace_fragment>
     `}/>
  </points>
 </>
}
