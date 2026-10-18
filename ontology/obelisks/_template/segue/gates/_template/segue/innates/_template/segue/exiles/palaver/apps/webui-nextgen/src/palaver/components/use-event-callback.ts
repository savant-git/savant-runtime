import {useCallback,useLayoutEffect,useRef} from "react"
/** Stable event identity with the latest committed closure, never a second state store. */
export function useEventCallback<A extends unknown[],R>(handler:(...args:A)=>R){
 const current=useRef(handler)
 useLayoutEffect(()=>{current.current=handler},[handler])
 return useCallback((...args:A)=>current.current(...args),[])
}
