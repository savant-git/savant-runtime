import {Matrix4,Mesh,Vector3} from "three"
import type {Object3D} from "three"
export type DepthEnvelope={cell:number;bounds:(x:number,y:number)=>{front:number;back:number}|null}
/* Conservative XY projection of the actual transformed triangles.
 * Z ranges cover each triangle's whole cell footprint, never just its center.
 * Source geometry/XY positions are untouched. Derived once per model. */
export function buildDepthEnvelope(model:Object3D,resolution=256):DepthEnvelope{
 model.updateWorldMatrix(true,true)
 const inverse=model.parent?model.parent.matrixWorld.clone().invert():new Matrix4()
 const surfaces:{mesh:Mesh;matrix:Matrix4}[]=[]
 let minX=Infinity,minY=Infinity,maxX=-Infinity,maxY=-Infinity
 const a=new Vector3(),b=new Vector3(),c=new Vector3()
 model.traverse(object=>{
  if(!(object instanceof Mesh))return
  const p=object.geometry.attributes.position,index=object.geometry.index
  if(!p)return
  const matrix=new Matrix4().multiplyMatrices(inverse,object.matrixWorld)
  surfaces.push({mesh:object,matrix})
  for(let i=0;i<p.count;i++){
   a.fromBufferAttribute(p,i).applyMatrix4(matrix)
   minX=Math.min(minX,a.x);maxX=Math.max(maxX,a.x);minY=Math.min(minY,a.y);maxY=Math.max(maxY,a.y)
  }
 })
 if(!surfaces.length)throw new Error("savant contour clearance requires model triangles")
 const size=resolution+2,cell=Math.max(maxX-minX,maxY-minY)/resolution
 minX-=cell;minY-=cell
 const front=new Float32Array(size*size).fill(-Infinity)
 const back=new Float32Array(size*size).fill(Infinity)
 const clamp=(n:number)=>Math.max(0,Math.min(size-1,n))

 for(const {mesh,matrix} of surfaces){
  const p=mesh.geometry.attributes.position,index=mesh.geometry.index,count=index?index.count:p.count
  for(let i=0;i+2<count;i+=3){
   a.fromBufferAttribute(p,index?index.getX(i):i).applyMatrix4(matrix)
   b.fromBufferAttribute(p,index?index.getX(i+1):i+1).applyMatrix4(matrix)
   c.fromBufferAttribute(p,index?index.getX(i+2):i+2).applyMatrix4(matrix)
   const x0=clamp(Math.floor((Math.min(a.x,b.x,c.x)-minX)/cell))
   const x1=clamp(Math.floor((Math.max(a.x,b.x,c.x)-minX)/cell))
   const y0=clamp(Math.floor((Math.min(a.y,b.y,c.y)-minY)/cell))
   const y1=clamp(Math.floor((Math.max(a.y,b.y,c.y)-minY)/cell))
   const low=Math.min(a.z,b.z,c.z),high=Math.max(a.z,b.z,c.z)
   for(let y=y0;y<=y1;y++)for(let x=x0;x<=x1;x++){
    const at=y*size+x;front[at]=Math.max(front[at],high);back[at]=Math.min(back[at],low)
   }
  }
 }
 return {cell,bounds(x,y){
  const ix=Math.floor((x-minX)/cell),iy=Math.floor((y-minY)/cell)
  let hi=-Infinity,lo=Infinity
  // A segment shorter than .4 cells shares a conservative neighborhood
  // at both ends, so the interpolated Z also clears crossed cell bounds.
  for(let j=Math.max(0,iy-1);j<=Math.min(size-1,iy+1);j++)
   for(let i=Math.max(0,ix-1);i<=Math.min(size-1,ix+1);i++){
    hi=Math.max(hi,front[j*size+i]);lo=Math.min(lo,back[j*size+i])
   }
  return Number.isFinite(hi)?{front:hi,back:lo}:null
 }}
}
export function clearZ(x:number,y:number,z:number,side:1|-1,envelope:DepthEnvelope,margin=.009){
 const bound=envelope.bounds(x,y)
 return bound?(side===1?Math.max(z,bound.front+margin):Math.min(z,bound.back-margin)):z
}
export function clearancePolyline(a:Vector3,b:Vector3,side:1|-1,envelope:DepthEnvelope){
 const count=Math.max(4,Math.ceil(Math.hypot(b.x-a.x,b.y-a.y)/(envelope.cell*.38)))
 const points:Vector3[]=[]
 // Keep each crossing span on one exterior side: switching sides through
 // an occupied XY span is impossible under the requested Z-only constraint.
 for(let i=0;i<=count;i++){
  const t=i/count,x=a.x+(b.x-a.x)*t,y=a.y+(b.y-a.y)*t
  const z=a.z+(b.z-a.z)*t
  points.push(new Vector3(x,y,clearZ(x,y,z,side,envelope)))
 }
 // Smooth the depth profile, then reapply the conservative bound.
 for(let pass=0;pass<2;pass++){
  const values=points.map((p,i)=>(points[Math.max(0,i-1)].z+2*p.z+points[Math.min(count,i+1)].z)*.25)
  points.forEach((p,i)=>{p.z=clearZ(p.x,p.y,values[i],side,envelope)})
 }
 return points
}
