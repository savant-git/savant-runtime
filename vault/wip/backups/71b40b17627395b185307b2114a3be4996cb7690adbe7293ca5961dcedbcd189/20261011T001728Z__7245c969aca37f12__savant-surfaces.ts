import {Color,DoubleSide,FrontSide,MeshDepthMaterial,MeshPhysicalMaterial} from "three"
export type ParticleShape="sphere"|"drop"|"shard"|"ring"|"reticle"|"flame"|"leaf"|"flake"|"splinter"|"ribbon"|"spore"|"tile"
type Optics={transmission:number;ior:number;thickness:number;attenuation:string;iridescence:number;sheen:number;anisotropy:number;coat:number;opacity:number;dispersion:number;film:number;specular:number;emission:number}
export type ScenePreset={energy:number;shadow:number;drift:number;tilt:number;glow:number;form:"rect"|"circle"|"ring";width:number;stretch:number}
export type MaterialPreset={
 id:string;name:string;color:string;accent:string;accent2:string;particle:string
 roughness:number;metalness:number;style:number;relief:number;glow:number;textureScale:number;effect:number
 optics:Optics;shape:ParticleShape;particleScale:number;particleStretch:number;description:string
 scene:ScenePreset;stroke:{color:string;light:string;width:number;roughness:number;metalness:number;speed:number;power:number}
}
type Definition=[string,string,string,string,string,number,number,ParticleShape,Partial<Optics>]
/* Art-directed optical analogues, not claims of measured rare-substance data.
 * No image maps, procedural surface patterns, bump, displacement or grain. */
