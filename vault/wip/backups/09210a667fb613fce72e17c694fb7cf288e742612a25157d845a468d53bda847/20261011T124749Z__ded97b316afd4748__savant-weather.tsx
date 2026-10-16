import React,{useMemo,useRef} from "react"
import {useFrame} from "@react-three/fiber"
import {AdditiveBlending,BufferAttribute,BufferGeometry,Color,LineSegments,PointLight,DynamicDrawUsage} from "three"
import {seeded} from "./savant-motion"
import {eventState,electricalPulse} from "./savant-events"
import type {MaterialPreset} from "./savant-surfaces"

/* Twenty scene-specific analytical atmospheres. Main and reflection stage
 * share a reproducible director, seed and clock; all particles are bounded. */
export function AtmosphericEvents({time,preset,moving,reflection=false}:{
 time:React.MutableRefObject<number>;preset:MaterialPreset;moving:boolean;reflection?:boolean
}){
 const count=reflection?32:72
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
  const e=eventState(time.current,preset.style)
  uniforms.uTime.value=time.current;uniforms.uKind.value=preset.style
  uniforms.uEnergy.value=moving?e.strength:0
  uniforms.uColor.value.set(preset.accent);uniforms.uAccent.value.set(preset.accent2)
  uniforms.uPixels.value=reflection?256:Math.min(size.height*gl.getPixelRatio(),900)
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
     varying float vFade,vKind,vSeed;
     float rnd(float n){return fract(sin(n*127.1+311.7)*43758.5453123);}
     void main(){
      vec3 p=position;float k=uKind,t=uTime,seed=aSeed;
      float speed=.55+rnd(seed+19.0)*.6;
      vKind=k;vSeed=seed;
      if(k<.5){p.y=mod(p.y-t*speed*2.7+3.0,4.8)-2.4;p.x+=sin(t*.7+seed)*.1;}
      else if(k<1.5){p+=vec3(sin(t*3.0+seed),cos(t*2.0+seed),0.0)*.08;}
      else if(k<2.5){p.x+=sin(t*.19+seed)*.5;p.y+=cos(t*.23+seed)*.3;}
      else if(k<3.5){p+=vec3(-3.0,3.0,-1.0)*(fract(t*.23*speed+rnd(seed))-.5);}
      else if(k<4.5){p.x=mod(p.x+t*speed+3.0,5.0)-2.5;p.y+=sin(t+seed)*.12;}
      else if(k<5.5){p.y=mod(p.y+t*speed*.7+3.0,4.8)-2.4;p.z+=sin(t*.7+seed)*.1;}
      else if(k<6.5){p.y+=sin(p.x*1.8+t*.6)*.5;p.z+=cos(t*.3+seed)*.3;}
      else if(k<7.5){p.y=mod(p.y-t*speed*.35+3.0,4.8)-2.4;p.x+=sin(t*.8+seed)*.2;}
      else if(k<8.5){p.y+=sin(t*speed+seed)*.2;p.x+=cos(t*.7+seed)*.2;}
      else if(k<9.5){float a=t*speed+seed;p=vec3(cos(a)*1.4,p.y,sin(a)*1.4);}
      else if(k<10.5){p.y=mod(p.y-t*speed*1.3+3.0,4.8)-2.4;p.x+=sin(seed)*.25;}
      else if(k<11.5){p.y=mod(p.y+t*speed*.45+3.0,4.8)-2.4;p.x+=sin(t*.8+seed)*.15;}
      else if(k<12.5){p+=vec3(sin(t*2.0+seed)*.035,cos(t*3.0+seed)*.035,0.0);}
      else if(k<13.5){p+=vec3(sin(t+seed),cos(t*.8+seed),sin(t*.6+seed))*.18;}
      else if(k<14.5){p.y+=sin(t*speed*2.0+seed)*.3;p.z+=cos(t*.9+seed)*.2;}
      else if(k<15.5){p.y=mod(p.y-t*speed*.8+3.0,4.8)-2.4;p.x=floor(p.x*8.0)/8.0;}
      else if(k<16.5){p+=vec3(sin(t*.4+seed),cos(t*.7+seed),sin(t*.5+seed))*.3;}
      else if(k<17.5){p.y=mod(p.y+t*speed*.85+3.0,4.8)-2.4;p.x+=sin(t*2.0+seed)*.15;}
      else if(k<18.5){p.y=mod(p.y-t*speed*.22+3.0,4.8)-2.4;p.x+=sin(t*.3+seed)*.4;}
      else{float a=t*speed+seed;p=vec3(cos(a)*1.7,sin(a)*.65,sin(a)*1.7);}
      vec4 view=modelViewMatrix*vec4(p,1.0);gl_Position=projectionMatrix*view;
      float base=k>1.5&&k<2.5?165.0:k>5.5&&k<6.5?130.0:k<.5?20.0:k>10.5&&k<11.5?25.0:12.0;
      gl_PointSize=clamp(base*uPixels/600.0/max(-view.z,.5),1.0,180.0);
      vFade=uEnergy*(1.0-smoothstep(1.5,2.4,abs(p.y)));
     }`}
    fragmentShader={`
     uniform vec3 uColor,uAccent;uniform float uTime;varying float vFade,vKind,vSeed;
     void main(){
      vec2 p=(gl_PointCoord-.5)*2.0;float r=length(p),k=vKind,shape=0.0;
      float glint=pow(max(0.0,sin(uTime*4.3+vSeed*7.1)),16.0);
      if(k<.5){shape=exp(-p.x*p.x*220.0-p.y*p.y*2.0)*.5;}
      else if(k<1.5){shape=exp(-r*r*18.0)*glint;}
      else if(k<2.5){shape=exp(-r*r*4.0)*.018;}
      else if(k<3.5){vec2 q=vec2((p.x+p.y)*.707,(p.y-p.x)*.707);shape=exp(-q.x*q.x*140.0-q.y*q.y*2.0);}
      else if(k<4.5){shape=exp(-r*r*15.0)*.24;}
      else if(k<5.5){shape=(exp(-p.x*p.x*70.0)+exp(-p.y*p.y*70.0))*exp(-r*r*5.0)*.24;}
      else if(k<6.5){shape=exp(-p.y*p.y*18.0-p.x*p.x*2.0)*.025;}
      else if(k<7.5){shape=exp(-r*r*12.0)*(1.0+glint);}
      else if(k<8.5){shape=exp(-pow(r-.48,2.0)*120.0)*.5+exp(-r*r*25.0)*glint;}
      else if(k<9.5){shape=exp(-pow(r-.6,2.0)*180.0)*.3;}
      else if(k<10.5){shape=(1.0-smoothstep(.48,.7,r+.08*sin(atan(p.y,p.x)*7.0)))*.55;}
      else if(k<11.5){shape=exp(-pow(r-.7,2.0)*180.0)*.35+exp(-dot(p-vec2(-.3,.4),p-vec2(-.3,.4))*90.0);}
      else if(k<12.5){shape=(1.0-smoothstep(.4,.48,max(abs(p.x),abs(p.y))))*(.2+glint);}
      else if(k<13.5){shape=exp(-r*r*7.0)*(.3+.2*sin(uTime*3.0+vSeed));}
      else if(k<14.5){shape=exp(-p.x*p.x*120.0-p.y*p.y*3.0)*.65;}
      else if(k<15.5){shape=(1.0-smoothstep(.3,.4,max(abs(p.x),abs(p.y))))*glint;}
      else if(k<16.5){shape=exp(-pow(abs(p.x)+abs(p.y)-.55,2.0)*190.0)*.5;}
      else if(k<17.5){shape=exp(-p.x*p.x*8.0-pow(p.y+.35,2.0)*5.0)*(1.0+glint);}
      else if(k<18.5){shape=exp(-r*r*18.0)*.13;}
      else{shape=exp(-pow(r-.68,2.0)*150.0)*.3;}
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
 const lines=useRef<LineSegments>(null)
 const light=useRef<PointLight>(null)
 const branches=5,segments=16
 const geometry=useMemo(()=>{
  const g=new BufferGeometry()
  const positions=new Float32Array(branches*segments*6)
  const attribute=new BufferAttribute(positions,3)
  attribute.setUsage(DynamicDrawUsage)
  g.setAttribute("position",attribute)
  g.setDrawRange(0,positions.length/3)
  return g
 },[])
 React.useEffect(()=>()=>geometry.dispose(),[geometry])
 useFrame(()=>{
  if(!lines.current)return
  const event=electricalPulse(time.current,preset.style)
  const cycle=event.epoch,phase=event.phase,pulse=event.strength
  const active=moving&&pulse>.035
  lines.current.visible=active
  if(light.current)light.current.intensity=active?pulse*9*preset.scene.energy:0
  const material=lines.current.material
  if(!Array.isArray(material))material.opacity=pulse*.85
  if(!active)return
  const positions=(geometry.getAttribute("position") as BufferAttribute).array as Float32Array
  const tick=Math.floor(phase*22)
  let offset=0
  for(let branch=0;branch<branches;branch++){
   const direction=branch%2===0?1:-1
   const originX=-1.15+branch*.56
   let x=originX,y=1.65,z=.12+branch*.015
   for(let i=0;i<segments;i++){
    const seed=cycle*917+branch*79+i*13+tick*3
    const nx=originX+Math.sin(i*.67+branch)*.21+
      (seeded(seed)-.5)*.19
    const ny=y-.205
    const nz=z+(seeded(seed+51)-.5)*.18
    positions[offset++]=x
    positions[offset++]=y
    positions[offset++]=z
    positions[offset++]=nx+direction*i*.009
    positions[offset++]=ny
    positions[offset++]=nz
    x=nx+direction*i*.009
    y=ny
    z=nz
   }
  }
  geometry.getAttribute("position").needsUpdate=true
  geometry.computeBoundingSphere()
 },-2)
 return <group>
  <pointLight ref={light} position={[0,.7,.5]} color={preset.accent2}
   intensity={0} distance={5} decay={2}/>
  <lineSegments ref={lines} visible={false} frustumCulled={false}>
   <primitive object={geometry} attach="geometry" dispose={null}/>
   <lineBasicMaterial color={preset.accent2} transparent opacity={0}
    blending={AdditiveBlending} depthWrite={false} toneMapped={false}/>
  </lineSegments>
 </group>
}
