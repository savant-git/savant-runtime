import { Color, DoubleSide, FrontSide, MeshDepthMaterial, MeshPhysicalMaterial } from "three"

export type ParticleShape="sphere"|"drop"|"shard"|"ring"|"reticle"|"flame"|"leaf"|"flake"|"splinter"|"ribbon"|"spore"|"tile"
type Optics={transmission:number;ior:number;thickness:number;attenuation:string;iridescence:number;sheen:number;anisotropy:number;coat:number;opacity:number}
export type ScenePreset={energy:number;shadow:number;drift:number;tilt:number;glow:number;form:"rect"|"circle"|"ring";width:number;stretch:number}
export type MaterialPreset={
 stroke:{color:string;light:string;width:number;roughness:number;metalness:number;speed:number;power:number};
 scene:ScenePreset;
 id:string;name:string;color:string;accent:string;accent2:string;particle:string
 roughness:number;metalness:number;style:number;relief:number;glow:number;textureScale:number;effect:number
 optics:Optics;shape:ParticleShape;particleScale:number;particleStretch:number;description:string
}
type Definition=[string,string,string,string,string,number,number,ParticleShape,string,Partial<Optics>]
/* Single appearance registry. Motion and interaction are independent of appearance. */
const definitions:Definition[]=[
 [
  "hologram",
  "negative-space interferometer",
  "#102a45",
  "#7afaff",
  "#e5b8ff",
  0.12,
  0,
  "ring",
  "Sweeping interference fields with luminous wave rings.",
  {
   "opacity": 0.55,
   "iridescence": 0.4
  }
 ],
 [
  "cipher",
  "ceramic signal armor",
  "#c9c4b2",
  "#91ff6b",
  "#f3ecc0",
  0.35,
  0.1,
  "reticle",
  "Ivory circuitry, phosphor traces and targeting reticles.",
  {
   "coat": 0.8
  }
 ],
 [
  "crystal",
  "dichroic gel prism",
  "#e6fff4",
  "#9affd8",
  "#ffb7f3",
  0.025,
  0,
  "shard",
  "Clear gel, moving internal bands and dichroic needles.",
  {
   "transmission": 0.95,
   "ior": 1.46,
   "thickness": 0.8,
   "iridescence": 0.8
  }
 ],
 [
  "amethyst",
  "fluorite faultglass",
  "#d9bdff",
  "#904bff",
  "#ffd5fa",
  0.055,
  0,
  "shard",
  "Absorbing violet fault planes and elongated prisms.",
  {
   "transmission": 0.85,
   "ior": 1.58,
   "thickness": 1.4,
   "attenuation": "#6526aa"
  }
 ],
 [
  "basalt",
  "gold-veined tectonite",
  "#18171b",
  "#ffc35e",
  "#fff0b1",
  0.62,
  0.35,
  "splinter",
  "Dark tectonic crust with branching molten gold.",
  {
   "coat": 0.4
  }
 ],
 [
  "fire",
  "arc-plasma enamel",
  "#08192f",
  "#65b7ff",
  "#ffffff",
  0.18,
  0.1,
  "flame",
  "Blue-white electrical turbulence under polished enamel.",
  {
   "coat": 1
  }
 ],
 [
  "obsidian",
  "black-opal anomaly",
  "#090c14",
  "#8afad5",
  "#ea9fff",
  0.055,
  0.2,
  "splinter",
  "Black opal with shifting spectral inclusions.",
  {
   "iridescence": 1,
   "coat": 1
  }
 ],
 [
  "ice",
  "brine cathedral",
  "#c5e9e5",
  "#7ae9ff",
  "#eefaff",
  0.16,
  0,
  "flake",
  "Frozen brine channels and crystalline flakes.",
  {
   "transmission": 0.7,
   "ior": 1.31,
   "thickness": 1.1
  }
 ],
 [
  "white-chrome",
  "magnetic titanium",
  "#dce6f0",
  "#f2fbff",
  "#d7b264",
  0.045,
  1,
  "drop",
  "Anisotropic mirror ripples and liquid metal beads.",
  {
   "anisotropy": 0.65,
   "coat": 1
  }
 ],
 [
  "petroleum",
  "chromatic oil lens",
  "#171126",
  "#d48aff",
  "#69ffcb",
  0.03,
  0.15,
  "drop",
  "Moving thin-film oil contours and glossy droplets.",
  {
   "iridescence": 1,
   "coat": 1
  }
 ],
 [
  "blood",
  "garnet capillary glass",
  "#6a0514",
  "#ff315a",
  "#ffa789",
  0.055,
  0,
  "drop",
  "Deep red absorption with capillary veins.",
  {
   "transmission": 0.72,
   "ior": 1.6,
   "thickness": 1.5,
   "attenuation": "#880b23",
   "coat": 1
  }
 ],
 [
  "bubble",
  "aerogel membrane",
  "#e1f7ff",
  "#ffbaf4",
  "#a0ffe6",
  0.025,
  0,
  "sphere",
  "Light-scattering membranes with pearlescent bubbles.",
  {
   "transmission": 0.85,
   "ior": 1.08,
   "thickness": 0.12,
   "iridescence": 0.7
  }
 ],
 [
  "porcelain",
  "charred porcelain relay",
  "#f2e9d7",
  "#27344a",
  "#d2ac59",
  0.18,
  0,
  "tile",
  "Glazed ivory and dark fractured glaze islands.",
  {
   "coat": 1
  }
 ],
 [
  "mycelium",
  "neural jellyglass",
  "#153b30",
  "#76ffd7",
  "#b4dfff",
  0.12,
  0,
  "spore",
  "Translucent neural channels and luminous spores.",
  {
   "transmission": 0.65,
   "ior": 1.36,
   "thickness": 0.7,
   "attenuation": "#31886b"
  }
 ],
 [
  "wood",
  "fossil amber engine",
  "#b56b23",
  "#ffce79",
  "#59301b",
  0.14,
  0,
  "leaf",
  "Absorbing amber growth rings and fossil leaves.",
  {
   "transmission": 0.55,
   "ior": 1.54,
   "thickness": 1.1,
   "attenuation": "#bb6317",
   "coat": 0.8
  }
 ],
 [
  "carbon",
  "carbon pearl laminate",
  "#171d29",
  "#b7d2ef",
  "#8d6dac",
  0.24,
  0.65,
  "ribbon",
  "Directional laminated fibers and pearl ribbons.",
  {
   "anisotropy": 0.85,
   "iridescence": 0.5,
   "coat": 0.6
  }
 ],
 [
  "stained-glass",
  "fractured cathedral prism",
  "#eedaf4",
  "#ff378b",
  "#5ec7ff",
  0.04,
  0,
  "tile",
  "Refractive multicolored panes and glass tesserae.",
  {
   "transmission": 0.8,
   "ior": 1.62,
   "thickness": 0.45,
   "iridescence": 0.4
  }
 ],
 [
  "ectoplasm",
  "superfluid phantom",
  "#bcf8e3",
  "#a2ffe0",
  "#b5b0ff",
  0.075,
  0,
  "flame",
  "Flowing spectral sheets and elongated fluid wisps.",
  {
   "transmission": 0.7,
   "ior": 1.2,
   "thickness": 0.8,
   "coat": 0.9
  }
 ],
 [
  "verdigris",
  "copper oxidation atlas",
  "#9d6740",
  "#54bbaa",
  "#f1c877",
  0.46,
  0.9,
  "splinter",
  "Copper islands and detailed patina deposits.",
  {
   "coat": 0.25
  }
 ],
 [
  "velvet",
  "nanofiber mourning cloth",
  "#180d24",
  "#9e477e",
  "#c5a5dc",
  0.94,
  0,
  "ribbon",
  "Dense folded fibers and grazing violet sheen.",
  {
   "sheen": 1,
   "anisotropy": 0.35,
   "coat": 0
  }
 ]
]
const defaults:Optics={transmission:0,ior:1.5,thickness:.2,attenuation:"#ffffff",iridescence:0,sheen:0,anisotropy:0,coat:.3,opacity:1}
export const materialPresets:MaterialPreset[]=definitions.map((r,style)=>({
 stroke:{color:["#b8cbe2","#172b1c","#e3fff6","#391456","#8e5922","#d9eaff","#5b375d","#efffff","#29323d","#a67bb9","#27040c","#e7f9ff","#252831","#244d43","#6c3616","#ccd9ea","#292333","#407c6c","#365b4e","#b79ab9"][style],light:r[4],width:.012+(style%3)*.003,roughness:.09+(style%4)*.06,metalness:[.8,.15,.1,.5,.95,.8,.6,.1,1,.6,.15,.1,.2,.25,.2,.85,.2,.1,.9,.1][style],speed:.55+(style%5)*.065,power:1.6+(style%4)*.3},
 scene:{
  energy:[1.6,1.2,1.8,1.55,1.9,2.2,1.45,1.6,2.3,1.85,1.65,1.9,1.3,1.7,1.2,1.6,2,1.55,1.5,1.1][style],
  shadow:[.12,.24,.3,.27,.48,.24,.42,.3,.38,.35,.4,.12,.32,.22,.42,.38,.26,.16,.46,.44][style],
  drift:.45+(style%5)*.13,
  tilt:(style%7-3)*.075,
  glow:[1.7,1.1,.4,.7,1.9,2.4,.25,.75,.45,1.25,.7,1.35,.35,1.8,.2,.3,1.05,1.65,.45,.15][style],
  form:(style%4===0?"ring":style%3===0?"circle":"rect") as ScenePreset["form"],
  width:1.1+(style%4)*.38,
  stretch:.35+(style%5)*.24,
 },
 id:r[0],name:String(style+1).padStart(2,"0")+" · "+r[1],color:r[2],accent:r[3],accent2:r[4],
 particle:style===8?"#eaf0f7":style===10?"#a80718":r[3],roughness:r[5],metalness:r[6],
 shape:r[7],description:r[8],optics:{...defaults,...r[9]},style,effect:style,relief:0,
 glow:[1.4,1.1,.02,.08,2.3,2.8,.01,.08,0,.02,.01,.01,0,1.3,0,0,.08,.7,0,0][style],
 textureScale:1,particleScale:style===11?.065:style===5||style===17?.052:.038,
 particleStretch:style===3?2.2:style===9||style===10?1.6:1,
}))
export const legacyPresetIds:Record<string,string>={
 ivory:"crystal",opal:"bubble",blueprint:"cipher",rust:"blood",enamel:"stained-glass",
 eclipse:"obsidian",honeycomb:"ice",phosphor:"hologram",prism:"crystal",
}
/* Reset all optical channels. Glitch never controls alpha/transmission.
 * Transmission uses opacity=1; only projection and fire use alpha blending. */