const definitions:Definition[]=[
 [
  "hologram",
  "ionized sapphire veil",
  "#b8ebff",
  "#56e5ff",
  "#d3a4ff",
  0.025,
  0,
  "ring",
  {
   "transmission": 0.94,
   "ior": 1.08,
   "dispersion": 0.8,
   "iridescence": 0.6,
   "thickness": 0.1
  }
 ],
 [
  "cipher",
  "black diamond electrolyte",
  "#12191c",
  "#bfff66",
  "#f3ffd8",
  0.035,
  0,
  "reticle",
  {
   "transmission": 0.72,
   "ior": 2.2,
   "dispersion": 0.9,
   "thickness": 0.85,
   "attenuation": "#344532",
   "coat": 1
  }
 ],
 [
  "crystal",
  "achromatic diamond vacuum",
  "#ffffff",
  "#c6efff",
  "#ffe7b0",
  0.015,
  0,
  "shard",
  {
   "transmission": 1,
   "ior": 2.3,
   "dispersion": 1,
   "thickness": 0.7
  }
 ],
 [
  "amethyst",
  "alexandrite eclipse",
  "#936894",
  "#95ffc4",
  "#ee8cff",
  0.06,
  0,
  "shard",
  {
   "transmission": 0.88,
   "ior": 1.75,
   "dispersion": 0.6,
   "thickness": 1.3,
   "attenuation": "#753460",
   "iridescence": 0.8
  }
 ],
 [
  "basalt",
  "liquid ruthenium",
  "#42414b",
  "#dcb36a",
  "#d5dcf2",
  0.09,
  1,
  "drop",
  {
   "coat": 1,
   "anisotropy": 0.6
  }
 ],
 [
  "fire",
  "cerium plasma enamel",
  "#fb5a08",
  "#ffa12e",
  "#fff3d8",
  0.035,
  0.12,
  "flame",
  {
   "coat": 1,
   "specular": 1,
   "emission": 0.5
  }
 ],
 [
  "obsidian",
  "violet obsidian lens",
  "#100b20",
  "#ab79ff",
  "#ecd0ff",
  0.018,
  0,
  "splinter",
  {
   "transmission": 0.65,
   "ior": 1.9,
   "attenuation": "#280d49",
   "thickness": 1.5,
   "coat": 1
  }
 ],
 [
  "ice",
  "supercritical cyan gel",
  "#c4fff1",
  "#69ffda",
  "#ccedff",
  0.2,
  0,
  "sphere",
  {
   "transmission": 0.92,
   "ior": 1.12,
   "thickness": 1.7,
   "attenuation": "#7bdec7",
   "dispersion": 0.2
  }
 ],
 [
  "white-chrome",
  "white iridium mirror",
  "#f6f8ff",
  "#ffffff",
  "#d6b45f",
  0.018,
  1,
  "drop",
  {
   "coat": 1,
   "anisotropy": 0.15
  }
 ],
 [
  "petroleum",
  "dichroic liquid bismuth",
  "#d7accb",
  "#ff7ac2",
  "#6affd3",
  0.055,
  0.92,
  "drop",
  {
   "iridescence": 1,
   "film": 520,
   "coat": 1,
   "anisotropy": 0.45
  }
 ],
 [
  "blood",
  "ruby superfluid",
  "#9b001e",
  "#ff164f",
  "#ffb999",
  0.024,
  0,
  "drop",
  {
   "transmission": 0.86,
   "ior": 1.77,
   "thickness": 1.1,
   "attenuation": "#a00123",
   "dispersion": 0.4
  }
 ],
 [
  "bubble",
  "soap-film vacuum",
  "#f8fffc",
  "#f9adff",
  "#94ffe6",
  0.012,
  0,
  "sphere",
  {
   "transmission": 1,
   "ior": 1.025,
   "thickness": 0.012,
   "iridescence": 1,
   "film": 260
  }
 ],
 [
  "porcelain",
  "zirconia pearl ceramic",
  "#f7eee2",
  "#eccb87",
  "#8ab7d0",
  0.12,
  0,
  "tile",
  {
   "ior": 2.12,
   "coat": 1,
   "iridescence": 0.2,
   "film": 180
  }
 ],
 [
  "mycelium",
  "uranium-green optical glass",
  "#b9ff43",
  "#87ff12",
  "#eeffd2",
  0.045,
  0,
  "spore",
  {
   "transmission": 0.8,
   "ior": 1.65,
   "thickness": 0.8,
   "attenuation": "#69a717",
   "emission": 0.12
  }
 ],
 [
  "wood",
  "cognac amber condensate",
  "#e19936",
  "#ffc666",
  "#8e4217",
  0.07,
  0,
  "drop",
  {
   "transmission": 0.9,
   "ior": 1.54,
   "thickness": 1.5,
   "attenuation": "#ba5b16",
   "dispersion": 0.12
  }
 ],
 [
  "carbon",
  "anisotropic osmium",
  "#223048",
  "#8dbbff",
  "#d5c3ef",
  0.22,
  1,
  "ribbon",
  {
   "anisotropy": 1,
   "coat": 0.7
  }
 ],
 [
  "stained-glass",
  "pink spinel prism",
  "#ffadc9",
  "#ff397c",
  "#ffeaf0",
  0.025,
  0,
  "shard",
  {
   "transmission": 0.96,
   "ior": 1.72,
   "thickness": 0.65,
   "attenuation": "#db416c",
   "dispersion": 0.85,
   "coat": 0.7
  }
 ],
 [
  "ectoplasm",
  "opalescent superfluid",
  "#cbdaf1",
  "#a2ffdf",
  "#b7a0ff",
  0.24,
  0,
  "sphere",
  {
   "transmission": 0.6,
   "ior": 1.33,
   "thickness": 1.6,
   "iridescence": 1,
   "film": 380,
   "sheen": 0.25
  }
 ],
 [
  "verdigris",
  "rose-gold interference alloy",
  "#f1bda4",
  "#ffb283",
  "#6affe0",
  0.08,
  1,
  "splinter",
  {
   "iridescence": 0.7,
   "film": 340,
   "coat": 1,
   "anisotropy": 0.35
  }
 ],
 [
  "velvet",
  "absorptive violet satin",
  "#17091e",
  "#b16b9f",
  "#d5b9ed",
  0.8,
  0,
  "ribbon",
  {
   "sheen": 1,
   "anisotropy": 0.7,
   "coat": 0,
   "specular": 0.35
  }
 ]
]
const defaults:Optics={transmission:0,ior:1.5,thickness:.2,attenuation:"#ffffff",iridescence:0,sheen:0,anisotropy:0,coat:.3,opacity:1,dispersion:0,film:400,specular:1,emission:0}
export const materialPresets:MaterialPreset[]=definitions.map((r,style)=>({
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
 particle:r[2],roughness:r[5],metalness:r[6],shape:r[7],optics:{...defaults,...r[8]},
 style,effect:style,relief:0,textureScale:1,glow:1.7,
 description:r[1]+" — smooth layered PBR with matching physical particles.",
 particleScale:style===11?.055:.035,particleStretch:style===3?1.8:style===9||style===10?1.4:1,
 // Legacy name retained for the studio palette only; no separate stroke mesh.
 stroke:{color:r[2],light:r[4],width:0,roughness:r[5],metalness:r[6],speed:.68,power:1.7},
}))
export const legacyPresetIds:Record<string,string>={ivory:"crystal",opal:"bubble",blueprint:"cipher",rust:"blood",enamel:"stained-glass",eclipse:"obsidian",honeycomb:"ice",phosphor:"hologram",prism:"crystal"}
export function applyAppearance(m:MeshPhysicalMaterial,p:MaterialPreset,particle=false){
 const o=p.optics
 const signature=[o.transmission>0,o.iridescence>0,o.sheen>0,o.anisotropy>0,o.coat>0,o.dispersion>0].join(":")
 m.color.set(particle?p.particle:p.color);m.roughness=p.roughness;m.metalness=p.metalness
 m.transmission=o.transmission;m.ior=o.ior;m.thickness=particle?o.thickness*.12:o.thickness
 m.attenuationColor.set(o.attenuation);m.attenuationDistance=1.2;m.dispersion=o.dispersion
 m.iridescence=o.iridescence;m.iridescenceIOR=1.3;m.iridescenceThicknessRange=[o.film,o.film]
 m.sheen=o.sheen;m.sheenColor.set(p.accent);m.sheenRoughness=.45;m.anisotropy=o.anisotropy
 m.clearcoat=o.coat;m.clearcoatRoughness=.025;m.specularIntensity=o.specular
 m.opacity=1;m.transparent=false;m.depthWrite=true
 m.side=o.transmission>0?FrontSide:DoubleSide;m.envMapIntensity=p.scene.energy
 m.emissive.set(p.color);m.emissiveIntensity=o.emission
 // Explicitly remove inherited maps when reusing a material.
 m.map=null;m.normalMap=null;m.bumpMap=null;m.roughnessMap=null;m.metalnessMap=null
 m.displacementMap=null;m.alphaMap=null;m.clearcoatNormalMap=null
 if(m.userData.savantOptics!==signature){m.userData.savantOptics=signature;m.needsUpdate=true}
}
export type EffectUniforms={
 uSavantTime:{value:number};uSavantGlitch:{value:number};uSavantStyle:{value:number};
 uSavantAccent:{value:Color};uAccent2:{value:Color};uTextureScale:{value:number};uRelief:{value:number};uGlow:{value:number}
}
export function installSurface(material:MeshPhysicalMaterial|MeshDepthMaterial,u:EffectUniforms,unit:number){
 material.onBeforeCompile=shader=>{
  Object.assign(shader.uniforms,u,{uSavantUnit:{value:unit}})
  shader.vertexShader=shader.vertexShader.replace("#include <common>",
   "#include <common>\nuniform float uSavantTime,uSavantGlitch,uSavantUnit;attribute vec3 aSavantEdge;varying vec3 vSavantEdge;")
   .replace("#include <begin_vertex>",`#include <begin_vertex>
    vSavantEdge=aSavantEdge;
    float band=floor(position.y/uSavantUnit*64.0);
    float slice=sin(band*19.17+floor(uSavantTime*48.0)*2.4);
    transformed.x+=slice*uSavantGlitch*uSavantUnit*.017;
    transformed.z+=sin(band*7.0+floor(uSavantTime*43.0))*uSavantGlitch*uSavantUnit*.009;`)
  if(material instanceof MeshPhysicalMaterial){
   shader.fragmentShader=shader.fragmentShader.replace("#include <common>",
    "#include <common>\nuniform float uSavantTime,uGlow;uniform vec3 uSavantAccent,uAccent2;varying vec3 vSavantEdge;")
    .replace("#include <color_fragment>",`#include <color_fragment>
     float edgeDistance=vSavantEdge.x;
     float edgeAA=max(fwidth(edgeDistance),.0002);
     float edgeBand=1.0-smoothstep(.005,.008+edgeAA,edgeDistance);
     diffuseColor.rgb=mix(diffuseColor.rgb,uSavantAccent,edgeBand*.65);`)
    .replace("#include <roughnessmap_fragment>",`#include <roughnessmap_fragment>
     roughnessFactor=mix(roughnessFactor,.055,edgeBand);`)
    .replace("#include <emissivemap_fragment>",`#include <emissivemap_fragment>
     float arc=atan(vSavantEdge.z,vSavantEdge.y)/6.2831853;
     float phase=fract(arc-uSavantTime*.68);
     float distanceToPulse=min(phase,1.0-phase);
     float pulse=exp(-distanceToPulse*distanceToPulse*1400.0);
     float wake=pow(1.0-phase,17.0)*.3;
     float core=1.0-smoothstep(.0015,.0045+edgeAA,edgeDistance);
     // Emission is confined to the inlaid edge, never a floating border.
     totalEmissiveRadiance+=uSavantAccent*edgeBand*(.18+.06*sin(uSavantTime*2.0));
     totalEmissiveRadiance+=uAccent2*core*(pulse+wake)*uGlow*2.8;`)
  }
 }
 material.customProgramCacheKey=()=>material instanceof MeshPhysicalMaterial?"savant-inlaid-optics-028":"savant-inlaid-depth-028"
}
