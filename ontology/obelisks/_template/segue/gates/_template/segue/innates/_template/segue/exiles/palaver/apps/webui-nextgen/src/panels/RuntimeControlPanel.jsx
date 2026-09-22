import { useState } from "react"

const API = "http://127.0.0.1:8787"

async function get(path){
  const res = await fetch(API + path)
  return await res.json()
}

export default function RuntimeControlPanel(){
  const [title,setTitle] = useState("Runtime")
  const [data,setData] = useState(null)

  async function load(name,path){
    setTitle(name)
    try{
      const result = await get(path)
      setData(result)
    }catch(e){
      setData({ok:false,error:String(e)})
    }
  }

  return (
    <div className="trace">
      <b>{title}</b>

      <div style={{
        display:"grid",
        gridTemplateColumns:"repeat(2,1fr)",
        gap:"8px",
        margin:"12px 0"
      }}>
        <button onClick={()=>load("Runtime","/api/runtime")}>Runtime</button>
        <button onClick={()=>load("Repository","/api/repository/files")}>Repository</button>
        <button onClick={()=>load("Agents","/api/agents/jobs")}>Agents</button>
        <button onClick={()=>load("Timeline","/api/timeline")}>Timeline</button>
      </div>

      <pre>{data ? JSON.stringify(data,null,2).slice(0,12000) : "ready"}</pre>
    </div>
  )
}
