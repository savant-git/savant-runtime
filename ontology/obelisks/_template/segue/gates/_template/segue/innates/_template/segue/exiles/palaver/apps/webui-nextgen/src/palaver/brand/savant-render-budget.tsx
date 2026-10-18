import {useLayoutEffect,useRef} from "react"
import {useFrame,useThree} from "@react-three/fiber"
import {createRenderQuality,pixelCeiling,sampleRenderQuality} from "./savant-render-quality"
/** No React state updates per frame. Inactive demand-mode frames are never sampled. */
export function SavantRenderBudget({moving}:{moving:boolean}){
 const {size,setDpr,invalidate}=useThree()
 const policy=useRef(createRenderQuality(1))
 useLayoutEffect(()=>{
  const ceiling=pixelCeiling(size.width,size.height,window.devicePixelRatio||1)
  policy.current=createRenderQuality(ceiling);setDpr(ceiling);invalidate()
 },[size.width,size.height,setDpr,invalidate])
 useLayoutEffect(()=>{policy.current.warm=0;policy.current.slow=0;policy.current.fast=0},[moving])
 useFrame((_,delta)=>{
  if(!moving)return
  const next=sampleRenderQuality(policy.current,delta)
  if(next!==null){setDpr(next);invalidate()}
 },-4)
 return null
}
