import {useEffect,useRef} from "react"
import {useFrame,useThree} from "@react-three/fiber"
import {getEffectBudget,type EffectBudget} from "./savant-effect-budgets"
import {evaluateQuality,pixelRatioCap} from "./savant-quality-policy"
import type {SceneQualityTier,QualitySample} from "./savant-quality-policy"
export {qualityTier} from "./savant-quality-policy"
export type {SceneQualityTier} from "./savant-quality-policy"
export type SceneBudgetProps={active:boolean;onQualityChange?:(tier:SceneQualityTier)=>void;onEffectBudgetChange?:(budget:EffectBudget)=>void}
export function SceneBudget({active,onQualityChange,onEffectBudgetChange}:SceneBudgetProps){
 const {gl,setDpr,size}=useThree()
 const callbacks=useRef({onQualityChange,onEffectBudgetChange})
 const state=useRef({cap:1,tier:"cinematic" as SceneQualityTier})
 const stats=useRef<QualitySample>({elapsed:0,frames:0,slow:0,fast:0,cooldown:0})
 const visible=useRef(true)
 useEffect(()=>{callbacks.current={onQualityChange,onEffectBudgetChange}},[onQualityChange,onEffectBudgetChange])
 useEffect(()=>{
  const cap=pixelRatioCap(size.width,size.height,window.devicePixelRatio||1)
  state.current.cap=cap
  setDpr(Math.min(gl.getPixelRatio(),cap))
  stats.current={elapsed:0,frames:0,slow:0,fast:0,cooldown:0}
 },[gl,setDpr,size.width,size.height])
 useEffect(()=>{
  const update=()=>{visible.current=!document.hidden;stats.current={elapsed:0,frames:0,slow:0,fast:0,cooldown:0}}
  update();document.addEventListener("visibilitychange",update)
  return()=>document.removeEventListener("visibilitychange",update)
 },[])
 useFrame((_,delta)=>{
  if(!active||!visible.current){stats.current.elapsed=0;stats.current.frames=0;return}
  const next=evaluateQuality(stats.current,delta,state.current.tier,gl.getPixelRatio(),state.current.cap)
  if(!next)return
  if(Math.abs(next.dpr-gl.getPixelRatio())>.025)setDpr(next.dpr)
  if(next.tier!==state.current.tier){
   state.current.tier=next.tier
   callbacks.current.onQualityChange?.(next.tier)
   callbacks.current.onEffectBudgetChange?.(getEffectBudget(next.tier))
  }
 },-1)
 return null
}
