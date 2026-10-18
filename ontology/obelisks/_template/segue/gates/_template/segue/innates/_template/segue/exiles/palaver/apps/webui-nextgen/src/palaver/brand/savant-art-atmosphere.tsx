import {useEffect,useMemo} from "react"
import type {MutableRefObject} from "react"
import {useFrame} from "@react-three/fiber"
import {Color,DoubleSide,ShaderMaterial} from "three"
import type {ArtDirection} from "./savant-art-direction"
import {artFieldGLSL} from "./savant-art-surface"

export function ArtAtmosphere({profile,time,moving}:{
 profile:ArtDirection;time:MutableRefObject<number>;moving:boolean
}){
 const material=useMemo(()=>new ShaderMaterial({
  transparent:true,depthWrite:false,depthTest:true,side:DoubleSide,
  uniforms:{uTime:{value:0},uKind:{value:0},uOpacity:{value:0},
   uDrift:{value:0},uColor:{value:new Color()},uSecond:{value:new Color()}},
  vertexShader:`varying vec2 vUv;void main(){vUv=uv;gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.0);}`,
  fragmentShader:`uniform float uTime,uKind,uOpacity,uDrift;uniform vec3 uColor,uSecond;varying vec2 vUv;
${artFieldGLSL}
void main(){
 vec2 p=(vUv-.5)*2.0;
 float falloff=exp(-dot(p,p)*3.2)*(1.0-smoothstep(.65,1.0,max(abs(p.x),abs(p.y))));
 vec3 field=saField(vec3(p*1.3+vec2(sin(uTime*uDrift)*.035,cos(uTime*uDrift*.7)*.04),0),uKind,uTime);
 float wisp=.25+.4*field.x+.35*field.z;
 if(uKind>6.5&&uKind<7.5)wisp*=.7+.3*sin(uTime*1.8+p.y*13.0);
 if(uKind>3.5&&uKind<4.5)wisp*=.65+.35*sin(length(p)*19.0-uTime*.7);
 if(uKind>14.5&&uKind<15.5)wisp*=.65+.35*field.y;
 float wave=.8+.2*sin(uTime*.8+length(p)*11.0);
 gl_FragColor=vec4(mix(uColor,uSecond,field.x),clamp(falloff*wisp*wave*uOpacity,0.0,.22));
 #include <tonemapping_fragment>
 #include <colorspace_fragment>
}`,
 }),[])
 useEffect(()=>()=>material.dispose(),[material])
 useFrame(()=>{
  material.uniforms.uTime.value=moving?time.current:0
  material.uniforms.uKind.value=Math.max(profile.kind,0)
  material.uniforms.uOpacity.value=profile.haze
  material.uniforms.uDrift.value=profile.drift
  material.uniforms.uColor.value.set(profile.accent);material.uniforms.uSecond.value.set(profile.secondary)
 },-2)
 return <mesh name="savant-art-atmosphere" visible={profile.haze>0} position={[0,0,-.85]} scale={[3.8,3.8,1]} material={material} renderOrder={-1}>
  <planeGeometry args={[1,1]}/>
 </mesh>
}
