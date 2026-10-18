import {useLayoutEffect,useRef} from "react"
import {useThree} from "@react-three/fiber"
import {Color,DoubleSide,Mesh,PlaneGeometry,PMREMGenerator,Scene,ShaderMaterial} from "three"
import type {WebGLRenderTarget} from "three"
import type {ArtDirection} from "./savant-art-direction"

/** Soft reflector stage, captured/filtered only on selection; at most three cached targets. */
export function SavantStudio({profile}:{profile:ArtDirection}){
 const {gl,scene,invalidate}=useThree()
 const cache=useRef(new Map<string,WebGLRenderTarget>())
 useLayoutEffect(()=>{
  const previous=scene.environment,rotation=scene.environmentRotation.clone(),intensity=scene.environmentIntensity
  return()=>{
   scene.environment=previous;scene.environmentRotation.copy(rotation);scene.environmentIntensity=intensity
   cache.current.forEach(target=>target.dispose());cache.current.clear()
  }
 },[scene])
 useLayoutEffect(()=>{
  const key=profile.kind<0?"cinematic":String(profile.kind)
  let target=cache.current.get(key)
  if(target){cache.current.delete(key);cache.current.set(key,target)}
  else{
   const stage=new Scene();stage.background=new Color(profile.kind<0?"#343d45":profile.ink)
   const geometry=new PlaneGeometry(1,1),materials:ShaderMaterial[]=[]
   // A neutral/cool title key and narrow warm strips, rather than uniformly colored cards.
   // Captured once per selection and prefiltered; no per-frame six-face capture.
   const panels=[
    {position:[-3,2,4],scale:[4.8,3.6],color:"#e6eff5",power:2.3},
    {position:[3,.5,3],scale:[.65,5.4],color:profile.accent,power:2.1},
    {position:[2,1,-4],scale:[.8,5],color:"#e9c88a",power:2.0},
    {position:[-4,-1,-2],scale:[3.5,2.8],color:"#92aabb",power:.9},
    {position:[-1,4,-2],scale:[4.2,.45],color:profile.secondary,power:1.25},
   ]
   for(const p of panels){
    const material=new ShaderMaterial({side:DoubleSide,toneMapped:false,
     uniforms:{uColor:{value:new Color(p.color)},uPower:{value:p.power*profile.energy}},
     vertexShader:"varying vec2 vUv;void main(){vUv=uv;gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.0);}",
     fragmentShader:"uniform vec3 uColor;uniform float uPower;varying vec2 vUv;void main(){vec2 q=(vUv-.5)*2.0;float edge=exp(-dot(q,q)*2.6)*(1.0-smoothstep(.45,1.0,length(q)));gl_FragColor=vec4(uColor*edge*uPower,1.0);}",
    })
    materials.push(material)
    const panel=new Mesh(geometry,material)
    panel.position.set(p.position[0],p.position[1],p.position[2])
    panel.scale.set(p.scale[0],p.scale[1],1);panel.lookAt(0,0,0);stage.add(panel)
   }
   const generator=new PMREMGenerator(gl)
   try{target=generator.fromScene(stage,profile.softness,.1,30,{size:Math.min(512,gl.capabilities.maxCubemapSize)})}
   finally{generator.dispose();geometry.dispose();materials.forEach(m=>m.dispose());stage.clear()}
   cache.current.set(key,target)
   while(cache.current.size>3){
    const oldest=cache.current.keys().next().value
    if(oldest===undefined)break
    const removed=cache.current.get(oldest);cache.current.delete(oldest)
    if(scene.environment===removed?.texture)scene.environment=null
    removed?.dispose()
   }
  }
  scene.environment=target.texture;scene.environmentIntensity=1
  invalidate()
 },[gl,scene,invalidate,profile])
 return null
}
