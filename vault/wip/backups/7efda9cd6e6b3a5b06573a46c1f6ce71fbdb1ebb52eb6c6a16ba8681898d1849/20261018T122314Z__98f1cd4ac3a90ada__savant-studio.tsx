import {useLayoutEffect,useRef} from "react"
import {useThree} from "@react-three/fiber"
import {Color,DoubleSide,Mesh,PlaneGeometry,PMREMGenerator,Scene,ShaderMaterial} from "three"
import type {WebGLRenderTarget} from "three"
import {derelictStage} from "./savant-derelict-stage"
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
   const panels=[
    {position:[-3,2,4],scale:[5,4],color:profile.kind<0?"#eef5ff":profile.paper,power:3},
    {position:[3,.5,3],scale:[2.2,5],color:profile.kind<0?"#ff2f9d":profile.accent,power:2.4},
    {position:[2,1,-4],scale:[2.5,5],color:profile.kind<0?"#d6b45f":profile.secondary,power:2.3},
    {position:[-4,-1,-2],scale:[4,3],color:profile.paper,power:1.2},
   ]
   for(const p of panels){
    const material=new ShaderMaterial({side:DoubleSide,toneMapped:false,
     uniforms:{uColor:{value:new Color(p.color)},uPower:{value:p.power*profile.energy}},
     vertexShader:"varying vec2 vUv;void main(){vUv=uv;gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.0);}",
     fragmentShader:"uniform vec3 uColor;uniform float uPower;varying vec2 vUv;void main(){vec2 q=(vUv-.5)*2.0;float edge=exp(-dot(q,q)*3.5)*pow(max(0.0,1.0-max(abs(q.x),abs(q.y))),2.0);gl_FragColor=vec4(uColor*edge*uPower,1.0);}",
    })
    materials.push(material)
    const panel=new Mesh(geometry,material)
    panel.position.set(p.position[0],p.position[1],p.position[2])
    panel.scale.set(p.scale[0],p.scale[1],1);panel.lookAt(0,0,0);stage.add(panel)
   }
   const derelict=profile.kind===0?derelictStage():null
   if(derelict)stage.add(derelict.group)
   const generator=new PMREMGenerator(gl)
   try{target=generator.fromScene(stage,profile.softness,.1,30,{size:profile.kind===0?512:256})}
   finally{generator.dispose();derelict?.dispose();geometry.dispose();materials.forEach(m=>m.dispose());stage.clear()}
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