export function applyAppearance(m:MeshPhysicalMaterial,p:MaterialPreset,particle=false){
 const o=p.optics
 const signature=[o.transmission>0,o.opacity<1,o.iridescence>0,o.sheen>0,o.anisotropy>0,o.coat>0].join(":")
 m.color.set(particle?p.particle:p.color);m.roughness=p.roughness;m.metalness=p.metalness
 m.transmission=o.transmission;m.ior=o.ior;m.thickness=particle?o.thickness*.12:o.thickness
 m.attenuationColor.set(o.attenuation);m.attenuationDistance=1.2
 m.iridescence=o.iridescence;m.iridescenceIOR=1.3;m.iridescenceThicknessRange=[100,650]
 m.sheen=o.sheen;m.sheenColor.set(p.accent);m.sheenRoughness=.65;m.anisotropy=o.anisotropy
 m.clearcoat=o.coat;m.clearcoatRoughness=.045;m.opacity=o.opacity;m.transparent=o.opacity<1
 m.depthWrite=o.opacity>=1;m.side=particle||o.transmission===0?DoubleSide:FrontSide
 m.envMapIntensity=p.style===1?.25:p.style===19?.6:1.6
 m.emissive.set(particle&&[0,1,4,5,13,17].includes(p.style)?p.accent:"#000000")
 m.emissiveIntensity=particle?p.glow:0
 if(m.userData.savantOptics!==signature){m.userData.savantOptics=signature;m.needsUpdate=true}
}
export type EffectUniforms={
 uSavantTime:{value:number};uSavantGlitch:{value:number};uSavantStyle:{value:number}
 uSavantAccent:{value:Color};uAccent2:{value:Color};uTextureScale:{value:number};uRelief:{value:number};uGlow:{value:number}
}
export const surfaceFields=`
uniform float uSavantTime,uSavantGlitch,uSavantStyle,uTextureScale,uRelief,uGlow;
uniform vec3 uSavantAccent,uAccent2;
varying vec3 vSavantCell;
float hash3(vec3 p){p=fract(p*.1031);p+=dot(p,p.yzx+33.33);return fract((p.x+p.y)*p.z);}
float noise3(vec3 p){
 vec3 i=floor(p),f=fract(p);f=f*f*f*(f*(f*6.0-15.0)+10.0);
 return mix(mix(mix(hash3(i),hash3(i+vec3(1,0,0)),f.x),
 mix(hash3(i+vec3(0,1,0)),hash3(i+vec3(1,1,0)),f.x),f.y),
 mix(mix(hash3(i+vec3(0,0,1)),hash3(i+vec3(1,0,1)),f.x),
 mix(hash3(i+vec3(0,1,1)),hash3(i+vec3(1,1,1)),f.x),f.y),f.z);
}
float wave(float x){return .5+.5*sin(x)*exp(-.5*fwidth(x)*fwidth(x));}
float line(float x,float width){
 float fw=max(fwidth(x),.015);
 return mix(1.0-smoothstep(width,width+fw,abs(sin(x))),width*.637,smoothstep(.35,1.5,fw));
}
vec3 appearance(vec3 p){
 float s=uSavantStyle,t=uSavantTime,n=noise3(p*6.0),b=noise3(p*2.5);
 float pigment=0.0,emission=0.0,rough=0.0;
 if(s<.5){
  float interference=wave(p.y*80.0+sin(p.x*12.0-t)*2.0-t*2.0);
  pigment=interference*.65;emission=.2+line(p.y*9.0-t,.06)+interference*.5;
 }else if(s<1.5){
  float circuits=max(line(p.x*26.0+sin(p.y*8.0),.06),line(p.y*26.0,.04));
  pigment=circuits*.85;emission=circuits*pow(wave(p.y*5.0-t*2.0),12.0);
 }else if(s<2.5){
  pigment=.16*wave(p.y*11.0+p.x*8.0+sin(t*.3));rough=.012*wave(p.z*19.0);
 }else if(s<3.5){
  float planes=wave(p.y*32.0+p.x*14.0+b*2.0);
  pigment=planes*.7;rough=.035*line(p.y*16.0+p.x*7.0,.12);
 }else if(s<4.5){
  float cracks=line(n*19.0+b*7.0,.09);
  pigment=cracks;emission=cracks*(.6+.4*wave(p.y*7.0-t));rough=n*.18;
 }else if(s<5.5){
  float arc=line(p.y*15.0+noise3(p*9.0+vec3(t*.5,-t,0))*12.0,.09);
  pigment=arc*.9;emission=arc*1.5+.08*wave(p.y*20.0-t*5.0);rough=.03*n;
 }else if(s<6.5){
  float inclusions=pow(wave(n*13.0+b*8.0+sin(t*.3)),8.0);
  pigment=inclusions*.65;rough=inclusions*.04;
 }else if(s<7.5){
  float channels=max(line(p.y*21.0+p.x*17.0+n*3.0,.07),line(p.y*21.0-p.x*17.0,.035));
  pigment=channels*.8;rough=channels*.25;
 }else if(s<8.5){
  pigment=.055*wave(p.y*23.0+sin(p.x*8.0+t*.4));rough=.018*wave(p.x*70.0);
 }else if(s<9.5){
  pigment=wave(p.y*9.0+p.x*6.0+noise3(p*4.0+vec3(0,t*.15,0))*9.0)*.4;
  rough=.02*wave(p.y*25.0);
 }else if(s<10.5){
  pigment=line(p.y*17.0+n*8.0+sin(p.x*5.0),.12)*.55;rough=.025*n;
 }else if(s<11.5){
  pigment=.08*wave(p.y*7.0+p.x*3.0+t*.25);rough=.04*noise3(p*17.0);
 }else if(s<12.5){
  pigment=smoothstep(.52,.62,n)*.9;rough=line(n*17.0,.05)*.16;
 }else if(s<13.5){
  float nerves=line(n*17.0+b*9.0,.13);
  pigment=nerves;emission=nerves*(.4+.6*pow(wave(p.y*9.0-t*2.0),4.0));
 }else if(s<14.5){
  pigment=wave(length(p.xz*vec2(1,1.7))*55.0+noise3(p*3.0)*6.0)*.65;
  rough=.04*n;
 }else if(s<15.5){
  float weave=wave((p.x+p.y)*96.0)*wave((p.x-p.y)*96.0);
  pigment=weave*.55;rough=(1.0-weave)*.14;
 }else if(s<16.5){
  pigment=smoothstep(.2,.8,noise3(p*8.0));rough=line(n*19.0,.07)*.3;
 }else if(s<17.5){
  pigment=noise3(p*5.0+vec3(t*.16,-t*.3,0));
  emission=pow(pigment,4.0)*.9;rough=pigment*.06;
 }else if(s<18.5){
  pigment=smoothstep(.38,.6,n*.7+b*.3);rough=pigment*.35;
 }else{
  pigment=wave(p.y*48.0+sin(p.x*8.0)*3.0)*.09;rough=.035*wave(p.x*110.0);
 }
 return vec3(pigment,emission,rough);
}

`
export function installSurface(material:MeshPhysicalMaterial|MeshDepthMaterial,u:EffectUniforms,unit:number){
 material.onBeforeCompile=shader=>{
  Object.assign(shader.uniforms,u,{uSavantUnit:{value:unit}})
  shader.vertexShader=shader.vertexShader.replace("#include <common>",
   "#include <common>\nuniform float uSavantTime,uSavantGlitch,uSavantUnit;\nvarying vec3 vSavantCell;")
   .replace("#include <begin_vertex>",`#include <begin_vertex>
    vSavantCell=position/uSavantUnit;
    float band=floor(vSavantCell.y*64.0);
    float slice=sin(band*19.17+floor(uSavantTime*48.0)*2.4)+.45*sin(band*7.3-floor(uSavantTime*61.0)*3.1);
    transformed.x+=slice*uSavantGlitch*uSavantUnit*.028;
    transformed.z+=sin(band*7.0+floor(uSavantTime*43.0))*uSavantGlitch*uSavantUnit*.018;`)
  if(material instanceof MeshPhysicalMaterial){
   shader.fragmentShader=shader.fragmentShader.replace("#include <common>","#include <common>\n"+surfaceFields)
    .replace("#include <color_fragment>",`#include <color_fragment>
     vec3 coord=vSavantCell;
     // Optical strata flow; solid ceramic, cloth and stone retain their identity.
     if(uSavantStyle>8.5&&uSavantStyle<11.5||uSavantStyle>16.5&&uSavantStyle<17.5)
      coord+=vec3(sin(uSavantTime*.31+coord.y*3.0),cos(uSavantTime*.23+coord.x*4.0),0.0)*.045;
     vec3 surface=appearance(coord);
     vec3 pigment=mix(uAccent2,uSavantAccent,surface.x);
     diffuseColor.rgb=mix(diffuseColor.rgb,pigment,surface.x);
     if(uSavantStyle>15.5&&uSavantStyle<16.5){
      float leading=line(noise3(vSavantCell*8.0)*19.0,.09);
      diffuseColor.rgb=mix(pigment,vec3(.008),leading);
     }`)
    .replace("#include <roughnessmap_fragment>",`#include <roughnessmap_fragment>
     roughnessFactor=clamp(roughnessFactor+surface.z,.018,1.0);`)
    .replace("#include <emissivemap_fragment>",`#include <emissivemap_fragment>
     float rim=pow(1.0-abs(dot(normal,normalize(vViewPosition))),3.0);
     // Two independently moving, narrow highlight bands run over the physical surface.
     // Their energy follows the active material rather than forcing a white outline.
     float azimuth=atan(vSavantCell.y,vSavantCell.x);
     float trace=pow(max(0.0,cos(azimuth-uSavantTime*4.6)),90.0);
     float counterTrace=pow(max(0.0,cos(azimuth+uSavantTime*2.7+1.9)),140.0);
     float axial=pow(max(0.0,cos(vSavantCell.y*3.8-uSavantTime*3.1)),42.0);
     float projection=uSavantStyle<1.5?1.0:0.0;
     float flash=clamp(trace*.8+counterTrace*.65+axial*.35,0.0,1.0);
     totalEmissiveRadiance+=uSavantAccent*(surface.y*uGlow+rim*(flash*.85+projection*.9)+uSavantGlitch*.08);
     totalEmissiveRadiance+=uAccent2*rim*counterTrace*.36;
     // Intentional projection transparency is independent of glitch.
     if(uSavantStyle<1.5)diffuseColor.a*=.45+.55*max(rim,surface.y);`)
  }
 }
 material.customProgramCacheKey=()=>material instanceof MeshPhysicalMaterial?"savant-experimental-optics-027":"savant-chaotic-depth-027"
}
