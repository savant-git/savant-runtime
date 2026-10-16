import React, { useEffect, useLayoutEffect, useMemo, useRef } from "react"
import { useFrame, useThree } from "@react-three/fiber"
import { AdditiveBlending, Color, InstancedMesh, Matrix4, MeshPhysicalMaterial } from "three"
import type { MaterialPreset } from "./savant-surfaces"

const countFor=(mode:"header"|"preloader")=>mode==="header"?14:20
const samples=48
/* One analytic path is shared by visible particles and reflection capture.
 * Tails sample the path's past and add a second rotating corkscrew. */
export const trajectoryGLSL=`
uniform float uTime,uYaw,uPitch,uMoving,uEffect,uRatio;
uniform vec3 uColor,uAccent;
float phash(float n){return fract(sin(n*127.1+311.7)*43758.5453123);}
float riseSpeed(float id){return .07+phash(id+20.0)*.035;}
vec3 life(float id) {
 float period=11.0+phash(id+70.0)*13.0;
 float clock=uTime+phash(id+80.0)*period;
 float cycle=floor(clock/period), age=mod(clock,period);
 bool bursts=phash(id*73.0+cycle+200.0)>.55;
 if(!bursts||uMoving<.5) return vec3(-1.0,1.0,0.0);
 return vec3(age,age<3.0?0.0:smoothstep(3.0,3.65,age),0.0);
}
vec3 axisRotate(vec3 p) {
 float c=cos(uPitch),s=sin(uPitch);
 return vec3(p.x,p.y*c-p.z*s,p.y*s+p.z*c);
}
vec3 helix(float id,float time,float lag) {
 float travel=fract(time*riseSpeed(id)+phash(id+5.0));
 float phase=uYaw+id*2.39996323+time*(.7+phash(id+10.0)*.3);
 float radius=1.02+phash(id+13.0)*.12;
 vec3 p=vec3(cos(phase)*radius,(travel-.5)*2.65,sin(phase)*radius);
 float winding=uTime*6.0+lag*15.0+id;
 float coil=lag*.052;
 p+=vec3(cos(phase)*cos(winding),sin(winding),sin(phase)*cos(winding))*coil;
 return axisRotate(p);
}
float gleam(float id){
 float period=3.0+phash(id+101.0)*5.0;
 return uMoving*max(0.0,1.0-mod(uTime+phash(id+100.0)*5.0,period)/.12);
}
`
export function CinematicParticles({mode,time,preset,reflection=false,moving,angle,pitch}:{
 mode:"header"|"preloader";time:React.MutableRefObject<number>;preset:MaterialPreset
 reflection?:boolean;moving:boolean;angle:React.MutableRefObject<number>;pitch:number
}) {
 const count=countFor(mode)
 const heads=useRef<InstancedMesh>(null)
 const {gl}=useThree()
 const uniforms=useMemo(()=>({
  uTime:{value:0},uYaw:{value:0},uPitch:{value:0},uMoving:{value:1},
  uEffect:{value:0},uRatio:{value:1},uColor:{value:new Color()},
  uAccent:{value:new Color()},
 }),[])
 const data=useMemo(()=>{
  const total=count*(samples+9)
  const positions=new Float32Array(total*3), ids=new Float32Array(total),
   lag=new Float32Array(total), kind=new Float32Array(total), piece=new Float32Array(total)
  let at=0
  for(let id=0;id<count;id++){
   for(let j=0;j<samples;j++,at++){ids[at]=id;lag[at]=j/(samples-1)*2.4;}
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
    "#include <common>\n"+trajectoryGLSL+"\nattribute float aEmitter;")
    .replace("#include <begin_vertex>",`#include <begin_vertex>
     vec3 state=life(aEmitter);
     float visibility=smoothstep(0.0,.1,fract(uTime*riseSpeed(aEmitter)+phash(aEmitter+5.0)))*
      (1.0-smoothstep(.9,1.0,fract(uTime*riseSpeed(aEmitter)+phash(aEmitter+5.0))));
     float scale=.019*state.y*visibility*(1.0+gleam(aEmitter)*.6);
     transformed*=scale;
     transformed.y*=1.0+mod(uEffect,4.0)*.35;
     transformed+=helix(aEmitter,uTime,0.0);`)
  }
  m.customProgramCacheKey=()=>"savant-gpu-heads-v1"
  return m
 },[uniforms])
 useEffect(()=>()=>material.dispose(),[material])
 useLayoutEffect(()=>{
  if(!heads.current)return
  const identity=new Matrix4(),color=new Color()
  for(let i=0;i<count;i++){
   heads.current.setMatrixAt(i,identity)
   color.set(i%3===0?preset.accent:preset.particle)
   heads.current.setColorAt(i,color)
  }
  heads.current.instanceMatrix.needsUpdate=true
  if(heads.current.instanceColor)heads.current.instanceColor.needsUpdate=true
  material.metalness=preset.style===0?1:Math.max(.05,preset.metalness)
  material.roughness=Math.max(.08,preset.roughness*.7)
 },[count,preset,material])
 useFrame(()=>{
  uniforms.uTime.value=time.current;uniforms.uYaw.value=angle.current
  uniforms.uPitch.value=pitch;uniforms.uMoving.value=moving?1:0
  uniforms.uEffect.value=preset.effect
  uniforms.uRatio.value=reflection?1:gl.getPixelRatio()
  uniforms.uColor.value.set(preset.particle);uniforms.uAccent.value.set(preset.accent)
 },-2)
 return <>
  {reflection&&<><ambientLight intensity={1}/><directionalLight position={[-3,4,4]} intensity={3}/></>}
  <instancedMesh ref={heads} args={[undefined,undefined,count]} frustumCulled={false}>
   <icosahedronGeometry args={[1,1]}>
    <instancedBufferAttribute attach="attributes-aEmitter" args={[data.headIds,1]}/>
   </icosahedronGeometry>
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
      float travel=fract(uTime*riseSpeed(aEmitter)+phash(aEmitter+5.0));
      float epoch=floor(uTime/3.0);
      float before=smoothstep(.15,.65,phash(aEmitter*31.0+epoch-1.0));
      float after=smoothstep(.15,.65,phash(aEmitter*31.0+epoch));
      float tailWindow=mix(before,after,smoothstep(0.0,.2,fract(uTime/3.0)));
      float alpha=pow(1.0-aLag/2.5,1.2)*state.y*
       step(aLag*riseSpeed(aEmitter),travel)*tailWindow*uMoving;
      float size=2.2+mod(uEffect,4.0)*.65;
      if(aKind>.5&&aKind<1.5){
       float age=state.x;
       float alive=step(0.0,age)*(1.0-step(.5,age))*uMoving;
       float az=phash(aEmitter*19.0+aPiece)*6.2831853;
       float z=phash(aEmitter*71.0+aPiece+13.0)*2.0-1.0;
       float r=sqrt(max(0.0,1.0-z*z));
       p=helix(aEmitter,uTime-max(age,0.0),0.0)+
        vec3(cos(az)*r,sin(az)*r,z)*max(age,0.0)*3.4;
       alpha=alive*(1.0-clamp(age/.5,0.0,1.0));size=2.0;
      }
      if(aKind>1.5){
       p=helix(aEmitter,uTime,0.0);
       float flash=step(0.0,state.x)*(1.0-smoothstep(0.0,.18,state.x))*uMoving;
       alpha=gleam(aEmitter)*state.y+flash;
       size=3.0+flash*15.0;
      }
      alpha*=smoothstep(0.0,.08,travel)*(1.0-smoothstep(.94,1.0,travel));
      vAlpha=alpha;vEffect=uEffect;
      vColor=mix(uColor,uAccent,step(.66,phash(aEmitter+17.0)));
      gl_Position=projectionMatrix*modelViewMatrix*vec4(p,1.0);
      gl_PointSize=clamp(uRatio*size,1.0,28.0);
     }`}
    fragmentShader={`
     varying float vAlpha,vEffect;varying vec3 vColor;
     void main(){
      vec2 p=(gl_PointCoord-.5)*2.0;float r=length(p);
      float angle=atan(p.y,p.x),s=vEffect,shape=0.0;
      if(s<.5)shape=max(exp(-r*r*8.0),exp(-abs(p.x*p.y)*60.0)*(1.0-r));
      else if(s<1.5)shape=(1.0-smoothstep(.45,.6,max(abs(p.x),abs(p.y))))*.8;
      else if(s<2.5)shape=exp(-r*r*4.0)*( .6+.4*sin(angle*3.0+r*9.0));
      else if(s<3.5)shape=exp(-p.x*p.x*35.0-p.y*p.y*3.0);
      else if(s<4.5)shape=exp(-abs(p.x)*12.0)*step(abs(p.y),.9);
      else if(s<5.5)shape=exp(-pow(r-.4,2.0)*65.0);
      else if(s<6.5)shape=exp(-r*r*5.0)*(.5+.5*cos(angle*6.0));
      else if(s<7.5)shape=step(abs(p.x),.13)*step(abs(p.y),.8)+step(abs(p.y),.13)*step(abs(p.x),.6);
      else if(s<8.5)shape=exp(-r*r*5.0)*step(.1,fract(p.x*5.0+p.y*3.0));
      else if(s<9.5)shape=exp(-pow(r-.25-.1*sin(angle*3.0),2.0)*60.0);
      else if(s<10.5)shape=exp(-abs(p.x)*10.0)*(.5+.5*cos(p.y*16.0))*(1.0-r);
      else if(s<11.5)shape=step(abs(p.x)+abs(p.y),.8);
      else if(s<12.5)shape=pow(max(0.0,1.0-r),2.0)*(.5+.5*cos(angle*5.0));
      else if(s<13.5)shape=exp(-pow(max(abs(p.x),abs(p.y))-.5,2.0)*180.0);
      else if(s<14.5)shape=exp(-r*r*4.0)*(.5+.5*sin(p.x*18.0)*sin(p.y*14.0));
      else if(s<15.5)shape=exp(-pow(r-.55,2.0)*90.0)*(.6+.4*cos(angle*2.0));
      else if(s<16.5)shape=exp(-p.y*p.y*45.0-p.x*p.x*3.0);
      else if(s<17.5)shape=exp(-pow(r-.45-.05*cos(angle*6.0),2.0)*110.0);
      else if(s<18.5)shape=exp(-r*r*3.0)*step(.35,fract(p.y*6.0));
      else shape=exp(-r*r*6.0)*(.5+.5*cos(angle*8.0+r*10.0));
      float alpha=clamp(shape*vAlpha,0.0,1.0);
      if(alpha<.01)discard;
      gl_FragColor=vec4(vColor*(1.0+vAlpha*.7),alpha);
      #include <colorspace_fragment>
     `}/>
  </points>
 </>
}
