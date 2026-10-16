import React,{useEffect,useMemo,useRef,useState} from "react"
import {useFrame} from "@react-three/fiber"
import {MeshSurfaceSampler} from "three/addons/math/MeshSurfaceSampler.js"
import {AdditiveBlending,CatmullRomCurve3,Color,Group,InstancedMesh,Matrix4,Mesh,Object3D,Vector3} from "three"
import {eventState} from "./savant-events"
import {seeded} from "./savant-motion"
import type {MaterialPreset} from "./savant-surfaces"
type Anchors={points:Vector3[];route:CatmullRomCurve3}
const up=new Vector3(0,1,0)
/* Built once, off the first paint, using the engine's surface-area sampler.
 * The creature follows a smooth surface-anchored artistic route, not a physics
 * simulation or a geodesic solver. No per-frame queries against the GLB. */
function useAnchors(model:Group,enabled:boolean){
 const [anchors,setAnchors]=useState<Anchors|null>(null)
 useEffect(()=>{
  if(!enabled||anchors)return
  let cancelled=false
  const timer=setTimeout(()=>{
   if(cancelled)return
   model.updateWorldMatrix(true,true)
   const meshes:Mesh[]=[]
   model.traverse(o=>{if(o instanceof Mesh)meshes.push(o)})
   const inverse=model.parent?model.parent.matrixWorld.clone().invert():new Matrix4()
   const points:Vector3[]=[]
   let sequence=0
   for(const mesh of meshes){
    const sampler=new MeshSurfaceSampler(mesh).setRandomGenerator(()=>seeded(++sequence+913)).build()
    const p=new Vector3(),n=new Vector3(),transform=inverse.clone().multiply(mesh.matrixWorld)
    for(let i=0;i<700;i++){
     sampler.sample(p,n);p.applyMatrix4(transform)
     if(p.z>.015)points.push(p.clone().add(new Vector3(0,0,.035)))
    }
   }
   if(points.length<32)return
   const ordered=[points.reduce((a,b)=>a.y<b.y?a:b).clone()]
   const remaining=points.slice()
   for(let i=0;i<40;i++){
    const last=ordered[ordered.length-1]
    let chosen=-1,best=Infinity
    for(let j=0;j<remaining.length;j++){
     const p=remaining[j],distance=p.distanceToSquared(last)
     if(distance<.006)continue
     const cost=distance+Math.max(0,last.y-p.y)*.25
     if(cost<best){best=cost;chosen=j}
    }
    if(chosen<0)break
    ordered.push(remaining.splice(chosen,1)[0].clone())
   }
   if(!cancelled)setAnchors({points,route:new CatmullRomCurve3(ordered,false,"centripetal")})
  },120)
  return()=>{cancelled=true;clearTimeout(timer)}
 },[model,enabled,anchors])
 return anchors
}
export function SurfaceEvents({model,time,preset,moving}:{
 model:Group;time:React.MutableRefObject<number>;preset:MaterialPreset;moving:boolean
}){
 const selected=preset.style===7||preset.style===12||preset.style===13
 const anchors=useAnchors(model,selected)
 const body=useRef<InstancedMesh>(null),legs=useRef<InstancedMesh>(null)
 const shards=useRef<InstancedMesh>(null)
 const portals=useRef<Array<Mesh|null>>([])
 const scratch=useMemo(()=>({o:new Object3D(),a:new Vector3(),b:new Vector3(),d:new Vector3(),q:new Color()}),[])
 const count=40
 useFrame(()=>{
  const e=eventState(time.current,preset.style),active=moving?e.strength:0
  const crawler=active>0&&preset.style===13&&!!anchors
  if(body.current)body.current.visible=crawler
  if(legs.current)legs.current.visible=crawler
  portals.current.forEach((p,i)=>{
   if(!p)return
   p.visible=crawler
   if(anchors){
    anchors.route.getPoint(i,scratch.a);p.position.copy(scratch.a);p.position.z+=.035
    p.rotation.z=time.current*(i?-.7:.7)
    p.scale.setScalar(active*(.11+.018*Math.sin(time.current*8)))
   }
  })
  if(crawler&&anchors&&body.current&&legs.current){
   const head=e.progress*1.32
   for(let i=0;i<24;i++){
    const phase=head-i*.012
    const visible=phase>=0&&phase<=1
    anchors.route.getPoint(Math.max(0,Math.min(1,phase)),scratch.a)
    anchors.route.getTangent(Math.max(0,Math.min(1,phase)),scratch.d)
    const size=visible?(.038+.008*Math.sin(i*.6))*active:0
    scratch.o.position.copy(scratch.a);scratch.o.quaternion.setFromUnitVectors(up,scratch.d)
    scratch.o.scale.set(size,size*1.6,size*.8);scratch.o.updateMatrix()
    body.current.setMatrixAt(i,scratch.o.matrix)
    for(let side=0;side<2;side++){
     scratch.b.set(-scratch.d.y,scratch.d.x,0).normalize().multiplyScalar(side?-1:1)
     scratch.b.multiplyScalar(size*(1.8+.5*Math.sin(time.current*12-i*.8)))
     scratch.o.position.copy(scratch.a).addScaledVector(scratch.b,.5)
     scratch.o.quaternion.setFromUnitVectors(up,scratch.b.normalize())
     scratch.o.scale.set(size*.18,size*2.4,size*.18);scratch.o.updateMatrix()
     legs.current.setMatrixAt(i*2+side,scratch.o.matrix)
    }
   }
   body.current.instanceMatrix.needsUpdate=true;legs.current.instanceMatrix.needsUpdate=true
  }
  if(shards.current){
   shards.current.visible=active>.001&&preset.style!==13&&!!anchors
   if(shards.current.visible&&anchors){
    for(let i=0;i<count;i++){
     const p=anchors.points[Math.floor(seeded(i+321)*anchors.points.length)]
     const growth=active*(.5+.5*seeded(i+721))
     scratch.o.position.copy(p)
     scratch.o.rotation.set(seeded(i+18)*.6,seeded(i+88)*6.28,seeded(i+99)*.7)
     scratch.o.scale.set(.02*growth,(preset.style===12?.035:.16)*growth,.02*growth)
     scratch.o.updateMatrix();shards.current.setMatrixAt(i,scratch.o.matrix)
    }
    shards.current.instanceMatrix.needsUpdate=true
   }
  }
 },-2)
 return <group>
  <instancedMesh ref={shards} args={[undefined,undefined,count]} visible={false} frustumCulled={false}>
   <octahedronGeometry args={[1,0]}/>
   <meshPhysicalMaterial color={preset.accent2} metalness={preset.style===12?.9:0}
    roughness={.07} clearcoat={1} transmission={preset.style===12?0:.6}
    thickness={.15} ior={1.46} envMapIntensity={2}/>
  </instancedMesh>
  <instancedMesh ref={body} args={[undefined,undefined,24]} visible={false} frustumCulled={false}>
   <sphereGeometry args={[1,12,8]}/>
   <meshPhysicalMaterial color={preset.color} metalness={.8} roughness={.15} clearcoat={1}
    iridescence={.65} emissive={preset.accent} emissiveIntensity={.08}/>
  </instancedMesh>
  <instancedMesh ref={legs} args={[undefined,undefined,48]} visible={false} frustumCulled={false}>
   <capsuleGeometry args={[1,1,2,5]}/>
   <meshPhysicalMaterial color={preset.accent2} metalness={.95} roughness={.13}/>
  </instancedMesh>
  {[0,1].map(i=><mesh key={i} ref={p=>{portals.current[i]=p}} visible={false}>
   <planeGeometry args={[2,2]}/>
   <shaderMaterial transparent depthWrite={false} blending={AdditiveBlending}
    uniforms={{uColor:{value:new Color(i?preset.accent:preset.accent2)}}}
    vertexShader={`varying vec2 vUv;void main(){vUv=uv;gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.0);}`}
    fragmentShader={`varying vec2 vUv;uniform vec3 uColor;void main(){
     vec2 p=(vUv-.5)*2.0;float r=length(p),a=atan(p.y,p.x);
     float ring=exp(-pow(r-.68-.04*sin(a*7.0),2.0)*280.0);
     float core=exp(-r*r*12.0);
     gl_FragColor=vec4(uColor*(ring*3.0+core*.2),ring*.85+core*.45);
     #include <colorspace_fragment>
    }`}/>
  </mesh>)}
 </group>
}
