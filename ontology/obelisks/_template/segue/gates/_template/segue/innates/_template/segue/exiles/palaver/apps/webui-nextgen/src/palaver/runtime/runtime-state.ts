export type RuntimeState = {
  authority:number
  lineage:number
  dependencies:number
  relationships:number
  repositories:number
  memories:number
  ontology:number
  timestamp:string
}

export async function loadRuntimeState():Promise<RuntimeState>{

  try{

    const r = await fetch(
      "http://127.0.0.1:8787/api/dashboard/state"
    )

    if(r.ok){
      return await r.json()
    }

  }catch{}

  return {
    authority:0,
    lineage:0,
    dependencies:0,
    relationships:0,
    repositories:0,
    memories:0,
    ontology:0,
    timestamp:new Date().toISOString()
  }
}
