import {useCallback,useEffect,useState} from "react"
import {MeshPhysicalMaterial} from "three"
import {applyAppearance,legacyPresetIds,materialPresets,palaverHybrid} from "./savant-surfaces"
import {artDirectionFor,artDirections} from "./savant-art-direction"
import type {MaterialPreset} from "./savant-surfaces"

const storageKey="savant-logo-material-v1",eventName="savant-logo-material"
export const blackChrome:MaterialPreset={
 ...palaverHybrid,id:"black-chrome",name:"black chrome · cinematic",
 color:"#515963",roughness:.19,metalness:1,
 description:"Current reflective black chrome with gold contour and cinematic lighting.",
 optics:{...palaverHybrid.optics,transmission:0,dispersion:0,iridescence:0,sheen:0,
  anisotropy:0,coat:1,emission:0},
 scene:{...palaverHybrid.scene,energy:1.35},
}
const artMaterials:MaterialPreset[]=artDirections.map(profile=>{
 const base=materialPresets.find(p=>p.style===profile.kind)||palaverHybrid
 return {...base,id:"rider-iso-"+String(profile.kind+1).padStart(2,"0"),
  name:String(profile.kind+1).padStart(2,"0")+" · "+profile.name,
  style:profile.kind,color:profile.paper,accent:profile.accent,accent2:profile.secondary,
  roughness:profile.rough,metalness:profile.metal,description:profile.summary,
  optics:{...base.optics,transmission:0,dispersion:0,anisotropy:0,
   iridescence:profile.kind===3?.45:profile.kind===9?.2:0,sheen:profile.sheen,coat:profile.coat,emission:0}}
})
export const logoMaterials:readonly MaterialPreset[]=artMaterials
export function resolveLogoMaterial(id:string){
 const canonical=legacyPresetIds[id]||id
 const direct=logoMaterials.find(option=>option.id===canonical)
 if(direct)return direct
 const previous=/^art-v3-(\d+)$/.exec(canonical)
 if(previous)return artMaterials[(Math.max(1,Number(previous[1]))-1)%artMaterials.length]
 const old=materialPresets.find(option=>option.id===canonical)
 if(old&&old.id!==palaverHybrid.id)return artMaterials[Math.max(0,old.style)%artMaterials.length]
 return artMaterials[0]
}
function storedMaterial(){
 try{return resolveLogoMaterial(localStorage.getItem(storageKey)||artMaterials[0].id).id}
 catch{return artMaterials[0].id}
}
export function useLogoMaterial(){
 const [id,setId]=useState(storedMaterial)
 useEffect(()=>{
  const storage=(event:StorageEvent)=>{
   if(event.key===null||event.key===storageKey)setId(storedMaterial())
  }
  const custom=(event:Event)=>{
   const id=(event as CustomEvent<unknown>).detail
   if(typeof id==="string")setId(resolveLogoMaterial(id).id)
  }
  window.addEventListener("storage",storage)
  window.addEventListener(eventName,custom)
  return()=>{window.removeEventListener("storage",storage);window.removeEventListener(eventName,custom)}
 },[])
 const choose=useCallback((next:string)=>{
  if(!logoMaterials.some(option=>option.id===next))return
  setId(next)
  try{localStorage.setItem(storageKey,next)}catch{}
  window.dispatchEvent(new CustomEvent(eventName,{detail:next}))
 },[])
 return {preset:resolveLogoMaterial(id),choose}
}
/** Reuse the authoritative catalog's optical parameters, not its former surface-field shader. */
export function applyLogoAppearance(material:MeshPhysicalMaterial,preset:MaterialPreset){
 applyAppearance(material,preset)
 // The supplied logo has no UVs/tangents. Do not enable UV-derived anisotropy.
 material.anisotropy=0
 material.clearcoatRoughness=preset.id===blackChrome.id?.13:.1
 material.opacity=1;material.transparent=false;material.depthWrite=true
 const profile=artDirectionFor(preset)
 if(profile.kind>=0){
  material.color.set(profile.paper);material.metalness=profile.metal
  material.roughness=profile.rough;material.clearcoat=profile.coat
  material.clearcoatRoughness=Math.max(.08,profile.rough*.55)
  material.sheen=profile.sheen;material.sheenColor.set(profile.secondary)
  material.emissive.set(profile.accent);material.emissiveIntensity=profile.emission*.17
  material.transmission=0
 }
 material.name="savant-rider-isometric-v1:"+preset.id
}
export function MaterialPicker({preset,choose}:{preset:MaterialPreset;choose:(id:string)=>void}){
 return <label className="savant-material-picker">
  <span>surface laboratory</span>
  <select aria-label="savant logo PBR material" title={artDirectionFor(preset).summary}
   value={preset.id} onChange={event=>choose(event.target.value)}>
   {logoMaterials.map(option=><option key={option.id} value={option.id}
    title={artDirectionFor(option).summary}>{option.name}</option>)}
  </select>
 </label>
}
