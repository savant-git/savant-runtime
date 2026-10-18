import {Color,MeshPhysicalMaterial} from "three"
import type {ArtDirection} from "./savant-art-direction"
export function artUniforms(){
 return {savantArtKind:{value:-1},savantArtTime:{value:0},savantArtStrength:{value:1},
  savantArtPaper:{value:new Color()},savantArtInk:{value:new Color()},
  savantArtAccent:{value:new Color()},savantArtSecondary:{value:new Color()}}
}
export type ArtUniforms=ReturnType<typeof artUniforms>
export function setArtUniforms(u:ArtUniforms,p:ArtDirection){
 u.savantArtKind.value=p.kind;u.savantArtStrength.value=0
 u.savantArtPaper.value.set(p.paper);u.savantArtInk.value.set(p.ink)
 u.savantArtAccent.value.set(p.accent);u.savantArtSecondary.value.set(p.secondary)
}
/** Twenty spatial constructions, sampled with derivative-aware line filtering. */
export const artFieldGLSL=`
float saHash(vec2 p){return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453);}
float saNoise(vec2 p){
 vec2 i=floor(p),f=fract(p);f=f*f*(3.0-2.0*f);
 return mix(mix(saHash(i),saHash(i+vec2(1,0)),f.x),
  mix(saHash(i+vec2(0,1)),saHash(i+vec2(1,1)),f.x),f.y);
}
float saLine(float v,float width){
 float w=max(fwidth(v),.001);
 return 1.0-smoothstep(width,width+w,abs(v));
}
vec3 saField(vec3 p,float k,float t){
 vec2 q=p.xy;float n=saNoise(q*18.0),grain=saNoise(q*95.0);
 float a=0.0,b=0.0,c=0.0;
 if(k<.5){a=saNoise(vec2(q.x*32.0,q.y*7.0));b=saLine(sin(q.y*93.0+q.x*4.0),.18);c=grain;}
 else if(k<1.5){a=saNoise(q*7.0+vec2(sin(q.y*8.0),0));b=saLine(sin(q.x*51.0+q.y*32.0),.22);c=n;}
 else if(k<2.5){a=floor((saNoise(q*2.8)+q.y*.15)*4.0)/4.0;b=saLine(sin(q.y*47.0+q.x*5.0),.09);c=0.0;}
 else if(k<3.5){float r=length(vec2(q.x*1.8,q.y*.75));a=.5+.5*sin(r*95.0+q.y*8.0);b=saLine(sin(r*95.0+q.y*8.0),.2);c=saNoise(q*40.0);}
 else if(k<4.5){a=.5+.5*sin(q.y*4.0+q.x*3.0+p.z*7.0);b=pow(max(0.0,cos(q.x*8.0-q.y*5.0)),8.0);c=grain*.25;}
 else if(k<5.5){a=saNoise(q*5.0+vec2(n*.3));b=smoothstep(.38,.64,saNoise(q*12.0));c=grain;}
 else if(k<6.5){a=step(.52,n+q.x*.15);b=saLine(sin(q.y*53.0-q.x*31.0),.14);c=0.0;}
 else if(k<7.5){a=saNoise(q*8.0+vec2(sin(q.y*7.0)));b=.5+.5*sin(q.y*37.0+sin(q.x*15.0)*3.0);c=grain;}
 else if(k<8.5){vec2 f=fract(vec2(q.x*11.0+q.y*4.0,q.y*13.0));a=step(f.x,f.y);b=saLine(f.x-f.y,.025);c=saHash(floor(q*12.0));}
 else if(k<9.5){a=smoothstep(-.7,.7,q.y)+saNoise(q*13.0)*.12;b=saLine(sin(q.y*23.0),.06);c=grain*.18;}
 else if(k<10.5){a=saNoise(vec2(q.x*22.0,q.y*3.0+t*.05));b=pow(.5+.5*sin(q.x*21.0+q.y*2.0),12.0);c=grain*.3;}
 else if(k<11.5){a=step(.1,sin(q.x*7.0+q.y*3.0));b=saLine(sin(q.x*71.0),.08);c=saHash(floor(q*67.0));}
 else if(k<12.5){vec2 f=fract(vec2(q.x+q.y*.58,q.y-q.x*.58)*12.0);a=step(f.x,f.y)*.5+step(f.x+f.y,1.0)*.5;b=max(saLine(f.x-f.y,.025),saLine(f.x+f.y-1.0,.025));c=saLine(sin((q.x+q.y)*170.0),.16);}
 else if(k<13.5){a=floor((.5+.5*sin(q.x*6.0+sin(q.y*5.0)*2.0))*5.0)/5.0;b=saLine(sin(q.x*6.0+sin(q.y*5.0)*2.0),.1);c=0.0;}
 else if(k<14.5){float streak=saLine(q.x*8.0+sin(q.y*13.0)*.8-floor(q.x*8.0+sin(q.y*13.0)*.8)-.5,.09);a=max(step(.67,n),streak);b=saLine(sin(q.x*19.0+sin(q.y*9.0)*4.0),.13);c=grain;}
 else if(k<15.5){a=saNoise(q*17.0);b=max(saLine(sin(q.x*63.0+q.y*45.0),.2),saLine(sin(q.x*49.0-q.y*55.0),.11));c=step(.58,grain);}
 else if(k<16.5){vec2 s=vec2(abs(q.x),q.y);a=.5+.5*sin(length(s)*31.0+atan(s.y,s.x)*6.0);b=saLine(sin(s.x*19.0+s.y*9.0),.16);c=grain*.2;}
 else if(k<17.5){a=saNoise(q*21.0);b=.5+.5*sin(q.x*170.0+sin(q.y*13.0));c=grain;}
 else if(k<18.5){vec2 f=fract(q*vec2(7.0,11.0));a=saHash(floor(q*vec2(7,11)));b=max(saLine(f.x-.05,.018),saLine(f.y-.05,.018));c=.5+.5*sin(q.y*139.0+q.x*3.0);}
 else{a=step(.49,saNoise(q*4.0)+q.y*.1);b=step(.55,grain)*smoothstep(.3,.65,n);c=grain;}
 return clamp(vec3(a,b,c),0.0,1.0);
}
`;
/** Compose after the existing glitch hook; preserve all vertex positions and alpha. */
export function installArtSurface(material:MeshPhysicalMaterial,u:ArtUniforms,scale:number,centerY:number){
 const prior=material.onBeforeCompile,key=material.customProgramCacheKey.bind(material)
 const common=`
uniform float savantArtKind,savantArtTime,savantArtStrength;
uniform vec3 savantArtPaper,savantArtInk,savantArtAccent,savantArtSecondary;
varying vec3 vSavantArtPoint;
`
 material.onBeforeCompile=(shader,renderer)=>{
  prior.call(material,shader,renderer);Object.assign(shader.uniforms,u)
  shader.vertexShader=shader.vertexShader.replace("#include <common>",
   "#include <common>\nvarying vec3 vSavantArtPoint;")
  shader.vertexShader=shader.vertexShader.replace("#include <begin_vertex>",
   `#include <begin_vertex>
vSavantArtPoint=vec3(position.x,position.y-(${centerY.toFixed(9)}),position.z)*${scale.toFixed(9)};`)
  shader.fragmentShader=shader.fragmentShader.replace("#include <common>",
   "#include <common>\n"+common+artFieldGLSL)
  shader.fragmentShader=shader.fragmentShader.replace("#include <color_fragment>",
   `#include <color_fragment>
vec3 savantArtField=vec3(0.0);
if(savantArtKind>=0.0){
 savantArtField=saField(vSavantArtPoint,savantArtKind,savantArtTime);
 vec3 f=savantArtField;
 vec3 pigment=mix(savantArtPaper,savantArtAccent,f.x*.7);
 pigment=mix(pigment,savantArtSecondary,f.z*.16);
 float ink=f.y*(savantArtKind==2.0||savantArtKind==6.0||savantArtKind==12.0||savantArtKind==19.0?.85:.24);
 pigment=mix(pigment,savantArtInk,ink);
 diffuseColor.rgb=mix(diffuseColor.rgb,pigment,.75*savantArtStrength);
}`)
  shader.fragmentShader=shader.fragmentShader.replace("#include <roughnessmap_fragment>",
   `#include <roughnessmap_fragment>
if(savantArtKind>=0.0){
 float detail=savantArtField.z;
 roughnessFactor=clamp(roughnessFactor+(detail-.5)*.12*savantArtStrength,.08,.95);
}`)
  shader.fragmentShader=shader.fragmentShader.replace("#include <opaque_fragment>",
   `if(savantArtKind>=0.0){
 vec3 f=savantArtField;
 float facing=abs(dot(normal,normalize(vViewPosition)));
 float ink=1.0-smoothstep(.08,.32,facing);
 float graphic=step(abs(savantArtKind-2.0),.1)+step(abs(savantArtKind-6.0),.1)+
  step(abs(savantArtKind-12.0),.1)+step(abs(savantArtKind-13.0),.1)+step(abs(savantArtKind-19.0),.1);
 if(graphic>.5){
  float lum=dot(outgoingLight,vec3(.2126,.7152,.0722));
  float level=floor(clamp(lum,0.0,1.0)*4.0+.5)/4.0;
  vec3 posterColor=mix(savantArtInk,mix(savantArtPaper,savantArtAccent,f.x),level);
  outgoingLight=mix(outgoingLight,mix(posterColor,savantArtInk,ink*.85),savantArtStrength*.9);
 }else outgoingLight=mix(outgoingLight,savantArtInk,ink*.17*savantArtStrength);
}
#include <opaque_fragment>`)
  shader.fragmentShader=shader.fragmentShader.replace("#include <dithering_fragment>",
   `#include <dithering_fragment>
if(savantArtKind>=0.0&&savantTitleAmount>.00001){
 float band=savantBand(vSavantTitleY)*savantTitleAmount;
 vec3 tint=mix(savantArtAccent,savantArtSecondary,step(.5,fract(gl_FragCoord.x*.125)));
 gl_FragColor.rgb=mix(gl_FragColor.rgb,tint,band*.12);
}`)
 }
 material.customProgramCacheKey=()=>key()+":savant-art-scene-v2-es300"
 material.needsUpdate=true
}
