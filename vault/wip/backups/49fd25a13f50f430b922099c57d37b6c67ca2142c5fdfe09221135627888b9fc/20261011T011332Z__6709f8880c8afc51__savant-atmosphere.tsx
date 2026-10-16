import React,{useMemo,useRef} from "react"
import {useFrame} from "@react-three/fiber"
import {Lightformer} from "@react-three/drei"
import {AdditiveBlending,Color,Group} from "three"
import type {MaterialPreset} from "./savant-surfaces"

/* Captured reflection sources use the same appearance registry as the logo. */
export function ReflectionLighting({time,preset}:{time:React.MutableRefObject<number>;preset:MaterialPreset}){
 const group=useRef<Group>(null),p=preset.scene
 useFrame(()=>{
  if(!group.current)return
  const t=time.current*p.drift
  group.current.rotation.set(Math.sin(t*.35)*.12,Math.sin(t*.23)*.28,p.tilt+Math.sin(t*.4)*.06)
  group.current.position.set(Math.sin(t*.25)*.25,Math.cos(t*.19)*.18,0)
 },-2)
 const warm=preset.style===0||preset.style===4||preset.style===17
 const slots=preset.style===1?8:preset.style===5?5:4
 return <group ref={group}>
  <Lightformer form="rect" color={warm?"#fff0cc":"#e8f4ff"} intensity={p.energy*2}
   position={[0,3,4]} scale={[3.5,1.5,1]} target={[0,0,0]}/>
  {Array.from({length:slots},(_,i)=><Lightformer key={i} form="rect"
   color={i%2?preset.accent:preset.accent2} intensity={p.energy*(.65+(i%3)*.3)}
   position={[Math.cos(i*6.283/slots)*4,(i-slots/2)*.6,-2-Math.sin(i)*2]}
   rotation={[0,0,preset.style===1?0:p.tilt+i*.27]}
   scale={[preset.style===1?.12:p.width,preset.style===1?4:p.stretch,1]} target={[0,0,0]}/>)}
 </group>
}
export function AtmosphereGlow({time,preset}:{
 time:React.MutableRefObject<number>;preset:MaterialPreset
}){
 const targets=useMemo(()=>[new Color(preset.accent),new Color(preset.accent2)],[preset.accent,preset.accent2])
 const uniforms=useMemo(()=>({
  uTime:{value:0},uStrength:{value:preset.scene.glow},uColor:{value:new Color(preset.accent)},
  uAccent:{value:new Color(preset.accent2)},
  uEnergy:{value:preset.scene.energy},uDrift:{value:preset.scene.drift},uStyle:{value:preset.style},
 }),[])
 useFrame((_,delta)=>{
  const blend=1-Math.exp(-5*Math.min(delta,.1))
  uniforms.uTime.value=time.current
  uniforms.uEnergy.value+=(preset.scene.energy-uniforms.uEnergy.value)*blend
  uniforms.uDrift.value+=(preset.scene.drift-uniforms.uDrift.value)*blend
  uniforms.uStyle.value=preset.style
  uniforms.uStrength.value+=(preset.scene.glow-uniforms.uStrength.value)*blend
  uniforms.uColor.value.lerp(targets[0],blend)
  uniforms.uAccent.value.lerp(targets[1],blend)
 },-2)
 return <mesh position={[0,.12,-1.9]} renderOrder={-2}>
  <planeGeometry args={[4.6,4.6]}/>
  <shaderMaterial uniforms={uniforms} transparent depthWrite={false}
   blending={AdditiveBlending} toneMapped={false}
   vertexShader={`varying vec2 vUv;
    void main(){vUv=uv;gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.0);}`}
   fragmentShader={`
    uniform float uTime,uStrength,uEnergy,uDrift,uStyle;uniform vec3 uColor,uAccent;varying vec2 vUv;
    void main(){
     vec2 p=(vUv-.5)*2.0;float r=length(p*vec2(1.0,1.12)),t=uTime*uDrift;
     float theta=atan(p.y,p.x);
     float breathe=.72+.18*sin(t*1.5)+.1*sin(t*2.9+.8);
     float ripple=.5+.5*sin(r*22.0-t*2.4+sin(atan(p.y,p.x)*3.0+t*.3)*.4);
     float core=exp(-r*r*5.5)*breathe;
     float halo=exp(-pow(r-.47-.025*sin(t*.8),2.0)*22.0)*ripple*.3;
     float outer=exp(-pow(r-.73-.025*sin(t*.41),2.0)*38.0)*.12;
     float spiral=pow(max(sin(theta*4.0-r*18.0+t*1.4+uStyle*.21),0.0),8.0)*exp(-r*3.5)*.12;
     float diffraction=pow(abs(cos(theta*8.0-t*.19)),32.0)*exp(-r*3.8)*.10;
     float flare=pow(abs(cos(theta-.24*sin(t*.31))),80.0)*exp(-r*3.0)*.14;
     float feather=1.0-smoothstep(.55,.98,r);
     vec3 color=mix(uColor,uAccent,.5+.5*sin(t*.2+r*5.0+uStyle*.618));
     float energy=core+spiral*.3+diffraction*.25+flare*.35;
     gl_FragColor=vec4(color*energy,clamp(energy*feather*uStrength*min(uEnergy,2.5),0.0,.55));
     #include <colorspace_fragment>
    }`}/>
 </mesh>
}
