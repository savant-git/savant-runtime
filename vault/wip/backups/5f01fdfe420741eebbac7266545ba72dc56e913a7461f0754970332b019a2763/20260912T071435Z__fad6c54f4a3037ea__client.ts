export const API_BASE =
  import.meta.env.VITE_PALAVER_API_BASE || "http://127.0.0.1:8787"

export async function getJson<T = any>(
  path: string
): Promise<T | null> {
  try {
    const response = await fetch(`${API_BASE}${path}`)
    if (!response.ok) return null
    return await response.json()
  } catch {
    return null
  }
}
