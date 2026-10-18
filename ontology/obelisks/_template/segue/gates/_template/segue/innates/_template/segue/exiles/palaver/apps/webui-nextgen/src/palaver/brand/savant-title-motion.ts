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
 const start=5+hash(cycle+1)*5,duration=1.05+hash(cycle+91)*.35
 const elapsed=local-start
 if(elapsed<0||elapsed>duration)return 0
 const packet=Math.floor(elapsed*18),stutter=hash(packet+cycle*37)>.72?.35:1
 return ease(elapsed/.09)*ease((duration-elapsed)/.14)*stutter
}
/** Narrow horizontal rolling bands, not whole-logo fragmentation. */
export function scanWarp(y:number,t:number){
 const tick=Math.floor(t*18),packet=tick-(hash(tick+83)>.7?1:0),phase=packet*1.618
 const center=-1.15+(((Math.floor(t*18)/18)*.82)%1+1)%1*2.3
 const second=center>.1?center-.91:center+.91
 let x=0,z=0,dx=0,dz=0
 for(let i=0;i<2;i++){
  const d=y-(i===0?center:second),sigma=i===0?.028:.017
  const g=Math.exp(-.5*d*d/(sigma*sigma)),dg=-d/(sigma*sigma)*g
  const frequency=i===0?180:260,theta=d*frequency+phase+i*2.1
  const sx=Math.sin(theta),cx=Math.cos(theta),sz=Math.sin(theta*.53),cz=Math.cos(theta*.53)
  const amplitude=i===0?.045:.022
  x+=amplitude*g*sx
  dx+=amplitude*(dg*sx+g*frequency*cx)
  z+=.0035*g*sz
  dz+=.0035*(dg*sz+g*frequency*.53*cz)
 }
 return {x,z,dx,dz}
}
export function warpTitlePoint(x:number,y:number,z:number,t:number,amount:number){
 if(amount<=0)return [x,y,z] as const
 const w=scanWarp(y,t)
 return [x+amount*w.x,y,z+amount*w.z] as const
}

/** Narrow-band vertex ripple with corrected normals and a transient RGB-only scan mask. */
export function installTitleGlitch(material:MeshPhysicalMaterial,uniforms:TitleGlitch,
 scale=1,centerY=0,depth=1){
 const f=(n:number)=>Number(n).toFixed(9)
 const scanGLSL=`
uniform float savantTitleTime;
uniform float savantTitleAmount;
float savantBand(float y){
 float center=-1.15+fract(floor(savantTitleTime*18.0)/18.0*.82)*2.3;
 float second=center>.1?center-.91:center+.91;
 float d=(y-center)/.028,e=(y-second)/.017;
 return max(exp(-.5*d*d),exp(-.5*e*e));
}
`
 material.onBeforeCompile=shader=>{
  shader.uniforms.savantTitleTime=uniforms.time
  shader.uniforms.savantTitleAmount=uniforms.amount
  shader.vertexShader=shader.vertexShader.replace("#include <common>",
   `#include <common>
${scanGLSL}
varying float vSavantTitleY;
vec4 savantWarp(float rawY){
 float y=(rawY-(${f(centerY)}))*${f(scale)};
 float tick=floor(savantTitleTime*18.0);
 float h=fract(sin((tick+83.0)*127.1+311.7)*43758.5453);
 float phase=(tick-(h>.7?1.0:0.0))*1.618;
 float center=-1.15+fract(floor(savantTitleTime*18.0)/18.0*.82)*2.3;
 float second=center>.1?center-.91:center+.91;
 vec4 result=vec4(0.0);
 for(int i=0;i<2;i++){
  float d=y-(i==0?center:second);
  float sigma=i==0?.028:.017;
  float frequency=i==0?180.0:260.0;
  float amplitude=i==0?.045:.022;
  float g=exp(-.5*d*d/(sigma*sigma));
  float dg=-d/(sigma*sigma)*g;
  float theta=d*frequency+phase+float(i)*2.1;
  result+=vec4(
   amplitude*g*sin(theta),.0035*g*sin(theta*.53),
   amplitude*(dg*sin(theta)+g*frequency*cos(theta)),
   .0035*(dg*sin(theta*.53)+g*frequency*.53*cos(theta*.53)));
 }
 return savantTitleAmount*result;
}`)
  shader.vertexShader=shader.vertexShader.replace("#include <beginnormal_vertex>",
   `#include <beginnormal_vertex>
if(savantTitleAmount>.00001){
 vec4 w=savantWarp(position.y);
 objectNormal.y-=w.z*objectNormal.x+w.w/${f(depth)}*objectNormal.z;
}`)
  shader.vertexShader=shader.vertexShader.replace("#include <begin_vertex>",
   `#include <begin_vertex>
vSavantTitleY=(position.y-(${f(centerY)}))*${f(scale)};
if(savantTitleAmount>.00001){
 vec4 w=savantWarp(position.y);
 transformed.x+=w.x/${f(scale)};
 transformed.z+=w.y/${f(scale*depth)};
}`)
  shader.fragmentShader=shader.fragmentShader.replace("#include <common>",
   "#include <common>\n"+scanGLSL+"\nvarying float vSavantTitleY;")
  shader.fragmentShader=shader.fragmentShader.replace("#include <dithering_fragment>",
   `#include <dithering_fragment>
if(savantTitleAmount>.00001){
 float band=savantBand(vSavantTitleY)*savantTitleAmount;
 vec2 cell=floor(gl_FragCoord.xy/vec2(3.0,1.0));
 float noise=fract(sin(dot(cell,vec2(127.1,311.7))+
  floor(savantTitleTime*18.0)*19.19)*43758.5453);
 float scan=mix(.72,1.18,step(.46,noise));
 gl_FragColor.rgb*=mix(1.0,scan,band*.8);
}`)
 }
 material.customProgramCacheKey=()=>`savant-title-scan-v4-ripple-stutter:${scale}:${centerY}:${depth}`
 material.needsUpdate=true
}
