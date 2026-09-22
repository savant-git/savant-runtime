const API = "http://127.0.0.1:8787"

async function get(path) {
  const res = await fetch(API + path)
  return await res.json()
}

export const runtimeStatus = () => get("/api/runtime")
export const repositoryFiles = () => get("/api/repository/files")
export const memoryFiles = () => get("/api/memory/files")
export const agentJobs = () => get("/api/agents/jobs")
