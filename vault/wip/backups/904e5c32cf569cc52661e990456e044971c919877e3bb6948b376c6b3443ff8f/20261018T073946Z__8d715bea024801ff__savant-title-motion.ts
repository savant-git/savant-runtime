import {MeshPhysicalMaterial} from "three"

export type TitleGlitch={time:{value:number};amount:{value:number}}
const tau=Math.PI*2
const ease=(x:number)=>{x=Math.max(0,Math.min(1,x));return x*x*x*(x*(x*6-15)+10)}
const hash=(x:number)=>{const v=Math.sin(x*127.1+311.7)*43758.5453;return v-Math.floor(v)}

/** Positive, continuous speed; one revolution remains eight seconds. */
export function rotationRate(yaw:number){
 const amount=.28
 return tau/8/Math.sqrt(1-amount*amount)*(1-amount*Math.cos(2*yaw))
}
export function advanceRotation(yaw:number,dt:number,engagement=1){
 const h=Math.max(0,Math.min(dt,.1))*Math.max(0,Math.min(engagement,1))
 const a=rotationRate(yaw),b=rotationRate(yaw+h*a/2)
 const c=rotationRate(yaw+h*b/2),d=rotationRate(yaw+h*c)
 return yaw+h*(a+2*b+2*c+d)/6
}

/** Rare, finite distortion; no opacity changes, strobe, shake or speed boost. */
export function titleGlitch(t:number){
 const cycle=Math.floor(t/32),local=t-cycle*32
 const start=5+hash(cycle+1)*5,duration=.55+hash(cycle+91)*.35
 const elapsed=local-start
 if(elapsed<0||elapsed>duration)return 0
 return ease(elapsed/.09)*ease((duration-elapsed)/.14)
}
export function warpTitlePoint(x:number,y:number,z:number,t:number,amount:number){
 const phase=Math.floor(t*22)*1.618
 return [
  x+amount*(.012*Math.sin(y*24+phase)+.004*Math.sin(y*61-phase)),
  y,
  z+amount*.006*Math.sin(y*37+phase*.73),
 ] as const
}

/** Vertex-only shear with inverse-Jacobian normals; stock PBR fragment shading. */
export function installTitleGlitch(material:MeshPhysicalMaterial,uniforms:TitleGlitch,
 scale=1,centerY=0,depth=1){
 const f=(n:number)=>Number(n).toFixed(9)
 material.onBeforeCompile=shader=>{
  shader.uniforms.savantTitleTime=uniforms.time
  shader.uniforms.savantTitleAmount=uniforms.amount
  shader.vertexShader=shader.vertexShader.replace("#include <common>",
   `#include <common>
uniform float savantTitleTime;
uniform float savantTitleAmount;
vec4 savantWarp(float rawY){
 float y=(rawY-${f(centerY)})*${f(scale)};
 float p=floor(savantTitleTime*22.0)*1.618;
 float a=savantTitleAmount;
 return a*vec4(
  .012*sin(y*24.0+p)+.004*sin(y*61.0-p),
  .006*sin(y*37.0+p*.73),
  .288*cos(y*24.0+p)+.244*cos(y*61.0-p),
  .222*cos(y*37.0+p*.73));
}`)
  shader.vertexShader=shader.vertexShader.replace("#include <beginnormal_vertex>",
   `#include <beginnormal_vertex>
if(savantTitleAmount>.00001){
 vec4 w=savantWarp(position.y);
 objectNormal.y-=w.z*objectNormal.x+w.w/${f(depth)}*objectNormal.z;
}`)
  shader.vertexShader=shader.vertexShader.replace("#include <begin_vertex>",
   `#include <begin_vertex>
if(savantTitleAmount>.00001){
 vec4 w=savantWarp(position.y);
 transformed.x+=w.x/${f(scale)};
 transformed.z+=w.y/${f(scale*depth)};
}`)
 }
 material.customProgramCacheKey=()=>`savant-title-warp-v1:${scale}:${centerY}:${depth}`
 material.needsUpdate=true
}
