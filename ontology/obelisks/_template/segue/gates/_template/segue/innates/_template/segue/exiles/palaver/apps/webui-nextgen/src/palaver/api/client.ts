export const API_BASE =
  String(
    import.meta.env.VITE_PALAVER_API_BASE || ""
  ).replace(/\/+$/, "")

export async function getJson<T = any>(
  path: string
): Promise<T | null> {
  try {
    const normalizedPath =
      path.startsWith("/") ? path : `/${path}`

    const response = await fetch(
      `${API_BASE}${normalizedPath}`
    )

    if (!response.ok) return null

    return await response.json()
  } catch {
    return null
  }
}
