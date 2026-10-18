import {installDynamicReflections} from "./savant-reflections"
import {fieldDeclarations} from "./savant-material-fields"
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
 * No bitmap maps. Smooth analytical fields modulate physical optical response. */
const definitions:Definition[]=[
 ["hologram","varnished illustration porcelain","#e6cdb3","#ffda8b","#a75e3c",0.22,0.15,"tile",{coat: 0.2, anisotropy: 0.0, iridescence: 0.0, sheen: 0.0, emission: 0.0}],
 ["cipher","molten bronze dragon scale","#8d3b21","#ff752f","#e9ba66",0.3,0.85,"shard",{coat: 0.42, anisotropy: 0.18, iridescence: 0.11, sheen: 0.22, emission: 0.014}],
 ["crystal","ink-lined cel enamel","#c7e4c5","#1c4cbd","#fce88d",0.16,0.28,"ribbon",{coat: 0.64, anisotropy: 0.36, iridescence: 0.22, sheen: 0.44, emission: 0.028, transmission: 0.26, ior: 1.52, thickness: 0.65}],
 ["amethyst","ribbed biomechanical graphite","#323a38","#a1c4bb","#a1bcb1",0.4,0.92,"splinter",{coat: 0.86, anisotropy: 0.54, iridescence: 0.33, sheen: 0.0, emission: 0.042}],
 ["basalt","iridescent heroic obsidian","#7b5865","#f8c5a4","#a5b5ed",0.11,0.78,"shard",{coat: 0.2, anisotropy: 0.72, iridescence: 0.0, sheen: 0.22, emission: 0.056}],
 ["fire","mist-veined woodland jade","#678c74","#d4edc3","#86a3c2",0.43,0.08,"leaf",{coat: 0.42, anisotropy: 0.0, iridescence: 0.11, sheen: 0.44, emission: 0.0}],
 ["obsidian","black-ink silver leaf","#171c29","#e8edf9","#8791aa",0.24,0.91,"splinter",{coat: 0.64, anisotropy: 0.18, iridescence: 0.22, sheen: 0.0, emission: 0.014}],
 ["ice","lichen-coated faerie ceramic","#6d8052","#e3d6a0","#c2a0db",0.66,0.13,"spore",{coat: 0.86, anisotropy: 0.36, iridescence: 0.33, sheen: 0.22, emission: 0.028, transmission: 0.26, ior: 1.52, thickness: 0.65}],
 ["white-chrome","fractured chromatic resin","#445be8","#ffcf48","#ff5c98",0.12,0.55,"shard",{coat: 0.2, anisotropy: 0.54, iridescence: 0.0, sheen: 0.44, emission: 0.042}],
 ["petroleum","sandblasted monolithic titanium","#ad8d67","#ffb56c","#83a6bd",0.51,0.91,"tile",{coat: 0.42, anisotropy: 0.72, iridescence: 0.11, sheen: 0.0, emission: 0.056}],
 ["blood","tungsten noir wet asphalt","#222b36","#dbd1ad","#8f9eb4",0.19,0.24,"drop",{coat: 0.64, anisotropy: 0.0, iridescence: 0.22, sheen: 0.22, emission: 0.0}],
 ["bubble","lacquered crimson celluloid","#b52229","#ffe45e","#111111",0.13,0.28,"shard",{coat: 0.86, anisotropy: 0.18, iridescence: 0.33, sheen: 0.44, emission: 0.014}],
 ["porcelain","impossible staircase marble","#dad9d0","#a9a6ff","#7777aa",0.25,0.35,"tile",{coat: 0.2, anisotropy: 0.36, iridescence: 0.0, sheen: 0.0, emission: 0.028}],
 ["mycelium","saturated poster-print enamel","#ec4967","#ffeb38","#267cc5",0.17,0.23,"ribbon",{coat: 0.42, anisotropy: 0.54, iridescence: 0.11, sheen: 0.22, emission: 0.042}],
 ["wood","splattered acrylic chrome","#e1c59b","#ff3a60","#329ac6",0.32,0.58,"spore",{coat: 0.64, anisotropy: 0.72, iridescence: 0.22, sheen: 0.44, emission: 0.056}],
 ["carbon","corroded gothic reliquary iron","#796344","#e0a449","#a93c3a",0.62,0.79,"splinter",{coat: 0.86, anisotropy: 0.0, iridescence: 0.33, sheen: 0.0, emission: 0.0}],
 ["stained-glass","alchemical gilded clay","#aa865b","#f8e7a1","#6c41a8",0.34,0.53,"ring",{coat: 0.2, anisotropy: 0.18, iridescence: 0.0, sheen: 0.22, emission: 0.014}],
 ["ectoplasm","translucent felted opal","#8b4f8b","#d0a3ed","#a3d4e4",0.71,0.05,"spore",{coat: 0.42, anisotropy: 0.36, iridescence: 0.11, sheen: 0.44, emission: 0.028, transmission: 0.48, ior: 1.52, thickness: 0.65}],
 ["verdigris","industrial spaceship hull alloy","#7d8e95","#e8faff","#ffae3a",0.29,0.95,"splinter",{coat: 0.64, anisotropy: 0.54, iridescence: 0.22, sheen: 0.0, emission: 0.042}],
 ["velvet","stenciled concrete and aerosol paint","#777f83","#ff5e39","#1c242d",0.77,0.06,"tile",{coat: 0.86, anisotropy: 0.72, iridescence: 0.33, sheen: 0.22, emission: 0.056}]
]
const sceneNames=["norman rockwell · varnished illustration porcelain", "frank frazetta · molten bronze dragon scale", "moebius · ink-lined cel enamel", "h. r. giger · ribbed biomechanical graphite", "boris vallejo · iridescent heroic obsidian", "alan lee · mist-veined woodland jade", "jae lee · black-ink silver leaf", "brian froud · lichen-coated faerie ceramic", "benedick bana · fractured chromatic resin", "denis villeneuve · sandblasted monolithic titanium", "martin scorsese · tungsten noir wet asphalt", "quentin tarantino · lacquered crimson celluloid", "m. c. escher · impossible staircase marble", "milton glaser · saturated poster-print enamel", "jackson pollock · splattered acrylic chrome", "john blanche · corroded gothic reliquary iron", "alejandro jodorowsky · alchemical gilded clay", "jim henson · translucent felted opal", "ridley scott · industrial spaceship hull alloy", "banksy · stenciled concrete and aerosol paint"]
const defaults:Optics={transmission:0,ior:1.5,thickness:.2,attenuation:"#ffffff",iridescence:0,sheen:0,anisotropy:0,coat:.3,opacity:1,dispersion:0,film:400,specular:1,emission:0}
const baseMaterialPresets:MaterialPreset[]=definitions.map((r,style)=>({
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
 id:r[0],name:String(style+1).padStart(2,"0")+" · "+sceneNames[style],color:r[2],accent:r[3],accent2:r[4],
 particle:r[2],roughness:r[5],metalness:r[6],shape:r[7],optics:{...defaults,...r[8]},
 style,effect:style,relief:.018+(style%6)*.012,textureScale:.8+(style%7)*.35,glow:.8+(style%5)*.26,
 description:sceneNames[style]+": physically based procedural finish with distinctive surface relief, optical response, and coordinated atmosphere.",
 particleScale:style===11?.055:.035,particleStretch:style===3?1.8:style===9||style===10?1.4:1,
}))
/* A derived finish: oxidized copper chemistry over cold titanium structure.
 * Existing preset identities remain available for older callers. */
