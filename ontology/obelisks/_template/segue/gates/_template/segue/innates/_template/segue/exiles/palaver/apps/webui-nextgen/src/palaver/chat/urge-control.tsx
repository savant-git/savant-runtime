import {lazy,Suspense,useId,useRef,useState} from "react"
import {Orbit} from "../components/savant-glyphs"
import type {UrgeControlProps} from "./urge-types"
export type {UrgePersona,UrgeRequest,UrgeExtendedRequest,UrgePersonaMode} from "./urge-types"
const UrgeDialog=lazy(()=>import("./urge-dialog"))
/** Reusable entry projection. Configuration is retained after the first opening. */
export default function UrgeControl(props:UrgeControlProps){
 const [open,setOpen]=useState(false),[activated,setActivated]=useState(false)
 const trigger=useRef<HTMLButtonElement>(null),id=useId()
 return <div className="urge-control">
  <button ref={trigger} type="button" className="urge-trigger"
   title="Configure urge iteration" aria-label="Configure urge" aria-expanded={open}
   aria-haspopup="dialog" aria-controls={open?id:undefined}
   onClick={()=>{setActivated(true);setOpen(value=>!value)}}>
   <Orbit size={14}/><span>urge</span>
  </button>
  {activated&&<Suspense fallback={null}>
   <UrgeDialog {...props} dialogId={id} open={open} setOpen={setOpen} trigger={trigger}/>
  </Suspense>}
 </div>
}
