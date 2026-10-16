import { create } from "zustand"

type LayoutState={left:number;center:number;right:number;save:(l:number,c:number,r:number)=>void}
const initial={left:18,center:64,right:18}
const normalize=(left:number,center:number,right:number)=>{
 const values=[left,center,right]
 if(values.some(v=>!Number.isFinite(v)||v<0))return initial
 const total=left+center+right
 if(total<=0)return initial
 if(values.every(v=>v>=5)&&Math.abs(total-100)<.001)return {left,center,right}
 const min=5
 const flexible=100-min*3
 const weights=values.map(v=>Math.max(0,v))
 const sum=weights.reduce((a,b)=>a+b,0)
 return {left:min+flexible*weights[0]/sum,center:min+flexible*weights[1]/sum,right:min+flexible*weights[2]/sum}
}
export const useLayoutStore=create<LayoutState>(set=>({
 ...initial,
 save:(left,center,right)=>set(normalize(left,center,right))
}))
