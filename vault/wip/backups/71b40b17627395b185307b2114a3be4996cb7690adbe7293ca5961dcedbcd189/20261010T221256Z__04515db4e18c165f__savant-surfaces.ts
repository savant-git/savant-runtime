import { Color, DoubleSide, FrontSide, MeshDepthMaterial, MeshPhysicalMaterial } from "three"

export type ParticleShape="sphere"|"drop"|"shard"|"ring"|"reticle"|"flame"|"leaf"|"flake"|"splinter"|"ribbon"|"spore"|"tile"
type Optics={transmission:number;ior:number;thickness:number;attenuation:string;iridescence:number;sheen:number;anisotropy:number;coat:number;opacity:number}
export type ScenePreset={energy:number;shadow:number;drift:number;tilt:number;glow:number;form:"rect"|"circle"|"ring";width:number;stretch:number}
export type MaterialPreset={
 scene:ScenePreset;
 id:string;name:string;color:string;accent:string;accent2:string;particle:string
 roughness:number;metalness:number;style:number;relief:number;glow:number;textureScale:number;effect:number
 optics:Optics;shape:ParticleShape;particleScale:number;particleStretch:number;description:string
}
type Definition=[string,string,string,string,string,number,number,ParticleShape,string,Partial<Optics>]
/* Single appearance registry. Motion and interaction are independent of appearance. */
const definitions:Definition[]=[
 ["hologram","spectral projection","#163b57","#70edff","#caabff",.18,0,"ring","Translucent interference sheets and luminous rings.",{opacity:.38}],
 ["cipher","tactical ghost","#091c0e","#b6ff76","#eef4b5",.8,0,"reticle","Phosphor contour display, targeting grid and 3D reticles.",{opacity:.68}],
 ["crystal","clear quartz","#f7fbff","#d7efff","#fff3d2",.025,0,"shard","Clear refractive quartz and crystal needles.",{transmission:1,ior:1.54,thickness:.65}],
 ["amethyst","amethyst reliquary","#e4ccff","#a861ff","#f7d3ff",.045,0,"shard","Violet absorption, mineral zoning and amethyst prisms.",{transmission:.92,ior:1.55,thickness:1.2,attenuation:"#7529b8"}],
 ["basalt","magma fault","#171312","#ff590b","#fff1a8",.78,.05,"shard","Cooled crust with orange fissures and incandescent slag.",{}],
 ["fire","cinder apparition","#421209","#ff740d","#fff4c4",.5,0,"flame","Turbulent emissive combustion and tapered fireballs.",{opacity:.8}],
 ["obsidian","volcanic mirror","#090d15","#8394cc","#eadde8",.06,.38,"splinter","Glossy volcanic flow bands and dark glass splinters.",{coat:1}],
 ["ice","glacial fracture","#c4e8fa","#79caff","#f2fbff",.17,0,"flake","Frosted transmission and six-arm snow crystals.",{transmission:.8,thickness:.9,ior:1.31}],
 ["white-chrome","liquid mercury","#f2f5f9","#f3fcff","#d6b45f",.035,1,"drop","Liquid mirror with silver beads and gold glints.",{coat:1}],
 ["petroleum","oil sacrament","#171422","#e8a7ff","#80f9cf",.045,.25,"drop","Thin-film interference and iridescent oil droplets.",{iridescence:1,coat:1}],
 ["blood","arterial lacquer","#510005","#ff283c","#b90d13",.09,0,"drop","Wet crimson, fluid veins and glossy blood droplets.",{coat:1}],
 ["bubble","soap cathedral","#e7f4ff","#ffb4e8","#a9f7ef",.018,0,"sphere","Thin-film soap membrane and rainbow bubbles.",{transmission:1,ior:1.05,thickness:.008,iridescence:1}],
 ["porcelain","ink porcelain","#f5eee0","#17253d","#c39f55",.2,0,"tile","Ivory ceramic glaze, cobalt veins and ceramic fragments.",{coat:1}],
 ["mycelium","abyssal bloom","#09271f","#69ffd4","#aed8ff",.42,0,"spore","Bioluminescent colonies and luminous spore pods.",{coat:.25}],
 ["wood","petrified heartwood","#302014","#d5a26a","#675041",.72,0,"leaf","Growth rings and curled mineralized wood leaves.",{}],
 ["carbon","carbon shroud","#10141b","#b8c4d5","#55657d",.32,.65,"ribbon","Woven directional carbon and reflective ribbons.",{anisotropy:.85,coat:.45}],
 ["stained-glass","vesper glass","#f4e7ef","#ff3a83","#57baff",.06,0,"tile","Ruby, sapphire and amber panes with dark leading; glass tesserae.",{transmission:.8,thickness:.3,ior:1.52}],
 ["ectoplasm","ectoplasmic veil","#a8dbc9","#acffd9","#b8b1ff",.25,0,"flame","Milky spectral transmission, wisps and ghost flames.",{transmission:.55,thickness:.7}],
 ["verdigris","buried bronze","#795635","#5ab5a4","#ecc778",.5,.85,"splinter","Oxidized bronze and corroded flakes.",{coat:.15}],
 ["velvet","funeral velvet","#170d22","#8a426f","#b493c6",.96,0,"ribbon","Violet velvet, grazing cloth sheen and fabric ribbons.",{sheen:1,coat:0}],
]
const defaults:Optics={transmission:0,ior:1.5,thickness:.2,attenuation:"#ffffff",iridescence:0,sheen:0,anisotropy:0,coat:.3,opacity:1}
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
 if(s<.5){pigment=wave(p.y*100.0-t*2.0)*.7;emission=.18+pigment*.6+line(p.y*7.0-t*.5,.09);}
 else if(s<1.5){
  float grid=max(line(p.x*35.0,.06),line(p.y*35.0,.06));
  pigment=grid*.7;emission=grid*.6+pow(wave(p.y*4.0-t),18.0)*.65;
 }else if(s<2.5){pigment=.025*wave(p.y*11.0+p.x*3.0);}
 else if(s<3.5){pigment=wave(p.y*26.0+p.x*9.0+noise3(p*4.0)*2.0)*.65;rough=.025*wave(p.x*25.0+p.z*14.0);}
 else if(s<4.5){pigment=line(n*13.0+b*9.0,.1);emission=pigment*(.65+.35*wave(p.y*5.0-t*2.0));rough=n*.15;}
 else if(s<5.5){pigment=smoothstep(.2,.8,noise3(p*7.0+vec3(0,-t*1.8,0)));emission=.3+pigment;rough=.2;}
 else if(s<6.5){pigment=wave(p.y*24.0+b*7.0)*.09;rough=.025*n;}
 else if(s<7.5){
  float frost=max(line(p.x*17.0+p.y*13.0+b*3.0,.04),line(p.x*17.0-p.y*13.0+n*2.0,.04));
  pigment=frost*.65;rough=frost*.32;
 }else if(s<8.5){pigment=0.0;}
 else if(s<9.5){pigment=wave(p.y*8.0+p.x*5.0+noise3(p*4.0+vec3(0,t*.12,0))*6.0)*.18;}
 else if(s<10.5){pigment=line(p.y*14.0+noise3(p*5.0+vec3(t*.08,0,0))*7.0,.14)*.22;}
 else if(s<11.5){pigment=0.0;}
 else if(s<12.5){pigment=line(p.x*7.0+p.y*11.0+n*8.0,.05)*.95;rough=.01;}
 else if(s<13.5){pigment=line(n*17.0+b*8.0,.13);emission=pigment*(.65+.35*wave(p.y*8.0-t));}
 else if(s<14.5){pigment=wave(length(p.xz*vec2(1,1.8))*65.0+noise3(p*3.0)*5.0)*.75;rough=n*.15;}
 else if(s<15.5){float weave=wave((p.x+p.y)*100.0)*wave((p.x-p.y)*100.0);pigment=weave*.6;rough=(1.0-weave)*.12;}
 else if(s<16.5){float panes=noise3(p*8.0);pigment=smoothstep(.2,.8,panes);rough=line(panes*19.0,.09)*.5;}
 else if(s<17.5){pigment=noise3(p*5.0+vec3(t*.12,-t*.22,0));emission=pow(pigment,3.0)*.8;}
 else if(s<18.5){pigment=smoothstep(.38,.58,n*.6+b*.4);rough=pigment*.3;}
 else{pigment=wave(p.y*50.0+sin(p.x*8.0))*.045;rough=.02;}
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
    float band=floor(vSavantCell.y*28.0);
    float slice=sin(band*19.17+floor(uSavantTime*30.0)*2.4);
    transformed.x+=slice*uSavantGlitch*uSavantUnit*.014;
    transformed.z+=sin(band*7.0)*uSavantGlitch*uSavantUnit*.006;`)
  if(material instanceof MeshPhysicalMaterial){
   shader.fragmentShader=shader.fragmentShader.replace("#include <common>","#include <common>\n"+surfaceFields)
    .replace("#include <color_fragment>",`#include <color_fragment>
     vec3 surface=appearance(vSavantCell);
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
 material.customProgramCacheKey=()=>material instanceof MeshPhysicalMaterial?"savant-distinct-optics-v6":"savant-closed-glitch-depth-v6"
}
end content
