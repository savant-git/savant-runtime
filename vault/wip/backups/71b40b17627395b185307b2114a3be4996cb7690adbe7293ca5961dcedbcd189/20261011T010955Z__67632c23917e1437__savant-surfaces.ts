import {Color,DoubleSide,FrontSide,MeshDepthMaterial,MeshPhysicalMaterial} from "three"
export type ParticleShape="sphere"|"drop"|"shard"|"ring"|"reticle"|"flame"|"leaf"|"flake"|"splinter"|"ribbon"|"spore"|"tile"
type Optics={transmission:number;ior:number;thickness:number;attenuation:string;iridescence:number;sheen:number;anisotropy:number;coat:number;opacity:number;dispersion:number;film:number;specular:number;emission:number}
export type WeatherKind="rain"|"lightning"|"fog"|"meteors"|"dust"|"snow"|"sparks"|"spores"
export type ScenePreset={event:WeatherKind;energy:number;shadow:number;drift:number;tilt:number;glow:number;form:"rect"|"circle"|"ring";width:number;stretch:number}
export type MaterialPreset={
 id:string;name:string;color:string;accent:string;accent2:string;particle:string
 roughness:number;metalness:number;style:number;relief:number;glow:number;textureScale:number;effect:number
 optics:Optics;shape:ParticleShape;particleScale:number;particleStretch:number;description:string
 scene:ScenePreset
}
type Definition=[string,string,string,string,string,number,number,ParticleShape,Partial<Optics>]
/* Art-directed optical analogues, not claims of measured rare-substance data.
 * No image maps, procedural surface patterns, bump, displacement or grain. */
