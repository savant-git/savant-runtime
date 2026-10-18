type ApiPayload={ok?:boolean;error?:string;[key:string]:any}
/** Same-origin transport: the server routes this prefix to the loopback PTY bridge. */
export async function terminalApi(path:string,options:RequestInit={}):Promise<ApiPayload>{
 if(!path.startsWith("/api/terminal/"))throw new Error("invalid terminal route")
 const controller=new AbortController(),timer=setTimeout(()=>controller.abort(),10000)
 try{
  const response=await fetch(path,{...options,credentials:"same-origin",cache:"no-store",signal:controller.signal})
  if(!response.headers.get("content-type")?.includes("application/json")){
   throw new Error("terminal bridge routing unavailable (HTTP "+response.status+"); start the bridge and use the terminal-enabled Vite configuration")
  }
  const payload=await response.json()
  if(!payload||typeof payload!=="object")throw new Error("invalid terminal response")
  if(!response.ok||payload.ok===false)throw new Error(typeof payload.error==="string"?payload.error.slice(0,240):"terminal request failed: "+response.status)
  return payload
 }catch(error){
  if(error instanceof Error&&error.name==="AbortError")throw new Error("terminal bridge timed out")
  throw error
 }finally{clearTimeout(timer)}
}