const copper = baseMaterialPresets.find(p => p.id === "verdigris")!
const titanium = baseMaterialPresets.find(p => p.id === "crystal")!
export const palaverHybrid: MaterialPreset = {
 ...copper,
 id: "palaver-copper-titanium",
 style: 20,
 name: "palaver · oxidized copper / biomechanical titanium",
 color: "#506c68",
 accent: "#8fdbc1",
 accent2: "#b5cad3",
 particle: "#b1e3d5",
 roughness: .19,
 metalness: .92,
 relief: .024,
 textureScale: 1.3,
 glow: 1.4,
 shape: "splinter",
 particleScale: .061,
 particleStretch: 1.7,
 optics: {
  ...titanium.optics,
  anisotropy: .38,
  coat: .48,
  iridescence: .12,
  transmission: 0,
  dispersion: 0,
  emission: .006,
 },
 scene: {
  ...copper.scene,
  event: "lightning",
  energy: 1.3,
  shadow: .38,
  drift: .9,
  glow: .42,
  form: "rect",
  width: 1.75,
  stretch: .62,
 },
 description: "Offworld oxidized copper and biomechanical cold titanium: anisotropic, weathered metallic PBR.",
}
/* The derived hybrid is selectable and is the default; original identities remain stable. */
export const materialPresets: MaterialPreset[] = [...baseMaterialPresets, palaverHybrid]

