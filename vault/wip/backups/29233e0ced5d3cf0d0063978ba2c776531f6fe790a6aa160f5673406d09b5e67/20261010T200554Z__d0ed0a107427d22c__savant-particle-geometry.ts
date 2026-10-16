import { BoxGeometry, BufferGeometry, Float32BufferAttribute, IcosahedronGeometry, OctahedronGeometry, SphereGeometry, TorusGeometry } from "three"
import type { ParticleShape } from "./savant-surfaces"
function combine(parts:BufferGeometry[]){
 const positions:number[]=[],normals:number[]=[],uvs:number[]=[]
 for(const original of parts){
  const g=original.index?original.toNonIndexed():original
  const p=g.getAttribute("position"),n=g.getAttribute("normal"),uv=g.getAttribute("uv")
  for(let i=0;i<p.count;i++){
   positions.push(p.getX(i),p.getY(i),p.getZ(i));normals.push(n.getX(i),n.getY(i),n.getZ(i))
   uvs.push(uv?uv.getX(i):0,uv?uv.getY(i):0)
  }
  if(g!==original)g.dispose()
  original.dispose()
 }
 const result=new BufferGeometry()
 result.setAttribute("position",new Float32BufferAttribute(positions,3))
 result.setAttribute("normal",new Float32BufferAttribute(normals,3))
 result.setAttribute("uv",new Float32BufferAttribute(uvs,2))
 return result
}
/* One shared instanced geometry per selected family; never rebuilt per frame. */
export function particleGeometry(shape:ParticleShape):BufferGeometry{
 if(shape==="ring")return new TorusGeometry(.85,.12,8,40)
 if(shape==="reticle"){
  const parts:BufferGeometry[]=[new TorusGeometry(.7,.055,6,32)]
  for(let i=0;i<4;i++)parts.push(new BoxGeometry(.5,.065,.065).translate(.9,0,0).rotateZ(i*Math.PI/2))
  return combine(parts)
 }
 if(shape==="flake"){
  const parts:BufferGeometry[]=[]
  for(let i=0;i<6;i++){
   parts.push(new BoxGeometry(.07,1,.07).translate(0,.45,0).rotateZ(i*Math.PI/3))
   for(const sign of [-1,1])parts.push(new BoxGeometry(.055,.45,.055).rotateZ(sign*.65).translate(sign*.13,.55,0).rotateZ(i*Math.PI/3))
  }
  return combine(parts)
 }
 if(shape==="shard")return new OctahedronGeometry(1,0).scale(.65,1.6,.65)
 if(shape==="splinter")return new IcosahedronGeometry(1,0).scale(.65,1.8,.2)
 if(shape==="tile")return new BoxGeometry(1.6,1.1,.18)
 const g=new SphereGeometry(1,24,16),p=g.getAttribute("position")
 for(let i=0;i<p.count;i++){
  const x=p.getX(i),y=p.getY(i),z=p.getZ(i)
  if(shape==="ribbon"||shape==="leaf"){
   const twist=y*(shape==="ribbon"?2.6:.8)
   p.setXYZ(i,x*.4*Math.cos(twist)+z*.04*Math.sin(twist),y*1.6,-x*.4*Math.sin(twist)+z*.04*Math.cos(twist))
  }else{
   const taper=shape==="drop"?1-.36*y:shape==="flame"?.7-.45*y:1
   const lobes=shape==="spore"?1+.12*Math.sin(Math.atan2(z,x)*6)*Math.sin(y*8):1
   p.setXYZ(i,x*taper*lobes,y*(shape==="flame"?1.9:1),z*taper*lobes)
  }
 }
 g.computeVertexNormals()
 return g
}
