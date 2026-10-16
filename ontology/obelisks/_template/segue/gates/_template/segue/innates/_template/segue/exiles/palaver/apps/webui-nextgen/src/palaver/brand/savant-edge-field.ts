import {BufferAttribute,BufferGeometry,Vector3} from "three"

/* Derived vertex data, never a second mesh or a texture. Source GLB is unchanged.
 * The verified source uses a shallow front cap; projected contours also cover
 * rear and side vertices so the luminous edge survives a full revolution. */
export function withEdgeField(source:BufferGeometry){
 const g=source.clone(),p=g.attributes.position,idx=g.index
 let front=-Infinity,minY=Infinity,maxY=-Infinity
 for(let i=0;i<p.count;i++){front=Math.max(front,p.getZ(i));minY=Math.min(minY,p.getY(i));maxY=Math.max(maxY,p.getY(i))}
 const unit=Math.max(maxY-minY,.001),radius=unit*.025,cell=radius
 const key=(v:Vector3)=>[v.x,v.y,v.z].map(x=>Math.round(x*100000)).join(":")
 const edges=new Map<string,{a:Vector3;b:Vector3;n:number}>()
 for(let i=0;i<(idx?idx.count:p.count);i+=3){
  const points=[0,1,2].map(k=>new Vector3().fromBufferAttribute(p,idx?idx.getX(i+k):i+k))
  if(points.some(v=>v.z<front-.001))continue
  for(let k=0;k<3;k++){
   const a=points[k],b=points[(k+1)%3],id=[key(a),key(b)].sort().join("|"),old=edges.get(id)
   if(old)old.n++;else edges.set(id,{a,b,n:1})
  }
 }
 const boundary=[...edges.values()].filter(e=>e.n===1)
 const adjacent=new Map<string,number[]>()
 boundary.forEach((e,i)=>[e.a,e.b].forEach(v=>adjacent.set(key(v),[...(adjacent.get(key(v))||[]),i])))
 const visited=new Set<number>(),segments:{a:Vector3;b:Vector3;start:number;end:number}[]=[]
 for(let si=0;si<boundary.length;si++){
  if(visited.has(si))continue
  let current=boundary[si].a,at=si
  const loop=[current]
  while(!visited.has(at)){
   visited.add(at);const e=boundary[at]
   current=key(current)===key(e.a)?e.b:e.a;loop.push(current)
   const next=adjacent.get(key(current))?.find(i=>!visited.has(i))
   if(next===undefined)break;at=next
  }
  if(loop.length<4||key(loop[0])!==key(loop[loop.length-1]))continue
  const lengths=loop.slice(1).map((v,i)=>Math.hypot(v.x-loop[i].x,v.y-loop[i].y))
  const total=lengths.reduce((a,b)=>a+b,0)
  if(total<unit*.04)continue
  let distance=0
  lengths.forEach((length,i)=>{
   segments.push({a:loop[i],b:loop[i+1],start:distance/total,end:(distance+length)/total});distance+=length
  })
 }
 const grid=new Map<string,number[]>()
 segments.forEach((e,i)=>{
  for(let x=Math.floor((Math.min(e.a.x,e.b.x)-radius)/cell);x<=Math.floor((Math.max(e.a.x,e.b.x)+radius)/cell);x++)
   for(let y=Math.floor((Math.min(e.a.y,e.b.y)-radius)/cell);y<=Math.floor((Math.max(e.a.y,e.b.y)+radius)/cell);y++){
    const id=x+":"+y;grid.set(id,[...(grid.get(id)||[]),i])
   }
 })
 // Unit-circle phase interpolation avoids a visible seam at the loop origin.
 const data=new Float32Array(p.count*3)
 for(let i=0;i<p.count;i++){
  const x=p.getX(i),y=p.getY(i);let best=radius*radius,phase=0
  for(const j of grid.get(Math.floor(x/cell)+":"+Math.floor(y/cell))||[]){
   const e=segments[j],dx=e.b.x-e.a.x,dy=e.b.y-e.a.y
   const t=Math.max(0,Math.min(1,((x-e.a.x)*dx+(y-e.a.y)*dy)/Math.max(dx*dx+dy*dy,1e-16)))
   const d=(x-e.a.x-dx*t)**2+(y-e.a.y-dy*t)**2
   if(d<best){best=d;phase=(e.start+(e.end-e.start)*t)*Math.PI*2}
  }
  data[i*3]=Math.sqrt(best)/unit;data[i*3+1]=Math.cos(phase);data[i*3+2]=Math.sin(phase)
 }
 g.setAttribute("aSavantEdge",new BufferAttribute(data,3))
 return g
}
