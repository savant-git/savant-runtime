import {Color,InstancedBufferAttribute,MeshStandardMaterial} from "three"
export const contourTailSamples=24
export const trailGold="#d6b45f",trailPink="#ff2f9d"
export function trailAgeAttribute(count:number,samples:number){
 return new InstancedBufferAttribute(Float32Array.from({length:count*samples},
  (_,index)=>(index%samples+.5)/samples),1)
}
export function trailFade(age:number){return Math.pow(Math.max(0,1-Math.min(1,age)),1.65)}
export function trailPinkMix(age:number){
 const t=Math.max(0,Math.min(1,(age-.46)/.08));return t*t*(3-2*t)
}
/** Smooth PBR trail color/opacity; never installed on the opaque logo body. */
export function installTrailSurface(material:MeshStandardMaterial,axial=false){
 const gold={value:new Color(trailGold)},pink={value:new Color(trailPink)}
 material.userData.savantTrailPalette={gold,pink}
 material.color.set("#ffffff");material.emissive.set("#ffffff")
 material.transparent=true;material.depthWrite=false;material.opacity=.9
 material.onBeforeCompile=shader=>{
  shader.uniforms.savantTrailGold=gold;shader.uniforms.savantTrailPink=pink
  shader.vertexShader=shader.vertexShader.replace("#include <common>",
   "#include <common>\nvarying float vSavantTrailAge;\n"+(axial?"":"attribute float aSavantTrailAge;"))
  shader.vertexShader=shader.vertexShader.replace("#include <begin_vertex>",
   "#include <begin_vertex>\nvSavantTrailAge="+(axial?"1.0-uv.y;":"aSavantTrailAge;"))
  shader.fragmentShader=shader.fragmentShader.replace("#include <common>",
   `#include <common>
varying float vSavantTrailAge;
uniform vec3 savantTrailGold,savantTrailPink;
vec3 savantTrailColor(){
 return mix(savantTrailGold,savantTrailPink,smoothstep(.46,.54,vSavantTrailAge));
}`)
  shader.fragmentShader=shader.fragmentShader.replace("#include <color_fragment>",
   `#include <color_fragment>
diffuseColor.rgb*=savantTrailColor();
diffuseColor.a*=pow(clamp(1.0-vSavantTrailAge,0.0,1.0),1.65);`)
  shader.fragmentShader=shader.fragmentShader.replace("#include <emissivemap_fragment>",
   "#include <emissivemap_fragment>\ntotalEmissiveRadiance*=savantTrailColor();")
 }
 material.customProgramCacheKey=()=>axial?"savant-gold-pink-trail-v1-axial":"savant-gold-pink-trail-v1-instanced"
 material.needsUpdate=true
}

export function setTrailPalette(material:MeshStandardMaterial,start:string,end:string){
 const palette=material.userData.savantTrailPalette as
  {gold:{value:Color};pink:{value:Color}}|undefined
 palette?.gold.value.set(start);palette?.pink.value.set(end)
}
