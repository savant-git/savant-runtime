import {useCallback,useEffect,useState} from "react"
import {MeshPhysicalMaterial} from "three"
import {applyAppearance,legacyPresetIds,materialPresets,palaverHybrid} from "./savant-surfaces"
import {artDirectionFor} from "./savant-art-direction"
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
export const logoMaterials:readonly MaterialPreset[]=[blackChrome,...materialPresets]
export function resolveLogoMaterial(id:string){
 const canonical=legacyPresetIds[id]||id
 return logoMaterials.find(option=>option.id===canonical)||blackChrome
}
function storedMaterial(){
 try{return resolveLogoMaterial(localStorage.getItem(storageKey)||blackChrome.id).id}
 catch{return blackChrome.id}
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
 material.name="savant-selectable-pbr-v1:"+preset.id
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
