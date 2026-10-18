import {Color,MeshPhysicalMaterial} from "three"
import type {ArtDirection} from "./savant-art-direction"
export function artUniforms(){
 return {savantArtKind:{value:-1},savantArtTime:{value:0},savantArtStrength:{value:1},savantArtRelief:{value:0},savantArtGraphic:{value:0},
  savantArtPaper:{value:new Color()},savantArtInk:{value:new Color()},
  savantArtAccent:{value:new Color()},savantArtSecondary:{value:new Color()}}
}
export type ArtUniforms=ReturnType<typeof artUniforms>
export function setArtUniforms(u:ArtUniforms,p:ArtDirection){
 u.savantArtRelief.value=p.relief;u.savantArtGraphic.value=p.graphic;
 u.savantArtKind.value=p.kind;u.savantArtStrength.value=0
 u.savantArtPaper.value.set(p.paper);u.savantArtInk.value.set(p.ink)
 u.savantArtAccent.value.set(p.accent);u.savantArtSecondary.value.set(p.secondary)
}
/** Twenty spatial constructions, sampled with derivative-aware line filtering. */
export const artFieldGLSL=`
float saHash(vec2 p){return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453);}
float saNoise(vec2 p){vec2 i=floor(p),f=fract(p);f=f*f*(3.0-2.0*f);return mix(mix(saHash(i),saHash(i+vec2(1,0)),f.x),mix(saHash(i+vec2(0,1)),saHash(i+vec2(1,1)),f.x),f.y);}
float saLine(float v,float w){return 1.0-smoothstep(w,w+max(fwidth(v),.001),abs(v));}
vec3 saField(vec3 p,float k,float t){
 vec2 q=p.xy;float n=saNoise(q*17.0),g=saNoise(q*73.0),a=0.0,b=0.0,c=0.0;
 if(k<.5)return vec3(0);
 else if(k<1.5){float r=q.y*35.0+sin(q.x*9.0)*3.0;a=pow(.5+.5*cos(r),4.0);b=saLine(sin(q.x*29.0+abs(q.y)*5.0),.08);c=pow(.5+.5*sin(r),8.0);}
 else if(k<2.5){a=saNoise(q*2.3);b=saLine(sin(q.y*45.0+sin(q.x*4.0)*2.0),.04)*.25;c=saNoise(q*9.0)*.4;}
 else if(k<3.5){a=floor((q.y*.3+saNoise(q*2.0))*5.0)/5.0;b=saLine(sin(q.y*49.0+q.x*5.0),.07);}
 else if(k<4.5){vec2 w=q+vec2(sin(q.y*3.0+t*.11)*.11,sin(q.x*5.0+t*.09)*.15);a=.5+.5*sin(w.y*15.0+sin(w.x*8.0)*3.0);b=saLine(sin(w.x*11.0+w.y*5.0),.08);c=.5+.5*cos(w.y*21.0);}
 else if(k<5.5){vec2 v=fract(q*vec2(13,21))-.5;float l=dot(v,v);a=1.0-smoothstep(.03,.26,l);b=saLine(l-.19,.012);c=a;}
 else if(k<6.5){float h=abs(fract(q.x*9.0)-.5)+fract(q.y*9.0)-.5;a=step(0.0,h);b=saLine(h,.045);c=.5+.5*cos(h*6.28);}
 else if(k<7.5){float v=sin(q.x*18.0+sin(q.y*9.0)*3.0);a=pow(max(0.0,1.0-abs(v)),6.0);b=a*(.5+.5*sin(q.y*12.0-t*2.8));c=n*.4;}
 else if(k<8.5){a=saNoise(q*4.0);b=saLine(sin(q.y*32.0+sin(q.x*7.0)),.13);c=saNoise(q*14.0);}
 else if(k<9.5){float v=q.x*210.0+sin(q.y*11.0)*3.0+sin(q.y*29.0);a=.5+.5*sin(v)*exp(-pow(max(fwidth(v),.01),2.0)*.1);b=pow(max(a,0.0),8.0);c=a;}
 else if(k<10.5){a=smoothstep(-.6,.8,q.y)+sin(q.x*3.0)*.12;b=pow(max(0.0,sin(q.x*5.0+q.y*2.0)),6.0)*.18;c=saNoise(q*3.0)*.2;}
 else if(k<11.5){vec2 v=fract(q*vec2(14,19))-.5;float r=length(v+vec2(sin(q.y*31.0)*.12,0));a=saHash(floor(q*vec2(14,19)));b=saLine(r-.23,.025);c=saLine(sin(q.x*91.0+q.y*67.0),.07);}
 else if(k<12.5){vec2 v=fract(q*vec2(17,23))-.5;float r=length(v*vec2(1.6,.7));a=1.0-smoothstep(.08,.45,r);b=saLine(r-.31,.018);c=pow(max(0.0,1.0-r*2.0),2.0);}
 else if(k<13.5){float v=q.x*7.0+q.y*3.0+sin(q.y*6.0)*2.0;a=floor((.5+.5*sin(v))*4.0)/4.0;b=saLine(sin(v),.08);}
 else if(k<14.5){float v=abs(sin(q.x*17.0+sin(q.y*12.0)*3.0));a=saNoise(q*5.0);b=pow(1.0-v,8.0);c=.5+.5*sin(q.y*47.0+sin(q.x*6.0));}
 else if(k<15.5){float h=abs(fract(q.x*11.0)-.5)*2.0+fract(q.y*17.0)-.5;a=n;b=saLine(h-.3,.055);c=max(g,saLine(sin(q.y*79.0-q.x*53.0),.08));}
 else if(k<16.5){vec2 v=fract(vec2(q.x+q.y*.57735,q.x-q.y*.57735)*15.0);a=step(v.x,v.y)*.5+step(v.x+v.y,1.0)*.5;b=max(saLine(v.x-.04,.012),saLine(v.y-.04,.012));c=floor(a*3.0)/3.0;}
 else if(k<17.5){vec2 v=fract(q*vec2(9,13))-.5;float r=length(v*vec2(1.8,.8));a=step(.25,r);b=saLine(r-.3,.026);c=saLine(v.x+sin(v.y*7.0)*.12,.016);}
 else if(k<18.5){a=saNoise(q*5.0);b=pow(.5+.5*sin(q.y*36.0+sin(q.x*12.0)*2.0),6.0);c=g*.55+n*.45;}
 else{a=step(.5,saNoise(q*4.0));b=max(saLine(sin(q.y*89.0+q.x*47.0),.12),saLine(sin(q.x*83.0-q.y*61.0),.06));c=saHash(floor(q*38.0));}
 return clamp(vec3(a,b,c),0.0,1.0);
}
vec3 saDerelict(vec3 r,float t){
 vec2 q=vec2(atan(r.z,r.x),r.y)-vec2(sin(t*.12)*.8,.13);
 float hull=(1.0-smoothstep(1.05,1.12,abs(q.x)))*(1.0-smoothstep(.32,.36,abs(q.y)));
 vec2 v=fract(q*vec2(29,53))-.5;
 float rib=saLine(fract(q.x*51.0)-.5,.07),panel=saHash(floor(q*vec2(29,53)));
 float seam=max(saLine(v.x,.017),saLine(v.y,.017));
 float pipe=saLine(q.y-.11*sin(q.x*13.0),.008);
 float lamp=pow(max(0.0,1.0-length(v*vec2(2,6))),8.0)*step(.7,panel);
 float blink=mix(.2,1.0,step(.7,fract(t*.55)));
 vec3 steel=mix(vec3(.035,.055,.065),vec3(.24,.30,.32),panel)*(.65+rib*.65);
 return hull*(steel*(1.0-seam*.8)+vec3(.4,.62,.7)*pipe*.9+mix(vec3(.9,.5,.16),vec3(.38,.7,1),step(.88,panel))*lamp*blink*3.0);
}
`;
/** Compose after the existing glitch hook; preserve all vertex positions and alpha. */
export function installArtSurface(material:MeshPhysicalMaterial,u:ArtUniforms,scale:number,centerY:number){
 const prior=material.onBeforeCompile,key=material.customProgramCacheKey.bind(material)
 const common=`
uniform float savantArtKind,savantArtTime,savantArtStrength,savantArtRelief,savantArtGraphic;
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
if(savantArtKind>=0.5){
 savantArtField=saField(vSavantArtPoint,savantArtKind,savantArtTime);
 vec3 f=savantArtField;
 vec3 pigment=mix(savantArtPaper,savantArtAccent,f.x*.7);
 pigment=mix(pigment,savantArtSecondary,f.z*.16);
 float ink=f.y*mix(.18,.8,savantArtGraphic);
 pigment=mix(pigment,savantArtInk,ink);
 diffuseColor.rgb=mix(diffuseColor.rgb,pigment,.75*savantArtStrength);
}`)
  shader.fragmentShader=shader.fragmentShader.replace("#include <roughnessmap_fragment>",
   `#include <roughnessmap_fragment>
if(savantArtKind>=0.5){
 float detail=savantArtField.z;
 roughnessFactor=clamp(roughnessFactor+(detail-.5)*.12*savantArtStrength,.08,.95);
}`)
  shader.fragmentShader=shader.fragmentShader.replace("#include <normal_fragment_maps>",
   `#include <normal_fragment_maps>
if(savantArtKind>.5&&savantArtRelief>0.0){
 float height=savantArtField.z*.015*savantArtRelief*savantArtStrength;
 vec3 sx=dFdx(-vViewPosition),sy=dFdy(-vViewPosition);
 vec3 r1=cross(sy,normal),r2=cross(normal,sx);
 float det=dot(sx,r1);
 if(abs(det)>1e-9)normal=normalize(abs(det)*normal-sign(det)*(dFdx(height)*r1+dFdy(height)*r2));
}`)
  shader.fragmentShader=shader.fragmentShader.replace("#include <opaque_fragment>",
   `if(savantArtKind>=0.5){
 vec3 f=savantArtField;
 float facing=abs(dot(normal,normalize(vViewPosition)));
 float ink=1.0-smoothstep(.08,.32,facing);
 float graphic=savantArtGraphic;
 if(graphic>.5){
  float lum=dot(outgoingLight,vec3(.2126,.7152,.0722));
  float level=floor(clamp(lum,0.0,1.0)*4.0+.5)/4.0;
  vec3 posterColor=mix(savantArtInk,mix(savantArtPaper,savantArtAccent,f.x),level);
  outgoingLight=mix(outgoingLight,mix(posterColor,savantArtInk,ink*.85),savantArtStrength*.9);
 }else outgoingLight=mix(outgoingLight,savantArtInk,ink*.17*savantArtStrength);
}
if(savantArtKind>=0.0&&savantArtKind<.5){
 vec3 ray=inverseTransformDirection(reflect(-normalize(vViewPosition),normal),viewMatrix);
 outgoingLight+=saDerelict(ray,savantArtTime)*savantArtStrength*.65;
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
 material.customProgramCacheKey=()=>key()+":savant-art-scenes-20-v3"
 material.needsUpdate=true
}
