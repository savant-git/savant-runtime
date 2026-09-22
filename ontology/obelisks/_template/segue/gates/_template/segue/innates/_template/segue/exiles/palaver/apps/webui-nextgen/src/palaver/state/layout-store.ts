import { create } from "zustand"

type LayoutState = {
  left:number
  center:number
  right:number
  save:(
    l:number,
    c:number,
    r:number
  )=>void
}

export const useLayoutStore =
create<LayoutState>((set)=>({

  left:18,
  center:64,
  right:18,

  save:(left,center,right)=>
    set({
      left,
      center,
      right
    })

}))
