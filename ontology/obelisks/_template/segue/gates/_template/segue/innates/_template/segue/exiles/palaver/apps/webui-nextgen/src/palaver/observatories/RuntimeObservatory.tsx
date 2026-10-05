import { useEffect, useState } from "react"
import { loadRuntimeState } from "../runtime/runtime-state"

export default function RuntimeObservatory(){

  const [state,setState] = useState<any>(null)

  useEffect(()=>{

    let mounted = true

    async function tick(){

      const next =
        await loadRuntimeState()

      if(mounted){
        setState(next)
      }
    }

    tick()

    const id =
      setInterval(tick,5000)

    return ()=>{
      mounted=false
      clearInterval(id)
    }

  },[])

  if(!state){
    return (
      <div className="runtime-loading">
        loading runtime
      </div>
    )
  }

  return (
    <section className="runtime-observatory">

      <h1>
        Runtime Observatory
      </h1>

      <div className="runtime-grid">

        {Object.entries(state)
          .filter(([k])=>k!=="timestamp")
          .map(([k,v])=>(
            <div
              key={k}
              className="runtime-card"
            >
              <span>{k}</span>
              <strong>{String(v)}</strong>
            </div>
          ))}

      </div>

    </section>
  )
}
