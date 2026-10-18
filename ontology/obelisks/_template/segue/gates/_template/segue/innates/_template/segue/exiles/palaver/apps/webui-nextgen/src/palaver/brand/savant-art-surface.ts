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
/** Ten armored constructions with a reference-derived microfinish, sampled with derivative-aware line filtering. */
export const artFieldGLSL=`
float saHash(vec2 p){return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453);}
float saNoise(vec2 p){
 vec2 i=floor(p),v=fract(p);v=v*v*(3.0-2.0*v);
 float n=mix(mix(saHash(i),saHash(i+vec2(1,0)),v.x),mix(saHash(i+vec2(0,1)),saHash(i+vec2(1,1)),v.x),v.y);
 float footprint=max(length(dFdx(p)),length(dFdy(p)));
 return mix(n,.5,smoothstep(.45,1.3,footprint));
}
float saLine(float v,float w){float aa=max(fwidth(v),.0008);return 1.0-smoothstep(w,w+aa,abs(v));}
// Object-space finish stays attached to the metal; only reflected lighting travels.
// The GLB has no UVs. Dominant-plane projection covers the thick sidewalls too.
vec3 saFinish(vec3 p){
 vec3 face=abs(cross(dFdx(p),dFdy(p)));
 vec2 q=face.z>=max(face.x,face.y)?p.xy:(face.x>face.y?p.zy:p.xz);
 float cloud=saNoise(q*5.7)*.65+saNoise(q*17.3+vec2(7.2,3.1))*.35;
 float grain=saNoise(q*112.0+vec2(2.3,9.1));
 float brush=saNoise(q*vec2(18.0,190.0));
 float wear=smoothstep(.48,.76,cloud);
 return vec3(wear,(grain-.5)*.055+(brush-.5)*.035,(cloud-.5)*.00018+(brush-.5)*.000025);
}
vec3 saField(vec3 p,float k,float t){
 vec2 q=p.xy;
 float density=4.5+mod(k,4.0)*.65;
 vec2 uv=vec2(q.x+q.y*.57735027,q.x-q.y*.57735027)*density;
 vec2 cell=fract(uv),s=cell-.5;
 float edge=min(min(cell.x,1.0-cell.x),min(cell.y,1.0-cell.y));
 float bevel=smoothstep(.015,.14,edge);
 float seam=1.0-smoothstep(.012,.012+max(fwidth(edge),.002),edge);
 float facet=smoothstep(-.06,.06,cell.y-cell.x)*.5+(1.0-smoothstep(.94,1.06,cell.x+cell.y))*.5;
 float lens=1.0-smoothstep(.10,.22,length(s*vec2(1.2,.8)));
 float accent=0.0,detail=0.0,height=bevel*.65;
 if(k<.5){accent=facet*.45+lens*.35;detail=saLine(s.x+s.y,.025);height+=lens*.3;}
 else if(k<1.5){float h=max(abs(s.x)*.866+abs(s.y)*.5,abs(s.y));accent=1.0-smoothstep(.23,.31,h);detail=saLine(h-.30,.018);height+=accent*.28;}
 else if(k<2.5){accent=step(.5,fract(uv.x*.5))*facet*.7;detail=saLine(s.y,.035)*bevel;height+=smoothstep(.05,.15,edge)*.25;}
 else if(k<3.5){float rib=.5+.5*cos(s.y*18.85);accent=lens*.65+facet*.2;detail=saLine(sin(s.y*18.85),.1)*bevel;height+=rib*.18*bevel;}
 else if(k<4.5){float crest=abs(s.x)*1.5+s.y;accent=step(.05,crest)*.55;detail=saLine(crest-.05,.025);height+=smoothstep(-.1,.2,crest)*.25*bevel;}
 else if(k<5.5){vec2 sub=fract(cell*3.0)-.5;float r=length(sub);accent=(1.0-smoothstep(.15,.32,r))*.6;detail=saLine(r-.27,.02)*bevel;height+=accent*.22;}
 else if(k<6.5){float rib=abs(s.x)*2.0;accent=facet*.35+pow(1.0-clamp(rib,0.0,1.0),3.0)*.4;detail=saLine(s.x,.03)*bevel;height+=accent*.3;}
 else if(k<7.5){float vent=saLine(s.y+.2,.025)+saLine(s.y,.025)+saLine(s.y-.2,.025);accent=facet*.55;detail=clamp(vent,0.0,1.0)*bevel;height-=detail*.22;}
 else if(k<8.5){float shell=length(s*vec2(1.6,.8));accent=1.0-smoothstep(.18,.39,shell);detail=saLine(shell-.32,.02);height+=accent*.3;}
 else{float diamond=abs(s.x)+abs(s.y);accent=clamp(facet*.4+(1.0-smoothstep(.1,.5,diamond))*.5,0.0,1.0);detail=saLine(diamond-.38,.018);height+=accent*.3;}
 float trace=.78+.22*sin(q.y*8.0-t*.85);
 return clamp(vec3(accent,seam*.55+detail*.35*trace,height),0.0,1.0);
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
vec3 savantFinish=vec3(0.0);
float savantSide=0.0;
if(savantArtKind>=0.0){
 savantArtField=saField(vSavantArtPoint,savantArtKind,savantArtTime);
 vec3 f=savantArtField;
 savantFinish=saFinish(vSavantArtPoint);
 vec3 plane=abs(cross(dFdx(vSavantArtPoint),dFdy(vSavantArtPoint)));
 savantSide=1.0-smoothstep(.35,.85,plane.z/max(length(plane),1e-8));
 vec3 pigment=mix(savantArtPaper,savantArtAccent,f.x*.24);
 pigment=mix(pigment,savantArtSecondary,f.z*.08);
 float ink=f.y*.17;
 pigment=mix(pigment,savantArtInk,ink+.24);
 // Steel face / warm sidewall relationship seen in the supplied title footage.
 vec3 sideMetal=mix(savantArtAccent,savantArtPaper,.24);
 pigment=mix(pigment,sideMetal,savantSide*.56);
 pigment=mix(pigment,mix(savantArtPaper,savantArtInk,.43),savantFinish.x*.14);
 diffuseColor.rgb=mix(diffuseColor.rgb,pigment,.75*savantArtStrength);
}`)
  shader.fragmentShader=shader.fragmentShader.replace("#include <roughnessmap_fragment>",
   `#include <roughnessmap_fragment>
if(savantArtKind>=0.0){
 float detail=savantArtField.z;
 roughnessFactor=clamp(roughnessFactor+((detail-.5)*.035+savantFinish.y+savantFinish.x*.065)*savantArtStrength,.17,.64);
}`)
  shader.fragmentShader=shader.fragmentShader.replace("#include <normal_fragment_maps>",
   `#include <normal_fragment_maps>
if(savantArtKind>=0.0&&savantArtRelief>0.0){
 float height=(savantArtField.z*.003*savantArtRelief+savantFinish.z)*savantArtStrength;
 vec3 sx=dFdx(-vViewPosition),sy=dFdy(-vViewPosition);
 vec3 r1=cross(sy,normal),r2=cross(normal,sx);
 float det=dot(sx,r1);
 if(abs(det)>1e-9)normal=normalize(abs(det)*normal-sign(det)*(dFdx(height)*r1+dFdy(height)*r2));
}`)
  shader.fragmentShader=shader.fragmentShader.replace("#include <opaque_fragment>",
   `if(savantArtKind>=0.0){
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
#include <opaque_fragment>`)
  shader.fragmentShader=shader.fragmentShader.replace("#include <dithering_fragment>",
   `#include <dithering_fragment>
if(savantArtKind>=0.0&&savantTitleAmount>.00001){
 float band=savantBand(vSavantTitleY)*savantTitleAmount;
 vec3 tint=mix(savantArtAccent,savantArtSecondary,step(.5,fract(gl_FragCoord.x*.125)));
 gl_FragColor.rgb=mix(gl_FragColor.rgb,tint,band*.12);
}`)
 }
 material.customProgramCacheKey=()=>key()+":savant-instrument-finish-v2"
 material.needsUpdate=true
}
