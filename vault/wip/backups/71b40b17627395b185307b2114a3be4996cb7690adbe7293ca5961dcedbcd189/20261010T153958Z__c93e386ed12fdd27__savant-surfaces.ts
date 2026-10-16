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
float shash(vec3 p) { return fract(sin(dot(p,vec3(127.1,311.7,74.7)))*43758.5453); }
float snoise(vec3 p) {
 vec3 i=floor(p), f=fract(p); f=f*f*(3.0-2.0*f);
 return mix(mix(mix(shash(i),shash(i+vec3(1,0,0)),f.x),
 mix(shash(i+vec3(0,1,0)),shash(i+vec3(1,1,0)),f.x),f.y),
 mix(mix(shash(i+vec3(0,0,1)),shash(i+vec3(1,0,1)),f.x),
 mix(shash(i+vec3(0,1,1)),shash(i+vec3(1,1,1)),f.x),f.y),f.z);
}
float stripe(float x,float width) {
 float d=abs(fract(x)-0.5);
 return 1.0-smoothstep(width,width+max(fwidth(x),0.002),d);
}
vec3 field(vec3 p) {
 p*=uTextureScale;
 float t=uSavantTime*.1, s=uSavantStyle;
 float n=snoise(p), m=snoise(p*.37+4.2);
 float h=0.0, ink=0.0, glow=0.0;
 if(s<.5) { h=shash(floor(p)); ink=stripe(p.x+p.y*.65,.025); glow=ink*.1; }
 else if(s<1.5) { h=abs(sin(p.x+m*8.0)*sin(p.y*.8+n)); ink=1.0-smoothstep(.025,.1,h); }
 else if(s<2.5) { h=n*.7+snoise(p*2.0)*.3; ink=1.0-smoothstep(.03,.14,abs(h-.48)); glow=ink; }
 else if(s<3.5) { h=sin(p.x*3.0+sin(p.y*.4))*.5+.5; ink=stripe(p.y+h*.3,.12)*.2; glow=pow(h,12.0)*.18; }
 else if(s<4.5) { h=sin(p.y+m*5.0)*.5+.5; ink=stripe(p.y+m*5.0,.08); }
 else if(s<5.5) { h=n; ink=pow(1.0-abs(sin(p.x+sin(p.y*1.3))*sin(p.z+sin(p.x))),8.0); glow=ink*(.7+.3*sin(t+p.y)); }
 else if(s<6.5) { h=sin(p.x*.7+sin(p.y*.6+t))*sin(p.z*.8-p.y); ink=h*.5+.5; glow=stripe(p.x+p.y+t,.035)*.3; }
 else if(s<7.5) { h=shash(floor(p)); ink=max(stripe(p.x,.03),stripe(p.y,.03))*step(.45,h); glow=ink; }
 else if(s<8.5) { h=n*.6+m*.4; ink=smoothstep(.35,.65,h); }
 else if(s<9.5) { h=sin(p.x*.6+sin(p.y*.7+t)+m*3.0)*.5+.5; ink=h; glow=pow(h,14.0)*.3; }
 else if(s<10.5) { h=sin(length(p.xz)*3.0+m*5.0)*.5+.5; ink=pow(h,7.0); }
 else if(s<11.5) { vec2 c=floor(p.xy); h=mod(c.x+c.y,2.0); ink=mix(stripe(p.x,.3),stripe(p.y,.3),h); h=ink; }
 else if(s<12.5) { h=shash(floor(p+sin(p.yzx)*.3)); ink=smoothstep(.2,.8,h); glow=stripe(p.x+p.z,.018)*.4; }
 else if(s<13.5) { h=n*.2; ink=max(stripe(p.x,.025),stripe(p.y,.025)); glow=ink; }
 else if(s<14.5) { h=n*.5+snoise(p*3.0)*.5; ink=smoothstep(.3,.7,m); }
 else if(s<15.5) { h=sin(length(p.xy+vec2(sin(p.z),cos(p.z)))*1.4)*.5+.5; ink=pow(h,5.0); }
 else if(s<16.5) { h=sin(p.y+sin(p.x*.2)*2.0)*.5+.5; ink=pow(h,12.0); glow=ink*.35; }
 else if(s<17.5) { vec2 q=vec2(p.x*.866,p.y+.5*floor(p.x*.866)); vec2 c=fract(q)-.5; h=max(abs(c.x),abs(c.y)*.866+abs(c.x)*.5); ink=smoothstep(.33,.46,h); glow=ink*.4; }
 else if(s<18.5) { h=shash(floor(p)); ink=stripe(p.y,.18)*step(.2,h); glow=ink; }
 else { h=snoise(p*.25+vec3(0,t,0)); ink=stripe(h*14.0,.07); glow=ink*.5; }
 return vec3(h,clamp(ink,0.0,1.0),clamp(glow,0.0,1.0));
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
      roughnessFactor=clamp(roughnessFactor+(surface.x-.5)*.2,.035,.98);`)
    .replace("#include <normal_fragment_maps>",`#include <normal_fragment_maps>
      vec3 dp1=dFdx(vViewPosition),dp2=dFdy(vViewPosition);
      vec3 r1=cross(dp2,normal),r2=cross(normal,dp1);
      float det=dot(dp1,r1);
      float dh1=dFdx(surface.x),dh2=dFdy(surface.x);
      if(abs(det)>0.00000001) normal=normalize(abs(det)*normal-sign(det)*(dh1*r1+dh2*r2)*uRelief);
    `)
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
   "savant-surface-atlas-v4":"savant-opaque-glitch-depth-v4"
}
