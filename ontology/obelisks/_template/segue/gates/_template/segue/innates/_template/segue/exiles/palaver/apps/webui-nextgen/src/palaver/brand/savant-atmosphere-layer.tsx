import React,{useMemo} from "react"
import {useFrame} from "@react-three/fiber"
import {AdditiveBlending,Color} from "three"
import type {MaterialPreset} from "./savant-surfaces"
export function ArtistAtmosphere({time,preset,moving}: {
 time:React.MutableRefObject<number>;preset:MaterialPreset;moving:boolean
}) {
 const uniforms=useMemo(()=>({
  uTime:{value:0},uStyle:{value:0},uEnergy:{value:1},
  uColor:{value:new Color()},uSecond:{value:new Color()},
 }),[])
 useFrame(()=>{
  uniforms.uTime.value=moving?time.current:0
  uniforms.uStyle.value=preset.style
  uniforms.uEnergy.value=preset.scene.energy
  uniforms.uColor.value.set(preset.accent)
  uniforms.uSecond.value.set(preset.accent2)
 },-2)
 return <mesh position={[0,0,-2.7]} renderOrder={-3} frustumCulled={false}>
  <planeGeometry args={[9,9]}/>
  <shaderMaterial uniforms={uniforms} transparent depthWrite={false} depthTest={false}
   blending={AdditiveBlending} toneMapped={false}
   vertexShader={`varying vec2 vUv;void main(){vUv=uv;gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.0);}`}
   fragmentShader={`
    varying vec2 vUv;
    uniform float uTime,uStyle,uEnergy;
    uniform vec3 uColor,uSecond;
    float hash(vec2 p){return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453);}
    float noise(vec2 p){vec2 i=floor(p),f=fract(p);f=f*f*(3.0-2.0*f);
     return mix(mix(hash(i),hash(i+vec2(1.,0.)),f.x),mix(hash(i+vec2(0.,1.)),hash(i+1.),f.x),f.y);}
    void main(){
     vec2 p=(vUv-.5)*2.;float t=uTime;
     float style=uStyle;
     float scale=1.4+mod(style,5.)*.68;
     float a=style*.61803398875;
     mat2 rotation=mat2(cos(a),-sin(a),sin(a),cos(a));
     vec2 q=rotation*p;
     // Layer 1: drifting light shafts with deterministic orientation.
     float shafts=pow(max(0.,sin(q.x*(4.+mod(style,7.))+t*(.12+mod(style,3.)*.07))),8.);
     // Layer 2: slow layered fog, moving in opposing directions.
     float fog=noise(q*scale+vec2(t*.07,-t*.035))*.65+
       noise(q*scale*2.7+vec2(-t*.11,t*.06))*.35;
     // Layer 3: fine etched, halftone, woven or gridded interference.
     float pattern=abs(sin(q.x*(18.+mod(style,6.)*9.))*cos(q.y*(12.+mod(style,5.)*7.)));
     pattern=pow(pattern,2.+mod(style,4.));
     // Layer 4: two asymmetric orbital caustics.
     float orbit=exp(-length(p-vec2(sin(t*.23+a)*.48,cos(t*.19+a)*.34))*5.);
     orbit+=.6*exp(-length(p-vec2(cos(t*.17-a)*.62,sin(t*.27-a)*.39))*8.);
     // Layer 5: sweeping diffraction rings, phase and spacing vary by treatment.
     float rings=pow(max(0.,cos(length(q*vec2(1.,1.+mod(style,4.)*.3))*
       (12.+mod(style,8.)*3.)-t*(.3+mod(style,3.)*.15))),12.);
     float vignette=pow(max(0.,1.-dot(p,p)*.5),2.2);
     float intensity=(shafts*.13+fog*.15+pattern*.055+orbit*.22+rings*.085)*vignette;
     float pulse=.88+.12*sin(t*(.5+mod(style,5.)*.1)+a);
     vec3 color=mix(uColor,uSecond,clamp(fog*.7+orbit*.2,0.,1.));
     gl_FragColor=vec4(color*intensity*pulse*min(uEnergy,2.5),clamp(intensity*.46,0.,.32));
    }
   `}/>
 </mesh>
}
