import {BufferGeometry} from "three"

/* Conservative derived cleanup: remove invalid zero-area faces only.
 * Existing UV seams, normals, groups and vertex addressability remain intact. */
export function cleanLogoGeometry(source:BufferGeometry){
 const g=source.clone(),p=g.attributes.position,index=g.index
 if(!p||p.itemSize!==3)throw new Error("savant logo requires three-component positions")
 g.computeBoundingBox()
 const size=g.boundingBox!.max.clone().sub(g.boundingBox!.min)
 const scale=Math.max(size.x,size.y,size.z,1e-6)
 const threshold=Math.pow(scale,4)*1e-24
 const count=index?index.count:p.count
 if(count%3!==0)throw new Error("savant logo has incomplete triangles")
 const ids:number[]=[]
 const oldGroups=g.groups.map(group=>({...group})),groups:{start:number;count:number;materialIndex:number}[]=[]
 const process=(start:number,end:number,materialIndex:number)=>{
  const first=ids.length
  for(let i=start;i<end;i+=3){
   const a=index?index.getX(i):i,b=index?index.getX(i+1):i+1,c=index?index.getX(i+2):i+2
   if([a,b,c].some(v=>!Number.isInteger(v)||v<0||v>=p.count))throw new Error("invalid savant logo index")
   const ax=p.getX(a),ay=p.getY(a),az=p.getZ(a)
   const ux=p.getX(b)-ax,uy=p.getY(b)-ay,uz=p.getZ(b)-az
   const vx=p.getX(c)-ax,vy=p.getY(c)-ay,vz=p.getZ(c)-az
   const nx=uy*vz-uz*vy,ny=uz*vx-ux*vz,nz=ux*vy-uy*vx
   const area=nx*nx+ny*ny+nz*nz
   if(!Number.isFinite(area))throw new Error("non-finite savant geometry")
   if(area>threshold)ids.push(a,b,c)
  }
  if(ids.length>first)groups.push({start:first,count:ids.length-first,materialIndex})
 }
 if(oldGroups.length)for(const group of oldGroups)process(group.start,group.start+group.count,0)
 else process(0,count,0)
 if(!ids.length)throw new Error("savant logo has no valid faces")
 g.setIndex(ids);g.clearGroups()
 // All faces share one material regardless of source primitive groups.
 g.addGroup(0,ids.length,0);g.setDrawRange(0,ids.length)
 if(!g.attributes.normal)g.computeVertexNormals()
 g.computeBoundingBox();g.computeBoundingSphere()
 return g
}
