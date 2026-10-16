const API = "http://127.0.0.1:8787"

async function request(path, options = {}) {
  const res = await fetch(API + path, options)

  let data = null

  try {
    data = await res.json()
  } catch {
    data = {
      ok: false,
      error: "non-json response",
    }
  }

  if (!res.ok) {
    return {
      ok: false,
      status: res.status,
      ...data,
    }
  }

  return data
}

export function chat(message) {
  return request("/api/chat", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({message}),
  })
}

export function health() {
  return request("/api/health")
}

export function tree(path = "") {
  return request("/api/tree?path=" + encodeURIComponent(path))
}

export function readFile(path) {
  return request("/api/file?path=" + encodeURIComponent(path))
}

export function saveFile(path, content) {
  return request("/api/file/save", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({path, content}),
  })
}

export function diffFile(path, content) {
  return request("/api/file/diff", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({path, content}),
  })
}

export function graph() {
  return request("/api/graph")
}

export function timeline() {
  return request("/api/timeline")
}

export function runtime() {
  return request("/api/runtime")
}

export function repositoryFiles() {
  return request("/api/repository/files")
}

export function memoryFiles() {
  return request("/api/memory/files")
}

export function agentJobs() {
  return request("/api/agents/jobs")
}

export function saveWorkspace(payload) {
  return request("/api/workspace/save", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify(payload),
  })
}


export function memorySearch(
  query
){
  return request(
    "/api/memory/search?q=" +
    encodeURIComponent(
      query
    )
  )
}
