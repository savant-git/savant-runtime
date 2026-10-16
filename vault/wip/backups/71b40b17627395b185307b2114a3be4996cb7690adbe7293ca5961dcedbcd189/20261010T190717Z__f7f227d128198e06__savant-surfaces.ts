import { Color, MeshDepthMaterial, MeshPhysicalMaterial } from "three"

export type MaterialPreset = {
  id: string; name: string; color: string; accent: string; accent2: string
  particle: string; roughness: number; metalness: number; style: number
  relief: number; glow: number; textureScale: number; effect: number
}
/* One appearance registry; timing and interaction are deliberately independent. */
const rows = [
 ["white-chrome","01 · fractured reliquary","#9eaab5","#d6b45f","#eef6ff",.09,1,.035,.16,17,0],
 ["porcelain","02 · ink-veined porcelain","#e6ded0","#ff2f9d","#10151c",.25,.04,.05,.06,12,1],
 ["basalt","03 · wounded basalt","#16191d","#ee7950","#d6b45f",.72,.12,.09,.72,9,2],
 ["velvet","04 · velvet interference","#28182b","#ba719b","#c9c1df",.94,.02,.025,.14,45,3],
 ["ivory","05 · fossil cathedral","#d5c6a7","#9d7831","#f1e5c7",.52,.02,.045,.04,16,4],
 ["mycelium","06 · nocturnal mycelium","#102b29","#8fcab8","#d6b45f",.38,.06,.055,.65,19,5],
 ["opal","07 · opal diffraction","#abb4ca","#ff2f9d","#b7ead7",.18,.3,.015,.18,13,6],
 ["cipher","08 · cipher membrane","#15202b","#d6b45f","#86bfcd",.3,.5,.025,.65,24,7],
 ["verdigris","09 · weathered oracle","#356763","#d6b45f","#a55837",.63,.62,.07,.03,21,8],
 ["petroleum","10 · petroleum hymn","#151322","#a983bf","#d6b45f",.055,.7,.025,.12,8,9],
 ["wood","11 · petrified blackwood","#291f1b","#b4936a","#e0ccb0",.57,.01,.085,.04,30,10],
 ["carbon","12 · carbon liturgy","#181d23","#9aacbc","#d6b45f",.42,.5,.065,.05,55,11],
 ["amethyst","13 · amethyst fracture","#51405f","#c8a7e4","#d6b45f",.14,.18,.055,.25,12,12],
 ["blueprint","14 · spectral architecture","#101b26","#7da9bc","#e5ddd1",.35,.35,.025,.55,22,13],
 ["rust","15 · sacrificial patina","#613f30","#d6b45f","#8e9c8e",.88,.22,.095,.02,18,14],
 ["enamel","16 · orbital enamel","#401b30","#ff2f9d","#f1e5c7",.12,.08,.02,.13,14,15],
 ["eclipse","17 · eclipse lamellae","#111318","#a1a9ba","#d6b45f",.6,.15,.07,.2,38,16],
 ["honeycomb","18 · gilded ossuary","#252117","#d6b45f","#eae0c4",.28,.8,.08,.25,23,17],
 ["phosphor","19 · phosphor revenant","#13221e","#a7d3bb","#d6b45f",.4,.08,.02,.8,46,18],
 ["prism","20 · prism topography","#9aabb9","#ff2f9d","#d6b45f",.17,.45,.04,.3,20,19],
] as const
export const materialPresets: MaterialPreset[] = rows.map((r, style) => ({
 id:r[0], name:r[1], color:r[2], accent:r[3], accent2:r[4],
 particle: style === 0 ? "#dce6ef" : r[4],
 roughness:r[5], metalness:r[6], relief:r[7], glow:r[8], textureScale:r[9],
 effect:r[10], style,
}))
export type EffectUniforms = {
 uSavantTime:{value:number}; uSavantGlitch:{value:number}
 uSavantStyle:{value:number}; uSavantAccent:{value:Color}
 uAccent2:{value:Color}; uTextureScale:{value:number}
 uRelief:{value:number}; uGlow:{value:number}
}
export const surfaceFields = `
uniform float uSavantTime, uSavantGlitch, uSavantStyle;
uniform float uTextureScale, uRelief, uGlow;
uniform vec3 uSavantAccent, uAccent2;
varying vec3 vSavantCell;

/* Lattice values are interpolated with a C2-continuous quintic curve.
 * No cell hash is ever displayed directly as a surface color or normal. */
float smoothHash(vec3 p) {
 p=fract(p*.1031);
 p+=dot(p,p.yzx+33.33);
 return fract((p.x+p.y)*p.z);
}
float smoothNoise(vec3 p) {
 vec3 i=floor(p),f=fract(p);
 f=f*f*f*(f*(f*6.0-15.0)+10.0);
 return mix(mix(mix(smoothHash(i),smoothHash(i+vec3(1,0,0)),f.x),
 mix(smoothHash(i+vec3(0,1,0)),smoothHash(i+vec3(1,1,0)),f.x),f.y),
 mix(mix(smoothHash(i+vec3(0,0,1)),smoothHash(i+vec3(1,0,1)),f.x),
 mix(smoothHash(i+vec3(0,1,1)),smoothHash(i+vec3(1,1,1)),f.x),f.y),f.z);
}
/* Attenuate subpixel frequencies instead of letting them alias into pixels. */
float filteredWave(float phase) {
 float footprint=fwidth(phase);
 return .5+.5*sin(phase)*exp(-.5*footprint*footprint);
}
float filteredLine(float phase,float width) {
 float footprint=max(fwidth(phase)*.5,.002);
 float distance=abs(sin(phase*.5));
 float line=1.0-smoothstep(width,width+footprint,distance);
 float average=2.0*asin(clamp(width,0.0,.95))/3.14159265;
 return mix(line,average,smoothstep(.35,1.5,footprint));
}
vec3 field(vec3 position) {
 vec3 p=position*uTextureScale*.42;
 float footprint=max(length(dFdx(p)),length(dFdy(p)));
 float detail=1.0-smoothstep(.22,.9,footprint);
 float t=uSavantTime*.1,s=uSavantStyle;
 float n=smoothNoise(p*.65),m=smoothNoise(p*.23+4.2);
 float h=.5,ink=0.0,glow=0.0;
 if(s<.5) {
   h=.5+(m-.5)*.18; ink=filteredLine(p.x*.45+p.y*.3,.035)*.065;
 } else if(s<1.5) {
   h=n; ink=filteredLine(p.x*.7+p.y*.4+m*4.0,.055)*.65;
 } else if(s<2.5) {
   h=m*.6+n*.4; ink=filteredLine(h*16.0,.065)*.65; glow=ink*.55;
 } else if(s<3.5) {
   h=filteredWave(p.x*2.0+sin(p.y*.35)); ink=h*.12;
   glow=filteredWave(p.y*.2+t)*.025;
 } else if(s<4.5) {
   h=filteredWave(p.y*.75+m*3.0); ink=filteredLine(p.y*.75+m*3.0,.14)*.35;
 } else if(s<5.5) {
   h=n; ink=filteredLine(p.x*.6+sin(p.y*.7)+m*2.0,.13)*
    filteredWave(p.z*.5+p.y*.3); glow=ink*.65;
 } else if(s<6.5) {
   h=filteredWave(p.x*.45+sin(p.y*.4+t)+p.z*.3);
   ink=.25+h*.4; glow=h*.08;
 } else if(s<7.5) {
   h=n; ink=max(filteredLine(p.x*.8+sin(p.y*.2),.055),
    filteredLine(p.y*.8+sin(p.z*.25),.055))*smoothstep(.3,.7,m); glow=ink*.55;
 } else if(s<8.5) {
   h=m*.55+n*.45; ink=smoothstep(.25,.75,h)*.75;
 } else if(s<9.5) {
   h=filteredWave(p.x*.35+sin(p.y*.5+t)+m*2.0);
   ink=h*.65; glow=filteredWave(p.z*.3+t)*.04;
 } else if(s<10.5) {
   h=filteredWave(length(p.xz)*1.5+m*3.0);
   ink=filteredLine(length(p.xz)*1.5+m*3.0,.2)*.45;
 } else if(s<11.5) {
   float warp=filteredWave(p.x*2.0),weft=filteredWave(p.y*2.0);
   h=warp*weft; ink=h*.4;
 } else if(s<12.5) {
   h=filteredWave(p.x*.65+p.z*.35+sin(p.y*.3));
   ink=smoothstep(.18,.82,h)*.6; glow=filteredLine(p.y*.45+p.z*.5,.04)*.15;
 } else if(s<13.5) {
   h=m; ink=max(filteredLine(p.x*.7,.04),filteredLine(p.y*.7,.04))*.6; glow=ink*.6;
 } else if(s<14.5) {
   h=n*.45+m*.55; ink=smoothstep(.2,.8,h)*.8;
 } else if(s<15.5) {
   h=filteredWave(length(p.xy+vec2(sin(p.z*.3),cos(p.z*.3)))*.75);
   ink=h*.5;
 } else if(s<16.5) {
   h=filteredWave(p.y*.8+sin(p.x*.2)*1.2);
   ink=h*.3; glow=filteredLine(p.y*.8+sin(p.x*.2)*1.2,.035)*.12;
 } else if(s<17.5) {
   float a=filteredWave(p.x*.8),b=filteredWave(p.x*.4+p.y*.69282);
   float c=filteredWave(p.x*.4-p.y*.69282);
   h=(a+b+c)/3.0; ink=smoothstep(.35,.75,h)*.65; glow=ink*.12;
 } else if(s<18.5) {
   h=n; ink=filteredLine(p.y*.9,.12)*smoothstep(.2,.8,m); glow=ink*.7;
 } else {
   h=smoothNoise(p*.18+vec3(0,t*.4,0));
   ink=filteredLine(h*20.0,.1)*.55; glow=ink*.25;
 }
 /* Gradual filtering retains broad pigment while fine detail resolves away. */
 return vec3(mix(.5,h,detail),clamp(ink*detail,0.0,1.0),
   clamp(glow*detail,0.0,1.0));
}
`
/* Both color and depth passes preserve a closed, opaque surface. */
export function installSurface(material: MeshPhysicalMaterial|MeshDepthMaterial,
 u:EffectUniforms, unit:number) {
 material.onBeforeCompile=shader=>{
  Object.assign(shader.uniforms,u,{uSavantUnit:{value:unit}})
  shader.vertexShader=shader.vertexShader.replace("#include <common>",
   "#include <common>\nuniform float uSavantTime,uSavantGlitch,uSavantUnit;\nvarying vec3 vSavantCell;")
   .replace("#include <begin_vertex>",`#include <begin_vertex>
    vSavantCell=position/uSavantUnit;
    float bend=sin(vSavantCell.y*31.0+floor(uSavantTime*24.0));
    transformed.x+=bend*uSavantGlitch*uSavantUnit*.014;
    transformed.z+=sin(vSavantCell.y*19.0)*uSavantGlitch*uSavantUnit*.006;`)
  if(material instanceof MeshPhysicalMaterial) {
   shader.fragmentShader=shader.fragmentShader
    .replace("#include <common>","#include <common>\n"+surfaceFields)
    .replace("#include <color_fragment>",`#include <color_fragment>
      vec3 surface=field(vSavantCell);
      vec3 pigment=mix(uAccent2,uSavantAccent,surface.x);
      diffuseColor.rgb=mix(diffuseColor.rgb,pigment,surface.y*.8);
    `)
    .replace("#include <roughnessmap_fragment>",`#include <roughnessmap_fragment>
      roughnessFactor=clamp(roughnessFactor+(surface.x-.5)*.055,.035,.98);`)
    .replace("#include <emissivemap_fragment>",`#include <emissivemap_fragment>
      float sweep=pow(max(0.0,cos(atan(vSavantCell.y,vSavantCell.x)-uSavantTime*1.3)),40.0);
      float rim=pow(1.0-abs(dot(normal,normalize(vViewPosition))),3.0);
      float glitchBand=step(.7,fract(vSavantCell.y*25.0+uSavantTime*8.0));
      totalEmissiveRadiance+=uSavantAccent*(surface.z*uGlow+sweep*rim*.6+
        glitchBand*uSavantGlitch*.25);
    `)
  }
 }
 material.customProgramCacheKey=()=>material instanceof MeshPhysicalMaterial?
   "savant-smooth-surface-atlas-v5":"savant-opaque-glitch-depth-v4"
}