export const legacyPresetIds:Record<string,string>={ivory:"crystal",opal:"bubble",blueprint:"cipher",rust:"blood",enamel:"stained-glass",eclipse:"obsidian",honeycomb:"ice",phosphor:"hologram",prism:"crystal"}
export function applyAppearance(m:MeshPhysicalMaterial,p:MaterialPreset,particle=false){
 const o=p.optics
 const hybrid=p.style===20
 if(hybrid)m.defines.SAVANT_HYBRID=1;else delete m.defines.SAVANT_HYBRID
 const signature=[hybrid,o.transmission>0,o.iridescence>0,o.sheen>0,o.anisotropy>0,o.coat>0,o.dispersion>0].join(":")
 m.color.set(particle?p.particle:p.color);m.roughness=p.roughness;m.metalness=p.metalness
 m.transmission=o.transmission;m.ior=o.ior;m.thickness=particle?o.thickness*.12:o.thickness
 m.attenuationColor.set(o.attenuation);m.attenuationDistance=1.2;m.dispersion=o.dispersion
 m.iridescence=o.iridescence;m.iridescenceIOR=1.3;m.iridescenceThicknessRange=[o.film,o.film]
 m.sheen=o.sheen;m.sheenColor.set(p.accent);m.sheenRoughness=.45;m.anisotropy=o.anisotropy
 m.clearcoat=o.coat;m.clearcoatRoughness=p.style===20?.09:.04;m.specularIntensity=o.specular
 m.opacity=1;m.transparent=false;m.depthWrite=true
 m.side=FrontSide;m.envMapIntensity=p.scene.energy
 m.emissive.set(p.color);m.emissiveIntensity=o.emission
 // Explicitly remove inherited maps when reusing a material.
 m.map=null;m.normalMap=null;m.bumpMap=null;m.roughnessMap=null;m.metalnessMap=null
 m.displacementMap=null;m.alphaMap=null;m.clearcoatNormalMap=null
 if(m.userData.savantOptics!==signature){m.userData.savantOptics=signature;m.needsUpdate=true}
}
export type EffectUniforms={
 uSavantTime:{value:number};uSavantGlitch:{value:number};uSavantStyle:{value:number};uInteraction:{value:number};
 uSavantAccent:{value:Color};uAccent2:{value:Color};uTextureScale:{value:number};uRelief:{value:number};uGlow:{value:number};uEvent:{value:number};uEventProgress:{value:number}
}
export function installSurface(material:MeshPhysicalMaterial|MeshDepthMaterial,u:EffectUniforms,unit:number){
 material.onBeforeCompile=shader=>{
  Object.assign(shader.uniforms,u,{uSavantUnit:{value:unit}})
  shader.vertexShader=shader.vertexShader.replace("#include <common>",
   "#include <common>\nuniform float uSavantTime,uSavantGlitch,uSavantUnit,uSavantStyle,uEvent;varying vec3 vFieldPoint;")
   .replace("#include <begin_vertex>",`#include <begin_vertex>
    vFieldPoint=position/uSavantUnit;
    // Preserve the original GLB silhouette for every preset.
    // Material-specific detail remains in fragment shading only.
    if(uSavantGlitch>.0001){
    float band=floor(position.y/uSavantUnit*64.0);
    float slice=sin(band*19.17+floor(uSavantTime*48.0)*2.4);
    transformed.x+=slice*uSavantGlitch*uSavantUnit*.017;
    transformed.z+=sin(band*7.0+floor(uSavantTime*43.0))*uSavantGlitch*uSavantUnit*.009;
    }`)
  if(material instanceof MeshPhysicalMaterial){
   shader.fragmentShader=shader.fragmentShader.replace("#include <common>",
    "#include <common>\nuniform float uInteraction;\n"+fieldDeclarations)
    .replace("#include <color_fragment>",`#include <color_fragment>
     vec4 sf=surfaceField(vFieldPoint);
     float tintStrength=uSavantStyle>9.5&&uSavantStyle<10.5?.75:.16;
     diffuseColor.rgb=mix(diffuseColor.rgb,mix(uSavantAccent,uAccent2,sf.x),sf.x*tintStrength);
     if(uSavantStyle>6.5&&uSavantStyle<7.5)
      diffuseColor.rgb=mix(diffuseColor.rgb,vec3(.72,.9,1.0),uEvent*.75);
    `)
    .replace("#include <roughnessmap_fragment>",`#include <roughnessmap_fragment>
     roughnessFactor=clamp(roughnessFactor+sf.y,.018,.85);
    `)
    .replace("#include <normal_fragment_begin>",`#include <normal_fragment_begin>
     vec3 fieldDx=dFdx(-vViewPosition),fieldDy=dFdy(-vViewPosition);
     float relief=sf.x*.00012;
     vec3 grad=cross(fieldDy,normal)*dFdx(relief)+cross(normal,fieldDx)*dFdy(relief);
     normal=normalize(normal-grad/max(abs(dot(fieldDx,cross(fieldDy,normal))),.00001));
    `)
    .replace("#include <emissivemap_fragment>",`#include <emissivemap_fragment>
     totalEmissiveRadiance+=mix(uSavantAccent,uAccent2,sf.x)*sf.z;
     // Broad smooth volume-like glow during interaction; no edge mask or outline.
     float glowFacing=.3+.7*max(dot(normal,normalize(vViewPosition)),0.0);
     float heartbeat=.48+.32*sin(uSavantTime*3.4)+.2*sin(uSavantTime*6.8+.7);
     totalEmissiveRadiance+=mix(uSavantAccent,uAccent2,.35)*
      uInteraction*max(heartbeat,.05)*glowFacing*.9;`)
  }
 }
 material.customProgramCacheKey=()=>material instanceof MeshPhysicalMaterial?"savant-smooth-copper-1":"savant-cinematic-depth-068"
 if(material instanceof MeshPhysicalMaterial)installDynamicReflections(material,u.uSavantTime)
}
