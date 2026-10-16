import React,{useMemo,useRef} from "react"
import {useFrame} from "@react-three/fiber"
import {AdditiveBlending,BufferAttribute,BufferGeometry,Color,LineSegments,PointLight} from "three"
import {seeded,ease} from "./savant-motion"
import type {MaterialPreset} from "./savant-surfaces"
const kinds=["rain","lightning","fog","meteors","dust","snow","sparks","spores"]

/* Bounded 3D scene events. The exact same clock and seed drive the reflection
 * stage, so visible events and their reflected projections stay in phase. */
export function AtmosphericEvents({time,preset,moving,reflection=false}:{
 time:React.MutableRefObject<number>;preset:MaterialPreset;moving:boolean;reflection?:boolean
}){
 const count=preset.scene.event==="fog"?20:preset.scene.event==="rain"?110:56
 const data=useMemo(()=>{
  const p=new Float32Array(count*3),ids=new Float32Array(count)
  for(let i=0;i<count;i++){
   p[i*3]=(seeded(i+83)-.5)*4.4;p[i*3+1]=(seeded(i+173)-.5)*3.8
   p[i*3+2]=-1.6+seeded(i+271)*3;ids[i]=i
  }
  return {p,ids}
 },[count])
 const uniforms=useMemo(()=>({uTime:{value:0},uKind:{value:0},uEnergy:{value:0},
  uColor:{value:new Color()},uAccent:{value:new Color()},uPixels:{value:200}}),[])
 useFrame(({gl,size})=>{
  const t=time.current,cycle=Math.floor(t/11),age=t-cycle*11
  const begin=1+seeded(cycle+51)*2,span=preset.scene.event==="fog"?5:3.3
  const envelope=ease((age-begin)/.7)*(1-ease((age-begin-span)/.8))
  uniforms.uTime.value=t;uniforms.uKind.value=kinds.indexOf(preset.scene.event)
  uniforms.uEnergy.value=moving?envelope:0
  uniforms.uColor.value.set(preset.accent);uniforms.uAccent.value.set(preset.accent2)
  uniforms.uPixels.value=reflection?512:Math.min(size.height*gl.getPixelRatio(),1200)
 },-2)
 return <group>
  <points frustumCulled={false}>
   <bufferGeometry>
    <bufferAttribute attach="attributes-position" args={[data.p,3]}/>
    <bufferAttribute attach="attributes-aSeed" args={[data.ids,1]}/>
   </bufferGeometry>
   <shaderMaterial uniforms={uniforms} transparent depthWrite={false}
    blending={AdditiveBlending} toneMapped={false}
    vertexShader={`
     uniform float uTime,uKind,uEnergy,uPixels;attribute float aSeed;
     varying float vFade,vKind;varying float vSeed;
     float rnd(float n){return fract(sin(n*127.1+311.7)*43758.5453123);}
     void main(){
      vec3 p=position;float speed=.6+rnd(aSeed+19.0)*.7;
      vKind=uKind;vSeed=aSeed;
      if(uKind<.5){p.y=mod(position.y-uTime*speed*2.5+3.0,4.8)-2.4;p.x+=.16*sin(uTime*.7+aSeed);}
      else if(uKind<1.5){p+=vec3(sin(uTime+aSeed),cos(uTime*.8+aSeed),0.0)*.02;}
      else if(uKind<2.5){p.x+=sin(uTime*.19+aSeed)*.45;p.y+=cos(uTime*.23+aSeed)*.25;}
      else if(uKind<3.5){float phase=fract(uTime*.23*speed+rnd(aSeed+31.0));p+=vec3(-3.0,3.0,-1.0)*(phase-.5);}
      else if(uKind<4.5){p.x+=sin(uTime*.35+aSeed)*.5;p.y+=cos(uTime*.23+aSeed)*.25;}
      else if(uKind<5.5){p.y=mod(position.y-uTime*speed*.38+3.0,4.8)-2.4;p.x+=sin(uTime*.8+aSeed)*.2;}
      else if(uKind<6.5){p.y=mod(position.y+uTime*speed*.8+3.0,4.8)-2.4;p.x+=sin(uTime*1.6+aSeed)*.2;}
      else{p+=vec3(sin(uTime*.6+aSeed),cos(uTime*.4+aSeed),sin(uTime*.3+aSeed))*.22;}
      vec4 view=modelViewMatrix*vec4(p,1.0);
      gl_Position=projectionMatrix*view;
      float base=uKind>1.5&&uKind<2.5?180.0:uKind<.5?20.0:uKind>2.5&&uKind<3.5?25.0:5.0;
      gl_PointSize=clamp(base*uPixels/600.0/max(-view.z,.5),1.0,240.0);
      vFade=uEnergy*(1.0-smoothstep(1.5,2.4,abs(p.y)));
     }`}
    fragmentShader={`
     uniform vec3 uColor,uAccent;uniform float uTime;varying float vFade,vKind,vSeed;
     void main(){
      vec2 p=(gl_PointCoord-.5)*2.0;float shape;
      if(vKind<.5){shape=exp(-p.x*p.x*220.0-p.y*p.y*2.0)*.55;}
      else if(vKind<1.5){shape=0.0;}
      else if(vKind<2.5){shape=exp(-dot(p,p)*4.0)*.035;}
      else if(vKind<3.5){
       vec2 q=vec2((p.x+p.y)*.707,(p.y-p.x)*.707);
       shape=exp(-q.x*q.x*140.0-q.y*q.y*2.0)*(1.0+.7*q.y);
      }else{shape=exp(-dot(p,p)*8.0)*(.55+.45*sin(uTime*1.4+vSeed));}
      float a=shape*vFade;if(a<.002)discard;
      gl_FragColor=vec4(mix(uColor,uAccent,.5+.5*sin(vSeed))*1.8,a);
      #include <colorspace_fragment>
     }`}/>
  </points>
  {preset.scene.event==="lightning"&&<Lightning time={time} preset={preset} moving={moving}/>}
 </group>
}
function Lightning({time,preset,moving}:{
 time:React.MutableRefObject<number>;preset:MaterialPreset;moving:boolean
}){
 const lines=useRef<LineSegments>(null),light=useRef<PointLight>(null)
 const geometry=useMemo(()=>{
  const p:number[]=[]
  for(let branch=0;branch<3;branch++){
   let x=-1.4+branch*1.2,y=1.65,z=-.45-branch*.2
   for(let i=0;i<14;i++){
    const nx=x+(seeded(i+branch*31)-.5)*.3,ny=y-.19
    p.push(x,y,z,nx,ny,z);x=nx;y=ny
   }
  }
  const g=new BufferGeometry();g.setAttribute("position",new BufferAttribute(new Float32Array(p),3));return g
 },[])
 React.useEffect(()=>()=>geometry.dispose(),[geometry])
 useFrame(()=>{
  if(!lines.current)return
  const t=time.current,cycle=Math.floor(t/13),age=t-cycle*13
  const start=3+seeded(cycle+705)*4
  const pulse=age>start&&age<start+.45?Math.pow(Math.max(0,Math.sin((age-start)*51)),6):0
  lines.current.visible=moving&&pulse>.03
  if(light.current)light.current.intensity=moving?pulse*5*preset.scene.energy:0
  const m=lines.current.material
  if(!Array.isArray(m)){m.opacity=pulse*.75}
  lines.current.rotation.y=Math.sin(cycle*2.3)*.7
 },-2)
 return <group><pointLight ref={light} position={[-.4,1.2,.6]} color={preset.accent2} intensity={0} distance={5} decay={2}/><lineSegments ref={lines} visible={false} frustumCulled={false}>
  <primitive object={geometry} attach="geometry" dispose={null}/>
  <lineBasicMaterial color={preset.accent2} transparent opacity={0} blending={AdditiveBlending} depthWrite={false} toneMapped={false}/>
 </lineSegments></group>
}
