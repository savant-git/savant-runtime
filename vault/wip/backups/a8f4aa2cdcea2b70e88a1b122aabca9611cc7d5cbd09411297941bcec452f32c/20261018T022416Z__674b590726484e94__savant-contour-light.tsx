import React,{useEffect,useMemo,useRef} from "react"
import {useFrame} from "@react-three/fiber"
import {AdditiveBlending,BufferAttribute,BufferGeometry,Color,LineBasicMaterial,Mesh,PointLight,Vector3} from "three"
import type {Object3D} from "three"
import {savantContour} from "./savant-contour-data"
import {buildDepthEnvelope,clearancePolyline,clearZ} from "./savant-contour-clearance"
type Props={time:React.MutableRefObject<number>;active:boolean;color?:string;model:Object3D;glitch?:{value:number}}
const front=.18,back=-.18,spacing=.055,tracerSpeed=.19
function buildContour(){
 const points=savantContour.map(([x,y])=>new Vector3(x,y,0)),lengths=[0]
 let total=0
 for(let i=1;i<points.length;i++){total+=points[i].distanceTo(points[i-1]);lengths.push(total)}
 total+=points.at(-1)!.distanceTo(points[0])
 return {total,sample(distance:number,out:Vector3){
  const d=((distance%total)+total)%total
  let lo=1,hi=lengths.length
  while(lo<hi){const mid=(lo+hi)>>>1;if(lengths[mid]<d)lo=mid+1;else hi=mid}
  const index=Math.min(lo,points.length)
  const a=points[index-1],b=points[index%points.length]
  const start=lengths[index-1],end=index<lengths.length?lengths[index]:total
  return out.copy(a).lerp(b,(d-start)/Math.max(end-start,1e-8))
 }}
}
export function SavantContourLight({time,active,model,glitch}:Props){
 const contour=useMemo(buildContour,[])
 const envelope=useMemo(()=>buildDepthEnvelope(model),[model])
 const geometry=useMemo(()=>{
  const positions:number[]=[],colors:number[]=[],sides:number[]=[]
  const count=Math.max(48,Math.ceil(contour.total/spacing))
  const a=new Vector3(),b=new Vector3(),gold=new Color("#e5ad39"),pink=new Color("#ef6ca5"),color=new Color()
  const add=(start:Vector3,end:Vector3,side:1|-1,at:number)=>{
   const points=clearancePolyline(start,end,side,envelope)
   color.copy(gold).lerp(pink,at)
   for(let i=1;i<points.length;i++){
    const p=points[i-1],q=points[i]
    positions.push(p.x,p.y,p.z,q.x,q.y,q.z)
    colors.push(color.r,color.g,color.b,color.r,color.g,color.b);sides.push(side,side)
   }
  }
  for(let i=0;i<count;i++){
   contour.sample(i/count*contour.total,a);contour.sample((i+1)/count*contour.total,b)
   add(a.clone().setZ(front),b.clone().setZ(front),1,i/count)
   add(a.clone().setZ(back),b.clone().setZ(back),-1,i/count)
   add(a.clone().setZ(front),b.clone().setZ(back),1,i/count)
   add(a.clone().setZ(back),b.clone().setZ(front),-1,i/count)
  }
  const g=new BufferGeometry()
  g.setAttribute("position",new BufferAttribute(new Float32Array(positions),3))
  g.setAttribute("color",new BufferAttribute(new Float32Array(colors),3))
  g.setAttribute("aExteriorSide",new BufferAttribute(new Float32Array(sides),1))
  g.computeBoundingSphere();return g
 },[contour,envelope])
 const extra=useMemo(()=>({value:0}),[])
 const materials=useMemo(()=>[.72,.12].map((opacity,i)=>{
  const m=new LineBasicMaterial({vertexColors:true,transparent:true,opacity,depthWrite:false,depthTest:true,toneMapped:true,
   ...(i?{blending:AdditiveBlending}:{})})
  m.onBeforeCompile=shader=>{
   shader.uniforms.uContourExtra=extra
   shader.vertexShader=shader.vertexShader.replace("#include <common>",
    "#include <common>\nattribute float aExteriorSide;uniform float uContourExtra;")
    .replace("#include <begin_vertex>","#include <begin_vertex>\ntransformed.z+=aExteriorSide*uContourExtra;")
  }
  m.customProgramCacheKey=()=>"savant-z-clear-contour-1"
  return m
 }),[extra])
 const first=useRef<Mesh>(null),second=useRef<Mesh>(null)
 const firstLight=useRef<PointLight>(null),secondLight=useRef<PointLight>(null)
 const points=useMemo(()=>[new Vector3(),new Vector3()],[])
 useEffect(()=>()=>{geometry.dispose();materials.forEach(m=>m.dispose())},[geometry,materials])
 useFrame(()=>{
  extra.value=(glitch?.value||0)*.04
  const phase=active?time.current*tracerSpeed:0
  contour.sample(phase*contour.total,points[0]);contour.sample((phase+.5)*contour.total,points[1])
  points[0].z=clearZ(points[0].x,points[0].y,front,1,envelope)+.012+extra.value
  points[1].z=clearZ(points[1].x,points[1].y,back,-1,envelope)-.012-extra.value
  first.current?.position.copy(points[0]);second.current?.position.copy(points[1])
  firstLight.current?.position.copy(points[0]);secondLight.current?.position.copy(points[1])
  const pulse=active ? .9+.1*Math.sin(time.current*3.1):1
  if(firstLight.current)firstLight.current.intensity=1.1*pulse
  if(secondLight.current)secondLight.current.intensity=.9*pulse
 },-2)
 return <group>
  <lineSegments geometry={geometry} material={materials[1]} frustumCulled={false}/>
  <lineSegments geometry={geometry} material={materials[0]} frustumCulled={false}/>
  <mesh ref={first}><sphereGeometry args={[.021,12,8]}/><meshBasicMaterial color="#ffe4a0" toneMapped={false}/></mesh>
  <mesh ref={second}><sphereGeometry args={[.021,12,8]}/><meshBasicMaterial color="#e5ad39" toneMapped={false}/></mesh>
  <pointLight ref={firstLight} color="#e5ad39" intensity={1.1} distance={.7} decay={2}/>
  <pointLight ref={secondLight} color="#ef6ca5" intensity={.9} distance={.7} decay={2}/>
 </group>
}
