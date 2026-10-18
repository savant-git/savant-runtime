import {defineConfig,loadConfigFromFile,mergeConfig} from "vite"
import react from "@vitejs/plugin-react"
import {fileURLToPath} from "node:url"
import {dirname} from "node:path"
const root=dirname(fileURLToPath(import.meta.url))
/** Explicit opt-in entry: preserve the normal project configuration when present. */
export default defineConfig(async env=>{
 const original=await loadConfigFromFile(env,undefined,root)
 const base=original?.config||{plugins:[react()]}
 const config=mergeConfig(base,{
  server:{host:"127.0.0.1",port:5173,strictPort:true,
   proxy:{"/api/terminal":{target:"http://127.0.0.1:8788",changeOrigin:false,
    configure(proxy){proxy.on("error",(_error,_req,res)=>{
     if(!res.headersSent&&"writeHead" in res){
      res.writeHead(502,{"Content-Type":"application/json","Cache-Control":"no-store"})
      res.end(JSON.stringify({ok:false,error:"palaver PTY bridge is not running on 127.0.0.1:8788"}))
     }
    })}}}},
  preview:{host:"127.0.0.1",port:5173,strictPort:true,
   proxy:{"/api/terminal":{target:"http://127.0.0.1:8788",changeOrigin:false}}}
 })
 for(const key of ["server","preview"]){
  const routes=config[key].proxy
  config[key].proxy={"/api/terminal":routes["/api/terminal"],...Object.fromEntries(Object.entries(routes).filter(([path])=>path!=="/api/terminal"))}
 }
 return config
})
