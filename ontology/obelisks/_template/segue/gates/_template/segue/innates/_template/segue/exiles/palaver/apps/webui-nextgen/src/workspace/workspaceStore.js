const KEY = "palaver.workspace"

export function loadWorkspace() {
  try {
    return JSON.parse(
      localStorage.getItem(KEY)
    ) || {
      tabs: [],
      active: null,
    }
  } catch {
    return {
      tabs: [],
      active: null,
    }
  }
}

export function saveWorkspace(state) {
  localStorage.setItem(
    KEY,
    JSON.stringify(state)
  )
}