const definitions:Definition[]=[
 [
  "hologram",
  "2049 sodium noir",
  "#182027",
  "#ffaf48",
  "#8bdaff",
  0.065,
  0.65,
  "drop",
  {
   "coat": 1,
   "anisotropy": 0.25
  }
 ],
 [
  "cipher",
  "grid lightcycle ceramic",
  "#08161f",
  "#00e9ff",
  "#ffffff",
  0.09,
  0.25,
  "ring",
  {
   "coat": 1,
   "emission": 0.02
  }
 ],
 [
  "crystal",
  "nostromo cold titanium",
  "#65737a",
  "#a5c6cb",
  "#d4f4c4",
  0.26,
  1,
  "splinter",
  {
   "anisotropy": 0.75,
   "coat": 0.2
  }
 ],
 [
  "amethyst",
  "hyperspace ion glass",
  "#b4d7ef",
  "#87c8ff",
  "#fff2d4",
  0.025,
  0,
  "shard",
  {
   "transmission": 0.93,
   "ior": 1.65,
   "dispersion": 0.6,
   "thickness": 0.8
  }
 ],
 [
  "basalt",
  "arrakis dark alloy",
  "#3b2920",
  "#d8a253",
  "#efd8a1",
  0.38,
  0.85,
  "drop",
  {
   "anisotropy": 0.4,
   "coat": 0.1
  }
 ],
 [
  "fire",
  "matrix obsidian code",
  "#050d08",
  "#68ff91",
  "#dcffe5",
  0.035,
  0.5,
  "reticle",
  {
   "coat": 1,
   "iridescence": 0.15
  }
 ],
 [
  "obsidian",
  "tyrell violet lens",
  "#171025",
  "#eb72ef",
  "#79e4ff",
  0.035,
  0,
  "sphere",
  {
   "transmission": 0.5,
   "ior": 1.75,
   "attenuation": "#2f1748",
   "thickness": 1.2,
   "coat": 1
  }
 ],
 [
  "ice",
  "cryostasis sapphire",
  "#cee5f0",
  "#89caff",
  "#ffffff",
  0.055,
  0,
  "flake",
  {
   "transmission": 0.92,
   "ior": 1.4,
   "dispersion": 0.25,
   "thickness": 0.9
  }
 ],
 [
  "white-chrome",
  "liquid hunter mirror",
  "#eef5fb",
  "#ddefff",
  "#ff8f63",
  0.02,
  1,
  "drop",
  {
   "coat": 1
  }
 ],
 [
  "petroleum",
  "quantum interference metal",
  "#8aadc4",
  "#b7ffcc",
  "#f4a2ed",
  0.08,
  0.8,
  "drop",
  {
   "iridescence": 1,
   "film": 470,
   "coat": 1
  }
 ],
 [
  "blood",
  "imperial crimson enamel",
  "#8b0522",
  "#ff395f",
  "#f8d8a9",
  0.07,
  0.15,
  "shard",
  {
   "coat": 1,
   "ior": 1.8
  }
 ],
 [
  "bubble",
  "precog liquid membrane",
  "#c0dff0",
  "#e2fbff",
  "#88cce8",
  0.015,
  0,
  "sphere",
  {
   "transmission": 1,
   "ior": 1.12,
   "thickness": 0.12,
   "iridescence": 0.35
  }
 ],
 [
  "porcelain",
  "lunar machine porcelain",
  "#f5e9de",
  "#ff8b63",
  "#d4ebff",
  0.13,
  0,
  "tile",
  {
   "ior": 1.8,
   "coat": 1
  }
 ],
 [
  "mycelium",
  "pandora bioglass",
  "#28809c",
  "#6bffed",
  "#9ec1ff",
  0.065,
  0,
  "spore",
  {
   "transmission": 0.78,
   "ior": 1.4,
   "attenuation": "#16776a",
   "thickness": 0.7,
   "emission": 0.04
  }
 ],
 [
  "wood",
  "europa amber shield",
  "#ba813e",
  "#efc778",
  "#9de6ff",
  0.12,
  0.35,
  "drop",
  {
   "coat": 1,
   "iridescence": 0.2
  }
 ],
 [
  "carbon",
  "neural ceramic armor",
  "#333850",
  "#ec74cb",
  "#8bd8ff",
  0.19,
  0.6,
  "ribbon",
  {
   "anisotropy": 0.8,
   "coat": 0.8
  }
 ],
 [
  "stained-glass",
  "stellar ruby prism",
  "#f593ad",
  "#ff5692",
  "#66ddff",
  0.04,
  0,
  "shard",
  {
   "transmission": 0.86,
   "ior": 1.7,
   "dispersion": 0.85,
   "thickness": 0.8
  }
 ],
 [
  "ectoplasm",
  "solar lens plasma",
  "#f8c36c",
  "#ffad33",
  "#fff6d9",
  0.075,
  0.1,
  "flame",
  {
   "transmission": 0.35,
   "ior": 1.3,
   "thickness": 0.6,
   "emission": 0.15,
   "coat": 1
  }
 ],
 [
  "verdigris",
  "offworld oxidized copper",
  "#627b64",
  "#b8e295",
  "#edc892",
  0.34,
  0.85,
  "splinter",
  {
   "anisotropy": 0.3,
   "coat": 0.3
  }
 ],
 [
  "velvet",
  "black-hole optical skin",
  "#080711",
  "#ab6ce8",
  "#e33f78",
  0.055,
  0.2,
  "ribbon",
  {
   "transmission": 0.25,
   "ior": 2,
   "thickness": 1.3,
   "attenuation": "#20092d",
   "coat": 1
  }
 ]
]
const defaults:Optics={transmission:0,ior:1.5,thickness:.2,attenuation:"#ffffff",iridescence:0,sheen:0,anisotropy:0,coat:.3,opacity:1,dispersion:0,film:400,specular:1,emission:0}
export const materialPresets:MaterialPreset[]=definitions.map((r,style)=>({
 scene:{event:["rain","lightning","fog","meteors","dust","rain","fog","snow","sparks","spores","meteors","rain","dust","spores","snow","rain","meteors","sparks","dust","lightning"][style] as WeatherKind,
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
 description:["Blade Runner 2049 inspired lighting and smooth physical material.","Tron: Legacy inspired lighting and smooth physical material.","Alien inspired lighting and smooth physical material.","Star Wars inspired lighting and smooth physical material.","Dune inspired lighting and smooth physical material.","The Matrix inspired lighting and smooth physical material.","Blade Runner inspired lighting and smooth physical material.","Interstellar inspired lighting and smooth physical material.","Terminator 2 inspired lighting and smooth physical material.","Annihilation inspired lighting and smooth physical material.","Star Wars inspired lighting and smooth physical material.","Minority Report inspired lighting and smooth physical material.","2001: A Space Odyssey inspired lighting and smooth physical material.","Avatar inspired lighting and smooth physical material.","The Expanse inspired lighting and smooth physical material.","Ghost in the Shell inspired lighting and smooth physical material.","The Fifth Element inspired lighting and smooth physical material.","Sunshine inspired lighting and smooth physical material.","District 9 inspired lighting and smooth physical material.","Event Horizon inspired lighting and smooth physical material."][style],
 particleScale:style===11?.055:.035,particleStretch:style===3?1.8:style===9||style===10?1.4:1,
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
 uSavantTime:{value:number};uSavantGlitch:{value:number};uSavantStyle:{value:number};uInteraction:{value:number};
 uSavantAccent:{value:Color};uAccent2:{value:Color};uTextureScale:{value:number};uRelief:{value:number};uGlow:{value:number}
}
export function installSurface(material:MeshPhysicalMaterial|MeshDepthMaterial,u:EffectUniforms,unit:number){
 material.onBeforeCompile=shader=>{
  Object.assign(shader.uniforms,u,{uSavantUnit:{value:unit}})
  shader.vertexShader=shader.vertexShader.replace("#include <common>",
   "#include <common>\nuniform float uSavantTime,uSavantGlitch,uSavantUnit;")
   .replace("#include <begin_vertex>",`#include <begin_vertex>
    float band=floor(position.y/uSavantUnit*64.0);
    float slice=sin(band*19.17+floor(uSavantTime*48.0)*2.4);
    transformed.x+=slice*uSavantGlitch*uSavantUnit*.017;
    transformed.z+=sin(band*7.0+floor(uSavantTime*43.0))*uSavantGlitch*uSavantUnit*.009;`)
  if(material instanceof MeshPhysicalMaterial){
   shader.fragmentShader=shader.fragmentShader.replace("#include <common>",
    "#include <common>\nuniform float uSavantTime,uInteraction;uniform vec3 uSavantAccent,uAccent2;")
    .replace("#include <emissivemap_fragment>",`#include <emissivemap_fragment>
     // Broad smooth volume-like glow during interaction; no edge mask or outline.
     float glowFacing=.3+.7*max(dot(normal,normalize(vViewPosition)),0.0);
     float heartbeat=.48+.32*sin(uSavantTime*3.4)+.2*sin(uSavantTime*6.8+.7);
     totalEmissiveRadiance+=mix(uSavantAccent,uAccent2,.35)*
      uInteraction*max(heartbeat,.05)*glowFacing*.9;`)
  }
 }
 material.customProgramCacheKey=()=>material instanceof MeshPhysicalMaterial?"savant-film-optics-029":"savant-film-depth-029"
}
